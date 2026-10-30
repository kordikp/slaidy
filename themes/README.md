# Themes

A theme is a brand's look for the slides: the fonts, the colours, the cover and the closing, the
header and the footer. It changes how a deck looks and nothing else. The words, the figures and the
markdown stay as they are, so the same deck can be shown in any theme.

**See them:** [kordikp.github.io/slaidy/gallery](https://kordikp.github.io/slaidy/gallery/). Each theme has
a sample deck at `kordikp.github.io/slaidy/themes/<name>/`.

**Use one:** in the editor open **⋯ → Deck settings → Style → Theme** and pick it. The deck keeps the
theme's CSS inside it, so it still opens offline and still needs nothing but itself. The colours and
sizes below the picker start from the theme's own, and you can change them.

## What is in the library

| Theme | | Brand |
|---|---|---|
| [`recombee`](recombee/) | dark green slide, mint, Inter, the logo in the header | © Recombee |
| [`aidetem`](aidetem/) | strawberry red and sky, Space Grotesk and Darker Grotesque, a red cover | © AI dětem |
| [`tiny`](tiny/) | dark violet and yellow, Inter | © AI dětem (tiny.school) |
| [`kurikulum`](kurikulum/) | a pink-to-blue gradient cover, Darker Grotesque | © AI dětem |
| [`fit-cvut`](fit-cvut/) | white, CTU blue and light blue, Titillium Web standing in for the university's Technika, the FIT logo on every slide | © Czech Technical University in Prague |
| [`mlcig`](mlcig/) | cool paper, CTU blue and the group's orange, Outfit, the group's mark in the corner | © ML & CI Group, FIT CTU |
| [`polirural`](polirural/) | the project's greens, League Spartan and Inter; the logo and the EU emblem on the cover, the grant acknowledgement on the closing | © PoliRuralPlus consortium; the EU emblem under the EU's rules |
| [`paper`](paper/) | ivory paper, Literata titles, Lexend text, vermilion and teal, a dot-grid cover; for lectures and research talks | none, use it for anything |

The CSS is MIT, like SlAIdy. The fonts are under the SIL Open Font Licence. **Logos and brands
belong to their owners** and are here so their own people can make their own decks. Use a brand's
theme only for that brand's materials. To make your own look, start from a theme's CSS, not from its
logo.

## Add yours

1. Fork the repository and make a folder `themes/<name>/`. The name uses lower-case letters, digits
   and dashes.
2. Put these in it:

   | File | What it is |
   |---|---|
   | `theme.css` | every rule starts with `html[data-slaidy-theme="<name>"]` (see below) |
   | `theme.json` | `name`, `label`, `description`, `author`, `licence`, and the `style` it gives a deck: `accent`, `ink`, `paper` (colours like `#1E1B4B`), optionally `titleSize`, `bodySize`, `header` |
   | fonts | `.woff2`, with their licence next to them (`OFL.txt`); latin and latin-ext subsets are plenty |
   | pictures | a logo, a cover background: `.svg`, `.png`, `.webp`, `.jpg` |

3. Build it and look at it:

   ```bash
   python3 scripts/themes.py            # themes/<name>.css with everything inlined, and the sample deck
   ./studio.sh themes/<name>/deck.json  # the sample deck in your theme; P presents
   python3 scripts/theme_preview.py <name>   # themes/<name>/preview.png for the gallery (Node, Chrome, Pillow)
   ```

   While you work on the CSS, use **Theme from a file…** in the same Style section to load your
   `themes/<name>.css` straight from the disk.
4. Run `tests/all.sh`, then open a pull request. The suite loads every theme through the editor's own
   filter, and a rule it would leave out fails it.

## What a theme can do

The editor applies a theme on the deck's own say-so, and a deck can come from anyone. So the editor
keeps only what a theme is for:

- **Rules for the slides.** Each selector is `html[data-slaidy-theme="<name>"] .stage …`, meaning a
  slide and what is inside it. A rule for anything else is left out: the toolbar, the page, a
  sibling of a slide (`~`, `+`).
- **Custom properties** `--th-*` on `html[data-slaidy-theme="<name>"]` itself, to name the palette
  once and use it everywhere.
- **`@font-face`**, **`@media`**, **`@supports`**, and **`@keyframes`** whose names start with
  `<name>-`.
- **Pictures and fonts inside the CSS only.** In the source they are relative `url(…)`s to files in
  the folder; `scripts/themes.py` turns them into `data:` URIs. A `url()` to an address is dropped,
  because opening a deck must not fetch anything. So is `@import`.
- `position:fixed` becomes `absolute`, so a slide cannot cover the window.

What the page gives a theme to work with:

| | |
|---|---|
| `html[data-slaidy-theme="<name>"]` | set while the deck uses the theme |
| `.stage.lay-<layout>` | every slide says its layout: `lay-cover`, `lay-closing`, `lay-text`, `lay-two`, … |
| `var(--slaidy-footer)` | the deck's footer line as a CSS string: `style.footer`, or the title. Use it as `content:var(--slaidy-footer)` |
| `var(--d-accent)`, `--d-ink`, `--d-paper`, `--d-title`, `--d-body` | the deck's style, after any change in the Style section |
| `.stage h2`, `.stage .hdr`, `.stage .tx` (the body), `.tx blockquote`, `table`, `code`, `pre` | the parts of a slide |

The themes here show two ways to build one. `recombee/theme.css` and `paper/theme.css` are small
and write their rules directly; `paper` also shows the footer line and a different cover and closing.
`aidetem/`, `tiny/` and `kurikulum/` share one structure that reads a palette of `--th-*`
properties, so a new look in that family is mostly a new palette.

## Figures

A theme does not redraw figures; they are SVG with their own colours. A figure that should follow
any theme can use the deck's colours through CSS: `style="fill:var(--d-accent)"`,
`style="fill:var(--d-ink)"`. The sample deck's figure (`themes/sample.json`) does exactly that.
