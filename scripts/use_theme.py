#!/usr/bin/env python3
"""Put a theme from the library on a deck, the way Deck settings → Style → Theme does.

    python3 scripts/use_theme.py decks/talk.json paper           # the theme's CSS into the deck, its style as the deck's
    python3 scripts/use_theme.py decks/talk.json paper --keep    # keep the deck's own colours and sizes
    python3 scripts/use_theme.py decks/talk.json none            # take the theme off again

The deck carries the theme's CSS with its fonts and pictures inside (S.themeCss), so it
still opens offline as one file.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import themes  # noqa: E402


def main(path, name, keep=False):
    deck = json.load(open(path, encoding="utf-8"))
    style = deck.setdefault("style", {})
    if name == "none":
        style.pop("theme", None)
        deck.pop("themeCss", None)
    else:
        if name not in themes.themes():
            sys.exit(f"no theme {name!r}; the library has {', '.join(themes.themes())}")
        css, meta, bad = themes.build(name)
        if bad:
            sys.exit(f"themes/{name}: " + "; ".join(bad))
        if not keep:
            style.update(meta.get("style") or {})
        style["theme"], deck["themeCss"] = name, css
    json.dump(deck, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{path}: {'no theme' if name == 'none' else name} · {os.path.getsize(path) // 1024} kB")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) != 2:
        sys.exit(__doc__)
    main(a[0], a[1], "--keep" in sys.argv)
