# Security

Slide Studio runs entirely in your browser. It has no server of its own, no account,
and nothing it edits leaves the machine unless you export it.

Two places are worth knowing about.

**Your AI key.** If you point the app at an OpenAI-compatible endpoint under
`⋯ → AI usage`, the key is stored in that browser's `localStorage` and sent only to
the endpoint you named. Run it with `./studio.sh` instead and the key stays in the
shell environment: the page never sees it, and it never appears on a command line
where `ps` would show it.

**The demo's key.** There is none in the page, and there cannot be: a static page keeps no
secrets. The demo's AI goes through a small function ([`demo/vercel`](demo/vercel)) that
holds the key in its own environment, accepts only the two fields the app sends, and caps
tokens per call and calls per day. There is an assertion in the suite that no key-shaped
string appears in the file at all.

**The local server.** `scripts/serve.py` binds to `127.0.0.1` only, because it writes
the deck file on request. Do not put it on a public interface.

## What a deck is allowed to do

A deck can arrive from anywhere — dropped in, imported, pasted from another machine,
or written by a model — so the app treats one as untrusted text.

- **Slide text is escaped before anything else happens.** Markdown is rendered from
  escaped text, so `<img src=x onerror=…>` in a slide is shown, not run.
- **A link is only a link.** `http`, `https`, `mailto`, an anchor or a relative path
  go through; `javascript:`, `data:` and `vbscript:` keep their words and lose their
  target — including when the scheme is hidden behind whitespace or control characters.
- **A figure is a drawing, not a program.** Every path that renders an SVG goes through
  `scopeSvg`, which strips `<script>`, `on*` handlers, `foreignObject` and script-bearing
  `href`s. The figure editor's canvas is additionally `sandbox="allow-same-origin"`, so
  even a drawing that got past that would run nothing.
- **No `eval`, no `new Function`, no `document.write`** anywhere in the file.

What the app does *not* defend against: a deck you open is still yours to trust for its
*content*. It can put any text and any drawing on a slide. It cannot run code.

## Reporting something

Open a [security advisory](https://github.com/kordikp/slaidy/security/advisories/new)
rather than a public issue, and give it a few days before saying more.
