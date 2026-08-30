# Slide Studio

A slide editor in one HTML file, where the deck stays a folder of markdown.

You edit in the browser, present full screen, and export a PDF — but the deck on disk
is `.md` files and `.svg` figures the whole time. Nothing is locked inside the
application, and if the application disappears you still have a deck.

```bash
git clone https://github.com/kordikp/slide-studio
cd slide-studio
./studio.sh
```

That serves the example deck at `http://localhost:8080` and opens it. Press `?` for
the shortcuts, `P` to present.

---

## The idea

Most slide tools own your content. Markdown-to-slides tools give the content back but
take away the editing. This does both: the markdown is the source of truth, and the
browser is a real editor on top of it — drag slides, edit figures, present, export.

Three properties fall out of that:

- **One stage, three surfaces.** The editor, the projector and the PDF render the same
  1280×720 markup and differ only in how far it is scaled. What you arrange is what the
  room sees. (They used to be three renderers, and they drifted.)
- **Round trips are guarded.** A test checks that markdown → bundle → markdown loses
  nothing. It exists because a regex once quietly ate 3539 words.
- **Figures are editable.** They are SVG, so you can select, move, resize, group and
  recolour their parts — and point a model at one element rather than the whole picture.

---

## The format

A section is a file. A slide is a `###` heading.

```markdown
# I · First Section

## Room 1 — Alpha

### 1. `[S]` A deck is a folder of markdown

*Summary:* What this slide is for, in one line.

**Figure:** `fig-markdown-truth` · split-r

*Bestseller:* yes

- A list, a table or a quote is *shown*
- Prose is what you *say*

> The line that has to land.

*Delivery note:* Speaker notes. Not projected.
```

| Line | Means |
|---|---|
| `### n. `[S]` Title` | a slide. The tag is `S` practical, `D` in depth, `E` evidence, `B` aside. Writing just `### Title` is fine — the rest is filled in. |
| `**Figure:** \`id\` · layout` | the figure and how it sits: `figure`, `split-l`, `split-r`, `background`, `text` |
| `*Summary:*` | one line saying what the slide is for. Editable, and usable as an instruction to the AI |
| `*Bestseller:*` | in the short run (see below) |
| `*Delivery note:*` | speaker notes |
| `> …` | a key line — it projects |
| `![[fig-id]]` | places a figure inline, anywhere in the body |
| `<!-- gap -->` | vertical space. An HTML comment, so every other renderer shows nothing |
| `***` | a divider. `---` is taken: it separates slides |

`deck.meta.json` beside the slides carries the title, the event details and the visual
style, so rebuilding from markdown never loses them.

Build a bundle the browser can open:

```bash
python3 scripts/build_bundle.py --src example/slides --figs example/images \
    --out decks/example.json --title "My Talk"
```

---

## What it does

**Editing.** Click the title on the slide to change it. Speaker notes sit under the slide and
render as text, so a link to the paper behind the slide is clickable while you write and
while you present; click the text to edit it. Hover a paragraph for move and
delete; the icon row inserts text, lists, tables, a divider, a spacer or a figure.
Double-click a section heading in the list to rename it on every slide under it. Drag a
slide anywhere and it adopts the section it lands in. `Ctrl-Z` covers the last forty
changes — one snapshot per gesture, not per keystroke.

**Figures.** A click on a picture opens its editor — editing is what you almost always
want; swapping it is a separate button. Adding one asks which you meant: pick from the
library, or describe what it should show and have it drawn to the same rules as the rest.
Every picture carries its own size, inline ones included: `![[fig-id|60%]]`.

Inside the editor: click takes the whole object, double-click steps inside, `Esc` steps back
out. Lines and arrows are **drawn by dragging**, from one point to any other, and a selected one
shows a handle at each end instead of corner handles. `Ctrl-J` joins two selected objects with an
arrow that **re-routes itself** when either of them moves — the join is stored as `data-from` and
`data-to` on the arrow, so it survives a save.

The **Source** tab reads the drawing as structure rather than coordinates: the element, then its
words, then the attributes worth editing by hand, with geometry dimmed and long values cut short.
Selecting on the canvas scrolls the source to that element; clicking a line selects it. `Edit as
text` is still there when you want the raw thing.

> No SVG library is vendored, and that is deliberate. The editing ones — Fabric and its kin — parse
> a document into their own object model and re-serialise on export, which would not survive figures
> that carry hand-written `<style>` keyframes, `<defs>`, `<use>` and comments. The ones that leave
> the DOM alone are drawing APIs, not editors: they give you `rect()` and `line()`, not selection,
> handles, grouping or connectors. What is needed here is small, specific, and has to keep the file
> diffable. Drag empty space to lasso what you enclose (`Alt` for what you touch). Handles
resize about the opposite corner, corners keeping proportions. `Ctrl-G` groups,
`Ctrl-Shift-G` ungroups, `Ctrl-E` lifts an element out of its group carrying the
wrapper's transform with it. Shapes and text can be added; anything can be duplicated.

