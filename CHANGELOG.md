# Changelog

Dates are when the work landed, not when it was released; there are no releases yet.

## Unreleased

### Added
- **Slides move between decks.** Select in the list — click, `Shift`-click, `Ctrl`-click,
  `Ctrl-A` — then `Ctrl-C` / `Ctrl-X` / `Ctrl-V`, or right-click for the same menu. The
  markdown goes to the system clipboard; the slides *and every figure they reference* go
  to the browser's store, so a paste into another deck arrives whole. An incoming figure
  whose id already means something else here does not overwrite it.
- **A deck from a brief.** Abstract, the questions it must answer, the arc, how long you
  have — it comes back with the shape: sections, and per slide a title and the one line
  it is there to do. What is seeded is each slide's *purpose*, so every slide is one
  press from being written.
- **Formulas.** `$x^2$` and `$$…$$`, TeX in and MathML out, no library. What it cannot
  parse comes back as the TeX you typed rather than as something quietly wrong.
- **Headings inside a slide** (`####`), fenced code blocks, strikethrough.
- **`⋯ → AI usage`** — calls, tokens as the endpoint reported them, time waited, and
  what the spending went on. Counted in the browser, never sent anywhere.
- **Per-slide style overrides.** A slide keeps only what it disagrees with; everything
  else follows the deck.
- **Text size per slide**, and a canvas that can be trimmed or cropped to its drawing.
- **A source editor shared by slides and figures**, with the preview linked to the
  source both ways.
- **`New deck…`** asks where it will be saved before you start.

### Changed
- **The project is called SlAIdy.** The name in the toolbar is the link to the source.
- The AI can be pointed at **CESNET e-INFRA CZ** in one click, and `studio.sh` prefers it
  when `CESNET_API_KEY` is in the environment or in `.env`. A reasoning model's token
  budget is scaled so it has room to answer after it has finished thinking, the e-INFRA
  four-at-a-time cap is respected, and an empty completion is reported as what it is.
- **The deck file is the document.** Started with `studio.sh`, the server owns it and
  every save writes to it. No permission prompt, no second copy.
- Generated figures are told how sparse to be, in numbers measured from the deck they
  are drawing for: twelve labels of one to four words.
- Your instruction outranks the house style; it did not, and asking for something
  catchy quietly got you the house default back.

### Fixed
- The editor now fits the device. The slide was capped at 940px however large the screen, and
  below 1000px the three columns simply overflowed — on a phone the toolbar pushed **Present**
  off the edge.

- Centring a row collapsed its figure to nothing: the column stopped stretching, and the
  figure sizes itself from that column's height. Found by looking at the demo deck.

- **Edits could be lost three ways at once**: the deck was copied to be served, so every
  restart looked newer than your work; a file handle could not be re-permissioned after
  a restart; and rebuilding from markdown wrote over a newer deck. All three closed, and
  a save that fails now says so loudly rather than in a corner.
- **The per-paragraph controls were invisible** — positioned in a gutter outside the
  text column, which clips. They are in the block's own corner now, and a paragraph can
  be dragged.
- An inline figure was contained on width only, so a figure among text could be taller
  than the slide and push everything under it off the bottom.
- A hidden slide vanished from the list, because its state class collided with a global
  `display:none` utility.

### Security
- A deck is treated as untrusted text, because one can now arrive from anywhere. Link
  schemes are checked (`javascript:` keeps its words and loses its target), figure SVGs
  are stripped of `<script>`, `on*` handlers and `foreignObject` on every render path,
  and the figure editor's canvas is sandboxed. `scripts/serve.py` caps the size of a
  written deck and refuses cross-origin calls to its AI proxy.
- Copying slides used to report success even when both the clipboard and the browser
  store had refused it.

### Removed
- **Trim to length.** Which slides matter is the one judgement a tool cannot make for
  you, and the deck-wide guess was worse than no answer. `scripts/short_run.py` still
  does it offline.
- The tag markers that used to trail slide titles. Nobody in the room knew what they meant.
