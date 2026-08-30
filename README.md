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

**The list.** Each slide shows a dot for what is on it — words alone, words and a picture,
a picture alone, or a table — which is the thing worth seeing when you are scanning two
hundred of them. A hidden slide stays in the list, greyed and struck through, rather than
disappearing.

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

**Design with AI.** What the panel offers depends on what is on the slide.

An **empty slide** does not hand you a blank box. **Suggest what goes here** reads where the
slide sits — the deck, the section, the four slides either side — and comes back with three
named ideas: a title, one line on what this slide does that its neighbours do not, and a
specification of what goes on it, what a figure would show, what a table would compare and
what it should cite.

**The title and the specification are editable before you build.** A proposal you cannot
adjust is one you take whole or throw away, and the useful case is almost always *yes, but*.
What is in the box is what gets built.

Then it is developed, not sketched: a figure where a picture carries the point, a table where
the content is really a comparison, a short list where it is an enumeration, the line that has
to land, and speaker notes for what is said rather than shown. Links come **only from the ones
this deck already carries** — its own section first — because a model asked for a citation will
otherwise invent an arXiv id that resolves to something else; one that slips through anyway has
its target dropped and its words kept. The layout is measured once the figure exists.

Or say it yourself in the box, with starter chips for the usual shapes.

A slide **with content** offers **Summarise**: one line saying what the slide is for, which
then doubles as the instruction — edit the line and **Update the slide** rewrites the slide
to deliver it. That button only wakes up once you have actually changed the line. Inside the
figure editor the same idea applies to one selected element rather than the whole slide.

**A figure that was asked for gets drawn.** When the model decides a slide wants a picture it
writes `![[fig-something]]`, and the app then draws it — same design system, same 800×450
canvas, same palette as everything else. It used to leave the reference dangling and the
slide reported a missing figure. If a drawing fails, the reference stays on the slide as a
box offering **Draw it**, **Pick one** and **Remove**, rather than as an error message.

**It says when it is working.** Every model call shows a labelled bar under the button that
started it, and multi-step work says which step it is on (`drawing fig-walls · 2 of 3`). The
bar creeps toward the end of the current step's band and only reaches it when that step
actually finishes, so it never claims progress it has not made.

**Tidy.** Layout is arranged by measuring, not by guessing: the slide is drawn into a hidden
stage at full size once per candidate arrangement, and the one that fills the frame without
clipping anything wins. The dials are the layout, the size of the figure, whether the slide
sits in the middle, and — only to rescue an overflow — the body size. **It never changes a
word.** The panel tidies the slide in front of you; `⋯ → Tidy every slide` does the deck.
One undo reverses either.

**Export.** PDF through the browser's own print engine (nothing is uploaded), markdown
in the shape you started with, one `.json` bundle carrying slides and figures, or the deck
**as an article**: the figure, what you would have said about it, then the line meant to
land. Hidden slides stay out.

The article goes out four ways. HTML with the figures inline as SVG is the smallest and
sharpest. HTML with the figures **rasterised** is the one to paste into Substack or Medium,
which will not take an inline SVG. A **`.docx`** carries the pictures inside a real Word
file — for LibreOffice, or for Google Docs when you want comments on it; it is written by
hand, zip and all, rather than by pulling in a library. And markdown, referencing the
figures as files.

**Pictures on a slide.** Hovering one gives it a toolbar in its own corner and a grip at
the bottom right: drag to size it, live, with the percentage shown. Every picture carries
its own size, hero or inline, so a slide with two of them sizes each on its own. When
something spills past the frame the warning offers to fix it — fit the slide, shrink the
picture, or move what is over the edge into the speaker notes — and the frame scrolls in
the editor so the thing you need to reach is reachable.

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

## Where the deck lives

**The deck file is the document.** One `.json` holding the slides, the figures and the
settings — you open it, you edit it, you save it, the way any editor works.

Started with `studio.sh`, the **server owns that file**: it serves the real file at
`/deck.json` and writes it back at `/api/deck`. Every save goes to the file on disk, the
status pill names it (`saved 20:51 → decks/my-talk.json`), and there is nothing to
re-permission after a restart. Opened another way, Chrome can hold a file handle instead;
without either, the deck lives in the browser's own storage and the pill says
`in this browser only` rather than pretending otherwise.

Markdown is how a deck comes **in** and goes **out**, not where it lives. `⋯ → Import
markdown` reads a folder of `.md` files, says what it found — how many slides, which
sections, which figures are referenced but missing — and only then imports.

### Not losing work

Everything here exists because a version of it once failed.

- **The deck is never copied to be served.** It used to be, and `cp` stamps the copy with
  the current time — so on every restart the served deck looked newer than the edits held
  in the browser, and the edits lost.
- **A save that fails says so loudly** — a banner, not just a pill — and offers a download.
  The browser copy is written *first* and unconditionally, so the one moment the safety net
  is needed is not the moment it gets skipped.
- **A file that changed underneath is never overwritten.** Each save carries the version it
  started from; if another tab or a script has written the file since, the server answers
  409 and the app says so. Nobody's work disappears quietly.
- **Rebuilding from markdown refuses to clobber a newer deck.** `build_bundle.py` compares
  mtimes and stops, naming both, unless `--force`.
- **Version history** (`⋯ → Version history`) keeps twelve snapshots, and each row says what
  that version has that the deck in front of you does not — *3 figures differ
  (fig-affiliation…) · 2 titles differ* — because "237 slides" is no help when you are
  hunting one edited figure. Restoring snapshots the current state first and is undoable.
- **Closing the window with unsaved changes warns.**

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
