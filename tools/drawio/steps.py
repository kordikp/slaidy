"""Which parts of a figure appear at each step of a series.

Each PNG of a series is a successive save of one draw.io drawing. Between saves
the drawing was moved around the canvas, and draw.io reissued cell ids, so
neither absolute geometry nor the id can identify a cell across two steps.

A cell is therefore identified by its content — label, style, size, and its
position relative to the rest of the drawing. Two steps are first aligned (the
offset between them is the most common displacement among cells that match on
label, style and size — most of the drawing does not move, so the mode is the
translation), and a cell counts as revealed at step k when nothing matching it
stood in step k-1.
"""
import collections
from xml.etree import ElementTree as ET


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def cells(path):
    """{cell id: {value, style, box, pts, edge}} for one .drawio file."""
    root = ET.parse(path).getroot()
    model = root if root.tag == 'mxGraphModel' else root.find('.//mxGraphModel')
    out = {}
    for cell in model.iter('mxCell'):
        cid = cell.get('id')
        if cid in (None, '0', '1'):
            continue
        geo = cell.find('mxGeometry')
        box = None
        if geo is not None and (geo.get('x') is not None or geo.get('y') is not None):
            box = (_f(geo.get('x')), _f(geo.get('y')), _f(geo.get('width')), _f(geo.get('height')))
        pts = [(_f(p.get('x')), _f(p.get('y')))
               for p in (geo.iter('mxPoint') if geo is not None else [])]
        out[cid] = dict(value=(cell.get('value') or '').strip(),
                        style=cell.get('style') or '', box=box, pts=pts,
                        edge=bool(cell.get('edge')))
    for obj in model.iter():                      # a label can sit on a wrapper element
        if obj.tag in ('object', 'UserObject') and obj.get('id') in out:
            out[obj.get('id')]['value'] = (obj.get('label') or obj.get('value') or '').strip()
    return out


def _kind(c):
    """What the cell is, independent of where it sits."""
    b = c['box']
    return (c['value'], c['style'], round(b[2], 1) if b else None, round(b[3], 1) if b else None)


def _at(c, dx=0.0, dy=0.0):
    """Where the cell sits, shifted by (dx, dy) and rounded to survive re-saves."""
    b = c['box']
    pos = (round(b[0] - dx), round(b[1] - dy)) if b else None
    return (pos, tuple((round(x - dx), round(y - dy)) for x, y in c['pts']))


def _offset(a, b):
    """How far drawing b was moved relative to a: the modal displacement."""
    by_kind = collections.defaultdict(list)
    for c in a.values():
        if c['box']:
            by_kind[_kind(c)].append(c['box'])
    votes = collections.Counter()
    for c in b.values():
        if not c['box']:
            continue
        for ob in by_kind.get(_kind(c), ()):
            votes[(round(c['box'][0] - ob[0], 1), round(c['box'][1] - ob[1], 1))] += 1
    return votes.most_common(1)[0][0] if votes else (0.0, 0.0)


def _fingerprints(cs, dx=0.0, dy=0.0):
    return collections.Counter((_kind(c), _at(c, dx, dy)) for c in cs.values())


def series_steps(paths):
    """[(path, {ids of cells revealed at this step})], in order.

    The first step reveals nothing — the whole drawing is simply there.
    """
    out, prev = [], None
    for p in paths:
        cur = cells(p)
        if prev is None:
            fresh = set()
        else:
            dx, dy = _offset(prev, cur)
            standing = _fingerprints(prev, -0.0, -0.0)
            fresh, seen = set(), collections.Counter()
            for cid, c in cur.items():
                fp = (_kind(c), _at(c, dx, dy))
                seen[fp] += 1
                if seen[fp] > standing.get(fp, 0):
                    fresh.add(cid)
        prev, out = cur, out + [(p, fresh)]
    return out
