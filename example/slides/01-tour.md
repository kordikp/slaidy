# A tour

### 1. `[S]` SlAIdy

*Summary:* Open on what the project is, and let the slide itself be the argument — everything the format can carry, on one slide.

**Figure:** `fig-slaidy-hero` · split-l · 88%

*Flags:* center

Slides where the deck stays **markdown and SVG** — legible to you, to `git`,
and to the model you edit it with.

#### What this one slide is made of

| | |
|---|---|
| an animated figure | SVG, `@keyframes`, 12 kB |
| a formula | $r_{ui} = \mathbf{p}_u^\top \mathbf{q}_i$ |
| a table | this one |
| code | below |
| a link | [kordikp.github.io/slaidy](https://kordikp.github.io/slaidy/) |

```bash
git clone https://github.com/kordikp/slaidy && ./studio.sh
```

***

> Everything on this slide is text. The animation is 12 kB of SVG.

*Delivery note:* The figure is a twelve-second loop in four beats — you ask for the intro, it writes six paragraphs too many, you wipe the lot, and it comes back with one line and a chart. All CSS keyframes, and it reads with the animation off, which is the rule every figure in this deck follows; a print takes one frame, so a loop that hides its point would lose it.

### 2. `[S]` One material, two readers

**Figure:** `fig-both-can-read` · split-r

*Flags:* center

*Summary:* The idea the whole project turns on — the material has to be legible to everyone working on it.

A deck here is text: markdown for the words, SVG for the drawings.

That is not a storage decision. It is what lets **two very different readers work on
the same thing** — you, when you come back to a talk a year later; the model, when you
ask it to make a figure sparser or to cut what repeats.

> Neither has to take the other's word for what is on the slide.

*Delivery note:* The claim to resist making here is "first". Plenty of tools put a model beside a document. What is unusual is that both sides read the same artefact, at the same level of detail.

### 3. `[S]` Who decides what

**Figure:** `fig-who-decides` · figure

*Summary:* Draw the line: the argument, the cuts and the words are the author's; the drafts, the drawings and the criticism are the model's.

*Delivery note:* Every AI action in this editor produces a proposal you accept or discard, and one Ctrl-Z puts the slide back. The panel that reads a slide and says what it would change writes those changes into a box you can edit — striking a line out is how you disagree.

### 4. `[S]` A picture you can take apart

**Figure:** `fig-opaque-vs-legible` · split-l

*Flags:* center

*Summary:* Why figures are SVG and never bitmaps, and why that is also why the format is small.

A bitmap can be shown and scaled. That is all: nobody can edit it, git cannot diff it,
and asking a model to change it means asking it to draw a new one and hope.

An SVG has parts with names. Move one, recolour one, ask for one fewer.

> 237 slides and 180 figures come to **1 MB**. The same deck as `.pptx` is 34.

### 5. `[S]` A deck is a folder of markdown

**Figure:** `fig-markdown-truth` · split-r

*Flags:* center

*Summary:* The file format, and what it means for a deck to outlive its editor.

Slides are `.md`, figures are `.svg`, and the bundle the app opens is one `.json` that
carries both. Export gives back the same files you started with.

> Nothing the app can write is something only the app can read.

### 6. `[S]` One stage, three surfaces

**Figure:** `fig-one-stage` · figure

*Summary:* Editor, projector and PDF draw the same 1280×720 stage from the same code.

*Delivery note:* This is the invariant everything else leans on. A layout that only looks right in the editor is a bug, and the test suite measures both surfaces and requires them to agree.

### 7. `[S]` Editing where you read

**Figure:** `fig-figure-editing` · split-l

*Flags:* center

*Summary:* You edit on the slide itself, at the size the room will see.

Click a title to change it. Hover a paragraph for a grip to drag it, a `＋` to insert
below it, arrows to move it a step.

Click a figure and its editor opens on the drawing — select a shape, move it, recolour
it, join two boxes with an arrow that re-routes itself when either moves.

### 8. `[S]` Ask, and argue back

*Summary:* How the AI is actually used in practice — as a first draft and a critic, never as an author.

| | |
|---|---|
| **Say what a slide is for** | one line, and it writes the slide to serve it |
| **Ask for changes** | *cut the third bullet, the figure already says it* |
| **Analyse this slide** | it writes what it would change into a box you can edit |
| **Suggest what goes here** | three named moves, with the question each answers |

***

> Strike out what you disagree with. What is left is what runs.

### 9. `[S]` Getting it out again

*Summary:* Close on the exits, because a format you cannot leave is a trap.

PDF through the browser's own print engine — nothing is uploaded. Markdown in the shape
you started with. One `.json` bundle carrying slides and figures. Or the whole deck as
an **article**, figures rasterised, ready to paste into Substack or a `.docx`.

<!-- gap -->

> Try it: <https://kordikp.github.io/slaidy/> · source: <https://github.com/kordikp/slaidy>

*Delivery note:* The editor is MIT, one file, no dependencies and no build step. The AI runs on capacity from CESNET e-INFRA CZ.
