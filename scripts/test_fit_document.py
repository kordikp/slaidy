#!/usr/bin/env python3
r"""Guard the document -> deck pass, mostly against losing somebody's words.

The whole promise of scripts/fit_document.py is that it moves words and never
changes or drops one: prose into the speaker notes, blocks onto the next slide,
nothing summarised and nothing deleted. A promise like that is worth exactly as
much as the test under it.

    python3 scripts/test_fit_document.py
"""
import importlib.util, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("fd", os.path.join(ROOT, "scripts", "fit_document.py"))
fd = importlib.util.module_from_spec(spec); spec.loader.exec_module(fd)

fails = []
def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name}{'  ' + detail if detail else ''}")
    if not cond:
        fails.append(name)


DOC = """---
title: "How Computers Understand Similarity"
type: spine
teaser: "A machine has no intuition for similarity, so how does it compute one?"
diagram: diagram-embeddings
highlights:
  - "Embeddings put items in a space where proximity is behaviour"
  - "Neural networks find qualities handcrafted features miss"
---

A long opening paragraph that explains the problem in the author's own words and
is far too much prose to project, so it belongs in the speaker notes where it can
be said out loud instead of read off the wall by everybody at once.

## The Legacy Approach

Early systems relied on explicit labels, and the paragraph saying so is prose.

| Method | Cost | Scale |
|---|---|---|
| tags | manual | poor |
| embeddings | learned | good |

## The Modern Approach

1. Feed the network pairs of items
2. It learns to place similar things near each other
3. Every item ends up with a vector

![the space](/images/diagram-space.svg)

```python
index = faiss.IndexFlatIP(dim)
```

## Nothing But Prose

This section has no list and no table and no figure at all, only this paragraph,
which means the slide it becomes would otherwise be a title over an empty frame.
"""

ASIDE = """---
title: "A Story About Netflix"
type: sidebar
teaser: "The million-dollar prize, and what it actually proved."
---

## The Prize

Forty thousand teams entered, and the winner used matrix factorisation.
"""


class Opts:
    grain, on_stage, reveal = "fill", "", False


def fit(text, name="doc.md", opts=None, budget=15.8):
    fm, body = fd.frontmatter(text)
    return fd.fit_file(name, name, fm, fd.figrefs(body), opts or Opts(), budget), fm, body


# ---------------------------------------------------------------- reading ---
fm, body = fd.frontmatter(DOC)
check("frontmatter reads a plain key", fm.get("title") == "How Computers Understand Similarity", fm.get("title", ""))
check("and a list", fm.get("highlights[]") and len(fm["highlights[]"]) == 2, str(len(fm.get("highlights[]", []))))
check("the body starts after it", body.lstrip().startswith("A long opening"), body.lstrip()[:20])

kinds = [k for k, _ in fd.blocks(fd.figrefs(body))]
check("a table is one block", kinds.count("table") == 1, str(kinds.count("table")))
check("a fenced code block is one block", kinds.count("code") == 1, str(kinds.count("code")))
check("an image on its own line is a figure", kinds.count("fig") == 1, str(kinds.count("fig")))
check("a path becomes the deck's own reference", "![[diagram-space]]" in fd.figrefs(body))

# ------------------------------------------------------------- the pass -----
sect = Opts(); sect.grain = "section"
plain, _, _ = fit(DOC, opts=sect)
check("every heading is a slide when nothing is merged",
      {"The Legacy Approach", "The Modern Approach", "Nothing But Prose"}
      <= {s["title"] for s in plain}, " | ".join(s["title"] for s in plain)[:70])

slides, fm, body = fit(DOC)
titles = [s["title"] for s in slides]
check("the document became slides", len(slides) >= 3, str(len(slides)))
check("merging is what fills the frame", len(slides) < len(plain), f"{len(slides)} against {len(plain)}")
check("a merged heading becomes a sub-head, not a lost one",
      any(k == "head" and "The Legacy Approach" in v for s in slides for k, v in s["shown"]))

first = slides[0]
check("the teaser is the first slide's purpose", first["summary"] == fm["teaser"], first["summary"][:40])
check("the frontmatter's drawing is on it",
      any(k == "fig" and "diagram-embeddings" in v for k, v in first["shown"]))
check("so are the author's own highlights",
      any(k == "list" and "proximity is behaviour" in v for k, v in first["shown"]))
check("the opening prose is spoken, not shown",
      any("far too much prose" in v for _, v in first["said"]) and
      not any("far too much prose" in v for _, v in first["shown"]))

prose_only = [s for s in slides if s["title"] == "Nothing But Prose"]
check("a slide always shows something", prose_only and prose_only[0]["shown"],
      str(len(prose_only[0]["shown"]) if prose_only else 0))

# ---------------------------------------------------------- never cut up ----
tight = fd.split_shown(fd.blocks(fd.figrefs(body)), 3.0)     # a budget nothing fits in
for kind in ("table", "code"):
    spread = sum(1 for page in tight for k, _ in page if k == kind)
    check(f"a {kind} is never split across slides", spread == 1, str(spread))
