# Security

Slide Studio runs entirely in your browser. It has no server of its own, no account,
and nothing it edits leaves the machine unless you export it.

Two places are worth knowing about.

**Your AI key.** If you point the app at an OpenAI-compatible endpoint under
`⋯ → AI usage`, the key is stored in that browser's `localStorage` and sent only to
the endpoint you named. Run it with `./studio.sh` instead and the key stays in the
shell environment: the page never sees it, and it never appears on a command line
where `ps` would show it.

**The local server.** `scripts/serve.py` binds to `127.0.0.1` only, because it writes
the deck file on request. Do not put it on a public interface.

## Reporting something

Open a [security advisory](https://github.com/kordikp/slide-studio/security/advisories/new)
rather than a public issue, and give it a few days before saying more.
