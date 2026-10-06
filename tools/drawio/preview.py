#!/usr/bin/env python3
"""Draw the figures the way a browser will, next to the slide they came from.

Renders each SVG through headless Chrome (which is the only renderer that has
the embedded font and the CSS) and, when the original slide PNG is at hand,
writes a side-by-side sheet so the two can be compared at a glance.

    python3 <slaidy>/tools/drawio/preview.py                     # every figure, side by side
    python3 <slaidy>/tools/drawio/preview.py fig-svd-06          # one
    python3 <slaidy>/tools/drawio/preview.py --plain fig-svd-06  # the figure alone, no comparison
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.getcwd()                      # the lecture folder this is run in
CHROMES = ('google-chrome', 'chromium', 'chromium-browser', 'google-chrome-stable')
VIEWBOX = re.compile(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"')


def chrome():
    for c in CHROMES:
        if shutil.which(c):
            return c
    sys.exit('No Chrome or Chromium found.')


def shoot(html, out, width, height, step=1):
    with tempfile.TemporaryDirectory() as d:
        page = os.path.join(d, 'p.html')
        open(page, 'w').write(html)
        subprocess.run([chrome(), '--headless=new', '--disable-gpu', '--no-sandbox',
                        '--hide-scrollbars', f'--window-size={width},{height}',
                        '--virtual-time-budget=8000', f'--screenshot={out}',
                        f'file://{page}?step={step}'], capture_output=True, timeout=120)


def size_of(svg):
    m = VIEWBOX.search(svg)
    return (float(m.group(3)), float(m.group(4))) if m else (1000.0, 700.0)


# A merged figure holds the whole series, so a sheet has to say which step it is
# showing — the same rule the projector applies: a shape is there when its
# data-step has come and its data-until has not.
STEP_JS = """<script>
(function(){
  const k=+(new URLSearchParams(location.search).get('step')||1);
  addEventListener('load',()=>document.querySelectorAll('[data-step],[data-until]')
    .forEach(el=>{
      const from=+(el.dataset.step||1);
      const until=el.dataset.until?+el.dataset.until:Infinity;
      if(k<from||k>=until)el.style.display='none';
    }));
})();
</script>"""

PAGE = """<!doctype html><meta charset="utf-8">
<style>html,body{{margin:0;background:#fff;font:12px system-ui}}
.row{{display:flex;gap:12px;padding:12px;align-items:flex-start}}
.col{{flex:1}} .lab{{color:#666;padding:2px 0}}
img,svg{{display:block;width:100%;height:auto;border:1px solid #eee}}</style>
{js}
{body}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('which', nargs='*', help='figure ids (default: all)')
    ap.add_argument('--figures', default=os.path.join(ROOT, 'figures'))
    ap.add_argument('--sources', default=os.path.join(ROOT, 'sources'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'preview'))
    ap.add_argument('--plain', action='store_true', help='figure alone, no original beside it')
    ap.add_argument('--width', type=int, default=1100)
    ap.add_argument('--step', type=int, default=1,
                    help='which click of a merged figure to draw, and which '
                         'original slide to put beside it')
    a = ap.parse_args()

    index = json.load(open(os.path.join(a.figures, 'index.json')))
    ids = a.which or sorted(index)
    os.makedirs(a.out, exist_ok=True)
    for fid in ids:
        path = os.path.join(a.figures, fid + '.svg')
        if not os.path.exists(path):
            print(f'  ? {fid} — no such figure', file=sys.stderr)
            continue
        svg = open(path).read()
        w, h = size_of(svg)
        meta = index.get(fid, {})
        sources = meta.get('sources') or ([meta['source']] if meta.get('source') else [])
        src = os.path.join(a.sources, sources[min(a.step, len(sources)) - 1] if sources else '')
        out_name = fid if a.step == 1 and len(sources) < 2 else f'{fid}-step{a.step}'
        pair = not a.plain and os.path.exists(src)
        if pair:
            half = a.width // 2 - 18
            body = (f'<div class=row><div class=col><div class=lab>original · '
                    f'{os.path.basename(src)}</div><img src="file://{src}"></div>'
                    f'<div class=col><div class=lab>svg · {fid}</div>{svg}</div></div>')
            width, height = a.width, int(half * h / w) + 40
        else:
            body = svg
            width, height = a.width, int(a.width * h / w)
        shoot(PAGE.format(body=body, js=STEP_JS), os.path.join(a.out, out_name + '.png'),
              width, height, a.step)
        print(f'  {out_name}  {os.path.join(a.out, out_name + ".png")}')


if __name__ == '__main__':
    main()
