#!/usr/bin/env python3
r"""Lay a document out as a deck.

A chapter of a book, a paper or a set of lecture notes is markdown written to be
*read*: headings, lists, tables, figures and a great deal of prose. It carries
nothing a slide needs — no slide boundaries, no columns, no clicks, no speaker
notes, and no idea how much fits on a stage. Put one through the generic
importer and every section becomes one slide, most of them a wall of text.

This does the arrangement instead, and the rule it works to is one sentence:

    Tidy arranges what is on a slide and never moves a word.
    Fit decides what is on it: it moves words — into the speaker notes, or onto
    the next slide — and never changes one.

So nothing here summarises, deletes or invents. Prose comes out in the author's
words, in the author's order, either on a slide or in the notes under it, and
the script fails loudly if a single word goes missing. No model is involved.

    python3 scripts/fit_document.py --src content/ch05-algorithms          # just say what it would do
    python3 scripts/fit_document.py --src content --out /tmp/deck --figs images
    python3 scripts/build_bundle.py --src /tmp/deck/slides --figs /tmp/deck/figures \
        --out decks/ch05.json --title "Algorithms"

Three dials, and they are the ones in docs/proposals/a-deck-from-a-document.md:

  --grain fill        a slide per ## heading, then neighbours merged while they
                      fit. Half-empty slides are their own kind of wrong, and
                      merging is worth as much as splitting: 37% fill against 69%.
       section        a slide per ## heading, no merging
       subsection     a slide per ### heading

  --on-stage PATTERN  which files carry the talk. Everything else still comes in,
                      hidden — in the file, in the list, greyed, walked by H in a
                      rehearsal. Nothing is dropped, because which slides matter
                      is the one judgement a tool must not make for you.
                      A regular expression on the path, or `key=value` on the
                      frontmatter.

  --reveal            <!-- step --> between the blocks of a slide, so it builds
                      one block at a time. Off by default: a document says
                      nothing about pacing.

What fits is measured, not guessed — but a browser is what measures properly, so
offline a line budget stands in for it, calibrated on a deck somebody accepted
(`--calibrate`, decks/isd2026.json by default): the budget is the 90th percentile
of what that deck's own slides carry per column.
"""

import argparse, collections, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BUDGET = 15.8          # lines per column, if there is no deck to calibrate on
WORDS_PER_LINE = 13            # body text at full width, from the same deck

# ---------------------------------------------------------------- reading ----

FM_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)")


