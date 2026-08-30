/* The demo is a static page, and a static page keeps no secrets. So the key
   lives here instead, as an environment variable on the server, and the page
   calls this.
 *
 * It exists so a stranger can try the AI for a minute without an account. It is
 * not an API, and everything below is there to stop it becoming one.
 */

const UPSTREAM = process.env.CESNET_BASE_URL || 'https://llm.ai.e-infra.cz/v1';
const MODEL = process.env.CESNET_MODEL || 'qwen3.5';

/* One origin. A proxy that answers everyone is an open relay with somebody's
   academic quota behind it. */
const ORIGINS = (process.env.DEMO_ORIGINS || 'https://kordikp.github.io')
  .split(',').map(s => s.trim()).filter(Boolean);

const MAX_CHARS = 24000;   // system and user together
const MAX_TOKENS = 6000;
/* A figure is a whole SVG document — twenty thousand tokens of it, with room on
   top for a model that thinks before it writes. Capping it at MAX_TOKENS meant
   the demo could never draw one at all: the answer came back truncated and the
   app reported, correctly, that it was not an SVG. */
const FIG_TOKENS = 32000;

/* A figure is the expensive call by an order of magnitude — twenty thousand
   tokens of SVG against a few hundred for a paragraph — so it gets its own
   allowance rather than sharing one. Enough to draw a few and see what the
   thing does; not enough to make a deck on somebody else's quota. */
const PER_IP_HOUR = Number(process.env.DEMO_PER_IP_HOUR || 15);
const PER_IP_DAY = Number(process.env.DEMO_PER_IP_DAY || 40);
const FIGS_IP_DAY = Number(process.env.DEMO_FIGS_IP_DAY || 6);
const PER_DAY = Number(process.env.DEMO_PER_DAY || 300);

/* Counted in the instance's own memory. Serverless means several instances and
   a cold start wipes the count, so this is a speed bump, not a guarantee — the
   caps that actually hold are the token ceiling and the daily total. */
const seen = new Map();
let day = '', spent = 0;

const midnight = () => { const d = new Date(); d.setUTCHours(24, 0, 0, 0); return d.getTime(); };

function allow(ip, isFig) {
  const now = Date.now(), today = new Date().toISOString().slice(0, 10);
  if (today !== day) { day = today; spent = 0; seen.clear(); }
  const rec = seen.get(ip) || { hour: [], dayN: 0, figs: 0 };
  rec.hour = rec.hour.filter(t => now - t < 3600e3);

  const left = {
    hour: Math.max(0, PER_IP_HOUR - rec.hour.length),
    day: Math.max(0, PER_IP_DAY - rec.dayN),
    figures: Math.max(0, FIGS_IP_DAY - rec.figs),
    shared: Math.max(0, PER_DAY - spent),
    resetsAt: midnight(),
  };

  let why = null;
  if (spent >= PER_DAY) why = 'the demo has used its shared budget for today';
  else if (rec.dayN >= PER_IP_DAY) why = `the demo allows ${PER_IP_DAY} calls a day`;
  else if (isFig && rec.figs >= FIGS_IP_DAY) why = `the demo allows ${FIGS_IP_DAY} drawn figures a day`;
  else if (rec.hour.length >= PER_IP_HOUR) {
    why = `the demo allows ${PER_IP_HOUR} calls an hour`;
    left.resetsAt = rec.hour[0] + 3600e3;      // when the oldest call falls out
  }
  if (why) return { why, left };

  rec.hour.push(now); rec.dayN++; if (isFig) rec.figs++;
  seen.set(ip, rec); spent++;
  if (seen.size > 5000) seen.clear();          // it is a Map, not a database
  return { why: null, left: {
    hour: left.hour - 1, day: left.day - 1,
    figures: isFig ? left.figures - 1 : left.figures,
    shared: left.shared - 1, resetsAt: midnight(),
  } };
}

