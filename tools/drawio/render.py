#!/usr/bin/env python3
"""Render the recovered draw.io drawings as slide-ready SVG figures.

draw.io's own renderer does the drawing — the viewer library runs in headless
Chrome, so the hand-drawn (`sketch`) strokes, the cylinders and the text metrics
come out exactly as they do in the app. What this adds around it is what a deck
needs and an export does not:

* **one frame per series** — the steps of a figure were saved at different spots
  on the draw.io canvas, so each is shifted into a frame shared by the whole
  series and the drawing no longer jumps from slide to slide;
* **a reveal marker** — every cell that appears at this step is tagged, so the
  slide can animate in exactly what the click added;
* **no `foreignObject`** — labels are rendered as real SVG text, both because
  SlAIdy strips `foreignObject` from figures and because text stays editable;
* **the font travels with the figure** — a 7 kB subset of Architects Daughter
  is embedded, so a figure looks right offline and on a machine without it;
* **no `light-dark()`** — draw.io's adaptive colours would turn black labels
  light on a white slide under a dark desktop theme.

    python3 <slaidy>/tools/drawio/render.py [--only universe] [--keep-scratch]   # in the lecture folder
"""
import argparse
import base64
import collections
import glob
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from steps import cells, series_steps, _kind, _at, _offset   # noqa: E402
import merge as merger                                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.getcwd()                      # the lecture folder this is run in
VENDOR = os.path.join(HERE, 'vendor')   # the viewer is fetched here on first use, not kept in git
VIEWER = os.path.join(VENDOR, 'viewer.min.js')
FONT = os.path.join(VENDOR, 'architects-daughter.subset.woff2')
VIEWER_URL = 'https://viewer.diagrams.net/js/viewer-static.min.js'

CHROMES = ('google-chrome', 'chromium', 'chromium-browser', 'google-chrome-stable')

# The drawing is rendered once per step, so a step's own name orders the series.
STEP = re.compile(r'^(.*?)(\d+)([a-z]?)$')


def default_tex(root):
    """The lecture's .tex: the one in sources/, if there is exactly one."""
    import glob as _g
    found = sorted(_g.glob(os.path.join(root, 'sources', '*.tex')))
    return found[0] if len(found) == 1 else None


def series_of(name):
    m = STEP.match(name)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (name, 0, '')


def tex_order(path):
    """The order the lecture actually shows the figures in.

    Sorting by filename gets `universe010b` after `universe010`; the lecture
    shows it before, and a step series read in the wrong order both animates
    the wrong shapes and stops being a series of additions at all. The .tex is
    the authority on the order, so when it is at hand it decides.
    """
    tex = re.sub(r'(?<!\\)%.*', '', open(path).read())
    uses = re.finditer(r'\\simpleFigure(?:Transition)?\s*\{[\d.]+\}\s*\{([^}]+)\}'
                       r'|\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}', tex)
    out = []
    for m in uses:
        name = m.group(1) or m.group(2)
        name = name[:-4] if name.endswith('.png') else name
        if name not in out:
            out.append(name)
    return out


def group_series(names, order=None):
    """{series: [step names in order]}.

    The order comes from the lecture when it is known, and from the filename
    otherwise — `svd003b` then sorts between 003 and 004.
    """
    rank = {n: i for i, n in enumerate(order or [])}
    out = collections.defaultdict(list)
    for n in names:
        out[series_of(n)[0]].append(n)
    return {k: sorted(v, key=lambda n: (rank[n],) if n in rank else (len(rank),) + series_of(n)[1:])
            for k, v in sorted(out.items())}


# ---------------------------------------------------------------- rendering

def chrome():
    for c in CHROMES:
        if shutil.which(c):
            return c
    sys.exit('No Chrome or Chromium found — needed to run the draw.io renderer.')


