#!/usr/bin/env python3
r"""Generate the deck the browser tests run against.

The suite needs a deck with shape, not content: several sections, subsections
inside them, every layout, slides with and without figures, and one figure built
the way a real one is — nested groups carrying their own ids, so grouping,
ungrouping and duplication have something honest to work on.

    python3 tests/make-fixture.py            # writes tests/fixture.json
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

SECTIONS = [
    ("I · First Section",  ["Room 1 — Alpha", "Room 2 — Beta"]),
    ("II · Second Section", ["Part one", "Part two"]),
    ("III · Third Section", ["Only part"]),
    ("Epilogue", []),
]
LAYOUTS = ["figure", "split-r", "split-l", "background", "text"]
TAGS = ["S", "D", "E", "B"]

BODY = [
    "A paragraph that says something, so the slide has words on it.\n\n"
    "- First point\n- Second point\n- Third point\n\n"
    "> The line that has to land.",
    "One short paragraph.\n\n> A key line.",
    "| Column | Column |\n|---|---|\n| cell | cell |\n| cell | cell |",
    "Just prose, nothing structured, long enough to fill a little of the frame "
    "and to give the fitting rules something to think about.",
]

def marks():
    """A figure shaped like a real one: two logo-ish groups, ids and a <use>."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'viewBox="0 0 800 150" font-family="system-ui,sans-serif">'
        '<rect width="800" height="150" fill="none"/>'
        '<g transform="translate(40,40) scale(0.5)">'
        '<defs><path id="a" d="M0 0 h120 v120 h-120 Z"/></defs>'
        '<use xlink:href="#a" fill="#0065BD"/>'
        '<circle cx="60" cy="60" r="28" fill="#FFFFFF"/>'
        '</g>'
        '<text x="140" y="62" font-size="15" font-weight="700" fill="#1E1B4B">First Mark</text>'
        '<text x="140" y="85" font-size="14" fill="#6B7280">a line under it</text>'
        '<line x1="452" y1="38" x2="452" y2="112" stroke="#E5E7EB" stroke-width="1.5"/>'
        '<g transform="translate(488,42) scale(0.1452)">'
        '<defs><path id="b" d="M0 0 h300 v200 h-300 Z"/></defs>'
        '<use xlink:href="#b" fill="#0FA5A5"/>'
        '<polygon points="0,200 150,40 300,200" fill="#FFC021"/>'
        '</g>'
        '<text x="488" y="97" font-size="14" fill="#6B7280">and a line under that</text>'
        '</svg>')

def panel(i):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" '
        'font-family="system-ui,sans-serif">'
        '<style>@keyframes p{0%,100%{opacity:.4}50%{opacity:1}}.b{animation:p 6s ease-in-out infinite}</style>'
        '<rect width="800" height="450" rx="14" fill="#FAFAF7" stroke="#E5E7EB"/>'
        f'<text x="400" y="34" text-anchor="middle" font-size="19" font-weight="700" fill="#1E1B4B">Panel {i}</text>'
        '<rect class="b" x="260" y="150" width="280" height="150" rx="10" fill="#E0F2FE" stroke="#0EA5E9" stroke-width="2"/>'
        '<text x="400" y="230" text-anchor="middle" font-size="14" fill="#075985">a shape to select</text>'
        '<text x="400" y="428" text-anchor="middle" font-size="12.5" fill="#6B7280">A takeaway line.</text>'
        '</svg>')

def main():
    slides, n = [], 0
    for si, (group, subs) in enumerate(SECTIONS):
        for sub in (subs or [None]):
            for j in range(6 if subs else 4):
                n += 1
                fig = None if j == 3 else ("fig-marks" if n == 1 else f"fig-panel-{(n % 5) + 1}")
                layout = "text" if fig is None else LAYOUTS[j % 4]
                slides.append({
                    "n": n, "tag": TAGS[j % 4], "group": group, "sub": sub,
                    "title": f"Slide {n} in {sub or group}",
                    "fig": fig, "layout": layout,
                    "body": BODY[j % len(BODY)],
                    "notes": f"What to say on slide {n}." if j % 2 == 0 else "",
                    "summary": "" if j else f"What slide {n} is for.",
                    "pick": False,
                })
    # one slide places a figure inside the body, the way ![[fig-id]] does
    slides[1]["body"] = ("A line before the mark.\n\n![[fig-marks]]\n\n"
                        "![[fig-panel-2|60%]]\n\nAnd a line after it.")
    slides[1]["fig"] = None
    slides[1]["layout"] = "text"

    # one slide with nothing on it at all, for the empty-slide path
    slides.append({"n": len(slides) + 1, "tag": "S", "group": SECTIONS[-1][0], "sub": None,
                   "title": "An empty slide", "fig": None, "layout": "text",
                   "body": "", "notes": "", "summary": "", "pick": False})
    # and one whose notes carry a link
    slides[2]["notes"] = "Background: https://arxiv.org/abs/2409.10309 and [the paper](https://example.org/p)."

    figs = {"fig-marks": marks()}
    figs.update({f"fig-panel-{i}": panel(i) for i in range(1, 6)})
    out = {"id": "fixture", "title": "Fixture Deck",
           "meta": {"author": "Test", "affiliation": "Nowhere", "event": "Suite",
                    "venue": "localhost", "date": "today"},
           "style": {"accent": "#7C3AED", "ink": "#1E1B4B", "paper": "#FFFFFF",
                     "titleSize": 38, "bodySize": 19, "header": "position"},
           "slides": slides, "figs": figs}
    path = os.path.join(HERE, "fixture.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    subs = len({s["sub"] for s in slides if s["sub"]})
    print(f"{path}\n  {len(slides)} slides · {len(SECTIONS)} sections · {subs} subsections · {len(figs)} figures")

if __name__ == "__main__":
    main()
