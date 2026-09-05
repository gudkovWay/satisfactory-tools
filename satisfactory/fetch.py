"""Downloading blueprint packs from satisfactory-calculator.com.

Both files are fetched for every blueprint: the .sbp and the .sbpcfg. Without
the cfg the game does not show the blueprint at all.
"""

import http.client
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://satisfactory-calculator.com"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DETAILS_RE = re.compile(
    r'/blueprints/index/details/id/(\d+)/name/([^"\'<>]*)')


def fetch(url, retries=4, timeout=30):
    """GET with retries. -> (bytes, headers)."""
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 403):
                raise
            time.sleep(2 ** attempt)
    raise last


def list_url(id_user, user, page):
    return (f"{BASE}/en/blueprints/index/index/idU/{id_user}"
            f"/user/{urllib.parse.quote(user)}/p/{page}")


def collect(id_user, user, delay, max_pages=200, log=print):
    """Walk the listing pages until they stop yielding new ids.

    Asking for a page past the end returns the last one again, so "this page
    had no id we have not seen" is the only reliable stop condition."""
    seen, out = set(), []
    for page in range(1, max_pages + 1):
        html, _ = fetch(list_url(id_user, user, page))
        html = html.decode("utf-8", "replace")
        found = []
        for bp_id, slug in DETAILS_RE.findall(html):
            if bp_id not in seen:
                seen.add(bp_id)
                found.append((bp_id, slug))
        if not found:
            break
        out += found
        log(f"  page {page}: +{len(found)} (total {len(out)})")
        time.sleep(delay)
    return out


def safe_name(name):
    name = urllib.parse.unquote_plus(name).strip()
    name = re.sub(r'[\x00-\x1f/\\:*?"<>|]', "_", name)
    return name[:180] or "blueprint"


def filename_from(headers, fallback):
    cd = headers.get("Content-Disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
    return safe_name(m.group(1)) if m else fallback


def download(kind, bp_id, slug, outdir, delay, force):
    """kind: 'download' -> .sbp, 'download-cfg' -> .sbpcfg"""
    ext = ".sbp" if kind == "download" else ".sbpcfg"
    fallback = f"{safe_name(slug)}{ext}"
    url = f"{BASE}/en/blueprints/index/{kind}/id/{bp_id}/name/{slug}"

    # quick skip when a file under the expected name is already there
    guess = os.path.join(outdir, fallback)
    if not force and os.path.exists(guess) and os.path.getsize(guess) > 0:
        return "skip", fallback

    data, headers = fetch(url)
    fname = filename_from(headers, fallback)
    if not fname.lower().endswith(ext):
        fname += ext
    path = os.path.join(outdir, fname)
    if not force and os.path.exists(path) and os.path.getsize(path) == len(data):
        return "skip", fname
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    time.sleep(delay)
    return "ok", fname


def parse_target(target):
    """Accepts a full listing URL or the short '51246/sixsense' form."""
    m = re.search(r"idU/(\d+)/user/([^/?#]+)", target)
    if not m:
        m = re.fullmatch(r"(\d+)[/:]([^/?#]+)", target.strip())
    if not m:
        raise SystemExit("cannot read that target: pass a blueprint listing "
                         "URL or 'userId/username'")
    return m.group(1), urllib.parse.unquote(m.group(2))


def download_user(target, outdir, delay=1.0, force=False, with_cfg=True, log=print):
    """Fetch every blueprint a user published. -> (outdir, ok, skipped, failed)."""
    id_user, user = parse_target(target)
    outdir = outdir or os.path.join(".", safe_name(user))
    log(f"  user {user} (id {id_user})")
    items = collect(id_user, user, delay, log=log)
    log(f"  {len(items)} blueprints listed")

    os.makedirs(outdir, exist_ok=True)
    kinds = ["download"] + (["download-cfg"] if with_cfg else [])
    ok = skipped = failed = 0
    for i, (bp_id, slug) in enumerate(items, 1):
        title = urllib.parse.unquote_plus(slug)
        parts = []
        for kind in kinds:
            try:
                status, fname = download(kind, bp_id, slug, outdir, delay, force)
                parts.append("new" if status == "ok" else "have")
                ok += status == "ok"
                skipped += status == "skip"
            except Exception as e:                       # noqa: BLE001 -- report and go on
                parts.append(f"FAILED ({e})")
                failed += 1
        log(f"  [{i}/{len(items)}] {title}: {', '.join(parts)}")
    return outdir, ok, skipped, failed
