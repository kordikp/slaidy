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
const MAX_TOKENS = 6000;   // a figure is the expensive call; nothing needs more
const PER_IP_HOUR = Number(process.env.DEMO_PER_IP_HOUR || 20);
const PER_DAY = Number(process.env.DEMO_PER_DAY || 2000);

/* Counted in the instance's own memory. Serverless means several instances and
   a cold start wipes the count, so this is a speed bump, not a guarantee — the
   caps that actually hold are the origin, the shape, and the token ceiling. The
   daily number is the one to lower before telling anyone about the demo. */
const seen = new Map();
let day = '', spent = 0;

function allow(ip) {
  const now = Date.now(), today = new Date().toISOString().slice(0, 10);
  if (today !== day) { day = today; spent = 0; }
  if (spent >= PER_DAY) return 'the demo has used its budget for today';
  const hits = (seen.get(ip) || []).filter(t => now - t < 3600e3);
  if (hits.length >= PER_IP_HOUR) return `the demo allows ${PER_IP_HOUR} calls an hour`;
  hits.push(now); seen.set(ip, hits); spent++;
  if (seen.size > 5000) seen.clear();          // it is a Map, not a database
  return null;
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
  const stop = allow(ip);
  if (stop) return no(429, `${stop}. Run it locally with your own key — ⋯ → AI usage has a preset `
                         + `for CESNET e-INFRA, which is free for Czech academia.`);

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

  return res.status(200).json({ text: msg.content || '', usage: d.usage || {}, model: d.model || MODEL });
};

function safeJson(s) { try { return JSON.parse(s); } catch { return {}; } }
