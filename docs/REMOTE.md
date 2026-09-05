# A deck at a URL

`slaidy.html?deck=<url>` opens the deck served at that address, and every save
is a `PUT` of the same JSON back to it. That is the whole protocol:

- `GET <url>` → the deck bundle `{id, title, meta, style, slides[], figs{}}`
- `PUT <url>` (body = the bundle) → store a new revision; reply `{ok, rev}`

Anything that answers those two verbs is a deck storage. Two that exist:

- **A class storage on Vercel** — the p-book living-textbook engine
  ([recsys-pbook](https://github.com/kordikp/recsys-pbook)) exposes
  `/api/decks`: decks are grouped under a class code, every revision is kept,
  and the book's studio saves and loads decks with one click. A share link
  looks like
  `…/slaidy/?deck=https://pbook-internet.vercel.app/api/decks%3Fid%3Ddx7…`
- **A GitLab repository** — a raw-file URL works read-only out of the box
  (`https://gitlab…/raw/main/decks/talk.json`); writes need the commits API
  behind a tiny proxy that turns `PUT` into a commit. Storage stays under the
  faculty's roof, history is `git log`.

If the storage refuses a write (read-only link, network down), the banner says
so and the browser copy still holds the work — same guarantee as a local file.
`#present` combines with `?deck=` for a projector link.
