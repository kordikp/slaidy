# Converting a presentation into SlAIdy — for agents

Someone has a deck in PowerPoint, Keynote, Google Slides, Canva or a PDF, and has told you
something like *"convert my presentation to SlAIdy (github.com/kordikp/slaidy), theme paper"*.
This page is the procedure. Read [`AGENTS.md`](../AGENTS.md) too: it is the contract for
pictures, and it applies to everything below.

What you deliver is a folder of markdown and SVG that builds into one deck, the deck as
JSON, and the deck as one HTML file that presents from a disk. The person should be able
to open it, press `P`, and give the talk.

## Two ways to convert: lean and rich

**Lean is the default.** A SlAIdy deck is meant to stay small and readable: words as
markdown, diagrams as SVG drawings a model can read and change, pictures only where nothing
else will do. A lean deck is tens of kB a slide, diffs well in git, and the next agent can
work on every part of it.

**Rich is for when the person says the deck is for people more than for machines:** "make
it wow", "keep the photos", "it is for a big audience", "efektní", "pro lidi". It spends
bytes on the eye: more photographs, full-bleed pictures, bitmaps kept where a redraw would
lose their charm, and motion on top of them. If the request does not say, convert lean,
and say in your report that rich is available.

| | Lean (default) | Rich |
|---|---|---|
| words | markdown | markdown, the same |
| diagrams, charts, timelines, process steps, icon rows | redrawn as SVG | redrawn as SVG; an intricate infographic may stay a picture, with its words copied into the notes |
| photographs, screenshots | kept only when they carry content | kept, also for mood: a full-bleed photo on a title or a section slide |
| decoration: stock photos, textures, clip art, the template's strips and logos | dropped; the theme draws the brand | the template's still dropped; photos that set the mood kept |
| picture size | as small as it is shown: about 1000 px for half a slide | up to 1920 px, WebP |
| motion | builds by click (`data-step`), light CSS animation in drawings | also motion on pictures: a slow zoom, a reveal, annotations that arrive one by one |
| budget | under 50 kB a slide on average; a figure under 15 kB | under 400 kB a picture; a 40-slide deck under 15 MB |

What does not change between the two: text stays text (never a picture of words), every
picture has a description, measured results are never redrawn or "improved", and nothing is
invented. Generate an illustration only when the person asks for one, and say in its
description that it is generated.

## 0. What to settle first

From the request, or by asking once, in one message:

- **lean or rich** (default lean);
- **the theme**: one from [`themes/`](../themes/README.md), `none`, or "keep the original
  colours" (then set `accent`, `ink` and `paper` in `deck.meta.json` from the original);
