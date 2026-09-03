# Decks published on the web

Every folder here becomes a page of its own at
`https://kordikp.github.io/slaidy/<folder>/`, carrying the whole editor and that deck.

```
site/
  isd2026/
    deck.json                ← the only file that has to be here
    notes/index.html         ← the speaker notes, as a document that prints
    commentary/index.html    ← the deck read slide by slide, for the audience
    slides/slide-N.png       ← each slide as it projects, for the commentary
```

`scripts/publish.py` writes the first two:

```bash
python3 scripts/publish.py decks/isd2026.json isd2026
git add site && git commit -m "Publish the ISD 2026 keynote" && git push
```

`scripts/commentary.py` writes the other two, from a markdown file you keep beside the
deck — one `## N. Title` block per slide — and a folder of slide images:

```bash
python3 scripts/commentary.py site/isd2026/deck.json commentary.md slides/ site/isd2026
```

A published page is the same single file as everywhere else, so anyone opening it can
present it (`P`), read the speaker notes (`N`), export a PDF, or edit their own copy — their
edits stay in their browser and never touch what you published. Add `#present` to the link
to open straight into the projector:

`https://kordikp.github.io/slaidy/isd2026/#present`

The root of the site stays the tour: `https://kordikp.github.io/slaidy/`. Here now:
`isd2026/`, the ISD 2026 keynote *The Great Convergence*, which is also
`decks/isd2026.json` in the repository; and `isd2026-v2/`, an earlier draft of it.
