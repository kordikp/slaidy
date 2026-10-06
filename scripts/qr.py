#!/usr/bin/env python3
"""A QR code as a SlAIdy figure: SVG, not a picture.

    python3 scripts/qr.py https://example.org/homework "Homework" > figures/fig-qr-homework.svg
    python3 scripts/qr.py https://example.org --lang cs --ink "#1E1B4B" > qr.svg

A link on a slide that the room is meant to open — homework, a survey, the slides
themselves — is better as a code a phone can read than as an address to type. The
figure is 460 × 520: the code, a label and the shortened address under it. It is
one <path> per row of modules, so it stays small, diffs, and recolours like any
other drawing. Needs `segno` (pure Python): python3 -m pip install segno.

As a module: from qr import qr_figure.
"""
import html, re, sys

INK = "#1E1B4B"
GRAY = "#6B7280"


def qr_figure(url, label="", sub=None, ink=INK, lang="en"):
    """The figure's SVG. `sub` replaces the address shown under the code."""
    try:
        import segno
    except ImportError:
        sys.exit("qr.py needs segno: python3 -m pip install segno")
    qr = segno.make(url, error="m" if len(url) < 120 else "l")
    n = qr.symbol_size(scale=1, border=0)[0]          # modules per side
    d = []
    for y, row in enumerate(qr.matrix):
        x = 0
        while x < n:
            if row[x]:
                run = 1
                while x + run < n and row[x + run]:
                    run += 1
                d.append("M%d %dh%dv1h-%dz" % (x, y, run, run))
                x += run
            else:
                x += 1
    scale = 400 / n
    shown = sub if sub is not None else re.sub(r"^https?://", "", url)
    if len(shown) > 44:
        shown = shown[:41] + "…"
    what = {"cs": "QR kód"}.get(lang, "QR code")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 520" '
        'font-family="system-ui,sans-serif" role="img" lang="%s">\n'
        "  <title>%s</title>\n"
        "  <desc>%s: %s</desc>\n"
        '  <rect x="20" y="10" width="420" height="420" rx="14" fill="#FFFFFF" stroke="#E5E7EB"/>\n'
        '  <g transform="translate(30 20) scale(%.5f)"><path d="%s" fill="%s"/></g>\n'
        '  <text x="230" y="470" text-anchor="middle" font-size="22" font-weight="700" fill="%s">%s</text>\n'
        '  <text x="230" y="502" text-anchor="middle" font-size="15" fill="%s">%s</text>\n'
        "</svg>"
    ) % (html.escape(lang), html.escape(label or shown), what, html.escape(url), scale, "".join(d), ink,
         ink, html.escape(label or ""), GRAY, html.escape(shown))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = lambda k, d: next((sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == k), d)
    if not args:
        sys.exit(__doc__.strip())
    print(qr_figure(args[0], args[1] if len(args) > 1 else "", ink=opt("--ink", INK), lang=opt("--lang", "en")))
