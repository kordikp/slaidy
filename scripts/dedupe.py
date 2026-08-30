#!/usr/bin/env python3
r"""Stop the slide from saying what the figure already says.

A figure and the text beside it should work as one thing. Where the body repeats
the figure — the same four labels, the same three bullets — the slide reads as a
stutter. This moves the repeated blocks into the speaker notes, block by block,
and leaves whatever the figure cannot say.

A block counts as repeated when the figure's own labels already cover most of its
distinctive words. Lists and tables are where this happens: the same four labels,
the same three bullets, once in the drawing and once beside it.

Key lines are never touched. A good one shares the figure's vocabulary on purpose
— it names what the picture shows and then says what it means — and word overlap
cannot tell that apart from an echo. Nine of them were nearly deleted before this
rule existed.

    .venv/bin/python scripts/dedupe.py --dry-run
    .venv/bin/python scripts/dedupe.py --threshold 0.7
"""
import argparse, importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("bb", os.path.join(ROOT, "scripts", "build_bundle.py"))
bb = importlib.util.module_from_spec(spec); spec.loader.exec_module(bb)
fspec = importlib.util.spec_from_file_location("fs", os.path.join(ROOT, "scripts", "fit_slides.py"))
fs = importlib.util.module_from_spec(fspec); fspec.loader.exec_module(fs)

STOP = set("""a an the and or of to in for on with is are be by as it its that this these those
from at not no you your we our they their he she i if then than so but what which who when where
how why can could will would may might must should do does did done have has had one two three four
same each every all any some more most less least other another new old only just also very into
out up down over under between about after before while during because such per via than""".split())


def words(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9@\-]{2,}", t)} - STOP


def figure_words(svg):
    parts = re.findall(r"<text[^>]*>(.*?)</text>|<tspan[^>]*>(.*?)</tspan>", svg or "", re.S)
    return words(" ".join(a or c for a, c in parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.75,
                    help="how much of a block the figure must already cover (0-1)")
    ap.add_argument("--src", default=os.path.join(ROOT, "slides"))
    ap.add_argument("--figs", default=os.path.join(ROOT, "images"))
    a = ap.parse_args()

    figs = {}
    for fn in os.listdir(a.figs):
        if fn.endswith(".svg"):
            figs[fn[:-4]] = figure_words(open(os.path.join(a.figs, fn), encoding="utf-8").read())

    moved = kept = touched = 0
    report = []
    for f in sorted(os.listdir(a.src)):
        if not f.endswith(".md"):
            continue
        path = os.path.join(a.src, f)
        text = open(path, encoding="utf-8").read()
        hits = list(bb.SLIDE_RE.finditer(text))
        subs = [m.start() for m in bb.SUB_RE.finditer(text)]
        out, last = [], 0
        for i, m in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
            end = min([end] + [x for x in subs if m.start() < x < end])
            seg = text[m.start():end]
            new, info = strip(seg, figs, a)
            if info:
                touched += 1
                moved += info["moved"]
                kept += info["kept"]
                report.append((int(m.group(1)), m.group(3)[:44], info))
            out.append(text[last:m.start()]); out.append(new); last = end
        out.append(text[last:])
        res = re.sub(r"\n{4,}", "\n\n\n", "".join(out))
        if not a.dry_run and res != text:
            open(path, "w", encoding="utf-8").write(res)

    for n, title, info in report[:24]:
        print(f"  {n:3d} {title:46s} −{info['moved']} block(s), {info['kept']} left")
    if len(report) > 24:
        print(f"  … and {len(report) - 24} more")
    print(f"\n  {touched} slides touched · {moved} blocks moved to the notes · {kept} blocks left on slides")
    if a.dry_run:
        print("  (dry run — nothing written)")


def strip(seg, figs, a):
    head_m = bb.SLIDE_RE.match(seg)
    if not head_m:
        return seg, None
    head, rest = head_m.group(0).rstrip(), seg[head_m.end():]
    fig = bb.FIG_RE.search(rest)
    if not fig or fig.group(1) not in figs:
        return seg, None
    fw = figs[fig.group(1)]
    if len(fw) < 6:
        return seg, None

    sm = bb.SUM_RE.search(rest); note = bb.NOTE_RE.search(rest)
    sk = bb.SKIP_RE.search(rest); fl = bb.FLAGS_RE.search(rest)
    body = rest
    for rx in (bb.SUM_RE, bb.FIG_RE, bb.FIG_NONE_RE, bb.NOTE_RE, bb.SKIP_RE, bb.FLAGS_RE):
        body = rx.sub("", body)
    body = re.sub(r"^---\s*$", "", body, flags=re.M)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if not body:
        return seg, None

    keep, drop = [], []
    for kind, block in fs.blocks(body):
        bw = words(block)
        if kind in ("quote", "fig") or len(bw) < 3:
            keep.append(block); continue          # the key line is the slide's own voice
        cover = len(bw & fw) / len(bw)
        (drop if cover >= a.threshold else keep).append(block)
    if not drop:
        return seg, None

    kept_text = "\n\n".join(keep).strip()
    said = " ".join(fs.as_prose(b) for b in drop)
    if note:
        said = note.group(1).strip() + " — " + said

    w = fs.words(kept_text)
    layout = "text" if not fig else ("figure" if w <= fs.UNDER_MAX else "split-r")
    parts = [head, ""]
    if sm:
        parts += [sm.group(0).strip(), ""]
    if fl:
        parts += [fl.group(0).strip(), ""]
    parts += ["**Figure:** `%s`%s" % (fig.group(1), "" if layout == "figure" else " · " + layout), ""]
    if sk:
        parts += [sk.group(0).strip(), ""]
    if kept_text:
        parts += [kept_text, ""]
    parts += ["*Delivery note:* " + said, ""]
    return "\n".join(parts), {"moved": len(drop), "kept": len(keep)}


if __name__ == "__main__":
    main()