ordered = [v for k, v in fd.blocks(fd.figrefs(body)) if k == "list" and v.lstrip().startswith("1.")]
check("an ordered list stays one block", len(ordered) == 1 and ordered[0].count("\n") == 2,
      str(len(ordered)))

# ------------------------------------------------------- not a word lost ----
rows = [(s, fm) for s in slides]
total, lost, which = fd.conserved([fd.figrefs(body)], rows)
check("not a word is lost", lost == 0, f"{lost} of {total}: " + " ".join(list(which)[:6]))

# a budget that makes it split, and a grain that makes it merge, both conserve
for grain in ("fill", "section", "subsection"):
    o = Opts(); o.grain = grain
    got, _, _ = fit(DOC, opts=o)
    _, l2, w2 = fd.conserved([fd.figrefs(body)], [(s, fm) for s in got])
    check(f"…at grain {grain} too", l2 == 0, " ".join(list(w2)[:6]))
o = Opts(); o.reveal = True
got, _, _ = fit(DOC, opts=o)
check("…and with the clicks in", fd.conserved([fd.figrefs(body)], [(s, fm) for s in got])[1] == 0)
check("a step lands between blocks, never after a sub-head",
      all(not (g["shown"][i - 1][0] == "head" and k == "step")
          for g in got for i, (k, _) in enumerate(g["shown"]) if i))

# ------------------------------------------------------------- on stage -----
o = Opts(); o.on_stage = "type=spine"
check("a frontmatter convention keeps a file on stage", not fit(DOC, opts=o)[0][0]["skip"])
check("and takes the others off it", fit(ASIDE, "aside.md", o)[0][0]["skip"])
o2 = Opts(); o2.on_stage = r"spine"
check("a path pattern does the same", fit(DOC, "01-spine-x.md", o2)[0][0]["skip"] is False)

# --------------------------------------------------- the whole way through --
tmp = tempfile.mkdtemp()
try:
    src = os.path.join(tmp, "src"); os.makedirs(os.path.join(src, "ch1"))
    open(os.path.join(src, "ch1", "01-spine-a.md"), "w", encoding="utf-8").write(DOC)
    open(os.path.join(src, "ch1", "02-sidebar-b.md"), "w", encoding="utf-8").write(ASIDE)
    figs = os.path.join(tmp, "figs"); os.makedirs(figs)
    for fid in ("diagram-space", "diagram-embeddings"):
        open(os.path.join(figs, fid + ".svg"), "w", encoding="utf-8").write(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450"></svg>')
    out = os.path.join(tmp, "out")
    run = lambda d: subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "fit_document.py"),
         "--src", src, "--figs", figs, "--out", d, "--on-stage", r"\-spine\-", "--title", "T"],
        capture_output=True, text=True)
    r = run(out)
    check("the pass runs clean", r.returncode == 0, (r.stderr or r.stdout).strip()[-90:])
    check("and says so", "PASS not a word lost" in r.stdout,
          next((l.strip() for l in r.stdout.split("\n") if "word" in l), ""))

    md = open(os.path.join(out, "slides", os.listdir(os.path.join(out, "slides"))[0]),
              encoding="utf-8").read()
    check("it writes the deck's own markdown", re.search(r"^### 1\.\s*`\[S\]`", md, re.M) is not None)
    check("the aside comes in hidden, not dropped",
          "*Skip:* yes" in md and "A Story About Netflix" in md)
    check("the prose is in the notes", "*Delivery note:*" in md)
    check("the figures came with it", len(os.listdir(os.path.join(out, "figures"))) == 2,
          str(os.listdir(os.path.join(out, "figures"))))

    again = os.path.join(tmp, "out2"); run(again)
    same = open(os.path.join(again, "slides", os.listdir(os.path.join(again, "slides"))[0]),
                encoding="utf-8").read()
    check("a second pass writes the same thing", same == md)

    deck = os.path.join(tmp, "deck.json")
    b = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_bundle.py"),
                        "--src", os.path.join(out, "slides"), "--figs", os.path.join(out, "figures"),
                        "--out", deck, "--title", "T"], capture_output=True, text=True)
    check("build_bundle reads what it wrote", b.returncode == 0, (b.stderr or "").strip()[-90:])
    if os.path.exists(deck):
        D = json.load(open(deck, encoding="utf-8"))
        check("every slide has something on it",
              all((s.get("body") or "").strip() for s in D["slides"]),
              str(sum(1 for s in D["slides"] if not (s.get("body") or "").strip())))
        check("the hidden ones are hidden", any(s.get("skip") for s in D["slides"]))
        check("the drawings are in the bundle", len(D.get("figs", {})) == 2, str(len(D.get("figs", {}))))

    # a deck is not a document
    r2 = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "fit_document.py"),
                         "--src", os.path.join(out, "slides")], capture_output=True, text=True)
    check("a deck's own markdown is refused, not wrecked",
          r2.returncode == 2 and "already a deck" in r2.stdout, r2.stdout.strip()[-60:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n" + ("all good" if not fails else f"{len(fails)} failed: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
