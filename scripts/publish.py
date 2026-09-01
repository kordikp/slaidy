#!/usr/bin/env python3
"""Put a deck on the web.

    python3 scripts/publish.py decks/isd2026.json isd2026keynote

Copies the deck into site/<name>/deck.json, which the Pages workflow turns into
https://kordikp.github.io/slaidy/<name>/ — the whole editor with that deck in it,
so the link presents, reads and exports without anything to install.

It also writes site/<name>/notes/index.html: every slide with its figure and
what you meant to say about it, on paper. A presenter wants that on a lectern,
not in a browser, so it is a plain document that prints — no application, no
JavaScript, one slide per block and a page break where the section changes.

Nothing is uploaded here: this writes a file in the repository. The deck reaches
the web when you commit and push it, which is deliberate — publishing a talk
should be a thing you decide, not a side effect of saving.
"""
import html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


NOTES_CSS = """
  :root{--ink:#14161B;--gray:#585E6B;--faint:#9AA1AE;--line:#E4E6EA;--acc:#4B3FCF}
  *{box-sizing:border-box}
  body{margin:0;background:#fff;color:var(--ink);
    font:15px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
  .wrap{max-width:860px;margin:0 auto;padding:40px 28px 80px}
  h1{font-size:26px;letter-spacing:-.02em;margin:0 0 4px}
  .sub{color:var(--gray);margin:0 0 28px;font-size:14px}
  .sub a{color:var(--acc)}
  .act{font:600 11px/1 system-ui;letter-spacing:.14em;text-transform:uppercase;color:var(--gray);
    margin:34px 0 10px;padding-top:14px;border-top:1px solid var(--line);break-before:page}
  .act:first-of-type{break-before:auto}
  .s{display:grid;grid-template-columns:52px 1fr;gap:0 16px;padding:14px 0;
    border-top:1px solid var(--line);break-inside:avoid}
  .n{font:600 12px/1.7 ui-monospace,SFMono-Regular,monospace;color:var(--faint)}
  .t{font-size:17px;font-weight:650;letter-spacing:-.01em;margin:0 0 6px}
  .fig{margin:8px 0 10px;max-width:340px}
  .fig svg{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:6px}
  .note{margin:0;color:#3A404C}
  .note.none{color:var(--faint);font-style:italic}
  .key{margin:8px 0 0;padding-left:12px;border-left:3px solid var(--acc);color:var(--gray);
    font-size:14px}
  .skip{opacity:.5}
  .skip .t::after{content:" · hidden";font-weight:400;color:var(--faint);font-size:12px}
  @media print{
    .wrap{max-width:none;padding:0}
    body{font-size:11pt}
    .s{padding:10px 0}
    .sub a{color:inherit;text-decoration:none}
  }
"""


def inline(t):
    """The little markdown a spoken note actually uses."""
    t = html.escape(t or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(\S(?:.*?\S)?)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', t)
    return t


def notes_page(deck, name):
    """Every slide, its figure and what you meant to say — on paper."""
    figs = deck.get("figs") or {}
    out, act = [], None
    for s in deck.get("slides") or []:
        g = (s.get("group") or "").strip()
        if g != act:
            act = g
            out.append('<div class="act">%s</div>' % html.escape(act or "—"))
        ids = re.findall(r"!\[\[([a-zA-Z0-9._-]+)", s.get("body") or "")
        pic = ""
        for fid in ids[:1]:
            if fid in figs:
                pic = '<div class="fig">%s</div>' % re.sub(r"<\?xml[^>]*\?>", "", figs[fid])
        note = (s.get("notes") or "").strip()
        key = ""
        for line in (s.get("body") or "").split("\n"):
            if line.startswith(">"):
                key = line.lstrip("> ").strip()
                break
        out.append(
            '<div class="s%s"><div class="n">%03d</div><div>'
            '<p class="t">%s</p>%s%s%s</div></div>' % (
                " skip" if s.get("skip") else "", s.get("n") or 0,
                html.escape(s.get("title") or ""), pic,
                ('<p class="note">%s</p>' % inline(note)) if note
                else '<p class="note none">no note</p>',
                ('<p class="key">%s</p>' % inline(key)) if key else ""))
    title = deck.get("title") or name
    n = len(deck.get("slides") or [])
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s · notes</title><style>%s</style></head><body><div class="wrap">
<h1>%s</h1>
<p class="sub">%d slides · speaker notes · <a href="../">the deck</a> ·
 <a href="../#present">present it</a></p>
%s
</div></body></html>""" % (html.escape(title), NOTES_CSS, html.escape(title), n, "\n".join(out)))


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

    # a mistyped flag used to become a deck called "name", published at /name/
    for a in sys.argv[2:]:
        if a.startswith("-"):
            sys.exit("Unknown option %s — usage: publish.py <deck.json> <name>" % a)
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

    nd = os.path.join(out, "notes")
    os.makedirs(nd, exist_ok=True)
    open(os.path.join(nd, "index.html"), "w", encoding="utf-8").write(notes_page(deck, name))

    figs = len(deck.get("figs") or {})
    mb = os.path.getsize(was) / 1e6
    print("site/%s/deck.json" % name)
    print("  %s — %d slides, %d figure%s, %.2f MB%s"
          % (deck.get("title") or name, len(deck["slides"]), figs, "" if figs == 1 else "s", mb,
             "" if before is None else "  (was %d slides)" % before))
    print("  https://kordikp.github.io/slaidy/%s/" % name)
    print("  https://kordikp.github.io/slaidy/%s/notes/   — the notes, for printing" % name)
    print()
    print("  It is on the web when it is pushed:")
    print("    git add site/%s && git commit -m 'Publish %s' && git push"
          % (name, deck.get("title") or name))


if __name__ == "__main__":
    main()
