# Contributing

## Running it

```bash
./studio.sh                  # the example deck, served with an AI proxy
./studio.sh decks/mine.json  # any other bundle
```

Or just open `slide-studio.html` in a browser. Served, it can also load `deck.json`
from the same directory by itself and reach `/api/generate`.

## Tests

```bash
python3 scripts/test_roundtrip.py    # the markdown path
tests/run.sh                         # the app, in headless Chrome
```

Both must pass before a change lands. The browser suite is not a formality — most of
the bugs worth having found in this codebase were found by adding an assertion, not by
reading the code. Three of them were:

- a metadata regex using `\s*`, which crosses a blank line, so the `**Figure:**` line
  swallowed the paragraph after it and 3539 words vanished with no error
- `contentEditable = 'false'` firing `blur` synchronously, so the rename handler
  re-entered itself and `Escape` committed the edit it was supposed to abandon
- a drag divided by the element's own scale rather than its parent's, so anything
  inside a scaled group outran the mouse sevenfold

If you fix something, add the assertion that would have caught it.

## The app is one file

`slide-studio.html` — no build step, no dependencies, no bundler. That is deliberate:
it has to keep working when opened from a USB stick in ten years. Keep it that way.

Inside it, roughly in order: storage, SVG scoping, the markdown reader and writer, the
importers, the nav, the stage, the inspector, the figure editor, export, presenting.

Two rules that are easy to break:

1. **One stage.** The editor, the projector and the PDF must render the same markup
   through the same CSS. Anything that adds height on only one of them — an editing
   handle, an insert bar — belongs outside the stage.
2. **The markdown is the truth.** Every field the app can edit has to survive a round
   trip to `.md` and back. If you add one, add it to `slideMd`, `importMarkdown`,
   `build_bundle.py` and `test_roundtrip.py` in the same change.

## Style

Match what is there. Comments explain why something is the way it is — usually the bug
that made it necessary — not what the next line does.
