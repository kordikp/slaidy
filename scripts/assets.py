#!/usr/bin/env python3
"""The pictures in a deck, without reading their bytes.

    python3 scripts/assets.py list decks/talk.json            what is there, where it is used
    python3 scripts/assets.py extract decks/talk.json figures/ write them out as files
    python3 scripts/assets.py describe decks/talk.json img-… "what it shows"
    python3 scripts/assets.py add figures/ photo.jpg [more files] [--desc "…"] [--trim]

A deck keeps its pictures as base64 under "assets", which is most of the file's
bytes and none of what an assistant needs to read. `list` prints each picture's
name, size, type, description and the figures that place it — the whole of what
there is to know without looking at the pixels. `extract` writes them into
<dir>/assets/ with assets.json beside them, the layout build_bundle.py reads back.
`describe` sets the description, which is what a model is told a picture shows.
`add` brings picture files into a source folder the way the app does: at most
1920 pixels on the longest side, WebP, named by SlAIdy's own content hash (so the
same picture pasted in the app later is the same picture, not a second copy),
and listed in <dir>/assets/assets.json. `--trim` cuts transparent or white
margins (logos). It needs Pillow; without it, files are copied as they are.
"""
import base64, io, json, os, re, sys

EXT = {"image/webp": ".webp", "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif"}


PIC_MAX = 1920      # the longest edge the app keeps
KEEP_UNDER = 350_000


def pic_hash(s):
    """SlAIdy's picHash (slaidy.html), ported: two 53-bit mixes of the base64, 24 hex digits."""
    M = 0xFFFFFFFF
    imul = lambda a, b: (a * b) & M

    def mix(seed):
        h1, h2 = (0xDEADBEEF ^ seed) & M, (0x41C6CE57 ^ seed) & M
        for ch in s:
            c = ord(ch)
            h1 = imul(h1 ^ c, 2654435761)
            h2 = imul(h2 ^ c, 1597334677)
        h1 = imul(h1 ^ (h1 >> 16), 2246822507) ^ imul(h2 ^ (h2 >> 13), 3266489909)
        h2 = imul(h2 ^ (h2 >> 16), 2246822507) ^ imul(h1 ^ (h1 >> 13), 3266489909)
        return f"{h2:08x}{h1:08x}"
    return "img-" + (mix(0) + mix(7))[:24]


def encode(path, trim=False):
    """(type, bytes, w, h) as the app would store the picture."""
    raw = open(path, "rb").read()
    ext = os.path.splitext(path)[1].lower()
    plain = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
    try:
        from PIL import Image
    except ImportError:
        if ext not in plain:
            sys.exit(f"{path}: not a picture type SlAIdy keeps ({', '.join(plain)}), and no Pillow to convert it")
        print(f"  (no Pillow: {os.path.basename(path)} kept as it is, not shrunk or trimmed)", file=sys.stderr)
        return plain[ext], raw, 0, 0
    img = Image.open(io.BytesIO(raw))
    w0, h0 = img.size
    if trim:
        rgba = img.convert("RGBA")
        px, xs, ys = rgba.load(), [], []
        for y in range(h0):
            for x in range(w0):
                r, g, b, a = px[x, y]
                if a > 24 and not (r > 244 and g > 244 and b > 244):
                    xs.append(x); ys.append(y)
        if xs:
            pad = max(2, int(0.02 * max(w0, h0)))
            img = rgba.crop((max(0, min(xs) - pad), max(0, min(ys) - pad), min(w0, max(xs) + pad + 1), min(h0, max(ys) + pad + 1)))
    w, h = img.size
    k = min(1, PIC_MAX / max(w, h))
    # a picture already small enough keeps its own bytes: re-encoding would only make it worse
    if not trim and k == 1 and ext in plain and (ext == ".gif" or len(raw) <= KEEP_UNDER):
        return plain[ext], raw, w, h
    if k < 1:
        img = img.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=86, method=6)
    return "image/webp", buf.getvalue(), img.size[0], img.size[1]


def cmd_add(figs, files, desc="", trim=False):
    ad = os.path.join(figs, "assets")
    os.makedirs(ad, exist_ok=True)
    jp = os.path.join(ad, "assets.json")
    about = json.load(open(jp, encoding="utf-8")) if os.path.isfile(jp) else {}
    for f in files:
        kind, data, w, h = encode(f, trim)
        pid = pic_hash(base64.b64encode(data).decode())
        open(os.path.join(ad, pid + EXT[kind]), "wb").write(data)
        entry = about.get(pid) or {}
        entry.update({"name": os.path.basename(f), **({"w": w, "h": h} if w else {})})
        if desc:
            entry["desc"] = desc
        about[pid] = entry
        print(f"{pid}  {f}  {len(data) // 1024} kB" + (f"  {w}×{h}" if w else ""))
        print(f'    <image href="asset:{pid}" x="0" y="0" width="{w or 800}" height="{h or 450}" preserveAspectRatio="xMidYMid meet"/>')
        if not entry.get("desc"):
            print("    no description yet: python3 scripts/assets.py describe … or edit assets.json")
    json.dump(about, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


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
    elif len(a) >= 3 and a[0] == "add":
        args, desc, trim = [], "", False
        it = iter(a[1:])
        for x in it:
            if x == "--desc":
                desc = next(it, "")
            elif x == "--trim":
                trim = True
            else:
                args.append(x)
        cmd_add(args[0], args[1:], desc, trim)
    else:
        sys.exit(__doc__.strip())