The canvas is an `<iframe>`. A figure carries its own `<style>`, and inlined, those
rules are global — which is how a figure once animated the application's toolbar off
the screen. Inside a frame they cannot reach the page at all.

**Presenting.** `P` goes full screen. `N` shows notes, `O` an overview grid, `B`
switches between the whole deck and the short run.

**Hiding slides.** Hide a slide and the presentation walks past it; it stays in the file
and in the list, greyed. `H` hides the current one, and `H` while presenting walks the
hidden ones too, for a rehearsal. `⋯ → Trim to length` does it in bulk: it hides the
slides that do the least work until the deck fits, sharing the budget between sections in
proportion to their length so the talk keeps its shape. Slides flagged `keep` are never
hidden automatically.

```bash
python3 scripts/short_run.py --minutes 45 --dry-run
```

**Checking the figures.** `scripts/check_figures.sh` renders every figure and looks for text
that collides with something: a label running past the canvas edge, two labels on top of
each other, a connector crossing the words. Animated labels are skipped in the collision
check — two that alternate share a spot on purpose, and a static measurement cannot tell.

**Removing what the figure already says.** `scripts/dedupe.py` compares each block of a
slide against the labels in its figure and moves the repeats into the speaker notes. Key
lines are never touched: a good one names what the picture shows and then says what it
means, and word overlap cannot tell that apart from an echo.

**Fitting.** `scripts/fit_slides.py` separates what is shown from what is said —
lists, tables and key lines stay on the slide, prose moves to the speaker notes — and
picks the layout from what is left.

**Design with AI.** One line saying what the slide is for, which doubles as the instruction.
The panel walks you through it: an empty slide says so and offers nothing; a slide with
content offers **Summarise**; once there is a line it becomes editable, and **Update the
slide** only wakes up when you have actually changed it. Inside the figure editor the same
idea applies to one selected element rather than the whole slide.

**Tidy.** Layout is arranged by measuring, not by guessing: the slide is drawn into a hidden
stage at full size once per candidate arrangement, and the one that fills the frame without
clipping anything wins. The dials are the layout, the size of the figure, whether the slide
sits in the middle, and — only to rescue an overflow — the body size. **It never changes a
word.** The panel tidies the slide in front of you; `⋯ → Tidy every slide` does the deck.
One undo reverses either.

**Export.** PDF through the browser's own print engine (nothing is uploaded), markdown
in the shape you started with, one `.json` bundle carrying slides and figures, or the deck
**as an article**: the figure, what you would have said about it, then the line meant to
land. Hidden slides stay out. The HTML is self-contained — open it, select all, paste, and
Substack or Medium take the figures with it.

**AI.** Optional, and off unless you give it an endpoint. `studio.sh` runs a small
proxy that forwards to OpenAI using `OPENAI_KEY`, so the key stays on your machine and
never reaches the page:

```bash
export OPENAI_KEY=sk-...   # or put it in .env beside studio.sh
./studio.sh                # prints "AI: on, <model> via <endpoint>"
```

A `.env` in the same directory is read if the variable is not already set —
`OPENAI_KEY`, `OPENAI_API_KEY` and `STUDIO_MODEL`, and nothing else.

Or point `⋯ → AI endpoint` at any OpenAI-compatible `/chat/completions` yourself, in
which case the key is held by the browser. Without either, the panels say so plainly.

`scripts/generate_figures.py` generates figures from a contract file against a locked
design system — a fixed canvas, a fixed palette, CSS keyframes, and a validator that
rejects anything unreadable at projection size.

---

## Storage, and what to trust

While you edit, the deck lives in the browser's IndexedDB, with localStorage as a
fallback and a timeout on every call so blocked storage cannot hang the app. The status
pill in the toolbar tells the truth: `saved 20:51`, or `saved · local storage`, or a red
`⚠ NOT saved` that downloads a backup when you click it. Version snapshots are kept
under `⋯ → Version history`.

**Keep `Export → Deck bundle` for anything you care about.** Browser storage is tied to
the address you opened the app from, and disappears with a cleared cache. Always start
the app the same way.

---

## Development

```bash
python3 scripts/test_roundtrip.py     # markdown -> bundle, content loss
tests/run.sh                          # 253 browser tests, headless Chrome
tests/run.sh t5 t6                    # just those
```

The browser suite loads the app in an iframe, drives it, and collects PASS/FAIL lines.
It runs against `tests/fixture.json`, generated by `tests/make-fixture.py` — a deck with
shape rather than content: several sections, subsections, every layout, and one figure
built the way a real one is, with nested groups carrying their own ids.

The app is one file, `slide-studio.html`, with no build step and no dependencies. Open it
directly and it works; serve it and it can also load a deck by itself and reach an AI
endpoint.

Requirements: Python 3 for the scripts, Chrome or Chromium for the tests. Nothing else.

---

## Licence

MIT. See [LICENSE](LICENSE).
