#!/usr/bin/env bash
# Look for text that collides with something in a figure: a label running past the
# canvas edge, two labels on top of each other, a connector crossing the words.
#
#   scripts/check_figures.sh                       # decks/example.json
#   scripts/check_figures.sh decks/other.json
#
# Animated elements are skipped in the label-collision check: two labels that
# alternate share a spot on purpose, and a static measurement cannot tell.
# A line deliberately struck through a label (a rejected item) is reported too —
# read the findings, do not apply them blindly.
set -uo pipefail
cd "$(dirname "$0")/.."
DECK="${1:-decks/example.json}"
CHROME=$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)
[ -n "$CHROME" ] || { echo "No Chrome or Chromium on PATH."; exit 1; }
[ -f "$DECK" ] || { echo "No such deck: $DECK"; exit 1; }

PORT="${PORT:-8945}"
WORK="$(mktemp -d)"
cleanup(){ [ -n "${SRV:-}" ] && kill "$SRV" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT
cp scripts/check-figures.html "$WORK/audit.html"
cp "$DECK" "$WORK/deck.json"
(cd "$WORK" && exec python3 -m http.server "$PORT" >/dev/null 2>&1) & SRV=$!
sleep 1
timeout 280 "$CHROME" --headless --disable-gpu --no-sandbox --virtual-time-budget=200000 \
  --dump-dom "http://localhost:$PORT/audit.html" 2>/dev/null \
  | sed -n '/<pre id="out">/,$p' | sed 's/<[^>]*>//g'
