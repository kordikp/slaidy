# A deck from a document

**A proposal, with its engine already built offline.** `scripts/fit_document.py` does the
whole mechanical pass from the command line and `scripts/test_fit_document.py` holds it to
the invariants below; **the part inside the application — the three dials, the plan you
approve, the deck-wide pass — is not built.** This file says what should be, why it looks
like this, and what it must never do. Numbers in it were measured, and the command that
produces each one is given beside it.

---

## What it is for

A deck from a brief takes the shape and leaves you to write the words. This is the other
half: you already have the words. A chapter of a book, a paper, lecture notes, a README —
a long markdown document written to be **read**, not projected. It has headings, lists,
tables, figures and a great deal of prose. It has nothing a slide needs: no slide
boundaries, no columns, no clicks, no speaker notes, no idea how much fits on a stage.

Today that document comes in through the generic branch of `importMarkdown` — a slide per
`##`, layout `text`, and the frontmatter teaser as the notes. Put a real one through it —
one chapter of the [recsys p-book](https://github.com/kordikp/recsys-pbook), 52 files and
36 542 words, read by a reimplementation of that branch:

| One p-book chapter through today's importer | |
|---|---|
| files | 52 |
| slides | 257 |
| words on those slides | 35 527 |
| **slides carrying more than 40 words** | **227 — 88%** |
| slides carrying more than 120 words | 115 |
| mean words per slide | 138 |

For comparison, the 37 slides of the ISD keynote — a deck a person made, gave and kept —
carry a **median of 97 body words** across a median of **five blocks**, and most of those
words are table cells and key lines rather than prose. So the import is not slightly off.
It produces 257 slides of which nine in ten are a wall of text, and the work of turning
that into a talk is all still to do, by hand, on every one of them.

What the document is missing is not words. It is **arrangement** — and arrangement is the
one thing this application already knows how to measure.

## The contract

> **Tidy** arranges what is on a slide. It never changes a word and never moves one.
> **Fit** decides what is on it. It moves words — into the speaker notes, or onto the
> next slide — and never changes one.

Everything else follows from that second sentence. Moving is not writing: the author's
prose arrives intact, in their order, in their words, either on a slide or in the notes
under it. Nothing is summarised, nothing is deleted, nothing is invented, and **no model is
required for any of it**. The model is offered afterwards, per slide, through the queue
that already exists — and, as everywhere else here, nothing it says lands until you take it.

Three invariants, each of them testable:

1. **Not a word is lost.** Every word of the document ends up in a slide's title, body or
   notes. The multiset of words in is a subset of the multiset of words out.
2. **A second pass changes nothing.** Fit is idempotent, so running it again — on import,
   on the whole deck, on one slide — is safe.
3. **A decision already made is left alone.** A slide carrying a column break, a named
   layout, a text scale or flags has been arranged by someone. Fit proposes *leave it* for
   those and you have to ask for more.

## What a document already says

Fit never guesses at structure. It uses what it can see, and what it cannot see it reports
rather than invents.

**Headings** give the tree. One level is the **grain** — the level at which a slide ends.
Everything above it becomes navigation (section, subsection); everything below it stays in
the body as a `####` sub-head, which slides already render.

**Blocks** give the separation, and the rule is the one `scripts/fit_slides.py` already
uses offline:

| shown — stays on the slide | said — goes to the speaker notes |
|---|---|
| lists, tables, quotes, code, formulas, figures, sub-heads | prose paragraphs |

with one exception that matters: **a slide must show something.** If a unit is nothing but
prose — which is most of a book — the lead paragraph stays on the slide and the rest is
spoken. A slide with a title and an empty frame is worse than a slide with a paragraph on it.

**Frontmatter**, where a document has it, says more than the body does. The p-book's is
not unusual for a document written to be processed:

| p-book frontmatter | what the deck does with it |
|---|---|
| `title` | the slide's title |
| `teaser` | `*Summary:*` — the line the AI panel's top box holds, so the slide is one press from being written |
| `highlights: [...]` | the author's own three one-line claims — a bullet list, on the first slide of the unit |
| `diagram: diagram-embedding-space` | `![[diagram-embedding-space]]` |
| `recallQ` / `recallA` | appended to the notes of the unit's last slide |
| `readingTime` | checked against the stage time the deck comes out at |
| `type`, `core`, `state` | **the convention, named by you** — see *On stage* below |

111 of the p-book's 307 content files carry `highlights`, 283 carry a `teaser`, 200 name a
`diagram`, and 169 SVG figures sit in `images/` where the existing importer's
`![alt](/images/x.svg)` → `![[x]]` rewrite already finds them. A document written for a
machine to read is *already* most of a deck. The fitter's job is to stop throwing that away.

Nothing about p-book is hard-coded. The frontmatter keys a deck understands are a small
table in the wizard, editable, saved on the deck — the same shape as `meta.layouts`.

## The pass

Per unit, in this order. Everything measured is measured the way Tidy measures: the slide
is drawn into the hidden stage at full size and the browser is asked where the last thing
painted ended.

1. **Read** — frontmatter, then split the body at the grain. Headings deeper than the
   grain stay in the body. A unit with nothing but frontmatter (the p-book has three in
   one chapter) becomes a slide from its title and teaser, and says so in the plan.
2. **Separate** — shown stays, said goes to the notes, in document order, joined the way
   `fit_slides.py` joins them (`as_prose`: list markers off, newlines flattened, words
   untouched).
3. **Pack** — walk the shown blocks, filling a slide until the frame is full, then start
   another **with the same title**. A continuation slide's title is repeated, not invented:
   the list shows them adjacent and the author renames what they want renamed. A block is
   never cut in half — except a long *unordered* list, which is a run of items and can be
   continued. An ordered one cannot, for the reason given under *Steps* below.
4. **Merge, when the grain is *fill the slide*** — two consecutive sibling units whose
   content fits together become one slide with each unit's heading as a `####` sub-head.
   This matters more than splitting does: without it, relocating the prose leaves slides at
   37% of the frame. With it, 69%.
5. **Arrange** — `tidySlide()`, unchanged: figure size, text size, where the slack goes.
   Then, and only here, the column count. **Tidy refuses to choose a layout** because how
   many columns a slide has is a decision — but a slide that arrived from a document has
   no decision behind it, so Fit may make one, using `splitBody()`, which already measures
   every block at column width and cuts where the columns come out most even. On a slide
   someone has arranged, rule 3 of the contract applies and Fit does not touch it.
6. **Reveal**, if asked — `<!-- step -->` between top-level blocks. Off by default.
7. **Name** — the title from the heading, or from the frontmatter for a file's first unit.
   A unit with no heading and no title keeps the words `Untitled` rather than having a
   title written for it by a model that was not asked.

## Three dials, and a report

The wizard has three controls and one paragraph of arithmetic. That is the whole surface.

**Grain** — *a slide per `##`* · *a slide per `###`* · **fill the slide** (default).
Changing it redraws the plan; the plan is cheap, because measuring 200 slides is the same
work `Tidy every slide` already does on 237.

**On stage** — which units carry the talk. Default: all of them. A document with a
convention can name it once — a filename pattern, or a frontmatter key and value — and
everything else still comes in, **hidden**: in the file, in the list, greyed, walkable with
`H` in a rehearsal, and there when someone asks the question it answers. Nothing is
dropped, because *which slides matter* is the judgement this application already decided a
tool must not make (see *What it refuses to do*).

**Reveal** — off · *between the blocks of a slide*. Off by default, because a document says
nothing about pacing and a build is a rhetorical choice. Offered, because reveal is the
commonest thing anyone asks a deck for after "make it fit".

**The report**, under the plan: slides, stage time at the deck's own 70 s a slide, words
shown against words spoken, and anything the fitter could not fit — named, with a link to
the slide. Reported, never enforced. `Trim to length` was removed from this application for
good reasons and is not coming back through a side door.

## Measured

The grain and the merge are not taste. This is one chapter of the p-book — 52 files,
36 542 words, 26 figures named in the text and 34 once the frontmatter's are added —
through a paper prototype of the pass. Offline, a line budget stands in for the browser's
measurement, **calibrated on the keynote**: the budget is the 90th percentile of what its
37 accepted slides carry per column (15.8 lines), so "fits" here means "no bigger than
slides that already work".

| `--grain` / `--on-stage` | slides | on stage | hidden | median fill | over the frame | stage time |
|---|---|---|---|---|---|---|
| today's importer | 257 | 257 | 0 | — | **227 (88%)** | — |
| `section` | 294 | 294 | 0 | 37% | 1 | 5 h 43 |
| `fill` | 206 | 206 | 0 | **69%** | 1 | 4 h 00 |
| `fill`, `--on-stage '\-spine\-'` | 206 | **34** | 172 | 73% | **0** | **39 min** |

The last row is the one to look at. A book chapter becomes **a 39-minute talk of 34
slides**, with 172 slides behind it that nobody sees unless they are asked for, and **not
one word of the chapter gone**. Those 34 carry a median of 69 body words, against the
keynote's own 97, and 5 381 words of notes wait under them; the other 17 430 sit behind
the hidden slides. That is the feature.

Two things the table also says. Packing is worth as much as splitting — it is the
difference between 37% and 69% fill, and a deck of half-empty slides is its own kind of
wrong. And the fitter cannot decide the last row on its own: *which files are the spine*
came from a convention in the document that a person named in one control.

Reproducing it — the last row, and the deck it makes:

```bash
git clone https://github.com/kordikp/recsys-pbook /tmp/pbook
python3 scripts/fit_document.py --src /tmp/pbook/content/ch05-algorithms \
    --figs /tmp/pbook/images --on-stage '\-spine\-' --out /tmp/ch05 --title Algorithms
python3 scripts/build_bundle.py --src /tmp/ch05/slides --figs /tmp/ch05/figures \
    --out decks/ch05.json --title Algorithms
#   206 slides · 52 subsections · 34/34 figures · 0.59 MB
```

> The script is the offline half, beside `fit_slides.py` and `dedupe.py`, which are the
> same family of tool. It estimates where the application measures — a line budget instead
> of a hidden stage — so the numbers the application gets will differ a little, and only
> downward. What it does **not** have is the part that matters most: a plan you read
> before anything happens.

## Yes, it should run over a whole deck — but not the way Tidy does

`Tidy every slide` can run silently over 237 slides with one `Ctrl-Z` behind it, because
every dial it turns is reversible and none of them changes what the deck *is*. Fit changes
the slide count. Twelve slides becoming twenty-six is not something to discover from a
toast.

So: the same engine, three entry points, and the deck-wide one runs behind a plan.

- **`⋯ → A deck from a document…`** — the main path, and the one the import wizard grows
  into. The wizard already says what it found before it does anything; it gains the three
  dials and the plan.
- **`⋯ → Fit every slide…`** — beside `Tidy every slide…`, for a deck that already exists:
  one imported before this landed, one pasted together, one that grew. Slides that fit are
  proposed as *leave alone*, which is most of a deck that has been worked on.
- **The overflow warning**, per slide — it already offers *fit the slide*, *shrink the
  picture* and *move what is over the edge into the notes*. It gains **Split it**, which is
  rules 2 to 5 on one slide.

**The plan** is modelled on the brief wizard's review, because that interaction is right and
already exists: one row per slide it would make, grouped by source unit, showing the title,
what would be shown on it, and how many words would move to the notes. Rows are editable.
A row can be set to *leave this slide alone*. Clicking one draws that slide at stage scale
in the preview — `stageHtml` and `scalePreview`, both already there. Nothing is applied
until you press the button, and what is applied is one snapshot and one undo.

## Where the model comes in, and where it does not

Everything above works with no endpoint configured. What a model adds is offered after, on
a slide, through `JOBS` — queued, visible in the list, stoppable, and waiting with
**Use this** / **Discard**:

- **Prose into bullets.** The real slide-making, and it is a rewrite, so it is the panel's
  existing *Rewrite it to do this* — except the purpose box is **already filled in**, from
  the document's teaser or its lead sentence. That is the same state `A deck from a brief`
  leaves you in, with the material already there.
- **A title** where the heading was a sentence, **a purpose line** where there was no
  teaser, **the key line** — which sentence should land.
- **A figure** where the prose describes a mechanism and the document drew nothing —
  `fulfilFigures`, unchanged.
- **Where the clicks go**, as a proposal, on a slide the author asked about.

Asking for all of it at once is the queue running 34 times, one at a time, which it is
built for. It is offered per section rather than per deck, and it is not the default.

## Steps, and the one new thing this needs

`<!-- step -->` between top-level blocks costs nothing to write and nothing to render:
steps are derived, the marker is a block, and the count takes care of itself. A figure
already brings its own `data-step`, and a p-book `anim-*.svg` often already animates.

Revealing **a list one item at a time** is the case everybody actually wants, and it does
not work today. A `<!-- step -->` inside a list splits it into two list blocks, which on an
unordered list shows as an extra `0.6em` gap and on an ordered list **restarts the
numbering at 1**. So:

> **The one renderer change this proposal asks for**: let a list block carry steps
> internally, and put `data-s` on the `<li>` rather than on the `<ul>`. `block()` builds
> the `<li>`s in one line and `applySteps` already hides by `data-s`, so the change is
> small and contained — and it is the only new capability in the whole feature.

Until it exists, Fit puts steps between blocks and says so.

## Pictures and figures

`![alt](path.svg)` → `![[path]]` already. Two additions:

- **Bitmaps come in as pictures.** The import reads `.md`, `.svg` and `.json` and ignores
  `.png`; a document's screenshots and plots should go through `picImport` like any other
  picture, and **the image's alt text becomes the picture's `desc`** — which is exactly
  what `AGENTS.md` requires a picture to carry, written by the author, about those pixels.
  A picture with no alt text arrives without a description and the plan says which ones.
- **A `mermaid` fence is a diagram**, and a drawn figure beats a code block on a slide. It
  stays a code block by default and the plan offers to draw it, because that is a model
  call and model calls are asked for, never assumed.

## What it refuses to do

**It does not decide what matters.** `Trim to length` was removed from this application
because a deck-wide guess at which slides do the least work was worse than no answer:
*which slides matter is the one judgement a tool cannot make for you.* Fit obeys that.
It decides **where a word is said** — on the slide or out loud — which is arrangement, and
measurable. It never decides **whether a word is said**. Nothing is hidden without being
asked for, nothing is deleted, and length is reported rather than enforced.

**It does not rewrite.** No summarising, no tightening, no "turning prose into three
punchy bullets" in the mechanical pass. That is a rewrite, it needs a model, and a model's
work waits on its slide with Use this / Discard like all the rest.

**It does not invent structure.** A document that is 4 000 words under one heading has
nothing to split on, and Fit says so rather than cutting it every 40 words. It puts the
lead on the slide, the rest in the notes, and points at the model.

## Tests

`scripts/test_fit_document.py` already holds the offline engine to these, and runs in
`tests/all.sh` with the rest. The application's half wants the same list again in the shape
of the browser suite — `tests/32-a-document-becomes-a-deck.html`, driving the app in an
iframe against a fixture document:

- **not a word is lost** — every word of the fixture is in a title, a body or a note
- **a second pass changes nothing** — deep-equal before and after
- **every slide it made measures inside the frame**, or is named in the report
- **a slide someone arranged is untouched** — column break, named layout, text scale, flags
- **a table, a code block and an ordered list are never split**
- **the application's own format still imports exactly as it did** — the keynote branch of
  `importMarkdown` is not in this path at all, and the existing round-trip test proves it
- **no endpoint is reached** during the mechanical pass
- **a deck's own markdown is refused**, not read as prose and wrecked

## Where the code goes

One file, as always. Almost all of it is reuse:

| new | does | built on |
|---|---|---|
| `docUnits(text, grain)` | frontmatter and headings to units | the generic branch of `importMarkdown` |
| `fitUnit(unit, profile)` | separate, pack, merge → slides | `blocks()`, `fit_slides.py`'s rule |
| `fitSlide(s)` | arrange one slide, split if it still spills | `measureStage()`, `tidySlide()`, `splitBody()` |
| `fitPlan(slides, dials)` | the plan, applying nothing | — |
| `fitApply(plan)` | one snapshot, one splice, one undo | `snap()`, `normalise()`, `paint()` |
| `fitWizard()` | the three dials, the plan, the preview | `briefWizard()`'s review, `stageHtml`, `scalePreview` |

Hooks: `importWizard` (the dials and the plan replace the straight import), the `⋯` menu
(`bFitAll` beside `bTidyAll`), the overflow warning (`data-fix="split"`), and the welcome
screen, where *A deck from a document…* belongs next to *A deck from a brief…* — which is
the pair this proposal is really about. One of them has the shape and needs the words. The
other has the words and needs the shape.

## Open questions

1. **Is `fill the slide` the right default grain?** It measures best (69% against 37%) but
   it puts two of the document's headings on one slide, which is a small editorial act.
   The alternative default is *a slide per `##`* with the merge offered.
2. **A continuation slide's title.** Repeated verbatim here. `Title (2)` reads better in
   the list and is a word nobody wrote.
3. **Should the deck-wide pass keep the frontmatter profile** on the deck (so a re-import
   of an updated chapter behaves the same), or ask each time? `meta.layouts` is the
   precedent for keeping it.
4. **How much of the notes is too much.** The stage slides come out at a median of 114
   words of notes, against the keynote's 36, and one of them carries 679 — more than
   anybody reads off a confidence monitor. The words must not be lost, and they are not
   the deck's to cut. But the notes may want the first sentences of the unit and then a
   marker saying the rest is in the hidden slide behind it.
