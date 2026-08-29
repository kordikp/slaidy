#!/usr/bin/env python3
r"""Mark a short run through the deck.

The talk cannot be personalised — it is projected to everyone at once — so the
deck carries the fallback every recommender falls back to: the popular path.
This picks one, writing *Bestseller:* yes into the markdown. Press B while
presenting to switch between the run and the whole deck.

A slide earns its place by carrying the argument on its own: it opens an act or
a subsection, it lands a key line, it shows evidence. Asides go first.

    .venv/bin/python scripts/short_run.py --minutes 45 --dry-run
    .venv/bin/python scripts/short_run.py --minutes 45
"""
import argparse, importlib.util, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("bb", os.path.join(ROOT, "scripts", "build_bundle.py"))
bb = importlib.util.module_from_spec(spec); spec.loader.exec_module(bb)

WPM = 145


def secs(s):
    w = len(re.sub(r"!\[\[[^\]]*\]\]|[#*`>|_]", " ", (s["body"] or "") + " " + (s["notes"] or "")).split())
    return round(w / WPM * 60)


def score(slides, i):
    s = slides[i]
    v = 0
    if re.search(r"^>", s["body"] or "", re.M):
        v += 3
    v += {"E": 2, "D": 1, "B": -4}.get(s["tag"], 0)
    if s["fig"]:
        v += 1
    prev = slides[i - 1] if i else None
    if not prev or (prev.get("sub") or "") != (s.get("sub") or ""):
        v += 2
    if not prev or (prev.get("group") or "") != (s.get("group") or ""):
        v += 3
    if i == 0 or i >= len(slides) - 3:
        v += 8
    if (s.get("summary") or "").strip():
        v += 1
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=45)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--clear", action="store_true", help="remove every mark instead")
    ap.add_argument("--src", default=os.path.join(ROOT, "slides"))
    a = ap.parse_args()

    files = sorted(f for f in os.listdir(a.src) if f.endswith(".md"))
    slides, where = [], []
    for f in files:
        text = open(os.path.join(a.src, f), encoding="utf-8").read()
        group = bb.GROUPS.get(f) or f[:-3]
        for s in bb.parse_slides(text, group):
            slides.append(s); where.append(f)

    chosen = set()
    if not a.clear:
        # Share the budget between the acts in proportion to their full length, so
        # every act is compressed by the same factor and the talk keeps its shape.
        # Greedy over the whole deck instead gave one act 14 of 26 and another 1 of 48.
        total = sum(secs(s) for s in slides) or 1
        budget = a.minutes * 60
        spent = 0
        acts = dict.fromkeys(s["group"] for s in slides)
        for g in acts:
            idx = [i for i, s in enumerate(slides) if s["group"] == g]
            share = budget * sum(secs(slides[i]) for i in idx) / total
            order = sorted(idx, key=lambda i: (-score(slides, i), secs(slides[i])))
            used = 0
            for i in order:
                t = secs(slides[i])
                if used + t > share and used > 0:
                    continue
                chosen.add(i); used += t
            spent += used
        print(f"  {len(chosen)} of {len(slides)} slides · {spent//60} min {spent%60} s")
        per = {}
        for i in chosen:
            per[slides[i]["group"]] = per.get(slides[i]["group"], 0) + 1
        for g in dict.fromkeys(s["group"] for s in slides):
            tot = sum(1 for s in slides if s["group"] == g)
            print(f"    {g:34s} {per.get(g,0):3d} of {tot:3d}")

    titles = {slides[i]["title"] for i in chosen}
    changed = 0
    for f in files:
        path = os.path.join(a.src, f)
        text = open(path, encoding="utf-8").read()
        out, last = [], 0
        hits = list(bb.SLIDE_RE.finditer(text))
        subs = [m.start() for m in bb.SUB_RE.finditer(text)]
        for i, m in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
            end = min([end] + [x for x in subs if m.start() < x < end])
            seg = text[m.start():end]
            seg = bb.PICK_RE.sub("", seg)
            seg = re.sub(r"\n{3,}", "\n\n", seg)
            if m.group(3).strip() in titles:
                head_end = seg.index("\n")
                seg = seg[:head_end] + "\n\n*Bestseller:* yes" + seg[head_end:]
                changed += 1
            out.append(text[last:m.start()]); out.append(seg); last = end
        out.append(text[last:])
        new = re.sub(r"\n{4,}", "\n\n\n", "".join(out))
        if not a.dry_run and new != text:
            open(path, "w", encoding="utf-8").write(new)
    print(f"\n  {'would mark' if a.dry_run else 'marked'} {changed} slides")
    if a.dry_run:
        print("  (dry run — nothing written)")


if __name__ == "__main__":
    main()
