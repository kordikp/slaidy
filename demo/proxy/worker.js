/* A key that reaches the browser is a key given away, and a static page has
   nowhere else to keep one. So the demo's AI goes through this: a worker that
   holds the key as a secret, forwards to CESNET e-INFRA, and is boring about
   everything else.
 *
 * It exists to let a stranger try the AI for a minute without an account. It is
 * not an API. Everything below is there to keep it from becoming one.
 *
 *   npx wrangler deploy
 *   npx wrangler secret put CESNET_API_KEY
 */

const UPSTREAM = 'https://llm.ai.e-infra.cz/v1/chat/completions';
const MODEL = 'qwen3.5';

/* Only the page it exists for. A proxy that answers everyone is an open relay
   with someone's academic quota behind it. */
const ORIGINS = ['https://kordikp.github.io'];

const PER_IP_PER_HOUR = 20;      // enough to try it, not enough to work with
const MAX_TOKENS = 6000;         // a figure is the expensive call; nothing needs more
const MAX_CHARS = 24000;         // the whole request, system and user together
const DAY_BUDGET = 4000;         // calls a day across everyone, then it stops

const cors = o => ({
  'Access-Control-Allow-Origin': ORIGINS.includes(o) ? o : ORIGINS[0],
  'Access-Control-Allow-Headers': 'content-type',
  'Access-Control-Allow-Methods': 'POST,OPTIONS',
  'Vary': 'Origin',
});

const no = (msg, status, o) => new Response(JSON.stringify({ error: msg }), {
  status, headers: { 'content-type': 'application/json', ...cors(o) },
});

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    if (request.method === 'OPTIONS') return new Response(null, { headers: cors(origin) });
    if (request.method !== 'POST') return no('POST only', 405, origin);
    if (!ORIGINS.includes(origin)) return no('this proxy answers one page only', 403, origin);
    if (!env.CESNET_API_KEY) return no('the demo has no key configured', 503, origin);

    let req;
    try { req = await request.json(); } catch { return no('unreadable request', 400, origin); }

    /* the shape the app sends, and nothing else — no passing a whole
       conversation through, no choosing a model, no streaming */
    const system = String(req.system || '');
    const user = String(req.user || '');
    if (!user) return no('nothing to answer', 400, origin);
    if (system.length + user.length > MAX_CHARS)
      return no('too long for the demo — run it locally with your own key', 413, origin);

    const ip = request.headers.get('CF-Connecting-IP') || 'anon';
    const hour = new Date().toISOString().slice(0, 13);
    const day = hour.slice(0, 10);

    // KV is optional: without it the proxy still works, just without the counters
    if (env.LIMITS) {
      const ipKey = `ip:${ip}:${hour}`, dayKey = `day:${day}`;
      const [used, spent] = await Promise.all([
        env.LIMITS.get(ipKey).then(Number).catch(() => 0),
        env.LIMITS.get(dayKey).then(Number).catch(() => 0),
      ]);
      if (used >= PER_IP_PER_HOUR)
        return no(`the demo allows ${PER_IP_PER_HOUR} calls an hour. Run it locally with your own ` +
                  `key — ⋯ → AI usage has a preset for e-INFRA.`, 429, origin);
      if (spent >= DAY_BUDGET)
        return no('the demo has used its budget for today. Run it locally with your own key.',
                  429, origin);
      await Promise.all([
        env.LIMITS.put(ipKey, String(used + 1), { expirationTtl: 7200 }),
        env.LIMITS.put(dayKey, String(spent + 1), { expirationTtl: 172800 }),
      ]);
    }

    /* qwen3.5 spends most of a budget thinking before it answers, so a small
       max_tokens comes back empty with finish_reason "length" */
    const asked = Math.min(MAX_TOKENS, Math.max(4000, Number(req.maxTok || 4000) * 8));

    let upstream;
    try {
      upstream = await fetch(UPSTREAM, {
        method: 'POST',
        headers: { 'content-type': 'application/json',
                   authorization: `Bearer ${env.CESNET_API_KEY}` },
        body: JSON.stringify({
          model: MODEL,
          messages: [{ role: 'system', content: system }, { role: 'user', content: user }],
          max_tokens: asked,
        }),
      });
    } catch (e) {
      return no(`could not reach the model — ${e.message}`, 502, origin);
    }

    const d = await upstream.json().catch(() => null);
    if (!d) return no('the model answered with something that is not JSON', 502, origin);
    if (d.error) return no(typeof d.error === 'string' ? d.error : (d.error.message || 'upstream error'),
                           502, origin);

    /* the gateway answers with choices: null under load rather than an error */
    const choice = (d.choices || [])[0];
    if (!choice) return no('the model returned no choices — usually load; try again', 502, origin);
    const msg = choice.message || {};
    if (!msg.content && msg.reasoning_content)
      return no('the model spent its whole budget thinking and never wrote an answer', 502, origin);

    return new Response(JSON.stringify({
      text: msg.content || '', usage: d.usage || {}, model: d.model || MODEL,
    }), { headers: { 'content-type': 'application/json', ...cors(origin) } });
  },
};
