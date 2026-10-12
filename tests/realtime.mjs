// Runs one test page in real time (no --virtual-time-budget) and prints its
// <pre id="out">. For tests that reload pages and rely on browser storage, where
// virtual time fires storage timeouts before the storage has answered.
//   node tests/realtime.mjs <url> [timeout-ms=120000]
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const [URL_, TMO = 120000] = process.argv.slice(2);
const chrome = process.env.CHROME_BIN || 'google-chrome';
const prof = mkdtempSync(join(tmpdir(), 'slaidy-rt-'));
const port = 9500 + Math.floor(Math.random() * 400);
const proc = spawn(chrome, ['--headless=new', '--disable-gpu', '--no-sandbox', `--user-data-dir=${prof}`,
  `--remote-debugging-port=${port}`, '--window-size=1280,800', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 60 && !target; i++) { await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pend = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } });
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate', { url: URL_ });
let out = null; const t0 = Date.now();
while (Date.now() - t0 < +TMO) { await sleep(500);
  const r = await send('Runtime.evaluate', { expression: "(document.getElementById('out')||{}).textContent||''", returnByValue: true });
  const v = r.result?.result?.value; if (v) { out = v; break; } }
console.log(out ?? 'ERROR the test did not finish in real time');
ws.close(); proc.kill(); await sleep(300);
try { rmSync(prof, { recursive: true, force: true }); } catch {}
