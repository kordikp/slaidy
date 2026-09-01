# Contributing

The short version: the whole app is `slaidy.html`. Open it, change it, run the
tests, send a pull request. There is no build to learn and nothing to install beyond
Python and a Chrome.

## Running it

```bash
./studio.sh                  # the example deck, served with an AI proxy
                             # (finds Ollama/LM Studio if one is running; see .env.example)
./studio.sh decks/mine.json  # any other bundle
```

Or open `slaidy.html` in a browser. Served, it loads `deck.json` from the same
directory by itself and can reach `/api/generate`.

## Tests

```bash
python3 scripts/test_roundtrip.py    # the markdown path
tests/all.sh                         # everything CI runs — run this before pushing
tests/run.sh                         # just the browser suite, in headless Chrome
tests/run.sh 16-designing-a-slide    # just one file
```

Both must pass before a change lands, and CI runs them on every pull request.

The browser suite is not a formality — most of what is in it was written **after** a
bug, and the assertion is usually the sentence explaining what went wrong. It drives
the real application in an iframe: it clicks buttons, drags things, and reads what the
browser actually laid out. Adding a feature without an assertion that would have failed
before it is the one thing likely to get a PR sent back.

Two guards run before the browser does:

- **`tests/preflight.py`** checks that every name the test hook exposes actually exists
  in the app. Cutting a block out of a 250 kB file by index has twice swallowed a
  neighbouring function, and the only symptom was `window.__api` never being assigned —
  so all 714 assertions failed at once and none of them said why.
- **A file that asserts nothing fails.** A syntax error in a test used to report
  "0 passed, 0 failed" and read as success.

## What the project says no to

Not to be difficult, but because these three are what it is:

- **A build step.** If `slaidy.html` needs compiling, it is no longer a file you
  can email to someone.
- **A dependency.** Vendoring a library would make the file bigger than the decks it
  edits, and the ones that matter here — an SVG editing model, a maths renderer — all
  wanted to own the document. The figure editor works on the real DOM; maths goes out
  as MathML, which the browser already sets.
- **A format only this app can read.** Every feature has to survive the round trip
  through markdown, or it belongs somewhere else.

Everything else is open, including the parts you think are wrong.

## Before you change anything

[**docs/DESIGN.md**](docs/DESIGN.md) is the long version: the file format, what the editor
does, where a deck lives and how it is kept from being lost. Most of it was written after
a bug, so where a paragraph explains why something is the way it is, it is usually because
it was once the other way.

## The shape of the file

Roughly in order, so you can find things:

| | |
|---|---|
| CSS | the stage first, then the chrome. `.stage` is 1280×720 and is drawn by the editor, the projector and the printer alike |
| storage | `persist`, `writeServer`, `writeFile`, version snapshots |
| markdown | `blocks` / `block` / `inl` render it; `slideMd` / `importMarkdown` are the round trip |
| figures | `figEdit` and everything `fe*` — the editor runs the drawing inside an `<iframe srcdoc>` so a figure's own `<style>` cannot reach the app |
| AI | `llm` and its callers, each tagged with a kind so `⋯ → AI usage` can say what the spending went on |
| the deck | `paintNav`, `paintBoard`, `paintSide` — the list, the stage, the inspector |

Two invariants worth knowing before you move code:

- **Anything that renders a slide goes through `stageHtml`.** Three surfaces, one
  function; a fix that only lands in the editor is a bug in the making.
- **A figure's SVG is scoped on the way in** (`scopeSvg`, `freshIds`). Figures carry
  their own `<style>` and their own ids; two copies of one figure on a page used to
  break each other.

## Style

Match what is there. British spelling, comments that say *why* rather than *what*, and
no comment that restates the line under it. If a comment can only be written by
describing a bug, that is usually the comment worth having.

## Reporting things

Issues for bugs and ideas, Discussions for questions. If you are not sure a change will
be welcome, open an issue first — it is a cheaper conversation than a rejected PR.