- **the language** of the deck (keep the original's unless told otherwise);
- **whether to shorten**: all slides, or a talk of a given length.

## 1. Read the original

```bash
S=path/to/slaidy                                   # a clone of github.com/kordikp/slaidy
python3 $S/scripts/ingest.py talk.pptx sources/    # or talk.pdf
```

This reads the file without any model and writes:

| | |
|---|---|
| `sources/inventory.md` | every slide: title, text in reading order, tables, **the numbers behind each chart**, pictures with size, alt text and how much of the slide they cover, how many shapes and connectors are drawn on it, and the speaker notes |
| `sources/render/s01.png` | each slide as it looks, 1000 px wide |
| `sources/media/s01-1.png` | the pictures of each slide, each written once; a picture on three slides or more is listed at the top as the template's |

Read `inventory.md` whole. Look at each render **once**, at the size it is, to see what the
inventory cannot say: the layout, which shapes form a diagram, what a picture shows. Do not
open the .pptx XML or the PDF yourself; the inventory has what is in them, at a fraction of
the size.

- **PowerPoint** `.pptx` is read directly. `.ppt`, `.pps`, `.odp` and `.key` go through
  LibreOffice; if that fails, ask for a .pptx or a PDF.
- **Keynote, Google Slides, Canva:** ask for an export as .pptx (it keeps the text, tables,
  charts and notes); a PDF is the fallback.
- **PDF:** text comes per page with its layout, and the embedded pictures are pulled out.
  There are no speaker notes and no chart data in a PDF, and a page that is one big picture
  is marked *no text layer*: retype what it says, or keep it as a picture in rich mode.
  For a vector chart in a PDF, `pdftocairo -svg -f N -l N talk.pdf page.svg` gives the page
  as SVG to **read coordinates from**; it is far too large and too glyph-ridden to place.
- **Beamer** with draw.io figures: [`tools/drawio/`](../tools/drawio/README.md) recovers the
  drawings as editable SVG and imports the LaTeX.
- **Marp, reveal.js, plain markdown:** the text maps almost one to one onto the format in
  step 3.
- **Speaker notes** of the original become `*Delivery note:*`. Keep them, in the original's
  words; tidy only the obvious.
- An **EMF/WMF** picture is a vector drawing: `inkscape x.emf -o x.svg` or
  `soffice --headless --convert-to svg x.emf` gives you something to redraw from.
- **Video and audio** do not play in SlAIdy: a still of the video as a picture and a link to
  it in the slide.

## 2. Plan before drawing

Write the plan as a table, one row per original slide: what it becomes, and for each visual
on it the decision: **text**, **table**, **redraw** (SVG), **chart** (SVG from the numbers),
**picture** (kept), or **drop** (and why). Merge slides that say one thing twice; split one
that says three. For a deck over 15 slides, show the plan to the person before you draw,
since drawing is where the time goes.

Decide with these questions:

- Is it a diagram, however it was made: boxes, arrows, a cycle, a timeline, a SmartArt, a
  row of icons? **Redraw it.** Many shapes and connectors in the inventory mean exactly this.
- Is it a chart? **Draw it from the numbers** the inventory gives. Without numbers (a chart
  pasted as a picture, a PDF), read them from the render only if they are labelled on it;
  otherwise keep the chart as a picture. Never estimate values from bar heights.
- Is it a photograph, a screenshot, a measured plot, a scan? **Keep it as a picture.**
- Is it the template's: a logo in the corner, a coloured strip, a footer? **Drop it.** The
  theme draws the header, the footer, the cover and the closing.
- Is it decoration (a stock photo of a handshake, a texture)? **Drop it** in lean, keep it
  in rich if it sets the mood.

## 3. Write the slides

```
talk/
  sources/             what ingest.py wrote; the original file too, never modified
  slides/              01-intro.md, 02-…: one file a section
  slides/deck.meta.json
  figures/             one SVG a figure
  figures/assets/      pictures, named by their content, and assets.json
  decks/talk.json      built
  build/talk.html      built: the deck and SlAIdy in one file
```

`slides/deck.meta.json`:

```json
{
  "title": "The talk's title",
  "meta": {"author": "…", "affiliation": "…", "event": "…", "venue": "…", "date": "…"},
  "style": {"accent": "#0065BD", "ink": "#1D1D1B", "paper": "#FFFFFF", "titleSize": 38, "bodySize": 22, "header": "position"},
  "groups": {"01-intro.md": "Introduction"}
}
```

A slide:

```markdown
### 4. `[S]` Hosting in Europe is not sovereignty

*Summary:* The one thing this slide is for, in a line.

![[fig-sovereign|90%]]

> The line that has to land.

*Delivery note:* What the speaker says. The original's notes go here.
```

- `### 4. `[S]` Title` starts a slide. `build_bundle.py` needs the number and the tag on every
  slide (without them a file is read as one long page); the numbers need not be in order,
  the build counts again. The tag is `S` for an ordinary slide.
- `*Layout:*` `cover` for the first slide, `closing` for the last; `two` or `three` columns
  with `<!-- col -->` where a column ends; `background` for a full-bleed figure.
- `![[fig-id]]` places a figure, `![[fig-id|80%]]` at a size.
- Lists, tables (`| a | b |`) and `>` key lines project. **Prose does not belong on a slide:**
  in lean mode a paragraph of the original becomes either a short list or a note.
- `<!-- step -->` holds what follows for the next click: the original's build animations.
- `$x^2$` and `$$ … $$` are formulas.
- `*Skip:* yes` keeps a slide in the deck but hides it when presenting (the original's
  hidden slides, a backup slide).

The whole format is in [DESIGN.md](DESIGN.md#the-format).

## 4. Draw the figures

A figure is an SVG file in `figures/`, its name is its id. House rules:

- **The markup is the finished state.** With animation off, the figure still reads
  completely. Motion is CSS `@keyframes` in the figure's own `<style>`, on `transform` and
  `opacity`; no SMIL, no script.
- **Click by click:** `data-step="2"` on an element = there from the second click,
  `data-until="3"` = gone at the third. The slide derives its number of clicks.
- **Text is `<text>`**, never paths. `font-family="inherit"` on the root `<svg>` and the
  figure takes the theme's font. To follow the theme's colours too, use
  `style="fill:var(--d-accent)"`, `var(--d-ink)`, `var(--d-paper)`.
- `viewBox` only, no fixed `width`/`height`; a full-width figure is about `0 0 1200 500`.
- No external references, no `data:` URIs, no `<foreignObject>`.
- Every label inside its box, nothing under the slide's edge: `scripts/check_figures.sh`
  checks it (step 6).

**A chart from the inventory's numbers** is a few rectangles and labels. Write the values
on the bars and the units on the axis, and keep every number exactly as the original has it.

**A picture:**

```bash
python3 $S/scripts/assets.py add figures/ sources/media/s07-1.jpg --desc "What the photo shows, in a sentence"
```

It is shrunk to 1920 px, stored as WebP and named by its content; the command prints the
name. In lean mode, shrink it first to the size it is shown at. Place it in a figure:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675">
  <image href="asset:img-…" x="0" y="0" width="1200" height="675" preserveAspectRatio="xMidYMid slice"/>
</svg>
```

Write the description from what you saw in the render, or from the original's alt text when
it is a real one ("Obsah obrázku text, Písmo…" is PowerPoint's guess, not a description).
A logo: `--trim` cuts its margins.

**Rich mode, the wow on top of a picture** (all of it SVG and CSS, the picture untouched):

- a full-bleed photo on a `background` slide with a translucent band behind the title, so
  the words stay legible;
- a slow zoom while the slide is up: `@keyframes z{from{transform:scale(1)}to{transform:scale(1.06)}}`
  on the `<image>`, `transform-origin:center; transform-box:fill-box`, 15–20 s;
- annotations that arrive one by one on a screenshot: arrows and labels with `data-step`;
- a reveal: the picture under a shape that slides away, or a `clipPath` that grows;
- numbers that count up, bars that grow: CSS on SVG, the same as in lean mode.

## 5. Build

```bash
python3 $S/scripts/build_bundle.py --src slides --figs figures --out decks/talk.json --force
python3 $S/scripts/use_theme.py decks/talk.json paper        # or --keep to keep deck.meta.json's colours
python3 $S/scripts/onefile.py decks/talk.json build/talk.html
```

Building from the markdown leaves the theme out, so run `use_theme.py` after every build.
`--force` is needed because the theme made the deck newer than its markdown.

## 6. Check

```bash
$S/scripts/check_figures.sh $PWD/decks/talk.json             # labels past an edge, on each other, crossed by a line
node $S/scripts/shots.mjs build/talk.html                    # every slide as the projector shows it, into shots/
python3 $S/scripts/ingest.py --missing sources/ decks/talk.json
python3 $S/scripts/assets.py list decks/talk.json            # every picture, its size and description
ls -l decks/talk.json build/talk.html
```

- Put each shot beside the original's render. Every slide keeps its point. Nothing runs past
  the edge. Text is readable from the back of a room (body text no smaller than the theme's).
- `--missing` lists, slide by slide, the numbers of the original that appear nowhere in the
  deck. Each one is either a deliberate cut you will report, or a fact you lost; put it back.
- Check the budget for the mode. In lean mode, a picture over 200 kB or a figure over 30 kB
  needs a reason. A theme's fonts are a fixed 100–400 kB that the per-slide budget leaves
  out.

## 7. Report

Tell the person, briefly:

- where the deck is (`build/talk.html` opens from a disk; `P` presents, `N` shows the notes)
  and how to edit it (`./studio.sh decks/talk.json` in a SlAIdy clone);
- the mode and the theme, and the other mode in one line if they did not choose;
- slides in and out: what was merged, split or dropped, and why;
- what was redrawn and what was kept as a picture;
- the numbers `--missing` reported and what you did about each;
- the size: deck, and the largest pictures;
- what you could not carry: a video, a font, an animation the format has no equivalent for.

## Working economically

- `ingest.py` first, always. A few kB of inventory a slide replaces reading hundreds of kB
  of XML, and the renders replace guessing.
- Look at each render once, small. Do not open the media files to look at them unless the
  render does not show enough.
- Never read a deck JSON's `assets`: it is base64. `assets.py list` says what is there.
- Write a script for anything you do to more than a handful of slides the same way.
- For a long deck, go section by section: write, build, check, then the next.
