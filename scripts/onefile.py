#!/usr/bin/env python3
"""The deck and SlAIdy in one HTML file, openable from a disk with no server.

    python3 scripts/onefile.py decks/my-talk.json build/my-talk.html
    python3 scripts/onefile.py decks/my-talk.json build/artifact.html --artifact

The deck is written into the page as <script id="slaidy-deck">, which SlAIdy
reads where it would otherwise fetch the deck.json beside it. So the file works
over file://, from any static host and as an e-mail attachment, and nothing about
the application is patched to get there: a newer slaidy.html only needs the file
built again. Edits made in it are kept by the browser as usual, and the page's
own copy wins again once it is newer than they are.

`?s=N` in the address opens at slide N and `&step=K` at its K-th click;
`#present` starts the projector.

`--artifact` leaves out the <!doctype>/<html>/<head>/<body> wrapper, because a
host that renders the page supplies its own. `--title=…` sets the tab title.
"""
import email.utils
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(deck_path, out_path, title=None, artifact=False):
    app = open(os.path.join(ROOT, 'slaidy.html'), encoding='utf-8').read()
    deck = json.load(open(deck_path, encoding='utf-8'))
    if not isinstance(deck.get('slides'), list):
        sys.exit(f'{deck_path} is not a SlAIdy deck: it has no slides')
    title = title or deck.get('title') or 'SlAIdy'
    modified = email.utils.formatdate(os.path.getmtime(deck_path), usegmt=True)
    # JSON inside <script>: nothing in it may close the element or open a comment
    payload = json.dumps(deck, ensure_ascii=False, separators=(',', ':')) \
                  .replace('<', '\\u003c')
    tag = (f'<script id="slaidy-deck" type="application/json" '
           f'data-modified="{modified}">{payload}</script>')
    if app.count('<title>SlAIdy</title>') != 1:
        sys.exit('slaidy.html has no <title>SlAIdy</title> to put the deck after')
    app = app.replace('<title>SlAIdy</title>',
                      f'<title>{html.escape(title)}</title>\n{tag}', 1)
    if artifact:
        app = re.sub(r'^<!doctype html>', '', app, flags=re.I)
        app = re.sub(r'<html[^>]*>', '', app, count=1)
        app = app.replace('<head>', '', 1).replace('</head>', '', 1)
        app = re.sub(r'<body[^>]*>', '', app, count=1)
        app = re.sub(r'</body>\s*</html>\s*$', '', app)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
    open(out_path, 'w', encoding='utf-8').write(app)
    print(f'{out_path}  {os.path.getsize(out_path)/1024:.0f} kB  '
          f'({len(deck["slides"])} slides, {len(deck.get("figs") or {})} figures)')


if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(args) != 2:
        sys.exit(__doc__.strip())
    build(args[0], args[1],
          next((x.split('=', 1)[1] for x in sys.argv if x.startswith('--title=')), None),
          '--artifact' in sys.argv)
