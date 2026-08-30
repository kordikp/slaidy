#!/usr/bin/env bash
# Open Slide Studio with a deck already loaded.
#
#   ./studio.sh                          # the example deck
#   ./studio.sh decks/my-talk.json
#
# Serving over http (rather than opening the file directly) is what lets the
# deck load by itself and gives the browser a proper storage origin, so your
# work and its version history survive a reload.

set -euo pipefail
cd "$(dirname "$0")"

DECK="${1:-decks/example.json}"
PORT="${PORT:-8080}"

[ -f "$DECK" ] || { echo "No such deck: $DECK"; echo "Available:"; ls -1 decks/*.json 2>/dev/null || echo "  (none — run scripts/build_bundle.py)"; exit 1; }
[ -f slide-studio.html ] || { echo "slide-studio.html is missing"; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp slide-studio.html "$WORK/index.html"
cp "$DECK" "$WORK/deck.json"

PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"

# Pick up OPENAI_KEY from .env if it is not already in the environment, so the AI
# panels work without an export every time. Only these three names are read, and
# the value never reaches the command line — just this shell's environment.
ENVFILE="${OPENAI_ENV_FILE:-.env}"
if [ -z "${OPENAI_KEY:-}${OPENAI_API_KEY:-}" ] && [ -r "$ENVFILE" ]; then
  for v in OPENAI_KEY OPENAI_API_KEY STUDIO_MODEL; do
    line=$(grep -m1 "^$v=" "$ENVFILE" 2>/dev/null) || continue
    val=${line#*=}; val=${val%\"}; val=${val#\"}; val=${val%\'}; val=${val#\'}
    [ -n "$val" ] && export "$v=$val"
  done
fi

echo "Slide Studio  ·  $(basename "$DECK")"
echo "  http://localhost:$PORT"
echo "  Ctrl-C to stop. Your edits are stored by the browser under that address,"
echo "  so always start it the same way — or keep a copy with Export."
echo

( sleep 1; (xdg-open "http://localhost:$PORT" || open "http://localhost:$PORT") >/dev/null 2>&1 || true ) &
exec "$PY" scripts/serve.py "$WORK" "$PORT"