def frontmatter(text):
    """{key: value} plus {key[]: [items]} for a YAML list. Anything cleverer than
    that is a YAML parser, and a document that needs one can say so."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm, key = {}, None
    for line in m.group(1).split("\n"):
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key:
            fm.setdefault(key + "[]", []).append(item.group(1).strip().strip("\"'"))
            continue
        i = line.find(":")
        if i > 0 and not line.startswith((" ", "\t")):
            key = line[:i].strip()
            fm[key] = line[i + 1:].strip().strip("\"'")
    return fm, text[m.end():]


def figrefs(md):
    """A document points at a drawing by path; a deck points at it by name. The
    alt text goes with the path: for an SVG it was never prose, and a bitmap
    needs its description carried into the deck's own picture store, which is
    the application's job and not this script's."""
    return IMG_RE.sub(lambda m: "![[%s]]" % os.path.splitext(os.path.basename(m.group(2)))[0], md)


def words(t):
    """The words of a piece of markdown. Image markup is not prose and is
    excluded on both sides of the conservation check, so the two agree."""
    t = IMG_RE.sub(" ", t or "")
    t = re.sub(r"!\[\[[^\]]*\]\]", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r" \1 ", t)
    return re.sub(r"[#*`>|_~$]", " ", t).split()


def blocks(md):
    """The app's own block kinds, in the app's own order of tests."""
    out, buf, kind, fence = [], [], None, None

    def flush():
        nonlocal buf, kind
        if buf:
            out.append((kind, "\n".join(buf)))
        buf, kind = [], None

    for raw in (md or "").split("\n"):
        line, t = raw.rstrip(), raw.strip()
        if fence:
            buf.append(line)
            if re.match(r"^```", t):
                flush(); fence = None
            continue
        if re.match(r"^```", t):
            flush(); kind = "code"; buf.append(line); fence = "code"; continue
        if re.match(r"^\$\$", t) and t.endswith("$$") and len(t) > 3:
            flush(); out.append(("math", t)); continue
        if re.match(r"^#{1,6}\s+\S", t):
            flush(); out.append(("head", t)); continue
        if re.fullmatch(r"!\[\[[A-Za-z0-9._-]+(\|\d{2,3}%)?\]\]", t):
            flush(); out.append(("fig", t)); continue
        k = ("table" if t.startswith("|") else
             "list" if re.match(r"^([-*+]|\d+\.)\s+", t) else
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
    """One block becomes one run of spoken words — the same flattening
    scripts/fit_slides.py does, and for the same reason: the notes are read
    aloud, not projected."""
    t = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", text, flags=re.M)
    t = re.sub(r"^\s*>\s?", "", t, flags=re.M)
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)
    return re.sub(r"\s{2,}", " ", re.sub(r"\s*\n\s*", " ", t).strip())


# ------------------------------------------------------------- what fits ----

# A deck's own markdown is not a document. Reading one as prose would strip its
# slide headings, fold its **Figure:** lines into paragraphs and shovel the lot
# into the speaker notes — so it is recognised and refused rather than wrecked.
DECK_RE = re.compile(r"^### \d+\.\s*`\[[SDEB]\]`", re.M)

SHOWN = {"list", "table", "quote", "fig", "code", "math", "head"}
# A block is the unit: nothing is ever cut in half. A long *unordered* list is
# the one exception, because it is a run of separate items and a run can be
# continued — but an ordered one cannot, since <ol> starts again at 1 on the
# next slide, and half a table or half a code block is worse than a small one.
ORDERED = re.compile(r"^\s*\d+[.)]\s")


def cost(kind, src):
    """How many lines of the frame a block asks for. Rough, and it only has to
    rank arrangements rather than predict pixels — the application measures."""
    n = len(words(src))
    if kind == "para":
        return max(1, -(-n // WORDS_PER_LINE)) + 0.6
    if kind == "list":
        return sum(max(1, -(-len(words(l)) // WORDS_PER_LINE))
                   for l in src.split("\n") if l.strip()) + 0.6
    if kind == "table":
        return len([l for l in src.split("\n")
                    if l.strip() and not re.match(r"^\s*\|[-: |]+\|\s*$", l)]) + 1.0
    if kind == "quote":
        return max(1, -(-n // (WORDS_PER_LINE - 1))) + 1.0
    if kind == "head":
        return 1.4
    if kind == "code":
        return len(src.split("\n")) + 0.8
    if kind == "math":
        return 2.0
    if kind == "fig":
        return 6.0
    return 1.0


def load(items):
    return sum(cost(k, v) for k, v in items)


def calibrate(path):
    """The budget is what a deck somebody made, gave and kept actually carries:
    the 90th percentile of its slides' load per column. Guessing a number here
    would be guessing at the one thing that can be looked up."""
    try:
        deck = json.load(open(path, encoding="utf-8"))
    except Exception:
        return DEFAULT_BUDGET, 0
    loads = []
    for s in deck.get("slides", []):
        body = s.get("body") or ""
        cols = body.count("<!-- col -->") + 1
        clean = re.sub(r"^<!--.*-->\s*$", "", body, flags=re.M)
        loads.append(load(blocks(clean)) * (s.get("textScale") or 100) / 100 / cols)
    if not loads:
        return DEFAULT_BUDGET, 0
    loads.sort()
    return round(loads[int(0.9 * len(loads))], 1), len(loads)


# ------------------------------------------------------------- the pass -----

def units(body, level):
    """Split at headings of `level` or shallower. Deeper ones stay in the unit,
    where they are a sub-head on the slide — which is what #### already is."""
    rx = re.compile(r"^#{1,%d}\s+(.+?)\s*$" % level, re.M)
    hits = list(rx.finditer(body))
    if not hits:
        return [(None, body.strip())]
    out = []
    lead = body[:hits[0].start()].strip()
    if lead:
        out.append((None, lead))
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(body)
        out.append((m.group(1), body[m.end():end].strip()))
    return out


