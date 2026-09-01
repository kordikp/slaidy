#!/usr/bin/env python3
"""Put a deck on the web.

    python3 scripts/publish.py decks/isd2026.json isd2026keynote

Copies the deck into site/<name>/deck.json, which the Pages workflow turns into
https://kordikp.github.io/slaidy/<name>/ — the whole editor with that deck in it,
so the link presents, reads and exports without anything to install.

Nothing is uploaded here: this writes a file in the repository. The deck reaches
the web when you commit and push it, which is deliberate — publishing a talk
should be a thing you decide, not a side effect of saving.
"""
import json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip())
    src = os.path.abspath(sys.argv[1])
    if not os.path.isfile(src):
        sys.exit("No such deck: " + src)
    try:
        deck = json.load(open(src, encoding="utf-8"))
    except Exception as e:
        sys.exit("That is not a deck: %s" % e)
    if not isinstance(deck.get("slides"), list) or not deck["slides"]:
        sys.exit("That deck has no slides in it.")

    name = sys.argv[2] if len(sys.argv) > 2 else (deck.get("id") or "deck")
    name = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    if not name:
        sys.exit("Give it a name for the url: publish.py <deck.json> <name>")

    out = os.path.join(ROOT, "site", name)
    was = os.path.join(out, "deck.json")
    before = None
    if os.path.exists(was):
        try:
            before = len(json.load(open(was, encoding="utf-8"))["slides"])
        except Exception:
            pass
    # A published deck says so, and the page then opens ready to watch rather
    # than asking the reader where they would like to save it.
    deck.setdefault("meta", {})["shared"] = True
    os.makedirs(out, exist_ok=True)
    json.dump(deck, open(was, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    figs = len(deck.get("figs") or {})
    mb = os.path.getsize(was) / 1e6
    print("site/%s/deck.json" % name)
    print("  %s — %d slides, %d figure%s, %.2f MB%s"
          % (deck.get("title") or name, len(deck["slides"]), figs, "" if figs == 1 else "s", mb,
             "" if before is None else "  (was %d slides)" % before))
    print("  https://kordikp.github.io/slaidy/%s/" % name)
    print()
    print("  It is on the web when it is pushed:")
    print("    git add site/%s && git commit -m 'Publish %s' && git push"
          % (name, deck.get("title") or name))


if __name__ == "__main__":
    main()