module.exports = async (req, res) => {
  const origin = req.headers.origin || '';
  const ok = ORIGINS.includes(origin) ? origin : ORIGINS[0];
  res.setHeader('Access-Control-Allow-Origin', ok);
  res.setHeader('Access-Control-Allow-Headers', 'content-type');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Vary', 'Origin');

  const no = (status, error) => res.status(status).json({ error });

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return no(405, 'POST only');
  if (!ORIGINS.includes(origin)) return no(403, 'this endpoint answers one page only');
  if (!process.env.CESNET_API_KEY)
    return no(503, 'the demo has no key configured — the editor works without AI, or set your own '
                 + 'endpoint under ⋯ → AI usage');

  const body = typeof req.body === 'string' ? safeJson(req.body) : (req.body || {});
  const isFig = String(body.kind || '') === 'figure' || Number(body.maxTok || 0) >= 10000;
  const system = String(body.system || ''), user = String(body.user || '');
  if (!user) return no(400, 'nothing to answer');
  if (system.length + user.length > MAX_CHARS)
    return no(413, 'too long for the demo — run it locally with your own key');

  const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'anon';
  const { why, left } = allow(ip, isFig);
  if (why)
    return res.status(429).json({
      error: `${why}.`,
      limits: left,
      /* the page turns this into "the AI is back at 01:00" and an offer to run
         it locally — a limit that does not say when it lifts is just a wall */
      hint: 'Run it on your own machine and there is no limit at all: clone the repo, '
          + 'put your key under ⋯ → AI usage, and it talks to e-INFRA or OpenAI directly.',
      repo: 'https://github.com/kordikp/slaidy',
    });

  /* qwen3.5 spends most of a budget thinking before it answers, so a small
     max_tokens comes back empty with finish_reason "length". Multiplying is the
     right instrument for a small request and the wrong one for a large: asking
     for 20 000 does not mean wanting 160 000, it means wanting headroom. */
  const want = Number(body.maxTok || 4000);
  const asked = Math.min(isFig ? FIG_TOKENS : MAX_TOKENS,
                         want < 4000 ? Math.max(4000, want * 8) : want + 8000);

  /* e-INFRA is not always there, and its failures are mostly the passing kind:
     a 429 from the shared cap, a 5xx, or a body with choices: null. Retrying
     here rather than in the page means one waiting user instead of one who has
     to press the button again, and the whole thing still fits inside the
     function's minute. It does not retry a refusal — a 400 will be a 400 again. */
  const ATTEMPTS = 3;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let d = null, last = 'unknown', tried = 0;

  for (let a = 0; a < ATTEMPTS; a++) {
    tried = a + 1;
    if (a) await sleep(700 * Math.pow(2, a - 1) + Math.floor(Math.random() * 400));
    let r;
    try {
      r = await fetch(`${UPSTREAM}/chat/completions`, {
        method: 'POST',
        headers: { 'content-type': 'application/json',
                   authorization: `Bearer ${process.env.CESNET_API_KEY}` },
        body: JSON.stringify({
          model: MODEL,
          messages: [{ role: 'system', content: system }, { role: 'user', content: user }],
          max_tokens: asked,
        }),
      });
    } catch (e) { last = `could not reach the model — ${e.message}`; continue; }

    if (r.status === 429 || r.status >= 500) { last = `the model answered ${r.status}`; continue; }

    let body = null;
    try { body = await r.json(); } catch { last = 'the model answered with something that is not JSON'; continue; }

    if (body && body.error) {
      const m = typeof body.error === 'string' ? body.error : (body.error.message || 'upstream error');
      if (!r.ok && r.status < 500 && r.status !== 429) return no(502, m);   // a refusal is not transient
      last = m; continue;
    }
    /* the gateway answers with choices: null under load rather than with an error */
    if (!((body && body.choices) || [])[0]) { last = 'the model returned no choices'; continue; }
    d = body; break;
  }

  if (!d) return no(502, `${last} — tried ${tried} times over a few seconds. e-INFRA is shared and `
                       + `not always there; give it a moment and press it again.`);

  const msg = (d.choices[0].message) || {};
  if (!msg.content && msg.reasoning_content)
    return no(502, 'the model spent its whole budget thinking and never wrote an answer');

  return res.status(200).json({ text: msg.content || '', usage: d.usage || {},
                               model: d.model || MODEL, limits: left,
                               attempts: tried });
};

function safeJson(s) { try { return JSON.parse(s); } catch { return {}; } }
