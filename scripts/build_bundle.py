#!/usr/bin/env python3
"""
Emit a deck bundle for Slide Studio.

  python3 scripts/build_bundle.py --src example/slides --figs example/images \
      --out decks/example.json --title "Slide Studio"

The bundle is {id, title, slides[], figs{id: svg}}. Only figures the deck actually
references are included, which is what keeps it small.
"""

import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SLIDE_RE = re.compile(r"^### (\d+)\.\s*`\[([SDEB])\]`\s*(.+?)\s*$", re.M)
SUB_RE = re.compile(r"^##\s+(?!#)(.+?)\s*$", re.M)          # subsection inside an act
FIG_RE = re.compile(r"^\*\*Figure:\*\*\s*(?:↺\s*)?`([a-zA-Z0-9._-]+)`[ \t]*(?:·[ \t]*([a-z-]+))?[^\n]*$", re.M)
LAYOUTS = {"figure", "split-l", "split-r", "background", "text"}
FIG_NONE_RE = re.compile(r"^\*\*Figure:\*\*\s*(?:none|žádná).*$", re.M | re.I)
NOTE_RE = re.compile(r"^\*(?:Delivery note|Transition)[^:]*:\*\s*(.+)$", re.M)
SUM_RE = re.compile(r"^\*Summary:\*\s*(.+)$", re.M)
PICK_RE = re.compile(r"^\*Bestseller:\*\s*(\S+)[^\n]*$", re.M)   # in the short run through the deck      # what the slide is for, in one or two lines
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)

# A section name per file. Anything not listed here is derived from the filename,
# so "04-how-it-works.md" becomes "How It Works".
GROUPS = {}


def parse_slides(text, group):
    """Walk the file in order so a ## heading attaches to the slides it introduces,
    rather than falling into the body of the slide above it."""
    marks = [("sub", m.start(), m.end(), m.group(1)) for m in SUB_RE.finditer(text)]
    marks += [("slide", m.start(), m.end(), m) for m in SLIDE_RE.finditer(text)]
    marks.sort(key=lambda x: x[1])

    slides, sub = [], None
    for i, (kind, a, b, payload) in enumerate(marks):
        if kind == "sub":
            sub = payload
            continue
        stop = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        body = text[b:stop]
        f = FIG_RE.search(body)
        notes = " ".join(x.strip() for x in NOTE_RE.findall(body))
        sm = SUM_RE.search(body)
        pk = PICK_RE.search(body)
        body = SUM_RE.sub("", body)
        body = PICK_RE.sub("", body)
        body = FIG_RE.sub("", body)
        body = FIG_NONE_RE.sub("", body)
        body = NOTE_RE.sub("", body)
        body = re.sub(r"^---\s*$", "", body, flags=re.M)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        slides.append({"tag": payload.group(2), "group": group, "sub": sub,
                       "title": payload.group(3).strip(),
                       "fig": f.group(1) if f else None,
                       "layout": (f.group(2) if f and f.group(2) in LAYOUTS else "figure") if f else "text",
                       "body": body, "notes": notes, "summary": sm.group(1).strip() if sm else "",
                       "pick": bool(pk) and pk.group(1).lower() in ("yes", "true", "1", "ano")})
    return slides


def from_generic(text, fallback_title, group):
    """p-book style: frontmatter + prose, split on ## headings."""
    fm = {}
    m = FM_RE.match(text)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip().strip("\"'")
        text = text[m.end():]
    group = fm.get("chapter", group)
    parts = [p for p in re.split(r"^(?=##\s)", text, flags=re.M) if p.strip()]
    slides = []
    for p in parts:
        h = re.search(r"^#{1,3}\s+(.+)$", p, re.M)
        title = (h.group(1) if h else fm.get("title", fallback_title)).strip()
        body = (p.replace(h.group(0), "", 1) if h else p).strip()
        # markdown images become inline figure markers the studio understands
        figs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
        body = re.sub(r"!\[[^\]]*\]\(([^)]+)\)",
                      lambda mm: "![[%s]]" % os.path.basename(mm.group(1)).rsplit(".", 1)[0], body)
        first = os.path.basename(figs[0]).rsplit(".", 1)[0] if figs else None
        if first:
            body = body.replace("![[%s]]" % first, "", 1).strip()
        slides.append({"tag": "S", "group": group, "title": title[:120],
                       "fig": first, "layout": "figure" if first else "text",
                       "body": body, "notes": fm.get("teaser", "")})
    return slides


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(ROOT, "slides"))
    ap.add_argument("--figs", action="append", default=None)
    ap.add_argument("--out", default=os.path.join(ROOT, "decks", "deck.json"))
    ap.add_argument("--title", default="Untitled deck")
    ap.add_argument("--id", default=None)
    a = ap.parse_args()

    figdirs = a.figs or [os.path.join(ROOT, "images"), os.path.join(a.src, "..", "images")]

    slides = []
    files = sorted(f for f in os.listdir(a.src) if f.endswith(".md"))
    for f in files:
        text = open(os.path.join(a.src, f), encoding="utf-8").read()
        group = GROUPS.get(f) or re.sub(r"^\d+[-_]", "", f[:-3]).replace("-", " ").title()
        slides += (parse_slides(text, group) if SLIDE_RE.search(text)
                   else from_generic(text, f[:-3], group))

    for i, s in enumerate(slides):
        s["n"] = i + 1

    # only the figures actually referenced, hero or inline
    used = set()
    for s in slides:
        if s["fig"]:
            used.add(s["fig"])
        used |= set(re.findall(r"!\[\[([a-zA-Z0-9._-]+)\]\]", s["body"] or ""))

    figs, seen = {}, set()
    for d in figdirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".svg"):
                continue
            fid = fn[:-4]
            if fid in seen or fid not in used:
                continue
            seen.add(fid)
            svg = open(os.path.join(d, fn), encoding="utf-8").read()
            figs[fid] = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()

    # presentation-level settings live beside the slides, so rebuilding never loses them
    side = os.path.join(a.src, "deck.meta.json")
    extra = {}
    if os.path.isfile(side):
        extra = json.load(open(side, encoding="utf-8"))

    bundle = {"id": a.id or os.path.basename(a.out).rsplit(".", 1)[0],
              "title": extra.get("title") or a.title,
              "meta": extra.get("meta", {}), "style": extra.get("style", {}),
              "slides": slides, "figs": figs}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(bundle, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    missing = sorted(used - set(figs))
    print(f"{a.out}")
    subs = len({s["sub"] for s in slides if s.get("sub")})
    print(f"  {len(slides)} slides · {subs} subsections · {len(figs)}/{len(used)} figures"
          f" · {os.path.getsize(a.out)/1e6:.2f} MB")
    if extra:
        print(f"  settings from {os.path.relpath(side, ROOT)}")
    if missing:
        print(f"  missing: {', '.join(missing[:8])}")


if __name__ == "__main__":
    main()
