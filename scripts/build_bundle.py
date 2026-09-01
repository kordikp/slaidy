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
FIG_RE = re.compile(r"^\*\*Figure:\*\*\s*(?:↺\s*)?`([a-zA-Z0-9._-]+)`[ \t]*"
                    r"(?:·[ \t]*([a-z-]+))?[ \t]*(?:·[ \t]*(\d{2,3})%)?[^\n]*$", re.M)
LAYOUTS = {"text", "two", "three", "background", "cover", "closing"}
# What the older markdown says, and what it means now that a figure is a block
# in the body like any other. Same mapping the app does when it reads a deck.
LAY_WAS = {"figure": "text", "split-l": "two", "split-r": "two",
           "background": "background", "text": "text"}
# A layout the figure line cannot carry — two columns, a cover — says so outright
LAY_RE = re.compile(r"^\*Layout:\*\s*([A-Za-z0-9_-]+)", re.M)
FIG_NONE_RE = re.compile(r"^\*\*Figure:\*\*\s*(?:none|žádná).*$", re.M | re.I)
NOTE_RE = re.compile(r"^\*(?:Delivery note|Transition)[^:]*:\*\s*(.+)$", re.M)
SUM_RE = re.compile(r"^\*Summary:\*\s*(.+)$", re.M)
SKIP_RE = re.compile(r"^\*Skip:\*\s*(\S+)[^\n]*$", re.M)      # hidden when presenting
FLAGS_RE = re.compile(r"^\*Flags:\*\s*([^\n]+)$", re.M)        # keep = never auto-hide, ours = our own work
TEXT_RE = re.compile(r"^\*Text:\*\s*(\d{2,3})%[^\n]*$", re.M)   # body size, as a percentage
# A slide keeps only what it disagrees with; everything else follows the deck.
STYLE_RE = re.compile(r"^\*Style:\*\s*([^\n]+)$", re.M)
STYLE_KEYS = ("accent", "ink", "paper", "titleSize", "bodySize", "header")


def parse_style(text):
    out = {}
    for pair in (text or "").split(","):
        k, _, v = pair.partition("=")
        k, v = k.strip(), v.strip()
        if k not in STYLE_KEYS or not v:
            continue
        if k.endswith("Size"):
            try:
                out[k] = int(v)
            except ValueError:
                continue
        else:
            out[k] = v
    return out
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)

# A section name per file. Anything not listed here is derived from the filename,
# so "04-how-it-works.md" becomes "How It Works".
GROUPS = {
    "01-prologue.md": "Prologue",
    "02-act1-four-rooms.md": "I · Four Rooms",
    "03-act2-one-question.md": "II · One Question",
    "04-act3-walls-came-down.md": "III · How the Walls Came Down",
    "05-act4-literature-map.md": "IV · The Literature, Mapped",
    "06-act5-who-built-what.md": "V · Who Has Built What",
    "07-act6-what-breaks.md": "VI · What Breaks",
    "08-act7-what-it-costs.md": "VII · What It Costs",
    "09-act8-what-we-build.md": "VIII · What We Build",
    "10-epilogue.md": "Epilogue",
}


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
        sk = SKIP_RE.search(body)
        fl = FLAGS_RE.search(body)
        ts = TEXT_RE.search(body)
        st = STYLE_RE.search(body)
        ly = LAY_RE.search(body)
        body = SUM_RE.sub("", body)
        body = SKIP_RE.sub("", body)
        body = FLAGS_RE.sub("", body)
        body = TEXT_RE.sub("", body)
        body = STYLE_RE.sub("", body)
        body = LAY_RE.sub("", body)
        body = FIG_RE.sub("", body)
        body = FIG_NONE_RE.sub("", body)
        body = NOTE_RE.sub("", body)
        body = re.sub(r"^---\s*$", "", body, flags=re.M)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        # A figure used to be a field on the slide with a layout to say where it
        # went. It is a block in the body now, so the old form is translated
        # here rather than carried: the drawing goes where the layout put it,
        # and the layout becomes one about columns.
        layout = (ly.group(1) if ly and ly.group(1) in LAYOUTS else "text")
        if f:
            was = f.group(2) if f.group(2) else "figure"
            scale = int(f.group(3)) if f.group(3) else 100
            mark = "![[%s%s]]" % (f.group(1), "" if scale == 100 else "|%d%%" % scale)
            layout = LAY_WAS.get(was, "text")
            if was == "split-r":
                body = (body + "\n\n" if body else "") + "<!-- col -->\n\n" + mark
            elif was == "split-l":
                body = mark + "\n\n<!-- col -->" + ("\n\n" + body if body else "")
            else:
                body = mark + ("\n\n" + body if body else "")
        slides.append({"tag": payload.group(2), "group": group, "sub": sub,
                       "title": payload.group(3).strip(),
                       "layout": layout,
                       "textScale": int(ts.group(1)) if ts else 100,
                       "body": body, "notes": notes, "summary": sm.group(1).strip() if sm else "",
                       "skip": bool(sk) and sk.group(1).lower() in ("yes", "true", "1", "ano"),
                       **({"style": parse_style(st.group(1))} if st and parse_style(st.group(1)) else {}),
                       "flags": [x.strip() for x in fl.group(1).split(",") if x.strip()] if fl else []})
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
        slides.append({"tag": "S", "group": group, "title": title[:120],
                       "layout": "text",
                       "body": body, "notes": fm.get("teaser", "")})
    return slides


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(ROOT, "slides"))
    ap.add_argument("--figs", action="append", default=None)
    ap.add_argument("--out", default=os.path.join(ROOT, "decks", "great-convergence.json"))
    ap.add_argument("--title", default="The Great Convergence")
    ap.add_argument("--id", default=None)
    ap.add_argument("--force", action="store_true",
                    help="rebuild even when the deck on disk is newer than the markdown")
    a = ap.parse_args()

    # The deck is the document now: Slide Studio writes it directly. Rebuilding
    # from markdown therefore *overwrites edits* — which is exactly how a slide
    # title typed in the studio came back to its old value. Refuse, unless the
    # markdown really is the newer thing or --force says otherwise.
    if os.path.exists(a.out) and not a.force:
        deck_at = os.path.getmtime(a.out)
        # the figures are source too: editing an SVG and rebuilding used to look
        # like "the deck is newer than the markdown", because only .md was counted
        srcs = [os.path.join(a.src, f) for f in os.listdir(a.src) if f.endswith((".md", ".json"))]
        for d in (a.figs or [os.path.join(ROOT, "images"), os.path.join(a.src, "..", "images")]):
            if os.path.isdir(d):
                srcs += [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".svg")]
        src_at = max([os.path.getmtime(f) for f in srcs] or [0])
        if deck_at > src_at:
            import datetime
            fmt = lambda t: datetime.datetime.fromtimestamp(t).strftime("%d %b %H:%M")
            sys.exit(
                f"Refusing to rebuild {os.path.relpath(a.out, ROOT)}.\n"
                f"  the deck      was written {fmt(deck_at)}\n"
                f"  the markdown  was written {fmt(src_at)}\n"
                "The deck is newer, so it holds edits the markdown does not, and rebuilding\n"
                "would discard them. Export markdown from the studio first\n"
                "(⋯ → Export → Markdown), or pass --force if you meant to overwrite.")

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
        used |= set(re.findall(r"!\[\[([a-zA-Z0-9._-]+)(?:\|\d{2,3}%)?\]\]", s["body"] or ""))

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
