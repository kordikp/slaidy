#!/usr/bin/env python3
"""A theme's picture for the gallery: its sample deck's cover and first content slide, side by side.

    python3 scripts/theme_preview.py recombee        # → themes/recombee/preview.png
    python3 scripts/theme_preview.py                 # every theme

Builds the theme (scripts/themes.py), opens its sample deck in Chrome as the projector
shows it (scripts/shots.mjs) and puts slides 1 and 2 next to each other, 960×270.
Needs Node 22+, Chrome and Pillow (pip install pillow).
"""
import os, subprocess, sys, tempfile
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import themes  # noqa: E402

names = sys.argv[1:] or themes.themes()
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "themes.py"), "--out", tmp], check=True,
                   stdout=subprocess.DEVNULL)
    for name in names:
        page, shots = os.path.join(tmp, name + ".html"), os.path.join(tmp, name + "-shots")
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "onefile.py"),
                        os.path.join(tmp, name, "deck.json"), page], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["node", os.path.join(ROOT, "scripts", "shots.mjs"), page, "1", "2", shots,
                        "--wait", "2500", "--size", "1280x720"], check=True, stdout=subprocess.DEVNULL)
        out = Image.new("RGB", (960, 270), "white")
        for i in (1, 2):
            out.paste(Image.open(os.path.join(shots, f"s0{i}.png")).convert("RGB").resize((480, 270), Image.LANCZOS),
                      ((i - 1) * 480, 0))
        dst = os.path.join(ROOT, "themes", name, "preview.png")
        out.save(dst, optimize=True)
        print(f"themes/{name}/preview.png")
