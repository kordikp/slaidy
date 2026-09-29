#!/usr/bin/env python3
"""The pictures in a deck, without reading their bytes.

    python3 scripts/assets.py list decks/talk.json            what is there, where it is used
    python3 scripts/assets.py extract decks/talk.json figures/ write them out as files
    python3 scripts/assets.py describe decks/talk.json img-… "what it shows"

A deck keeps its pictures as base64 under "assets", which is most of the file's
bytes and none of what an assistant needs to read. `list` prints each picture's
name, size, type, description and the figures that place it — the whole of what
there is to know without looking at the pixels. `extract` writes them into
<dir>/assets/ with assets.json beside them, the layout build_bundle.py reads back.
`describe` sets the description, which is what a model is told a picture shows.
"""
import base64, json, os, re, sys

EXT = {"image/webp": ".webp", "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif"}


def load(path):
    return json.load(open(path, encoding="utf-8"))


def uses(deck):
    where = {}
    for fid, svg in (deck.get("figs") or {}).items():
        for pid in set(re.findall(r"asset:(img-[0-9a-f]{12,40})", svg)):
            where.setdefault(pid, []).append(fid)
    return where


def cmd_list(path):
    deck = load(path)
    assets, where = deck.get("assets") or {}, uses(deck)
    if not assets:
        print("no pictures")
        return
    total = 0
    for pid, a in assets.items():
        kb = len(a.get("data") or "") * 3 // 4 // 1024
        total += kb
        size = f"{a['w']}×{a['h']} " if a.get("w") else ""
        print(f"{pid}  {size}{a.get('type', '?')} {kb} kB  in: {', '.join(where.get(pid, [])) or 'nothing'}")
        print(f"    {(a.get('desc') or '').strip() or '— no description: a model knows nothing about it'}")
        if a.get("source"):
            print(f"    from {a['source']}")
    print(f"{len(assets)} pictures, {total / 1024:.1f} MB")


def cmd_extract(path, out):
    deck = load(path)
    ad = os.path.join(out, "assets")
    os.makedirs(ad, exist_ok=True)
    about = {}
    for pid, a in (deck.get("assets") or {}).items():
        if a.get("type") not in EXT:
            continue
        open(os.path.join(ad, pid + EXT[a["type"]]), "wb").write(base64.b64decode(a["data"]))
        about[pid] = {k: a[k] for k in ("desc", "name", "source", "w", "h", "added") if a.get(k)}
    json.dump(about, open(os.path.join(ad, "assets.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"{len(about)} pictures in {ad}")


def cmd_describe(path, pid, text):
    deck = load(path)
    if pid not in (deck.get("assets") or {}):
        sys.exit(f"{pid} is not a picture in {path}")
    deck["assets"][pid]["desc"] = text.strip()
    json.dump(deck, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{pid}: {text.strip()}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "list":
        cmd_list(a[1])
    elif len(a) == 3 and a[0] == "extract":
        cmd_extract(a[1], a[2])
    elif len(a) == 4 and a[0] == "describe":
        cmd_describe(a[1], a[2], a[3])
    else:
        sys.exit(__doc__.strip())
