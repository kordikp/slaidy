# From Beamer and draw.io to a deck that clicks

A lecture written in Beamer with figures drawn in draw.io and exported as PNG
usually has the vectors still inside those PNGs: draw.io writes the diagram's
XML into a `tEXt` chunk of every image it exports. These tools get the drawings
back, render them as editable SVG, merge a series of saves (`fig001.png`,
`fig002.png`, …) into **one** figure whose shapes carry the click they arrive on,
and import the LaTeX as slides. The worked example is the Matrix Factorization
lecture (FIT CTU): 56 PNGs and one `.tex` became 35 slides, 14 figures and
76 clicks, at half the size of the one-figure-per-click version.

Read `../../AGENTS.md` too if an AI agent does the conversion.

## The procedure

Run everything **in the lecture's own folder**. The tools take their default
paths from there:

```
sources/        the .tex and every image it includes, never modified
drawio/         the drawings recovered from the PNGs
figures/        one SVG per figure, a series merged into one stepped figure
deck/slides/    the slides as markdown: from step 3 on, this is the source
```

```bash
S=../slide-studio                                   # where SlAIdy is

# 1. the drawings out of the PNGs (a PNG without one is reported: keep it as a picture)
python3 $S/tools/drawio/extract.py sources drawio

# 2. the figures, rendered by draw.io's own viewer in headless Chrome
python3 $S/tools/drawio/render.py                   # --only <series> for one
python3 $S/tools/drawio/preview.py                  # each figure beside its PNG, in build/preview/

# 3. the slides, once
python3 $S/tools/drawio/tex2deck.py                 # sources/*.tex → deck/slides/*.md

# 4. the deck and a one-file HTML
python3 $S/scripts/build_bundle.py --src deck/slides --figs figures --out decks/lecture.json --force
python3 $S/scripts/onefile.py decks/lecture.json build/lecture.html
```

What each step decides:

* **`render.py`** orders a series by the `.tex`, not by filename:
  `universe010b` sorts after `universe010` and the lecture shows it before. A shape
  is identified by its content (draw.io reissues cell ids between saves), so the
  merged figure records `data-step="n"` (there from click *n*) and
  `data-until="m"` (gone at click *m*), and a series in which something is
  *replaced* still works. Labels are laid out by draw.io, measured where they land
  and rewritten as real SVG `<text>`, so they stay editable. The hand-drawn font
  (Architects Daughter, a 7 kB subset, OFL) is embedded.
  The draw.io viewer (Apache 2.0, 4 MB) is fetched once into `vendor/` on first use.
  It is not kept in git.
* **`tex2deck.py`** runs **once**. After it, `deck/slides/*.md` is the deck. It
  refuses to overwrite markdown without `--force`. It knows the uic-beamer macros
  (`\simpleFigure`, `\centerBox`, `\columnSlide`, `\HO`, `\emphred`, …). Anything
  else is left visible rather than guessed: teach it the next lecture's macros
  and import again. `\pause` becomes `<!-- step -->`. The speaker notes of a
  stepped figure get one part per click, read off the labels of the shapes that
  click adds, and the projector shows the part for the click it is on.
  `deck/outline.json` names the sections. That is the one editorial decision
  left to a person.
* **A PNG with no drawing inside** (a photo, a screenshot, a plot) is not traced.
  Add it as a picture with `python3 $S/scripts/assets.py add figures <file> --desc "…"`
  and say what it shows, because the description is all a model ever sees of it.

Check every slide against the original PDF, at every click, before calling it
done. `?s=12&step=3` opens slide 12 at click 3, and
`node $S/scripts/shots.mjs build/lecture.html --steps` photographs them all.
