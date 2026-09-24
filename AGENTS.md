# Working on a SlAIdy deck — for assistants

A deck is meant to be read and changed by a model as well as a person. That only
works if the parts a model cannot see are treated with care. This page is the
contract. It applies whether you edit the source folder, the deck JSON, or answer
a request inside the app.

## What a deck is

| Form | What it holds | Who edits it |
|---|---|---|
| `slides/*.md` | the slides, as markdown | you and the person |
| `figures/*.svg` | the drawings, as SVG text | you and the person |
| `figures/assets/<id>.webp` etc. | **pictures** — photos, screenshots, plots | the person |
| `figures/assets/assets.json` | what each picture shows: `{"<id>": {"desc": "…"}}` | you and the person |
| `decks/<name>.json` | all of the above in one file, built by `scripts/build_bundle.py` | the app |

In a slide, `![[fig-id]]` places a figure and `<!-- step -->` holds what follows
for the next click (Beamer's `\pause`). In a figure, `data-step="n"` means "there
from click n" and `data-until="m"` means "gone at click m". Nothing declares how
many clicks a slide has: it is derived, so do not add a count.

## Pictures: what you must respect

A picture is a bitmap the author put there. It is stored once, under a name made
from its content (`img-` and 24 hex digits), and a figure places it:

```svg
<image href="asset:img-3f9c0a…" x="0" y="0" width="800" height="533"
       preserveAspectRatio="xMidYMid meet"/>
```

**You cannot see it.** You are told what it shows: the `desc` in `assets.json`,
or, inside the app, a list headed *PICTURES IN THIS FIGURE* that comes with the
figure. Work from that description. Do not guess at pixels you have not seen.

1. **Keep every `<image href="asset:…">` you were given, and keep its `href`
   exactly as it is.** Leaving one out deletes the author's picture.
2. **Never invent an `asset:` name.** A name that does not exist shows as
   *missing picture*, and the app removes it from what you return.
3. **Never embed pixels.** No `data:` URLs, no base64 and no web addresses in a
   figure. A deck does not point outside itself, because what is behind a link
   can change or vanish.
4. **Do not change the pixels, and never regenerate a picture.** A photo of an
   experiment, a measured plot or a screenshot is evidence. A "cleaned up" or
   redrawn version is a fabrication, however good it looks.
5. **Do not read `assets` out of a deck JSON.** It is base64: most of the file's
   bytes and none of what you need. Use `python3 scripts/assets.py list deck.json`,
   which prints each picture's name, size, description and the figures that use
   it.

What you **may** do, all of it as SVG text:

| Request | How |
|---|---|
| move it, size it | `x`, `y`, `width`, `height`. Keep the proportions. |
| crop it | `preserveAspectRatio="xMidYMid slice"` fills the box, so size the box to the part you want. For a region anywhere else, wrap the image in a `clipPath`. |
| black and white, lighter, more contrast | `style="filter:grayscale(1) brightness(1.1) contrast(1.2)"` on the `<image>` |
| point at something | arrows, labels, a highlight rectangle drawn *on top of* the image, placed from the description |
| hide something (a name, a face) | an opaque shape over it. Say that you did, because you placed it from the description, not from seeing it. |
| reveal it or its annotations click by click | `data-step` / `data-until` on the image or on what is drawn over it |

**A description is part of the source.** If a picture has no description, say so.
If one no longer matches what the slide says about the picture, say that too.
Only rewrite a description when you are told what the picture shows. A
description describes these pixels, so a different picture needs a new one.
Replacing a picture gives it a new name, and its old description does not move
with it.

## Adding pictures (for the person, or for you when asked)

- In the app: ＋ Figure → **Picture** (a file, the clipboard, a drop, or an
  address), the picture button in the figure editor's toolbar, or simply paste or
  drop a picture onto a slide.
- In the folder: put the file in `figures/assets/` named by its id and add its
  description to `assets.json`. It is simpler to add it in the app and run
  `python3 scripts/assets.py extract deck.json figures/`, which names it for you.
- Pictures are shrunk to 1920 pixels on the longest side and stored as WebP
  where the browser can write it. A slide never needs more.

Prefer a drawing when the thing *is* a diagram. A diagram you can redraw as SVG
stays editable by everyone, you included. A picture is for what cannot be drawn:
photographs, screenshots and measured results.