HARNESS = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Architects+Daughter">
<script>window.mxLoadStylesheets=false;
window.MathJax={tex:{inlineMath:[],displayMath:[]},svg:{fontCache:'none'},
                options:{enableMenu:false},startup:{typeset:false}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<script src="viewer.min.js"></script><script src="data.js"></script>
<script src="harness.js"></script></head>
<body><pre id="out">PENDING</pre>
<div id="host" style="position:absolute;left:0;top:0;width:4000px;height:4000px;visibility:hidden"></div>
<div id="stage" style="position:absolute;left:0;top:0;opacity:0"></div>
</body></html>
"""


def render_all(drawings, scratch):
    """{name: {svg, bx, by, bw, bh}} straight out of the draw.io renderer."""
    if not os.path.exists(VIEWER):
        # draw.io's own viewer (Apache 2.0), 4 MB: fetched once rather than kept in the repository
        import urllib.request
        print(f'fetching the draw.io viewer from {VIEWER_URL} (once)', file=sys.stderr)
        try:
            # the server refuses Python's default user agent
            req = urllib.request.Request(VIEWER_URL, headers={'User-Agent': 'Mozilla/5.0 (SlAIdy tools/drawio)'})
            with urllib.request.urlopen(req, timeout=120) as r, open(VIEWER + '.part', 'wb') as f:
                shutil.copyfileobj(r, f)
            os.replace(VIEWER + '.part', VIEWER)
        except Exception as e:
            sys.exit(f'Could not fetch {VIEWER_URL} ({e}). Fetch it by hand:\n  curl -o {VIEWER} {VIEWER_URL}')
    os.makedirs(scratch, exist_ok=True)
    shutil.copy(VIEWER, os.path.join(scratch, 'viewer.min.js'))
    shutil.copy(os.path.join(HERE, 'render_harness.js'), os.path.join(scratch, 'harness.js'))
    with open(os.path.join(scratch, 'data.js'), 'w') as f:
        f.write('window.DIA=' + json.dumps(drawings) + ';')
    budget = 60000 + 4000 * len(drawings)          # measuring every label is not fast
    with open(os.path.join(scratch, 'render.html'), 'w') as f:
        f.write(HARNESS)
    dump = subprocess.run(
        [chrome(), '--headless=new', '--disable-gpu', '--no-sandbox',
         f'--virtual-time-budget={budget}', '--dump-dom',
         'file://' + os.path.join(scratch, 'render.html')],
        capture_output=True, text=True, timeout=budget / 1000 + 300).stdout
    m = re.search(r'<pre id="out">([\s\S]*?)</pre>', dump)
    if not m or m.group(1) == 'PENDING':
        sys.exit('The draw.io renderer produced nothing — is the page loading viewer.min.js?')
    out = json.loads(html.unescape(m.group(1)))
    for name, err in out['errs'].items():
        print(f'  ! {name}: {err}', file=sys.stderr)
    return out['res']


# ------------------------------------------------------------ post-process

NS = 'http://www.w3.org/2000/svg'

# Rounding is confined to attributes that hold coordinates. Applied to the whole
# file it would also "round" a label reading 30.000.000 down to 30.000.
COORD_ATTRS = ('d', 'transform', 'points', 'x', 'y', 'x1', 'y1', 'x2', 'y2',
               'cx', 'cy', 'r', 'rx', 'ry', 'width', 'height', 'stroke-width')
LONG_NUMBER = re.compile(r'-?\d+\.\d{3,}')
COORD_VALUE = re.compile(r'\b(' + '|'.join(COORD_ATTRS) + r')="([^"]*)"')
DEAD_STROKE = re.compile(r'M (-?[\d.]+) (-?[\d.]+) C \1 \2 \1 \2 \1 \2 ')


def _shorten(m):
    """A tenth of a pixel is below seeing; a scale factor is not a pixel.

    Rounding every number to one decimal is right for the sketch strokes, which
    is most of the file, and catastrophic for the small ones: MathJax places a
    formula with `scale(0.0332)`, and one decimal makes that `scale(0)`.
    """
    x = float(m.group(0))
    out = f'{x:.1f}' if abs(x) >= 1 else f'{x:.4g}'
    return out.rstrip('0').rstrip('.') if '.' in out and abs(x) >= 1 else out


def _round(m):
    return f'{m.group(1)}="{LONG_NUMBER.sub(_shorten, m.group(2))}"'


def drop_light_dark(svg):
    """light-dark(a, b) -> a. Nested rgb(...) means this cannot be a regex."""
    out, i = [], 0
    while True:
        j = svg.find('light-dark(', i)
        if j < 0:
            return ''.join(out) + svg[i:]
        out.append(svg[i:j])
        depth, k, split = 0, j + len('light-dark(') - 1, None
        while k < len(svg):
            c = svg[k]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            elif c == ',' and depth == 1 and split is None:
                split = k
            k += 1
        if k >= len(svg):
            return ''.join(out) + svg[j:]
        out.append(svg[j + len('light-dark('):split if split else k].strip())
        i = k + 1


def tidy(svg):
    """Trim what a slide does not need out of draw.io's export."""
    svg = re.sub(r'<style type="text/css">@supports[\s\S]*?</style>', '', svg, count=1)
    # draw.io paints adaptively; on a light slide under a dark desktop theme that
    # turns black labels light. Keep the light half, which is the slide's half.
    svg = drop_light_dark(svg)
    svg = re.sub(r'var\(--ge-adaptive-bg,\s*(#[0-9a-fA-F]{3,8})\)', r'\1', svg)
    svg = re.sub(r'\s+pointer-events="[a-z]+"', '', svg)
    svg = re.sub(r'\s+id="ge-svg-[^"]*"', '', svg)
    svg = re.sub(r'<defs><style type="text/css">@import[^<]*</style></defs>', '<defs/>', svg)
    svg = COORD_VALUE.sub(_round, svg)          # sketch jitter to one decimal
    svg = DEAD_STROKE.sub('', svg)              # rough.js emits zero-length hachures
    return svg


def font_css():
    b64 = base64.b64encode(open(FONT, 'rb').read()).decode()
    return ("@font-face{font-family:'Architects Daughter';font-style:normal;font-weight:400;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


# The fade that says "this is what the click added" lives in SlAIdy, which knows
# which step is being shown. A figure is one file across every step of a series
# and cannot know, so it carries no animation of its own.


def frames(rendered, names):
    """Group the steps of a series into shared frames, and place each in its own.

    draw.io crops an export to the drawing, so successive saves of one drawing
    already arrive aligned on their own top-left corner — which is a steadier
    anchor than anything recovered from the cells, because in a series like
    `svdgeo` the cells genuinely move from step to step and there is no offset
    to find. What does have to be caught is a step that is not the same drawing
    at all: `svdgeo005` and `mfALS007` are separate pictures that happen to sit
    at the end of a series, and unioning their frame with the rest would pad
    every other step with the difference.

    Returns [(frame, [names in it])].
    """
    groups = []
    for n in names:
        w, h = rendered[n]['cw'], rendered[n]['ch']
        if groups and _alike(groups[-1][0], (w, h)):
            groups[-1][1].append(n)
            groups[-1][0] = (max(groups[-1][0][0], w), max(groups[-1][0][1], h))
        else:
            groups.append([(w, h), [n]])
    return [(tuple(g[0]), g[1]) for g in groups]


def _alike(a, b, tol=0.2):
    return (abs(a[0] - b[0]) <= tol * max(a[0], b[0])
            and abs(a[1] - b[1]) <= tol * max(a[1], b[1]))


PAD = 2

# A step that changes most of the drawing is a redraw, not an addition — in
# `svdgeo` the vectors themselves move — and animating all of it in reads as the
# picture arriving late rather than as something being pointed at. Past this
# share of the drawing, the step simply appears.
REDRAW = 0.4


def settled(revealed, path):
    """The cells worth animating in: an addition, not a whole redraw."""
    total = len(cells(path)) or 1
    return set() if len(revealed) > REDRAW * total else revealed


def keys_of(members, drawio_dir):
    """[{content key: cell id}] per step, in the order the renderer draws them.

    The key is what identifies a shape across steps: draw.io reissues cell ids
    between saves, so the id cannot, and the hand-drawn jitter is re-randomised
    on every render, so the drawn form cannot either.
    """
    out, cum, prev = [], (0.0, 0.0), None
    for name in members:
        cur = cells(os.path.join(drawio_dir, name + '.drawio'))
        if prev is not None:
            dx, dy = _offset(prev, cur)
            cum = (cum[0] + dx, cum[1] + dy)
        prev = cur
        out.append({(_kind(c), _at(c, *cum)): cid for cid, c in cur.items()})
    return out


def merged(rendered, members, drawio_dir, size, title):
    """One figure for the series, with a step range on every shape."""
    ET.register_namespace('', NS)
    renders = [ET.fromstring(tidy(rendered[m]['svg'])) for m in members]
    origins = [(rendered[m]['cx'] - PAD, rendered[m]['cy'] - PAD) for m in members]
    # the frame has to hold every step, not only the last one — an earlier step
    # can reach further up or left, and it would be cropped
    left = min(o[0] for o in origins)
    top = min(o[1] for o in origins)
    right = max(o[0] + rendered[m]['cw'] + 2 * PAD for o, m in zip(origins, members))
    bottom = max(o[1] + rendered[m]['ch'] + 2 * PAD for o, m in zip(origins, members))
    frame = (left, top, max(right - left, size[0]), max(bottom - top, size[1]))
    root, shapes, steps = merger.merge(renders, keys_of(members, drawio_dir),
                                       origins, frame, title)
    style = ET.Element(f'{{{NS}}}style', {'type': 'text/css'})
    style.text = font_css()
    root.insert(0, style)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            + ET.tostring(root, encoding='unicode') + '\n'), shapes, steps


def build(svg, size, origin, revealed, title):
    """One finished figure: framed with its group, tagged for the reveal."""
    ET.register_namespace('', NS)
    root = ET.fromstring(svg)
    w, h = size[0] + 2 * PAD, size[1] + 2 * PAD
    root.set('width', f'{w:.0f}px')
    root.set('height', f'{h:.0f}px')
    root.set('viewBox', f'{origin[0] - PAD:.1f} {origin[1] - PAD:.1f} {w:.0f} {h:.0f}')
    root.set('role', 'img')
    root.set('aria-label', title)
    for e in root.iter():
        cid = e.get('data-cell-id')
        if cid and cid in revealed:
            e.set('data-step', '2')          # "arrived on the click that made this slide"
    style = ET.Element(f'{{{NS}}}style', {'type': 'text/css'})
    style.text = font_css()
    root.insert(0, style)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            + ET.tostring(root, encoding='unicode') + '\n')


