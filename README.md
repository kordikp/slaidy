# SlAIdy

**A slide editor in one HTML file, where the deck stays a folder of markdown.**

*Slides, with the AI in the middle of the word and out of the way of the work.*

[![tests](https://github.com/kordikp/slaidy/actions/workflows/tests.yml/badge.svg)](https://github.com/kordikp/slaidy/actions/workflows/tests.yml)
[![MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)
![one file](https://img.shields.io/badge/dependencies-none-brightgreen)
![no build](https://img.shields.io/badge/build%20step-none-brightgreen)

You edit in the browser, present full screen, and export a PDF — but the deck on disk
is markdown and `.svg` figures the whole time. Nothing is locked inside the
application, and if the application disappears you still have a deck.

### [Try it in your browser →](https://kordikp.github.io/slaidy/)

A deck can also live at a URL — `?deck=<address>` opens it and saves back to it,
which is how a class shares one storage ([docs/REMOTE.md](docs/REMOTE.md)).

Nothing to sign up for and nothing uploaded — the same single file with the tour deck in
it, and a small daily allowance of AI so you can see what the panels do. A real talk is
published the same way: [the ISD 2026 keynote](https://kordikp.github.io/slaidy/isd2026/),
37 slides and 41 figures in one link, with [its notes](https://kordikp.github.io/slaidy/isd2026/notes/)
and [a reading of every slide](https://kordikp.github.io/slaidy/isd2026/commentary/).

## Run it on your machine, with your own key

This is the editor you work in. On Linux it is four commands; elsewhere skip
`install.sh` and `studio.sh` is the whole story.

```bash
git clone https://github.com/kordikp/slaidy && cd slaidy
cp .env.example .env        # put your key in it — or nothing, see below
./install.sh                # launcher entry, an icon, and `slaidy` on the command line
./studio.sh                 # or just start it from here
```

`studio.sh` serves the editor at `http://localhost:8080` and opens it — in a window of its
own where GTK and WebKit are present (Ubuntu ships both), in a browser window otherwise. It
reopens the deck you had last time; `./studio.sh decks/isd2026.json` opens a particular one.
Press `?` for the shortcuts, `P` to present.

**Where the key goes.** `studio.sh` reads `.env` into the server's environment and nowhere
else: not onto a command line where `ps` would show it, and not into the page. The page
talks to `studio.sh`, and `studio.sh` talks to the model, so the browser never holds a key.
`.env` is ignored by git; [`.env.example`](.env.example) is the template, with a block for
each way of pointing it at a model:

- **OpenAI**, or anything else that speaks `/chat/completions` — OpenRouter, Together, Groq,
  an institutional gateway: `OPENAI_KEY`, plus `OPENAI_BASE_URL` when it is not OpenAI.
- **A model on this machine** — Ollama, LM Studio, llama.cpp, vLLM: no key, because there is
  nobody to authenticate to, and nothing you write leaves the machine. If one is already
  running when you start `studio.sh`, it is found without any `.env` at all.
- **CESNET e-INFRA CZ**, free to anyone affiliated at a Czech academic institution:
  `CESNET_API_KEY`.

The banner says which one it found:

```
SlAIdy 3b83597  ·  isd2026.json  ·  AI via OpenAI
  http://localhost:8080
```

Everything except the AI panels works with no model at all.

**What is yours stays yours.** A deck is a file in `decks/`, and every save writes that file
— no second copy to disagree with it, no permission prompt after a restart, twelve version
snapshots behind it. Start it again from the launcher while one is running and the second
copy takes the next port, so two decks can sit side by side and slides can be carried
between them with `Ctrl-C` / `Ctrl-V`, figures included.

## Two decks to open

| | | |
|---|---|---|
| **The tour** | [`decks/example.json`](decks/example.json) | nine slides that show what the editor does, built from [`example/slides/01-tour.md`](example/slides/01-tour.md) and the SVGs beside it — a deck in its markdown form |
| **The keynote** | [`decks/isd2026.json`](decks/isd2026.json) | *The Great Convergence*, the ISD 2026 keynote: 37 slides in eight sections, 41 figures, 412 kB in all — a real talk, kept here as the worked example |

The keynote is what a deck looks like once it has been used in anger: one-, two- and
three-column layouts, tables on most slides, a formula or two, figures that were generated
by a model, drawn by a script or pasted in as SVG and then corrected by hand in the figure
editor, a QR code that is itself an SVG figure, and a speaker note on every slide that starts
with the clock time the slide should be reached at. It is published from the same file:
[the link that presents](https://kordikp.github.io/slaidy/isd2026/#present),
[the notes on paper](https://kordikp.github.io/slaidy/isd2026/notes/), and
[the deck read slide by slide](https://kordikp.github.io/slaidy/isd2026/commentary/) for
the audience.

## On the web

A talk you have finished and want to send. Any deck under `site/` becomes a page of its
own, carrying the whole editor:

```bash
python3 scripts/publish.py decks/isd2026.json isd2026    # site/isd2026/deck.json, and notes/
git add site && git commit -m "Publish it" && git push
```

→ `https://kordikp.github.io/slaidy/isd2026/` — a link that presents. Whoever opens it can
watch it (`P`), read the notes (`N`), take a PDF, or edit their own copy; their edits stay
in their browser and never touch what you published. `#present` on the end opens straight
into the projector, and `notes/` is the speaker notes as a document that prints.

`scripts/commentary.py` adds a third page, the deck read for its audience: every slide as
it projects, with a paragraph under it that says what the slide claims and links the
sources in the text. You write the commentary as markdown, one block per slide; the script
lays it out. `scripts/check_links.py` resolves every DOI and arXiv id in a deck or a page
and says which are dead.

The [demo](https://kordikp.github.io/slaidy/) is the same thing with the tour deck in it,
and a small daily allowance of AI so you can see what the panels do.

## What it is for

A talk you will give more than once, whose figures you want to keep, whose text you
want to `grep`, and whose history you want in git. If you need a deck by Thursday and
will never open it again, use anything else — this is for the deck you maintain.

**Three rules the project keeps**, in order, and which most decisions come back to:

1. **One file, no dependencies, no build step.** `slaidy.html` opens from a
   `file://` URL and works. CI fails the build if a `<script src=>` appears.
2. **The deck outlives the editor.** Markdown in, markdown out, figures as SVG. Nothing
   the app can write is something only the app can read.
3. **One stage, three surfaces.** The editor, the projector and the PDF draw the same
   1280×720 stage from the same code, differing only by `transform: scale()`. What you
   arrange is what the room sees.

---

## What you get

Most slide tools own your content. Markdown-to-slides tools give the content back but
take away the editing. This does both.

| | |
|---|---|
| **Write** | click the title on the slide, drag a paragraph by its grip, insert a heading (`###` for a big one), table, formula, code block or figure below it |
| **Draw** | figures are SVG, written into the body like any other block: draw one by hand, paste SVG, or have it generated — a generated one is measured, thin lines and labels inside their boxes, and drawn again if it fails — then edit it in place: select a shape, move it, join two boxes with an arrow that re-routes itself |
| **Ask** | say what a slide is for and it writes the slide; ask what it would change and it answers with a list you can strike lines out of; the work waits on its slide while you move on |
| **Arrange** | pick a shape for the slide — one column, two, three, a cover; the deck holds the shapes and can carry your own |
| **Present** | `P` for full screen, `N` for notes, `O` for the grid, `H` to rehearse the hidden slides too, tap or swipe on a phone |
| **Carry** | select slides in the list, `Ctrl-C`, and `Ctrl-V` them into another deck — the figures travel with them |
| **Export** | PDF, markdown, one `.json` bundle, or the whole deck as an article with the figures rasterised |
| **Keep** | every save writes the file on disk; twelve version snapshots; one `Ctrl-Z` per gesture; it reopens the deck you had |

Everything works without the AI. Nothing the AI does lands without you taking it.

## Why there are no bitmaps

A figure here is SVG, and only SVG. You cannot drop a PNG on a slide and have it become the
picture. That is not an omission.

The whole deck is text — markdown for the words, SVG for the drawings — because **both of you
have to be able to read it**. You, when you come back to a talk a year later and want to know
what a diagram claims. Git, when it shows you what changed. And the AI, when you ask it to make
a figure sparser or to swap two boxes: it can only do that to a drawing it can read. A bitmap is
opaque to all three. It can be shown and it can be scaled, and that is all — nobody can edit it,
nobody can diff it, and asking a model to change it means asking it to draw a new one from
scratch and hope.

The compactness follows from the same choice rather than being a separate feature:

| | |
|---|---|
| a 237-slide deck, 180 figures | **1.0 MB**, everything included |
| the median figure | 3.7 kB |
| the same deck exported as `.pptx` | 33.8 MB — **33× larger** |
| the ISD 2026 keynote, 37 slides, 41 figures, 28 of them animated | 412 kB |
| the editor itself | 391 kB, one file |

This is the same bet [**pbook**](https://github.com/kordikp/recsys-pbook)
([live](https://recsys-pbook.vercel.app)) makes, and the reason the two projects feel related: a
book whose concepts, contracts and diagrams are all readable text, so a reader and a model can
both extend it, and neither has to take the other's word for what is there. Different artefact,
same principle — **the material has to be legible to everyone working on it, human or not.**

## How it works

The parts worth knowing before you change anything:

- **[docs/DESIGN.md](docs/DESIGN.md)** — the file format, what the editor does, where a
  deck lives and how it is kept, and the reasoning behind the odd-looking parts.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — running it, the test suite, what the project
  says no to and why, and a map of the one file it is all in.
- **[.env.example](.env.example)** — every way of pointing it at a model, local or hosted.
- **`scripts/`** — `serve.py` and `window.py` are what `studio.sh` runs; `publish.py`,
  `commentary.py` and `check_links.py` are the way to the web; `build_bundle.py` turns a
  folder of markdown into a deck.

## Thanks

The AI here runs on capacity from **[CESNET e-INFRA CZ](https://www.e-infra.cz/en)**, free to anyone
affiliated at a Czech academic institution. Everything else in the editor works without it.

## Who

Built by [Pavel Kordík](https://kordikp.github.io) — CTU FIT and Recombee.

## Licence

MIT. See [LICENSE](LICENSE).
