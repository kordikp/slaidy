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
[ -f slaidy.html ] || { echo "slaidy.html is missing"; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# The DECK is deliberately not copied in. `cp` stamps the copy with the current
# time, so every restart made the served deck look newer than the edits held in
# the browser — and the edits lost. The server owns the real file instead: it
# streams it at /deck.json and writes it back at /api/deck.
cp slaidy.html "$WORK/index.html"

PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"

# Where the AI comes from, in order: what is already exported, then .env, then a
# model already running on this machine. Only these names are read, and no value
# ever reaches the command line — where `ps` would show it — just this shell.
#
# A local model needs no key, because there is nobody to authenticate to. Run it
# that way and nothing you write leaves the machine: the deck, the figures and
# every prompt stay here. See .env.example.
ENVFILE="${STUDIO_ENV_FILE:-${OPENAI_ENV_FILE:-.env}}"
readenv() {                       # readenv VAR — echo the value, never log it
  [ -r "$ENVFILE" ] || return 1
  line=$(grep -m1 "^$1=" "$ENVFILE" 2>/dev/null) || return 1
  val=${line#*=}; val=${val%\"}; val=${val#\"}; val=${val%\'}; val=${val#\'}
  [ -n "$val" ] && printf '%s' "$val"
}

if [ -z "${OPENAI_KEY:-}${OPENAI_API_KEY:-}" ]; then
  for v in OPENAI_KEY OPENAI_API_KEY OPENAI_BASE_URL STUDIO_MODEL; do
    val=$(readenv "$v" || true); [ -n "$val" ] && export "$v=$val" || true
  done
  # CESNET e-INFRA CZ hands out its own names; accept those too
  if [ -z "${OPENAI_KEY:-}${OPENAI_API_KEY:-}" ]; then
    CK=$(readenv CESNET_API_KEY || true)
    if [ -n "$CK" ]; then
      export OPENAI_KEY="$CK"
      export OPENAI_BASE_URL="${OPENAI_BASE_URL:-$(readenv CESNET_BASE_URL || echo https://llm.ai.e-infra.cz/v1)}"
      export STUDIO_MODEL="${STUDIO_MODEL:-$(readenv CESNET_MODEL || echo qwen3.5)}"
    fi
  fi
fi

# Still nothing? Look for a model already running here — these are the default
# ports of Ollama, LM Studio, and vLLM or llama.cpp's OpenAI-compatible server.
if [ -z "${OPENAI_KEY:-}${OPENAI_API_KEY:-}${OPENAI_BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  for hp in localhost:11434 localhost:1234 localhost:8000; do
    if curl -fsS -m 1 "http://$hp/v1/models" -o "$WORK/models.json" 2>/dev/null; then
      export OPENAI_BASE_URL="http://$hp/v1"
      if [ -z "${STUDIO_MODEL:-}" ]; then
        M=$("$PY" -c 'import json,sys
try: print((json.load(open(sys.argv[1])).get("data") or [{}])[0].get("id",""))
except Exception: print("")' "$WORK/models.json" 2>/dev/null || true)
        [ -n "$M" ] && export STUDIO_MODEL="$M" || true
      fi
      break
    fi
  done
fi

case "${OPENAI_BASE_URL:-}" in
  *localhost*|*127.0.0.1*) AI_VIA="${STUDIO_MODEL:-a model} on this machine";;
  *e-infra*)               AI_VIA="CESNET e-INFRA CZ";;
  "")                      [ -n "${OPENAI_KEY:-}${OPENAI_API_KEY:-}" ] && AI_VIA="OpenAI" || AI_VIA="";;
  *)                       AI_VIA="${OPENAI_BASE_URL}";;
esac

echo "SlAIdy  ·  $(basename "$DECK")${AI_VIA:+  ·  AI via $AI_VIA}"
echo "  http://localhost:$PORT"
echo "  Ctrl-C to stop. Your edits are stored by the browser under that address,"
echo "  so always start it the same way — or keep a copy with Export."
[ -n "${AI_VIA:-}" ] || echo "  AI: off. Copy .env.example to .env and put a key in it, or start a local
       model (Ollama, LM Studio, llama.cpp, vLLM) and run this again."
echo

( sleep 1; (xdg-open "http://localhost:$PORT" || open "http://localhost:$PORT") >/dev/null 2>&1 || true ) &
exec "$PY" scripts/serve.py "$WORK" "$PORT" "$DECK"
