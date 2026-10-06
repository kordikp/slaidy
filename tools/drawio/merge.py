"""Merge a series of renders into one figure whose shapes carry their steps.

A series is one drawing saved several times. Stored a step per file, the shapes
that do not change are written out again on every step, which is where a deck of
this shape keeps most of its bytes: `universe` costs 396 kB as fourteen files and
40 kB as one.

So the steps are merged. Every shape is identified by its content (draw.io
reissues cell ids between saves, and the hand-drawn jitter is re-randomised on
every render, so neither the id nor the drawn form can name it), and the merged
figure records the range of steps each shape stands for:

    <g data-step="5">…</g>                  arrives on click 5 and stays
    <g data-step="1" data-until="4">…</g>   there from the start, gone at 4

The second is what lets one file hold a series in which something *changes*:
the old version ends where the new one begins. Both are in the file, so a series
that redraws itself saves little — which is the truthful outcome.

The drawn form of a shape is taken from the last step it appears in, and shifted
into the frame of the merged figure, because each step was cropped to its own
drawing.
"""
import collections
import re
from xml.etree import ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
CELL = '{%s}g' % NS


def cell_order(svg):
    """[cell id] in the order the renderer drew them — which is the z-order."""
    return re.findall(r'data-cell-id="([^"]+)"', svg)


def merge_orders(sequences):
    """One order that every step's order is a subsequence of.

    The steps are the same drawing edited, so their orders agree wherever they
    overlap; a key not seen before goes in just after the last key from its own
    step that has already been placed.
    """
    master, at_index = [], {}
    for seq in sequences:
        after = -1
        for key in seq:
            if key in at_index:
                after = at_index[key]
                continue
            after += 1
            master.insert(after, key)
            at_index = {k: i for i, k in enumerate(master)}
    return master


def timeline(steps):
    """{key: (first step, last step)} over [{key: cell id}] per step, 1-based."""
    seen = collections.defaultdict(list)
    for i, keys in enumerate(steps, 1):
        for key in keys:
            seen[key].append(i)
    return {key: (at[0], at[-1]) for key, at in seen.items()}


# draw.io hangs the whole drawing under two cells of its own — the root and the
# default parent. They are containers, not shapes, so they do not count as the
# thing a nested cell is nested in.
ROOT_CELLS = ('0', '1')


def _index(svg_root):
    """{cell id: element}, and the ids that travel inside another cell.

    A grouped shape's cells are nested inside the group's own `<g>`, so pulling
    one out on its own would draw it twice. It comes with its parent instead,
    and takes the parent's steps.
    """
    found, inside = {}, set()

    def walk(el, under):
        cid = el.get('data-cell-id')
        if cid is not None:
            found[cid] = el
            if under is not None:
                inside.add(cid)
            if cid not in ROOT_CELLS:
                under = cid
        for child in el:
            walk(child, under)

    walk(svg_root, None)
    return found, inside


def merge(renders, keys_per_step, origins, frame, title):
    """One figure for the whole series.

    renders        [parsed SVG root per step]
    keys_per_step  [{key: cell id}] per step, in document order
    origins        [(x, y)] the crop origin each step was rendered at
    frame          (x, y, w, h) the merged figure's own frame
    """
    ET.register_namespace('', NS)
    total = len(renders)
    when = timeline([list(k) for k in keys_per_step])
    order = merge_orders([list(k) for k in keys_per_step])

    root = ET.Element('{%s}svg' % NS, {
        'width': f'{frame[2]:.0f}px', 'height': f'{frame[3]:.0f}px',
        'viewBox': f'{frame[0]:.1f} {frame[1]:.1f} {frame[2]:.0f} {frame[3]:.0f}',
        'role': 'img', 'aria-label': title,
    })
    defs = ET.SubElement(root, '{%s}defs' % NS)
    seen_defs = set()
    for step in renders:                       # patterns are named after their content
        for d in step.iter('{%s}defs' % NS):
            for child in d:
                key = ET.tostring(child, encoding='unicode')
                if key not in seen_defs:
                    seen_defs.add(key)
                    defs.append(child)
    body = ET.SubElement(root, '{%s}g' % NS)

    indexed = [_index(step) for step in renders]
    for key in order:
        first, last = when[key]
        source = last - 1
        cid = keys_per_step[source][key]
        found, inside = indexed[source]
        if cid in inside:
            continue                            # drawn as part of the group it is in
        node = found.get(cid)
        if node is None:
            continue
        # each step was cropped to its own drawing, so a shape pulled from an
        # earlier one has to be moved into the frame the merged figure uses
        shift = (frame[0] - origins[source][0], frame[1] - origins[source][1])
        node.set('data-step', str(first))
        if last < total:
            node.set('data-until', str(last + 1))
        if abs(shift[0]) > 0.05 or abs(shift[1]) > 0.05:
            moved = ET.Element('{%s}g' % NS,
                               {'transform': f'translate({shift[0]:.1f},{shift[1]:.1f})'})
            moved.append(node)
            body.append(moved)
        else:
            body.append(node)
    return root, len(order), total
