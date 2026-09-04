#!/usr/bin/env python3
"""Правит session settings SML прямо в сейве Satisfactory.

Пример:
  python3 hf-setting.py cachys.sav HeavyFluids.Pipeline.Limit off
  python3 hf-setting.py cachys.sav HeavyFluids.Divider.Main 3
  python3 hf-setting.py cachys.sav                 # просто показать все настройки
"""
import base64, os, re, shutil, struct, sys

SAVEDIR = os.path.expanduser(
    "~/games/SteamLibrary/steamapps/compatdata/526870/pfx/drive_c/users/steamuser/"
    "AppData/Local/FactoryGame/Saved/SaveGames/76561198736176585")

BOOL, FLOAT, INT = 2, 10, 14

def decode(b64):
    raw = base64.b64decode(b64)
    tag, size = struct.unpack_from("<II", raw)
    if tag == BOOL:  return "bool", bool(struct.unpack_from("<I", raw, 8)[0])
    if tag == FLOAT: return "float", struct.unpack_from("<f", raw, 8)[0]
    if tag == INT:   return "int", struct.unpack_from("<i", raw, 8)[0]
    return f"tag{tag}", raw[8:8+size].hex()

def encode(kind, value):
    tag, packed = {
        "bool":  (BOOL,  lambda v: struct.pack("<I", 1 if v else 0)),
        "float": (FLOAT, lambda v: struct.pack("<f", float(v))),
        "int":   (INT,   lambda v: struct.pack("<i", int(v))),
    }[kind]
    return base64.b64encode(struct.pack("<II", tag, 4) + packed(value)).decode()

def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    path = args[0] if os.path.sep in args[0] else os.path.join(SAVEDIR, args[0])
    data = open(path, "rb").read()
    head = data[:40000]

    if len(args) == 1:
        for m in re.finditer(rb"([A-Za-z0-9_.]+)=([A-Za-z0-9+/]+=*),", head):
            key, val = m.group(1).decode(), m.group(2).decode()
            try:
                kind, parsed = decode(val)
            except Exception:
                continue
            print(f"{key:55} {kind:6} {parsed}")
        return

    key, new = args[1], args[2]
    m = re.search(re.escape(key.encode()) + rb"=([A-Za-z0-9+/]+=*)", head)
    if not m:
        sys.exit(f"настройка {key} в сейве не найдена")
    kind, old = decode(m.group(1).decode())

    if kind == "bool":
        new_val = new.lower() in ("1", "on", "true", "yes", "да")
    else:
        new_val = new
    new_b64 = encode(kind, new_val)
    if len(new_b64) != len(m.group(1)):
        sys.exit("длина закодированного значения изменилась — правка небезопасна")

    shutil.copy2(path, path + ".bak")
    patched = data.replace(m.group(0), key.encode() + b"=" + new_b64.encode(), 1)
    assert len(patched) == len(data)
    open(path, "wb").write(patched)
    print(f"{key}: {old} -> {decode(new_b64)[1]}   (бэкап: {os.path.basename(path)}.bak)")

main()
