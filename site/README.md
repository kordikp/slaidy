# Decks published on the web

Every folder here becomes a page of its own at
`https://kordikp.github.io/slaidy/<folder>/`, carrying the whole editor and that deck.

```
site/
  isd2026keynote/
    deck.json        ← the only file that has to be here
```

`scripts/publish.py` puts one there:

```bash
python3 scripts/publish.py decks/isd2026.json isd2026keynote
git add site && git commit -m "Publish the ISD 2026 keynote" && git push
```

A published page is the same single file as everywhere else, so anyone opening it can
present it (`P`), read the speaker notes (`N`), export a PDF, or edit their own copy — their
edits stay in their browser and never touch what you published. Add `#present` to the link
to open straight into the projector:

`https://kordikp.github.io/slaidy/isd2026keynote/#present`

The root of the site stays the tour: `https://kordikp.github.io/slaidy/`.
