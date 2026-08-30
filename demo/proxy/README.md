# The demo's AI proxy

The demo is a static page. A static page cannot keep a secret: anything it can read,
so can anyone who opens it. So there is no way to put an API key in the demo — not in
an environment variable, not in a build step, not hidden anywhere. A key that reaches
the browser is a key given away.

This is the way round it. A worker holds the key, forwards to CESNET e-INFRA, and the
demo calls the worker.

```bash
cd demo/proxy
npx wrangler kv namespace create LIMITS   # optional; the limits need somewhere to count
npx wrangler deploy
npx wrangler secret put CESNET_API_KEY    # pasted, never committed
```

Then point the demo at it — in `slaidy.html`, `DEMO_AI` near the top of the script.

## What it will and will not do

It exists so a stranger can try the AI for a minute without an account. Everything in
it is there to stop it becoming an API:

| | |
|---|---|
| origin | one, the demo's. Anything else gets a 403 |
| shape | the two fields the app sends. No conversation, no model choice, no streaming |
| size | 24 000 characters in |
| tokens | 6 000 out, hard |
| per address | 20 calls an hour |
| per day | 4 000 calls across everyone, then it stops answering |

**It is somebody's academic quota.** The daily budget is the thing to watch; lower it
before you announce the project anywhere, not after. Deleting the worker turns the
demo's AI off and breaks nothing else — the editor, the presenter and every export work
without it.
