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
# The DECK is deliberately not copied in. `cp` stamps the copy with the current
# time, so every restart made the served deck look newer than the edits held in
# the browser — and the edits lost. The server owns the real file instead: it
# streams it at /deck.json and writes it back at /api/deck.
cp slide-studio.html "$WORK/index.html"

PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"

# Read the AI credentials from .env if they are not already exported, so the AI
# panels work without an export every time. Only these names are read, and no
# value ever reaches the command line — where `ps` would show it — just this
# shell's environment.
#
# CESNET e-INFRA CZ is preferred when it is configured: it is what the demo and
# the development of this tool run on, by their grace. Otherwise OpenAI.
ENVFILE="${STUDIO_ENV_FILE:-${OPENAI_ENV_FILE:-.env}}"
readenv() {                       # readenv VAR — echo the value, never log it
  [ -r "$ENVFILE" ] || return 1
  line=$(grep -m1 "^$1=" "$ENVFILE" 2>/dev/null) || return 1
  val=${line#*=}; val=${val%\"}; val=${val#\"}; val=${val%\'}; val=${val#\'}
  [ -n "$val" ] && printf '%s' "$val"
}
if [ -z "${OPENAI_KEY:-}${OPENAI_API_KEY:-}" ]; then
  CK=$(readenv CESNET_API_KEY || true)
  if [ -n "${CESNET_API_KEY:-}" ] || [ -n "$CK" ]; then
    export OPENAI_KEY="${CESNET_API_KEY:-$CK}"
    export OPENAI_BASE_URL="${CESNET_BASE_URL:-$(readenv CESNET_BASE_URL || echo https://llm.ai.e-infra.cz/v1)}"
    export STUDIO_MODEL="${STUDIO_MODEL:-${CESNET_MODEL:-$(readenv CESNET_MODEL || echo qwen3.5)}}"
    AI_VIA="CESNET e-INFRA CZ"
  else
    for v in OPENAI_KEY OPENAI_API_KEY STUDIO_MODEL OPENAI_BASE_URL; do
      val=$(readenv "$v" || true); [ -n "$val" ] && export "$v=$val"
    done
    AI_VIA="OpenAI"
  fi
fi

echo "SlAIdy  ·  $(basename "$DECK")${AI_VIA:+  ·  AI via $AI_VIA}"
echo "  http://localhost:$PORT"
echo "  Ctrl-C to stop. Your edits are stored by the browser under that address,"
echo "  so always start it the same way — or keep a copy with Export."
echo

( sleep 1; (xdg-open "http://localhost:$PORT" || open "http://localhost:$PORT") >/dev/null 2>&1 || true ) &
exec "$PY" scripts/serve.py "$WORK" "$PORT" "$DECK"
