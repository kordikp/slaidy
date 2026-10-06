// Screenshots of a deck as the projector shows it, through the Chrome DevTools
// Protocol in real time — no virtual clock, so CSS animations run as they do in
// a room, and a figure is caught where its animation is at that moment.
//
//   node scripts/shots.mjs build/talk.html                 every slide → shots/s01.png …
//   node scripts/shots.mjs build/talk.html 3 7 out/         slides 3 to 7 into out/
//   node scripts/shots.mjs https://kordikp.github.io/slaidy/isd2026/ --steps
//
//   --steps        one picture per click (s05-2.png), not only the last state of a slide
//   --wait 3000    milliseconds to let a slide settle before the picture (default 2500)
//   --size 1920x1080
//
// The page is any SlAIdy page with a deck: a one-file build (scripts/onefile.py),
// a published site, or studio.sh's address. It is opened at ?s=N&step=K#present.
// Needs Node 22+ (fetch and WebSocket built in) and Chrome or Chromium.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const argv = process.argv.slice(2);
const flag = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv.splice(i, 2)[1] : d; };
const steps = argv.includes('--steps'); if (steps) argv.splice(argv.indexOf('--steps'), 1);
const WAIT = +flag('--wait', 2500);
const [W, H] = flag('--size', '1280x720').split('x').map(Number);
const [page, first = '1', last = '', OUT = 'shots'] = argv;
if (!page) { console.error('usage: node scripts/shots.mjs <page.html | url> [first] [last] [outdir] [--steps] [--wait ms]'); process.exit(2); }
const base = /^https?:|^file:/.test(page) ? page.split(/[?#]/)[0] : 'file://' + resolve(page);
const chrome = process.env.CHROME_BIN || ['google-chrome', 'chromium', 'chromium-browser'].find(c =>
  ['/usr/bin/', '/usr/local/bin/', '/snap/bin/'].some(d => existsSync(d + c))) || 'google-chrome';
const prof = mkdtempSync(join(tmpdir(), 'slaidy-shots-'));
const port = 9300 + Math.floor(Math.random() * 500);
mkdirSync(OUT, { recursive: true });
const proc = spawn(chrome, ['--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
  `--user-data-dir=${prof}`, `--remote-debugging-port=${port}`, `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));

let target;
for (let i = 0; i < 75 && !target; i++) {
  await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch {}
}
if (!target) { console.error(`could not start ${chrome}`); proc.kill(); process.exit(1); }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
// the page's own state: how many slides are shown, and how many clicks this one has
const ask = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result?.result?.value;

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
const open = async (n, k) => { await send('Page.navigate', { url: `${base}?s=${n}${k ? '&step=' + k : ''}#present` }); await sleep(WAIT); };
await open(+first);
const total = await ask('typeof liveIdx==="function"?liveIdx().length:0');
const end = Math.min(+last || total || +first, total || Infinity);
const shoot = async name => {
  // the "fill the screen" prompt is for a person at the keyboard, not for a picture
  await ask('document.getElementById("turn")?.classList.remove("on"),1');
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  const f = join(OUT, name + '.png'); writeFileSync(f, Buffer.from(shot.result.data, 'base64')); console.log(f);
};
for (let n = +first; n <= end; n++) {
  if (n !== +first) await open(n);
  const name = 's' + String(n).padStart(2, '0');
  const k = steps ? await ask('typeof stepsOf==="function"?stepsOf(S.slides[cur]):1') || 1 : 1;
  if (k < 2) { await open(n, steps ? 0 : 99); await shoot(name); continue; }
  for (let s = 1; s <= k; s++) { await open(n, s); await shoot(`${name}-${s}`); }
}
ws.close(); proc.kill(); await sleep(300);
try { rmSync(prof, { recursive: true, force: true }); } catch {}