BITMAP_TITLES = {
    'dnaPCA': 'Genes mirror geography within Europe',
    'matrixFactorizationIdea': 'The idea of matrix factorization',
}


def wrap_bitmap(png, out_dir, max_width=1100):
    """A PNG with no diagram in it, wrapped as an SVG figure.

    Two of the slides are screenshots rather than drawings, and a SlAIdy figure
    is SVG — so the bitmap travels inside one, as a data URI. That is the one
    data: URL a figure is allowed to carry, and it keeps every figure in the
    deck the same kind of thing.
    """
    from PIL import Image
    name = os.path.basename(png)[:-4]
    img = Image.open(png).convert('RGB')
    if img.width > max_width:
        img = img.resize((max_width, round(img.height * max_width / img.width)), Image.LANCZOS)
    packed = img.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
    buf = io.BytesIO()
    packed.save(buf, format='PNG', optimize=True)
    data = base64.b64encode(buf.getvalue()).decode()
    title = BITMAP_TITLES.get(name, name)
    svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{img.width}px" height="{img.height}px" '
           f'viewBox="0 0 {img.width} {img.height}" role="img" aria-label="{title}">'
           f'<image x="0" y="0" width="{img.width}" height="{img.height}" '
           f'xlink:href="data:image/png;base64,{data}"/></svg>\n')
    fid = f'fig-{name}'
    open(os.path.join(out_dir, fid + '.svg'), 'w').write(svg)
    return fid, dict(series=name, step=1, of=1, source=name + '.png', revealed=[],
                     frame=[img.width, img.height], title=title, bytes=len(svg), bitmap=True)


