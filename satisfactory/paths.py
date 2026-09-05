"""Where Satisfactory keeps its saves and blueprints, on whatever you run.

The game is a Windows title, so on Linux and macOS the folders live inside a
Wine prefix. The layout below the prefix is always the same:

    <prefix>/drive_c/users/<user>/AppData/Local/FactoryGame/Saved/SaveGames

and on Windows that same tail hangs off %LOCALAPPDATA%. Inside SaveGames:

    <SaveGames>/<account id>/<name>.sav      saves
    <SaveGames>/blueprints/<session name>/   the .sbp + .sbpcfg pairs

Nothing here is authoritative -- it is a search over the usual install spots.
Anything it cannot find can be passed explicitly (`--save-dir`, `--bp-dir`).
"""

import glob
import os
import platform
import re
import subprocess

APP_ID = "526870"
TAIL = os.path.join("FactoryGame", "Saved", "SaveGames")

# every Wine/Proton prefix we know how to look inside, as glob patterns
PREFIX_GLOBS = {
    "Linux": [
        # Steam + Proton, in every library folder (filled in at runtime too)
        "~/.steam/steam/steamapps/compatdata/{app}/pfx",
        "~/.local/share/Steam/steamapps/compatdata/{app}/pfx",
        "~/.var/app/com.valvesoftware.Steam/data/Steam/steamapps/compatdata/{app}/pfx",
        # Heroic / Lutris / Bottles / plain wine
        "~/Games/Heroic/Prefixes/*/*",
        "~/.config/heroic/*/Prefixes/*/*",
        "~/Games/*/satisfactory*",
        "~/.local/share/lutris/prefixes/*",
        "~/.var/app/com.usebottles.bottles/data/bottles/bottles/*",
        "~/.wine",
    ],
    "Darwin": [
        # CrossOver and Whisky are how this runs on a Mac
        "~/Library/Application Support/CrossOver/Bottles/*",
        "~/Library/Containers/com.isaacmarovitz.Whisky/Bottles/*",
        "~/Library/Application Support/com.isaacmarovitz.Whisky/Bottles/*",
        "~/Library/Application Support/Whisky/Bottles/*",
        "~/Wine/*",
    ],
}


def _expand(pattern):
    return glob.glob(os.path.expanduser(pattern.format(app=APP_ID)))


def steam_libraries():
    """Every Steam library folder, from libraryfolders.vdf."""
    roots = ["~/.steam/steam", "~/.local/share/Steam", "~/.steam/root",
             "~/.var/app/com.valvesoftware.Steam/data/Steam",
             "~/Library/Application Support/Steam",
             os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Steam")]
    out = []
    for root in roots:
        root = os.path.expanduser(root)
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if not os.path.exists(vdf):
            continue
        out.append(root)
        try:
            text = open(vdf, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        out += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', text)]
    seen, uniq = set(), []
    for p in out:
        if p not in seen and os.path.isdir(p):
            seen.add(p)
            uniq.append(p)
    return uniq


def _prefix_savegames(prefix):
    """SaveGames folders inside one Wine prefix (the user name varies)."""
    return sorted(glob.glob(os.path.join(
        prefix, "drive_c", "users", "*", "AppData", "Local", TAIL)))


def save_dirs():
    """Every SaveGames folder we can find, most likely first."""
    found = []

    local = os.environ.get("LOCALAPPDATA")
    if local:                                            # native Windows
        found.append(os.path.join(local, TAIL))

    for lib in steam_libraries():                        # Proton, any library
        found += _prefix_savegames(
            os.path.join(lib, "steamapps", "compatdata", APP_ID, "pfx"))

    for pattern in PREFIX_GLOBS.get(platform.system(), []):
        for prefix in _expand(pattern):
            found += _prefix_savegames(prefix)

    seen, out = set(), []
    for p in found:
        real = os.path.realpath(p)
        if real not in seen and os.path.isdir(p):
            seen.add(real)
            out.append(p)
    return out


def save_dir(explicit=None):
    """The one SaveGames folder to work with."""
    if explicit:
        path = os.path.expanduser(explicit)
        if not os.path.isdir(path):
            raise SystemExit(f"no such SaveGames folder: {path}")
        return path
    found = save_dirs()
    if not found:
        raise SystemExit("could not find a SaveGames folder -- pass --save-dir")
    return found[0]


def saves(savegames):
    """Every .sav under a SaveGames folder (they sit in per-account subfolders)."""
    out = sorted(glob.glob(os.path.join(savegames, "*.sav")))
    out += sorted(glob.glob(os.path.join(savegames, "*", "*.sav")))
    return [p for p in out if os.path.basename(p) != "ServerManager_V2.sav"]


def find_save(savegames, name):
    """Resolve a save by path, file name, or bare save name."""
    if os.path.isabs(name) or os.sep in name:
        path = os.path.expanduser(name)
        if not os.path.exists(path):
            raise SystemExit(f"no such save: {path}")
        return path
    wanted = name if name.endswith(".sav") else name + ".sav"
    matches = [p for p in saves(savegames) if os.path.basename(p) == wanted]
    if not matches:
        raise SystemExit(f"no save named {wanted!r} under {savegames}")
    return matches[0]


def blueprint_dirs(savegames):
    return sorted(p for p in glob.glob(os.path.join(savegames, "blueprints", "*"))
                  if os.path.isdir(p))


def blueprint_dir(savegames, session=None, explicit=None):
    """The blueprint folder of a session.

    The game names it after the session, so a save's header is enough to find
    it. A single folder is used as-is; several with no session given is
    ambiguous and asks for --bp-dir.
    """
    if explicit:
        return os.path.expanduser(explicit)
    root = os.path.join(savegames, "blueprints")
    if session:
        return os.path.join(root, session)
    dirs = blueprint_dirs(savegames)
    if len(dirs) == 1:
        return dirs[0]
    if not dirs:
        raise SystemExit(f"no blueprint folders under {root} -- pass --bp-dir")
    names = ", ".join(os.path.basename(d) for d in dirs)
    raise SystemExit(f"several blueprint folders ({names}) -- pass --bp-dir")


def game_running():
    """Is Satisfactory up? An autosave would overwrite whatever we write.

    On Linux this reads /proc directly. `pgrep -f` is no good: the pattern sits
    in the command line of the shell that runs the pgrep, so it matches itself
    and always says yes. Our own process and its parents are excluded for the
    same reason.
    """
    names = ("FactoryGameSteam.exe", "FactoryGameEGS.exe", "FactoryGame-Win64",
             "FactoryGameServer")

    if os.path.isdir("/proc"):
        mine, pid = set(), os.getpid()
        while pid > 1:
            mine.add(pid)
            try:
                stat = open(f"/proc/{pid}/stat", "rb").read()
                pid = int(stat[stat.rindex(b")") + 2:].split()[1])       # ppid
            except (OSError, ValueError, IndexError):
                break
        for entry in os.listdir("/proc"):
            if not entry.isdigit() or int(entry) in mine:
                continue
            try:
                with open(f"/proc/{entry}/cmdline", "rb") as f:
                    cmd = f.read()
            except OSError:                                  # process is gone
                continue
            if any(n.encode() in cmd for n in names):
                return True
        return False

    cmd = ["tasklist"] if os.name == "nt" else ["ps", "-A", "-o", "comm="]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return False                                         # cannot tell; assume not
    return any(n in out for n in names)
