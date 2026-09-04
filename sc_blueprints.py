#!/usr/bin/env python3
"""
Скачивает все блюпринты пользователя с satisfactory-calculator.com.

Пример:
    python3 sc_blueprints.py "https://satisfactory-calculator.com/en/blueprints/index/index/idU/51246/user/sixsense"
    python3 sc_blueprints.py 51246/sixsense -o ./blueprints

Для каждого блюпринта качаются оба файла: .sbp и .sbpcfg (без cfg игра его не увидит).
Только stdlib, зависимостей нет.
"""

import argparse
import http.client
import os
import re
import sys
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
    """GET с ретраями. Возвращает (bytes, headers)."""
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


def collect(id_user, user, delay, max_pages=200):
    """Обходит страницы, пока не начнут повторяться id.

    Сайт на несуществующей странице отдаёт последнюю, поэтому условие
    остановки — «новых id на странице нет»."""
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
        print(f"  страница {page}: +{len(found)} (всего {len(out)})")
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

    # быстрый пропуск, если файл с ожидаемым именем уже есть
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
    """Принимает полный URL списка или '51246/sixsense'."""
    m = re.search(r"idU/(\d+)/user/([^/?#]+)", target)
    if not m:
        m = re.fullmatch(r"(\d+)[/:]([^/?#]+)", target.strip())
    if not m:
        sys.exit("Не понял цель: нужен URL со списком блюпринтов или 'idU/имя'")
    return m.group(1), urllib.parse.unquote(m.group(2))


def main():
    ap = argparse.ArgumentParser(description="Скачать все блюпринты пользователя с satisfactory-calculator.com")
    ap.add_argument("target", help="URL списка блюпринтов или 'idU/username'")
    ap.add_argument("-o", "--outdir", default=None, help="куда складывать (по умолчанию ./<username>)")
    ap.add_argument("-d", "--delay", type=float, default=1.0, help="пауза между запросами, сек (по умолчанию 1.0)")
    ap.add_argument("--no-cfg", action="store_true", help="не качать .sbpcfg")
    ap.add_argument("-f", "--force", action="store_true", help="перекачивать уже скачанное")
    ap.add_argument("--list-only", action="store_true", help="только показать список, ничего не качать")
    args = ap.parse_args()

    id_user, user = parse_target(args.target)
    outdir = args.outdir or f"./{safe_name(user)}"

    print(f"Пользователь: {user} (id {id_user})")
    print("Собираю список...")
    items = collect(id_user, user, args.delay)
    print(f"Найдено блюпринтов: {len(items)}")

    if args.list_only:
        for bp_id, slug in items:
            print(f"  {bp_id}  {urllib.parse.unquote_plus(slug)}")
        return

    os.makedirs(outdir, exist_ok=True)
    kinds = ["download"] + ([] if args.no_cfg else ["download-cfg"])
    ok = skipped = failed = 0

    for i, (bp_id, slug) in enumerate(items, 1):
        title = urllib.parse.unquote_plus(slug)
        line = f"[{i}/{len(items)}] {title}"
        parts = []
        for kind in kinds:
            try:
                status, fname = download(kind, bp_id, slug, outdir, args.delay, args.force)
                parts.append(f"{'✓' if status == 'ok' else '·'} {fname}")
                ok += status == "ok"
                skipped += status == "skip"
            except Exception as e:
                parts.append(f"✗ {kind}: {e}")
                failed += 1
        print(f"{line}\n    " + "\n    ".join(parts))

    print(f"\nГотово: скачано {ok}, пропущено {skipped}, ошибок {failed} → {os.path.abspath(outdir)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nПрервано.")