TITLES = {
    'universe': 'Who are you — the space of possible people',
    'matrixRS': 'Rank of a matrix, built up row by row',
    'svd': 'Singular value decomposition of the rating matrix',
    'svdgeo': 'SVD read geometrically',
    'svdapprox': 'Rank-k approximation by SVD',
    'svdDimRed': 'Dimensionality reduction by SVD',
    'svdDimRedGeo': 'Dimensionality reduction, geometrically',
    'svdDimRedGeoSum': 'Dimensionality reduction, all of it at once',
    'mfALS': 'Alternating least squares',
    'mfIMP': 'ALS for implicit feedback',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--drawio', default=os.path.join(ROOT, 'drawio'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'figures'))
    ap.add_argument('--sources', default=os.path.join(ROOT, 'sources'))
    ap.add_argument('--order', default=default_tex(ROOT),
                    help='the .tex whose figure order decides the steps')
    ap.add_argument('--only', help='render one series only')
    ap.add_argument('--steps', choices=('one', 'files'), default='one',
                    help="'one': a series is one figure whose shapes carry their step "
                         "(needs SlAIdy with steps). 'files': a file per step.")
    ap.add_argument('--keep-scratch', action='store_true')
    a = ap.parse_args()

    names = sorted(os.path.basename(p)[:-7] for p in glob.glob(os.path.join(a.drawio, '*.drawio')))
    order = tex_order(a.order) if a.order and os.path.exists(a.order) else None
    series = group_series(names, order)
    if a.only:
        series = {k: v for k, v in series.items() if k == a.only}
        if not series:
            sys.exit(f'No series called {a.only}. Have: {", ".join(group_series(names, order))}')
    wanted = [n for v in series.values() for n in v]
    drawings = {n: open(os.path.join(a.drawio, n + '.drawio')).read() for n in wanted}

    scratch = tempfile.mkdtemp(prefix='drawio-render-')
    try:
        print(f'Rendering {len(drawings)} drawings through draw.io in headless Chrome…')
        rendered = render_all(drawings, scratch)
    finally:
        if not a.keep_scratch:
            shutil.rmtree(scratch, ignore_errors=True)
        else:
            print(f'  scratch kept at {scratch}')

    os.makedirs(a.out, exist_ok=True)
    index, total = {}, 0
    for name, members in series.items():
        members = [m for m in members if m in rendered]
        if not members:
            continue
        reveals = dict((os.path.basename(p)[:-7], ids) for p, ids in
                       series_steps([os.path.join(a.drawio, m + '.drawio') for m in members]))
        reveals = {m: settled(ids, os.path.join(a.drawio, m + '.drawio'))
                   for m, ids in reveals.items()}
        title = TITLES.get(name, name)
        shown = []
        groups = frames(rendered, members)
        for gi, (size, group) in enumerate(groups, 1):
            fid = f'fig-{name}' if len(groups) == 1 else f'fig-{name}-{gi}'
            if a.steps == 'one' and len(group) > 1:
                svg, shapes, steps = merged(rendered, group, a.drawio, size, title)
                open(os.path.join(a.out, fid + '.svg'), 'w').write(svg)
                total += len(svg)
                index[fid] = dict(series=name, steps=steps, shapes=shapes,
                                  sources=[m + '.png' for m in group],
                                  frame=[round(size[0]), round(size[1])],
                                  title=title, bytes=len(svg))
                shown.append(f'{size[0]:.0f}x{size[1]:.0f} in {steps} steps, {shapes} shapes')
                continue
            for m in group:
                i = members.index(m) + 1
                one = fid if len(members) == 1 else f'fig-{name}-{i:02d}'
                svg = build(tidy(rendered[m]['svg']), size,
                            (rendered[m]['cx'], rendered[m]['cy']), reveals[m],
                            f'{title} ({i} of {len(members)})' if len(members) > 1 else title)
                open(os.path.join(a.out, one + '.svg'), 'w').write(svg)
                total += len(svg)
                index[one] = dict(series=name, step=i, of=len(members), source=m + '.png',
                                  steps=1, sources=[m + '.png'],
                                  frame=[round(size[0]), round(size[1])],
                                  title=title, bytes=len(svg))
            shown.append(f'{size[0]:.0f}x{size[1]:.0f}\u00d7{len(group)}')
        print(f'  {name:16s} {len(members):2d} step(s)  ' + '  '.join(shown))
    if not a.only:
        drawn = {os.path.basename(p)[:-7] for p in glob.glob(os.path.join(a.drawio, '*.drawio'))}
        for png in sorted(glob.glob(os.path.join(a.sources, '*.png'))):
            if os.path.basename(png)[:-4] in drawn:
                continue
            fid, meta = wrap_bitmap(png, a.out)
            index[fid], total = meta, total + meta['bytes']
            print(f'  {meta["series"]:16s} screenshot, wrapped as {fid}')
    with open(os.path.join(a.out, 'index.json'), 'w') as f:
        json.dump(index, f, indent=1, sort_keys=True)
    print(f'{len(index)} figures, {total/1024:.0f} kB in {a.out}/')


if __name__ == '__main__':
    main()
