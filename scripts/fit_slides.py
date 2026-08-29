#!/usr/bin/env python3
r"""Make every slide show what it is meant to show.

The deck was written as: figure on the slide, prose underneath. But the `figure`
layout projected only the figure, so on 222 of 237 slides the prose was invisible
to the room. The layout now projects the body too, which turns the problem into a
fitting problem — this script does the fitting.

The rule separates what is *shown* from what is *said*:

  lists, tables, key lines (>), inline figures  ->  stay on the slide
  prose paragraphs                              ->  speaker notes

Then the layout follows from how much stayed:

  nothing left      -> figure alone (it carries its own title and takeaway)
  up to 45 words    -> figure with the text under it
  more              -> split-r, text beside the figure

Slides whose whole body is already short (<= 40 words) are left alone.

    .venv/bin/python scripts/fit_slides.py --dry-run
    .venv/bin/python scripts/fit_slides.py
"""
import argparse, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLIDE_RE = re.compile(r"^### (\d+)\.\s*`\[([SDEB])\]`\s*(.+?)\s*$", re.M)
FIG_RE = re.compile(r"^\*\*Figure:\*\*\s*(?:↺\s*)?`([a-zA-Z0-9._-]+)`[ \t]*(?:·[ \t]*([a-z-]+))?[^\n]*$", re.M)
FIG_NONE_RE = re.compile(r"^\*\*Figure:\*\*\s*(?:none|žádná).*$", re.M | re.I)
NOTE_RE = re.compile(r"^\*(?:Delivery note|Transition)[^:]*:\*\s*(.+)$", re.M)
SUM_RE = re.compile(r"^\*Summary:\*\s*(.+)$", re.M)
SUB_RE = re.compile(r"^##\s+(?!#)(.+?)\s*$", re.M)

SHOWN = {"list", "table", "quote", "fig"}       # visual — belongs on the slide
KEEP_WHOLE = 40                                  # a body this short already fits
UNDER_MAX = 45                                   # text under a figure, beyond this go side by side


def words(t):
    return len(re.sub(r"!\[\[[^\]]*\]\]|[#*`>|_]", " ", t or "").split())


def blocks(md):
    out, buf, kind = [], [], None
    def flush():
        nonlocal buf, kind
        if buf:
            out.append((kind, "\n".join(buf)))
        buf, kind = [], None
    for raw in (md or "").split("\n"):
        line = raw.rstrip()
        t = line.strip()
        if re.match(r"^!\[\[[\w.-]+\]\]$", t):
            flush(); out.append(("fig", t)); continue
        k = ("table" if t.startswith("|") else
             "list" if re.match(r"^([-*]|\d+\.)\s", t) else
             "quote" if t.startswith(">") else
             None if t == "" else "para")
        if k is None:
            flush(); continue
        if kind and k != kind:
            flush()
        kind = k
        buf.append(line)
    flush()
    return out


def as_prose(text):
    """A block becomes one run of spoken words."""
    t = re.sub(r"^\s*[-*]\s+", "", text, flags=re.M)
    t = re.sub(r"\s*\n\s*", " ", t).strip()
    return re.sub(r"\s{2,}", " ", t)


def fit(seg):
    """Rewrite one slide segment. Returns (text, what_changed or None)."""
    head_m = SLIDE_RE.match(seg)
    if not head_m:
        return seg, None
    head, rest = head_m.group(0).rstrip(), seg[head_m.end():]

    fig = FIG_RE.search(rest)
    if not fig:
        return seg, None
    sm = SUM_RE.search(rest)
    note = NOTE_RE.search(rest)

    body = rest
    for rx in (SUM_RE, FIG_RE, FIG_NONE_RE, NOTE_RE):
        body = rx.sub("", body)
    body = re.sub(r"^---\s*$", "", body, flags=re.M)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    if not body or words(body) <= KEEP_WHOLE:
        return seg, None

    bs = blocks(body)
    shown = [t for k, t in bs if k in SHOWN]
    spoken = [t for k, t in bs if k not in SHOWN]
    if not spoken:
        return seg, None

    kept = "\n\n".join(shown).strip()
    w = words(kept)
    layout = "figure" if w <= UNDER_MAX else "split-r"

    said = " ".join(as_prose(t) for t in spoken)
    if note:
        said = said + " — " + note.group(1).strip()

    parts = [head, ""]
    if sm:
        parts += [sm.group(0).strip(), ""]
    parts += ["**Figure:** `%s`%s" % (fig.group(1), "" if layout == "figure" else " · " + layout), ""]
    if kept:
        parts += [kept, ""]
    parts += ["*Delivery note:* " + said, ""]
    return "\n".join(parts), {"moved": words(said) - (words(note.group(1)) if note else 0),
                              "kept": w, "layout": layout}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--src", default=os.path.join(ROOT, "slides"))
    a = ap.parse_args()

    tally = {"figure": 0, "split-r": 0, "untouched": 0}
    moved_total = 0
    for f in sorted(os.listdir(a.src)):
        if not f.endswith(".md"):
            continue
        path = os.path.join(a.src, f)
        text = open(path, encoding="utf-8").read()
        hits = list(SLIDE_RE.finditer(text))
        if not hits:
            continue
        subs = [m.start() for m in SUB_RE.finditer(text)]
        pieces, last, changed = [], 0, 0
        for i, m in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
            nxt = [x for x in subs if m.start() < x < end]
            end = min([end] + nxt)
            pieces.append(text[last:m.start()])
            seg = text[m.start():end]
            new, info = fit(seg)
            if info:
                changed += 1
                tally[info["layout"]] += 1
                moved_total += info["moved"]
            else:
                tally["untouched"] += 1
            pieces.append(new)
            last = end
        pieces.append(text[last:])
        out = "".join(pieces)
        out = re.sub(r"\n{4,}", "\n\n\n", out)
        print(f"  {f:34s} {changed:3d} of {len(hits):3d} slides reworked")
        if not a.dry_run and out != text:
            open(path, "w", encoding="utf-8").write(out)

    print(f"\n  figure with text under it : {tally['figure']}")
    print(f"  text beside the figure    : {tally['split-r']}")
    print(f"  left alone                : {tally['untouched']}")
    print(f"  words moved to the notes  : {moved_total}")
    if a.dry_run:
        print("\n  (dry run — nothing written)")


if __name__ == "__main__":
    main()