def runs(src, budget):
    """A list too long for one frame, cut at its own item boundaries."""
    items = [l for l in src.split("\n") if l.strip()]
    out, cur, used = [], [], 0.0
    for l in items:
        c = max(1, -(-len(words(l)) // WORDS_PER_LINE))
        if cur and used + c > budget - 0.6:
            out.append("\n".join(cur)); cur, used = [], 0.0
        cur.append(l); used += c
    if cur:
        out.append("\n".join(cur))
    return out or [src]


def split_shown(bs, budget):
    """Pack the blocks that stay on a slide, filling the frame before starting
    another. Blocks are atomic — nothing is cut in half — except a long
    unordered list, which is a run of items and can be continued."""
    pages, cur, used = [], [], 0.0
    for k, v in bs:
        parts = [v]
        if k == "list" and cost(k, v) > budget and not ORDERED.match(v.lstrip("\n")):
            parts = runs(v, budget)
        for part in parts:
            c = cost(k, part)
            if cur and used + c > budget:
                pages.append(cur); cur, used = [], 0.0
            cur.append((k, part)); used += c
    if cur:
        pages.append(cur)
    return pages or [[]]


def fit_unit(title, text, fm, first, budget):
    """One slice of the document becomes one or more slides. Shown stays, said
    is spoken — unless nothing would be left, because a slide with a title and
    an empty frame is worse than a slide with a paragraph on it."""
    bs = blocks(text)
    shown = [(k, v) for k, v in bs if k in SHOWN]
    said = [(k, v) for k, v in bs if k not in SHOWN]
    if first:
        # the author's own summary of their own section: three lines they wrote
        if fm.get("highlights[]"):
            shown.insert(0, ("list", "\n".join("- " + h for h in fm["highlights[]"])))
        d = fm.get("diagram")
        if d and d not in ("null", "none", "") and d not in text:
            shown.insert(0, ("fig", "![[%s]]" % d))
    if not shown and said:
        shown, said = [said[0]], said[1:]
    out = []
    for i, page in enumerate(split_shown(shown, budget)):
        out.append({"title": title, "shown": page,
                    "said": said if i == 0 else [], "lead": first and i == 0})
    return out


def merge(slides, budget):
    """Two neighbouring slices that fit together are one slide, the second one's
    heading becoming a sub-head on it. Without this the relocation leaves every
    slide at about a third of the frame."""
    out = []
    for s in slides:
        if out and load(out[-1]["shown"]) + load(s["shown"]) + cost("head", "#") <= budget:
            prev = out[-1]
            if s["title"]:
                prev["shown"] = prev["shown"] + [("head", "#### " + s["title"])] + s["shown"]
            else:
                prev["shown"] = prev["shown"] + s["shown"]
            prev["said"] = prev["said"] + s["said"]
            continue
        out.append(dict(s))
    return out


def reveal(shown):
    """A step before each block after the first — except one that follows a
    heading, because a sub-head and what it introduces arrive together."""
    out = []
    for i, (k, v) in enumerate(shown):
        if i and k != "head" and shown[i - 1][0] != "head":
            out.append(("step", "<!-- step -->"))
        out.append((k, v))
    return out


def fit_file(path, rel, fm, body, opts, budget):
    level = 3 if opts.grain == "subsection" else 2
    us = units(body, level)
    if not any(b.strip() for _, b in us):
        # metadata and nothing else. The teaser is still the author's sentence.
        us = [(fm.get("title") or stem(rel), fm.get("teaser", ""))]
    made = []
    for i, (t, b) in enumerate(us):
        made += fit_unit(t or fm.get("title") or stem(rel), b, fm, i == 0, budget)
    if opts.grain == "fill":
        made = merge(made, budget)
    for i, s in enumerate(made):
        s["file"], s["rel"] = path, rel
        s["skip"] = not on_stage(rel, fm, opts.on_stage)
        s["summary"] = fm.get("teaser", "") if i == 0 else lead_sentence(s)
        if i == len(made) - 1 and fm.get("recallQ"):
            s["said"] = s["said"] + [("para", "%s — %s" % (fm["recallQ"], fm.get("recallA", "")))]
        if opts.reveal:
            s["shown"] = reveal(s["shown"])
    return made


def lead_sentence(s):
    """A purpose line, taken from what the author already wrote. Nothing here
    writes a sentence — that is a model's job, and it is asked for."""
    for k, v in s["said"] + s["shown"]:
        if k in ("para", "quote"):
            first = re.split(r"(?<=[.!?])\s", as_prose(v))[0]
            return first if len(first) < 180 else ""
    return ""


def stem(rel):
    return re.sub(r"[-_]+", " ", os.path.basename(rel)[:-3]).strip().capitalize()


def on_stage(rel, fm, pattern):
    if not pattern:
        return True
    m = re.match(r"^([A-Za-z][\w-]*)=(.*)$", pattern)
    if m:
        return str(fm.get(m.group(1), "")).strip() == m.group(2).strip()
    return re.search(pattern, rel) is not None


# --------------------------------------------------------------- writing ----

TAGS = {"spine": "S", "depth": "D", "evidence": "E", "sidebar": "B", "game": "B",
        "question": "B"}


def slide_md(n, s, fm):
    tag = TAGS.get(str(fm.get("type", "")).strip(), "S")
    lines = ["### %d. `[%s]` %s" % (n, tag, s["title"] or "Untitled"), ""]
    if s["summary"]:
        lines += ["*Summary:* " + s["summary"], ""]
    if s["skip"]:
        lines += ["*Skip:* yes", ""]
    body = "\n\n".join(v for _, v in s["shown"]).strip()
    if body:
        lines += [body, ""]
    note = " ".join(as_prose(v) for _, v in s["said"]).strip()
    if note:
        lines += ["*Delivery note:* " + note, ""]
    return "\n".join(lines)


def emit(groups, out_dir, title):
    slides_dir = os.path.join(out_dir, "slides")
    os.makedirs(slides_dir, exist_ok=True)
    for i, (group, rows) in enumerate(groups.items()):
        parts, n, sub = ["# " + group, ""], 0, None
        for s, fm in rows:
            if s.get("sub") and s["sub"] != sub:
                sub = s["sub"]
                parts += ["## " + sub, ""]
            n += 1
            parts.append(slide_md(n, s, fm))
        name = "%02d-%s.md" % (i + 1, re.sub(r"\W+", "-", group.lower()).strip("-") or "section")
        open(os.path.join(slides_dir, name), "w", encoding="utf-8").write("\n".join(parts).rstrip() + "\n")
    json.dump({"title": title}, open(os.path.join(out_dir, "deck.meta.json"), "w",
                                     encoding="utf-8"), indent=2, ensure_ascii=False)
    return slides_dir


def copy_figures(rows, figs_src, out_dir):
    """Which drawings the deck asks for, which of them exist, and — once there is
    somewhere to write — the files themselves, beside the slides where
    build_bundle.py looks for them."""
    wanted, missing = set(), []
    for s, _ in rows:
        for _, v in s["shown"]:
            wanted |= set(re.findall(r"!\[\[([A-Za-z0-9._-]+)", v))
    dst = os.path.join(out_dir, "figures") if out_dir else None
    if dst:
        os.makedirs(dst, exist_ok=True)
    for fid in sorted(wanted):
        src = os.path.join(figs_src, fid + ".svg") if figs_src else None
        if src and os.path.exists(src):
            if dst:
                shutil.copyfile(src, os.path.join(dst, fid + ".svg"))
        else:
            missing.append(fid)
    return wanted, missing


# ------------------------------------------------------------ the invariant --

def conserved(sources, rows):
    """Not a word is lost. The whole design rests on this, so it is checked
    rather than believed: every word of every document has to come out in a
    title, a body or a note."""
    before = collections.Counter()
    for text in sources:
        before.update(words(text))
    after = collections.Counter()
    for s, _ in rows:
        after.update(words(s["title"] or ""))
        for _, v in s["shown"]:
            after.update(words(v))
        for _, v in s["said"]:
            after.update(words(v))
        after.update(words(s.get("summary") or ""))
    lost = before - after
    return sum(before.values()), sum(lost.values()), lost


def main():
    ap = argparse.ArgumentParser(description="Lay a document out as a deck.")
    ap.add_argument("--src", required=True, help="a folder of markdown documents")
    ap.add_argument("--out", help="where to write the deck's markdown; omit to only report")
    ap.add_argument("--figs", help="where the documents' .svg figures live")
    ap.add_argument("--grain", choices=("fill", "section", "subsection"), default="fill")
    ap.add_argument("--on-stage", default="", metavar="PATTERN",
                    help="a regex on the path, or key=value on the frontmatter; the rest come in hidden")
    ap.add_argument("--reveal", action="store_true", help="a step between the blocks of a slide")
    ap.add_argument("--title", default="", help="the deck's title")
    ap.add_argument("--calibrate", default=os.path.join(ROOT, "decks", "isd2026.json"))
    opts = ap.parse_args()

    budget, sampled = calibrate(opts.calibrate)
    print("  budget %.1f lines a column%s" %
          (budget, " (from %d slides of %s)" % (sampled, os.path.basename(opts.calibrate))
           if sampled else " (default — nothing to calibrate on)"))

    files = []
    for dirpath, _, names in os.walk(opts.src):
        for n in sorted(names):
            if n.endswith(".md") and not n.startswith("_"):
                files.append(os.path.join(dirpath, n))
    files.sort()
    if not files:
        sys.exit("no .md under " + opts.src)

    groups, rows, sources = collections.OrderedDict(), [], []
    for path in files:
        rel = os.path.relpath(path, opts.src)
        text = open(path, encoding="utf-8").read()
        if DECK_RE.search(text):
            print("  %s is already a deck, not a document — nothing to do" % rel)
            return 2
        fm, body = frontmatter(text)
        body = figrefs(body)
        sources.append(body)
        group = (os.path.dirname(rel).split(os.sep)[0] if os.sep in rel else "") or \
                opts.title or os.path.basename(os.path.abspath(opts.src))
        group = re.sub(r"^\d+[-_]", "", group).replace("-", " ").replace("_", " ").strip().title()
        for s in fit_file(path, rel, fm, body, opts, budget):
            s["sub"] = fm.get("title") or stem(rel)
            groups.setdefault(group, []).append((s, fm))
            rows.append((s, fm))

    stage = [s for s, _ in rows if not s["skip"]]
    per = sorted(load(s["shown"]) for s in stage) or [0]
    over = [s for s in stage if load(s["shown"]) > budget + 0.01]
    spoken = sum(len(words(v)) for s, _ in rows for _, v in s["said"])
    shown_w = sum(len(words(v)) for s, _ in rows for _, v in s["shown"])
    total, lost, which = conserved(sources, rows)

    print("  %d documents · %d slides · %d on stage · %d hidden"
          % (len(files), len(rows), len(stage), len(rows) - len(stage)))
    print("  fill %d%% of the frame at the median · %d slides still over it"
          % (100 * per[len(per) // 2] / budget, len(over)))
    print("  %d words shown · %d words spoken · about %d min on stage"
          % (shown_w, spoken, len(stage) * 70 / 60))
    wanted, missing = copy_figures(rows, opts.figs, opts.out)
    print("  %d figures referenced%s" %
          (len(wanted), (", %d not found: %s" % (len(missing), ", ".join(missing[:4])))
           if missing else ""))
    print("  %s not a word lost, of %d" % ("PASS" if not lost else "FAIL", total))
    if lost:
        print("       missing: " + " ".join(list(which)[:12]))
    for s in over[:5]:
        print("  over the frame: %s (%s)" % (s["title"], s["rel"]))

    if not opts.out:
        print("\n  (nothing written — pass --out to write the deck's markdown)")
        return 1 if lost else 0
    slides_dir = emit(groups, opts.out, opts.title or list(groups)[0])
    print("\n  written to %s" % slides_dir)
    print("  python3 scripts/build_bundle.py --src %s --figs %s --out decks/deck.json%s"
          % (slides_dir, os.path.join(opts.out, "figures"),
             ' --title "%s"' % opts.title if opts.title else ""))
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
