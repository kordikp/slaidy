# SlAIdy

**A slide editor in one HTML file, where the deck stays a folder of markdown.**

*Slides, with the AI in the middle of the word and out of the way of the work.*

[![tests](https://github.com/kordikp/slaidy/actions/workflows/tests.yml/badge.svg)](https://github.com/kordikp/slaidy/actions/workflows/tests.yml)
[![MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)
![one file](https://img.shields.io/badge/dependencies-none-brightgreen)
![no build](https://img.shields.io/badge/build%20step-none-brightgreen)

You edit in the browser, present full screen, and export a PDF — but the deck on disk
is `.md` files and `.svg` figures the whole time. Nothing is locked inside the
application, and if the application disappears you still have a deck.

### [Try it in your browser →](https://kordikp.github.io/slaidy/)

Nothing to sign up for and nothing uploaded — the same single file and an example deck,
with a small daily allowance of AI so you can see what it does.

Then run it properly, which takes one command:

```bash
git clone https://github.com/kordikp/slaidy
cd slaidy
./studio.sh
```

That serves the example deck at `http://localhost:8080` and opens it. Press `?` for
the shortcuts, `P` to present.

### Its own model, or yours

The AI is where you point it, and it never reaches the browser: the page talks to
`studio.sh`, and `studio.sh` talks to the model.

**A model on this machine** is the case the project is built around. Start Ollama, LM
Studio, llama.cpp or vLLM and run `./studio.sh` — it finds the server, asks it which
model to use, and says so in the banner. No key: there is nobody to authenticate to,
and nothing you write leaves the machine.

```
SlAIdy  ·  example.json  ·  AI via qwen3:14b on this machine
  AI: on, qwen3:14b via http://localhost:11434/v1 — nothing leaves this machine
```

**A hosted model** takes a key in `.env`, which stays in the shell environment and never
appears on a command line. Copy [`.env.example`](.env.example) and uncomment a block —
OpenAI, an institutional gateway, or anything else that speaks
`/chat/completions`.

Either way the editor is the same. Everything except the AI panels works with no model
at all.

### What it is for

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
| **Write** | click the title on the slide, drag a paragraph by its grip, insert a heading, table, formula, code block or figure below it |
| **Draw** | figures are SVG, written into the body like any other block, and editable in place — select a shape, move it, join two boxes with an arrow that re-routes itself |
| **Ask** | say what a slide is for and it writes the slide; ask what it would change and it answers with a list you can strike lines out of |
| **Arrange** | pick a shape for the slide — one column, two, three, a cover; the deck holds the shapes and can carry your own |
| **Present** | `P` for full screen, `N` for notes, `O` for the grid, tap or swipe on a phone |
| **Export** | PDF, markdown, one `.json` bundle, or the whole deck as an article with the figures rasterised |
| **Keep** | every save writes the file on disk; twelve version snapshots; one `Ctrl-Z` per gesture |

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
| the editor itself | 290 kB, one file |

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

## Thanks

The AI here runs on capacity from **[CESNET e-INFRA CZ](https://www.e-infra.cz/en)**, free to anyone
affiliated at a Czech academic institution. Everything else in the editor works without it.

## Who

Built by [Pavel Kordík](https://kordikp.github.io) — CTU FIT and Recombee.

## Licence

MIT. See [LICENSE](LICENSE).
