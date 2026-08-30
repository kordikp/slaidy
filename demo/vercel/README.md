# The demo's AI

The demo is a static page, and a static page keeps no secrets: anything it can read, so
can anyone who opens it. There is no arrangement of environment variables, build steps or
hidden files that changes that — a key in the page is a key given away.

So the key is not in the page. It sits in this function's environment on Vercel, and the
page calls the function.

```
demo (kordikp.github.io/slaidy)  ──POST──▶  api/ai on Vercel  ──▶  llm.ai.e-infra.cz
                                             holds CESNET_API_KEY
```

## Deploying it

```bash
cd demo/vercel
vercel link --yes
printf '%s' "$YOUR_KEY" | vercel env add CESNET_API_KEY production --yes   # stdin, never argv
vercel --prod --yes
```

Then set `DEMO_AI` in `slaidy.html` to the deployment URL. Leave it empty and the demo
simply has no AI — which breaks nothing: the editor, the presenter and every export work
without it.

Deployment protection has to be **off** for the production URL, or the demo gets a Vercel
login page instead of an answer.

## What holds, and what does not

| | |
|---|---|
| origin | one, the demo's — but an `Origin` header is trivially forged outside a browser, so treat this as tidiness, not a wall |
| shape | the two fields the app sends. No conversation, no model choice, no streaming |
| size | 24 000 characters in |
| tokens | 6 000 out, hard — this is a real limit |
| per address | `DEMO_PER_IP_HOUR`, 15 |
| per day | `DEMO_PER_DAY`, 300, then it stops answering |

The per-address count lives in one instance's memory. Serverless means several instances
and a cold start wipes it, so it is a speed bump rather than a guarantee. **The limits
that actually hold are the token ceiling and the daily budget**, and the daily budget is
the number to watch, because behind it is somebody's academic quota.

Turning it off is deleting the project, or emptying `DEMO_AI`. Neither breaks anything else.
