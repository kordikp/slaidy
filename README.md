# Slide Studio

**A slide editor in one HTML file, where the deck stays a folder of markdown.**

[![tests](https://github.com/kordikp/slide-studio/actions/workflows/tests.yml/badge.svg)](https://github.com/kordikp/slide-studio/actions/workflows/tests.yml)
[![MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)
![one file](https://img.shields.io/badge/dependencies-none-brightgreen)
![no build](https://img.shields.io/badge/build%20step-none-brightgreen)

You edit in the browser, present full screen, and export a PDF — but the deck on disk
is `.md` files and `.svg` figures the whole time. Nothing is locked inside the
application, and if the application disappears you still have a deck.

### [Try it in your browser →](https://kordikp.github.io/slide-studio/)

No sign-up and nothing uploaded; it is the same single file, served from GitHub Pages
with an example deck beside it.

```bash
git clone https://github.com/kordikp/slide-studio
cd slide-studio
./studio.sh
```

That serves the example deck at `http://localhost:8080` and opens it. Press `?` for
the shortcuts, `P` to present.

### What it is for

A talk you will give more than once, whose figures you want to keep, whose text you
want to `grep`, and whose history you want in git. If you need a deck by Thursday and
will never open it again, use anything else — this is for the deck you maintain.

**Three rules the project keeps**, in order, and which most decisions come back to:

1. **One file, no dependencies, no build step.** `slide-studio.html` opens from a
   `file://` URL and works. CI fails the build if a `<script src=>` appears.
2. **The deck outlives the editor.** Markdown in, markdown out, figures as SVG. Nothing
   the app can write is something only the app can read.
3. **One stage, three surfaces.** The editor, the projector and the PDF draw the same
   1280×720 stage from the same code, differing only by `transform: scale()`. What you
   arrange is what the room sees.

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

**Figures come out sparse, not chatty.** The design system tells the model how much text a figure
may carry, in numbers taken from the deck it is drawing for rather than from taste: across this
deck's 180 figures the median is **eleven text elements** and **four words per label**, and nearly
half the labels are one to three words. So the rule is at most twelve labels of one to four words,
the takeaway line the only sentence allowed, and *if a relationship can be drawn, do not caption
it*. A figure that will not fit in twelve labels is carrying two ideas.

**And you can add your own rule.** `⋯ → AI usage` has a box for what every figure in this
deck should obey — *three colours at most*, *arrows carry the verb* — appended to the house rules
on every figure the AI draws or revises. It lives on the deck, not in the browser, so figures come
out the same wherever it is opened and the rule travels with an export.

**Formulas.** `$x^2$` inline, `$$ … $$` on its own line. TeX in, **MathML out** — the browser
renders maths natively, so nothing is vendored for it. The subset is the one a systems talk uses:
sub- and superscripts, fractions, roots, sums and products with limits, `\mathbf`, `\hat` and
`\vec`, `argmax`, greek, the usual relations and arrows. What it cannot parse comes back as **the
TeX you typed**, marked, with the reason in its tooltip — never as something quietly wrong. `$5`
is left alone; a price is not a formula.

**Blocks.** Text, sub-head, bullets, numbers, quote, table, formula, code, figure, divider, space.
`####` and deeper are a heading *inside* a slide — `###` is what starts a new one, so a body cannot
use it. Fenced code keeps its lines and labels its language.

**Editing.** Click the title on the slide to change it. Speaker notes sit under the slide and
render as text, so a link to the paper behind the slide is clickable while you write and
while you present; click the text to edit it. **Reordering what is on a slide.** Hover a paragraph and its own controls appear in its top-right
corner: a grip to **drag it anywhere on the slide**, ＋ to insert a block **directly below it**, ▲ ▼
to move it a step, ✕ to delete. A line shows where a dragged block would land, and one undo puts
the order back. The icon row along the bottom appends instead.

These controls existed before and nobody could see them: they were positioned in a gutter at
`left:-34px`, outside the text column, which scrolls — so they were clipped away on every slide.
There is no gutter to have, because the column *is* the slide. (Two copies of the same CSS rule had
also drifted apart, and the later one was quietly winning.)
Double-click a section heading in the list to rename it on every slide under it. Drag a
slide anywhere and it adopts the section it lands in. `Ctrl-Z` covers the last forty
changes — one snapshot per gesture, not per keystroke.

**Figures.** A click on a picture opens its editor — editing is what you almost always
want; swapping it is a separate button. Adding one asks which you meant: pick from the
library, or describe what it should show and have it drawn to the same rules as the rest.
Every picture carries its own size, inline ones included: `![[fig-id|60%]]`.

**Carrying slides to another deck.** Click, `Shift`-click for a run, `Ctrl`-click for one more,
`Ctrl-A` for all of them — the list marks what would be taken. Then `Ctrl-C` / `Ctrl-X` / `Ctrl-V`,
or **right-click for the same menu**, which is where these belong: the thing you are acting on is
in the list, so the menu is on the list rather than in ⋯.

The markdown goes on the **system clipboard**, so it pastes into a mail, an editor, or a deck open
on another machine. The same slides **and every figure they reference** go into the browser's own
store at the same moment, so a paste into another deck in that browser arrives whole — drawings
included. Whichever is newer wins: if you copied something else since, the clipboard is what you
meant. Pasted somewhere without the figures, the references arrive as *not drawn yet* boxes
offering **Draw it** / **Pick one** / **Remove**.

An incoming figure whose id already means something else in this deck **does not overwrite it** —
it comes in beside it under a fresh name and the pasted slides are pointed at the new one. Identical
drawings are shared rather than duplicated. One undo takes a whole paste back out.

**Style, per slide.** The deck sets the house style; a slide keeps **only what it disagrees with**.
`Style just this slide…` in the panel gives it its own accent, text colour, background, title size
or header, and every control starts on *same as the deck* until you move it — so changing the deck
still moves every slide that has not spoken up. The markdown writes only the departures
(`*Style:* titleSize=30, accent=#0EA5E9`), and an override cleared away leaves nothing behind.

**Where the AI went.** `⋯ → AI usage` holds the endpoint, the key, the model, this deck's own
figure rule — and what it has all cost: calls, tokens **as the endpoint reported them**, time
waited, and what the spending went on (drawing figures, writing slides, proposing ideas…). Counted
in the browser and never sent anywhere. Where an endpoint reports no tokens, none are shown rather
than guessed: a usage panel that estimates invites you to plan against a number nobody measured.

**Type size.** For the whole deck, `⋯ → Deck settings` has a title size and a body size; they move
every slide at once, apply as you drag, and are kept on the deck so an export and a rebuild keep
them. For one slide, the panel's **Text size** slider is a percentage of that body size — it has
always been in the file as `*Text:* 82%` and Tidy has always set it, but until now there was no way
to reach it by hand.

**Figure size goes to 200%.** `100%` means *as large as fits*; past that it is deliberately bigger
than the frame — a backdrop bleeds, a figure crops. The slider and the on-slide grip both reach it.

The **Behind** layout ignored the size entirely: its width was written into the stylesheet, so the
slider moved and nothing happened, and the figure size was never passed to the backdrop in the
first place. It was also drawn at a *different size in the editor than on the projector*, because
in the editor a figure is wrapped in a box that sizes itself from a container query. Both fixed,
and the suite now asserts the two surfaces agree. While there: the slider's live preview set a
custom property nothing reads, so dragging it never moved anything on any layout until you let go.

**Figures never take more room than the slide has.** A figure among text is contained on both
axes, the way the hero figure always was. It used to be width only, and that is how a figure ate a
slide: asked for at 85% of a 1168-wide column it took 993 × 558 in a column 540 tall — taller than
the space it sat in — and the table and the key line under it were pushed off the bottom. The cap
is 340 stage pixels, measured rather than guessed: across a 238-slide deck it is the value at which
nothing overflows at all. A percentage now means *of the largest that fits*, which is what it
already meant for the hero figure.

**The canvas follows the drawing.** A figure gets exactly the room its `viewBox` asks for — the
slide reads the viewBox and takes that aspect ratio. So shrinking a drawing inside the editor used
to change nothing on the slide: the canvas was still 800 × 450 and the smaller drawing simply sat
in the middle of it, the empty margin holding the space. The editor's **Canvas** panel says how
much of it is empty and offers **Trim to the drawing**, which sets the canvas to what is actually
drawn, moves the paper with it, and keeps anything that was centred centred. Select part of the drawing
and **Crop the canvas to this** does it by hand instead: the canvas becomes the selection, whatever
falls outside it included. **Reset** puts the shared 800 × 450 back. All three go through the
editor's own undo, and a trimmed canvas is a choice, so it is no longer reported as a fault.

Inside the editor: click takes the whole object, double-click steps inside, `Esc` steps back
out. Lines and arrows are **drawn by dragging**, from one point to any other, and a selected one
shows a handle at each end instead of corner handles. `Ctrl-J` joins two selected objects with an
arrow that **re-routes itself** when either of them moves — the join is stored as `data-from` and
`data-to` on the arrow, so it survives a save.

The **Source** tab reads the drawing as structure rather than coordinates: the element, then its
words, then the attributes worth editing by hand, with geometry dimmed and long values cut short.
Selecting on the canvas scrolls the source to that element; clicking a line selects it.

`Edit as text` opens **the same editor a slide's markdown opens** — and the slide's markdown got
the link that was the figure's alone: click any block in the preview and the source selects it;
put the caret in the source and that block is outlined. Before, you read one pane and hunted in
the other. Under the hood every rendered block carries the index it came from, as an attribute
rather than a wrapper, because a wrapper would change the layout and the whole promise is that the
editor and the projector draw the same stage. In detail it is — the thing on the left, its
source on the right, the same Apply, Cancel and Copy in the same places, `Ctrl-Enter` to apply and
`Esc` to leave. A slide as markdown and a figure as SVG are the same act, and they used to be two
different experiences: the slide had a live preview and Apply, the figure had a Render button and
no preview at all, so what you learned in one was no use in the other. The drawing now redraws as
you type, invalid XML says so instead of drawing nothing, and applying leaves you back in the
figure editor with Undo able to step behind the edit.

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

**No browser dialogs.** Not for deleting, not for restoring a version, not for opening a deck over
unsaved work. `Delete this slide`, under `Hide this slide`, takes a snapshot and deletes, then
offers **Undo** where you can see it. Opening or importing over unsaved work **saves first** and
only stops if that save fails. A dialog you click through every time protects nothing; a real undo
does. It used to go straight to a
splice with a `confirm()` standing in for an undo that did not exist. Duplicating is undoable now
too, for the same reason.

**Hiding slides.** Hide a slide and the presentation walks past it; it stays in the file
and in the list, greyed. `H` hides the current one, and `H` while presenting walks the
hidden ones too, for a rehearsal.

> **"Trim to length" was removed.** Give it a number of minutes and it hid the slides that did the
> least work until the deck fitted. Which slides matter is the one judgement a tool cannot make for
> you, and a deck-wide guess at it was worse than no answer at all. `scripts/short_run.py` still
> does it offline for anyone who wants the bulk version.

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

An **empty slide** does not hand you a blank box. **Suggest what goes here** reads where the slide
sits — the deck, the section, the four slides either side — and comes back with three ideas at the
level a speaker thinks in: *A short history of information retrieval*, *What IR means in 2026*,
*Where generative models actually sit in the stack*. Each is a **move in the talk**, named, with
**the question it answers** — *Is generative AI used in IR, or only talked about?* — and a
specification of what it takes to answer it.

**Three more ideas** goes somewhere else: the request carries what has already been proposed for
that gap and asks for different territory. It used to send the identical prompt and get the
identical three back.

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

### Two boxes, two heights

The panel asks two different questions, and keeping them apart is most of what makes it usable.

**What this slide is for** — one line, the slide's job. *Rewrite it to do this* builds the whole
slide to serve it: title, body, notes, and a figure if it needs one. **Your instruction outranks
the house style**; it did not, and that was a bug — ask for something catchy and the standing
"no marketing adjectives" quietly won, so the model handed back what was already there. `↻` fills
the line by reading the slide.

**Changes to make** — the concrete level. **Analyse this slide** reads it and writes what it would
change *into the box*, as instructions: *cut the third bullet, the figure already says it* · *give
the 40% a source* · *the key line names the symptom, make it name the mechanism*. Strike the ones
you disagree with, keep the rest, press **Make these changes**. A proposed edit you can delete a
line from is worth more than a correct one you can only accept whole — which is why the analysis
is not shown as a verdict. Chips are the presets: Tighten, Make it concrete, Turn into a table,
Add a counterpoint, Split in two, Write the notes. A change that needs a different title gets one.

There used to be two free-text boxes doing the same thing at the same height. There is one of each
now.
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

### A deck from a brief

The blank deck is the worst screen in any presentation tool. `Start from a brief…` on the welcome
screen, or `⋯ → New deck from a brief…`, takes the abstract, **the questions the talk must answer**,
the arc if you have one, and how long you have — and comes back with **the shape**: the sections,
and for each slide a title and the one line it is there to do. Every question you give it has to be
answered somewhere in the deck, and the slide that answers one says so in its purpose.

Deliberately not forty finished slides. What is seeded is each slide's **purpose** — which is
exactly what the panel's top box holds — so every seeded slide arrives one press of *Write this
slide* away from being written, and you read and edit the arc before a word is spent on it. Rows
are editable and droppable before anything is built.

## Development

`tests/preflight.py` runs before the browser does. It checks that every name the test hook exposes
actually exists in the app — cutting a block out by index has twice swallowed a neighbouring
definition, and the only symptom was `window.__api` never being assigned, so all 582 assertions
failed with *cannot read properties of undefined* and none of them said why.

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
