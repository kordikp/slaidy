# A tour of Slide Studio

**~6 min · 6 slides**

This deck is written in the format Slide Studio reads, and it describes the tool you are looking at.
Open it, edit a slide, present it, export it — the file on disk stays the source of truth.

---

## What it is

### 1. `[S]` A deck is a folder of markdown

*Summary:* The tool is a view onto plain files, not a database you have to export from.

**Figure:** `fig-markdown-truth` · split-r

*Bestseller:* yes

- One `.md` file per section, one `### ` heading per slide
- Figures are SVG files, referenced by name
- Settings live in `deck.meta.json` beside the slides

> Nothing about your deck is locked inside the application.

*Delivery note:* The whole point of the format is that it survives the tool. If Slide Studio disappears tomorrow you still have readable, diffable markdown and a folder of SVGs.

---

### 2. `[D]` One stage, three surfaces

*Summary:* The editor, the projector and the PDF render the same markup at different scales.

**Figure:** `fig-one-stage`

*Bestseller:* yes

> What you arrange is what the room sees. There is no second layout to drift out of step.

*Delivery note:* This started as three separate renderers and they drifted, as three renderers do: text that sat neatly under a diagram in the editor jumped to the top of the screen when projected. They are now one 1280×720 stage, scaled three ways. The editing handles sit outside the stage so they cannot change its layout.

---

## Working in it

### 3. `[S]` Editing where you read

*Summary:* Titles, paragraphs and section names are edited in place, not in a properties panel.

**Figure:** `fig-figure-editing` · split-l

- Click the title on the slide to change it
- Hover a paragraph for move and delete; the row of icons inserts text, lists, tables, a divider, a spacer, a figure
- Double-click a section heading in the list to rename it everywhere under it
- Drag a slide anywhere; it adopts the section it lands in

> Speaker notes sit under the slide, where you read them, not in a panel on the right.

*Delivery note:* Ctrl-Z covers the last forty changes. A snapshot is taken at the start of each gesture, not per keystroke, so one undo returns a whole paragraph edit.

---

### 4. `[D]` Figures are editable, by hand and by model

*Summary:* Every figure is SVG, so it can be selected, moved, resized, grouped and asked about.

**Figure:** `fig-figure-editing`

*Bestseller:* yes

> A click takes the whole object; a double-click steps inside it. That is the difference between editing a logo and shattering it.

*Delivery note:* Drag over empty space to lasso what you enclose, Alt for what you merely touch. Handles resize about the opposite corner, corners keeping the proportions. Ctrl-G groups, Ctrl-Shift-G ungroups, Ctrl-E takes one element out of its group carrying the wrapper's transform with it. The AI panel can be pointed at the whole figure or at the one element you have selected.

---

## Presenting

### 5. `[S]` The short run

*Summary:* A curated path through the deck for when the slot is shorter than the deck.

**Figure:** `fig-short-run` · split-r

*Bestseller:* yes

- Star slides in the list, or ask for a suggestion at a target length
- Press <kbd>B</kbd> while presenting to switch between the run and everything
- The budget is shared between sections in proportion to their length, so the talk keeps its shape

> A talk projected to a room cannot be personalised. The popular path is what every recommender falls back to.

*Delivery note:* The suggestion scores a slide by whether it opens a section, lands a key line or shows evidence, and marks asides down hardest. It is a starting point, not a verdict — the stars are yours to move.

---

### 6. `[S]` Getting it out again

*Summary:* PDF, markdown and a self-contained bundle, all from the same stage.

**Figure:** none.

| Export | What it is for |
|---|---|
| **PDF** | one landscape page per slide, optionally with speaker notes underneath |
| **Markdown** | the files you started with, in the same shape |
| **Deck bundle** | one `.json` with slides and figures — the backup to keep |

> Your work lives in the browser's storage while you edit. The bundle is what survives a cleared cache.

*Delivery note:* PDF goes through the browser's own print engine — no service, nothing uploaded. Choose Save as PDF and set margins to none.
