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
  const system = String(body.system || ''), user = String(body.user || '');
  if (!user) return no(400, 'nothing to answer');
  if (system.length + user.length > MAX_CHARS)
    return no(413, 'too long for the demo — run it locally with your own key');

  const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'anon';
  const isFig = String(body.kind || '') === 'figure' || Number(body.maxTok || 0) >= 10000;
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
     max_tokens comes back empty with finish_reason "length" */
  const asked = Math.min(MAX_TOKENS, Math.max(4000, Number(body.maxTok || 4000) * 8));

  let d;
  try {
    const r = await fetch(`${UPSTREAM}/chat/completions`, {
      method: 'POST',
      headers: { 'content-type': 'application/json',
                 authorization: `Bearer ${process.env.CESNET_API_KEY}` },
      body: JSON.stringify({
        model: MODEL,
        messages: [{ role: 'system', content: system }, { role: 'user', content: user }],
        max_tokens: asked,
      }),
    });
    d = await r.json();
  } catch (e) {
    return no(502, `could not reach the model — ${e.message}`);
  }

  if (d && d.error) return no(502, typeof d.error === 'string' ? d.error : (d.error.message || 'upstream error'));
  /* the gateway answers with choices: null under load rather than with an error */
  const choice = ((d && d.choices) || [])[0];
  if (!choice) return no(502, 'the model returned no choices — usually load; try again');
  const msg = choice.message || {};
  if (!msg.content && msg.reasoning_content)
    return no(502, 'the model spent its whole budget thinking and never wrote an answer');

  return res.status(200).json({ text: msg.content || '', usage: d.usage || {},
                               model: d.model || MODEL, limits: left });
};

function safeJson(s) { try { return JSON.parse(s); } catch { return {}; } }
