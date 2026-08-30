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

| | | |
|---|---|---|
| origin | one, the demo's | tidiness, not a wall — an `Origin` header is trivially forged outside a browser |
| shape | the two fields the app sends | no conversation, no model choice, no streaming |
| size | 24 000 characters in | |
| tokens | 6 000 out | hard, and a real limit |
| figures a day, per address | `DEMO_FIGS_IP_DAY`, 6 | a drawn figure is twenty thousand tokens of SVG against a few hundred for a paragraph, so it gets its own allowance |
| calls a day, per address | `DEMO_PER_IP_DAY`, 40 | |
| calls an hour, per address | `DEMO_PER_IP_HOUR`, 15 | |
| calls a day, everyone | `DEMO_PER_DAY`, 300 | then it stops answering |

Every answer carries what is left and when it resets, so the page can show it and say
when the AI comes back rather than only that it has gone. A refusal also carries the way
round it: run it locally, where there is no limit at all.

The per-address counts live in one instance's memory. Serverless means several instances
and a cold start wipes them, so they are a speed bump rather than a guarantee. **The
limits that actually hold are the token ceiling and the shared daily budget**, and that
daily number is the one to watch, because behind it is somebody's academic quota.

Turning it off is deleting the project, or emptying `DEMO_AI`. Neither breaks anything else.
