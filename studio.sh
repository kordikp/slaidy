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

# Which deck: the one you name, else the one you had last, else the example.
# The application should come back where you left it — a launcher icon that
# always opens the sample deck is a launcher icon you stop pressing.
STATE="${SLAIDY_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/slaidy}"
LAST="$STATE/last-deck"
DECK="${1:-}"
if [ -z "$DECK" ] && [ -r "$LAST" ]; then
  want=$(cat "$LAST" 2>/dev/null || true)
  if [ -n "$want" ] && [ -f "$want" ]; then DECK="$want"
  elif [ -n "$want" ]; then
    # the deck you had open is gone from that path: take the newest one that is
    # still there rather than a fresh example nobody asked for
    echo "  $want is no longer there"
    for cand in $(python3 -c 'import json,sys;[print(x) for x in json.load(open(sys.argv[1])) if isinstance(x,str)]' "$STATE/recent-decks" 2>/dev/null); do
      if [ -f "$cand" ]; then DECK="$cand"; echo "  opening the most recent deck that is: $cand"; break; fi
    done
  fi
fi
DECK="${DECK:-decks/example.json}"
PORT="${PORT:-8080}"

[ -f "$DECK" ] || { echo "No such deck: $DECK"; echo "Available:"; ls -1 decks/*.json 2>/dev/null || echo "  (none — run scripts/build_bundle.py)"; exit 1; }
[ -f slaidy.html ] || { echo "slaidy.html is missing"; exit 1; }

STAMP=$(sha1sum slaidy.html | cut -c1-7)
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# The DECK is deliberately not copied in. `cp` stamps the copy with the current
# time, so every restart made the served deck look newer than the edits held in
# the browser — and the edits lost. The server owns the real file instead: it
# streams it at /deck.json and writes it back at /api/deck.
cp slaidy.html "$WORK/index.html"

# serve.py writes $LAST, not this script: the deck can change while it is
# running — Save As and Open both move it — and a note taken once here would
# then say the wrong thing.

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

echo "SlAIdy $STAMP  ·  $(basename "$DECK")${AI_VIA:+  ·  AI via $AI_VIA}"
echo "  http://localhost:$PORT"
echo "  Ctrl-C to stop. Your edits are stored by the browser under that address,"
echo "  so always start it the same way — or keep a copy with Export."
[ -n "${AI_VIA:-}" ] || echo "  AI: off. Copy .env.example to .env and put a key in it, or start a local
       model (Ollama, LM Studio, llama.cpp, vLLM) and run this again."
echo

# A window of its own, not a tab among thirty, and under its own icon.
#
# --app= drops the address bar; --class names the window so the desktop can match
# it to slaidy.desktop. The profile directory is the part that is easy to miss:
# without it, a Chrome that is already running opens the window itself, and the
# window is then that Chrome's — its class, its icon, filed under the browser in
# the dock. Its own profile means its own process, which owns its own window.
open_window() {
  # Wait for the server to answer before opening anything. It used to sleep for
  # a second and hope, and when the second was not enough the window showed the
  # browser's own "could not connect" page — which is the application appearing
  # to be broken because it was asked about too early.
  local i
  for i in $(seq 1 120); do
    if (exec 3<>/dev/tcp/127.0.0.1/$PORT) 2>/dev/null; then exec 3<&- 3>&-; break; fi
    sleep 0.25
  done
  # A window of its own, if this machine has what it takes to make one: GTK and
  # WebKit, both of which Ubuntu ships. No address bar, no tabs, its own icon,
  # and the dock files it under the application rather than under the browser.
  #
  # Tried, then checked: WebKit's sandbox needs user namespaces, which are not
  # always there, and it exits rather than saying so. If it does not survive two
  # seconds it is tried once without the sandbox — the page is localhost and
  # nothing else — and if that fails too, a browser is opened, which is what
  # this did before and is no worse than it was.
  local wurl="http://localhost:$PORT/?v=$STAMP" wlog=/tmp/slaidy-window.log wp
  # SLAIDY_BROWSER=1 asks for the browser instead, which is the escape hatch
  # when something works there and not here.
  if [ -z "${SLAIDY_BROWSER:-}" ] &&
     "$PY" -c 'import gi;gi.require_version("Gtk","4.0");gi.require_version("WebKit","6.0")' 2>/dev/null; then
    : > "$wlog"
    "$PY" scripts/window.py "$wurl" >>"$wlog" 2>&1 & wp=$!
    sleep 2; kill -0 "$wp" 2>/dev/null && return
    WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1 \
      "$PY" scripts/window.py "$wurl" >>"$wlog" 2>&1 & wp=$!
    sleep 2; kill -0 "$wp" 2>/dev/null && return
    echo "  the application window would not start — opening a browser instead ($wlog)"
  fi
  # The address carries the hash of the file being served. A cache cannot
  # answer for a url it has never seen, so a window opened this way is the
  # application that was just installed and not a copy of last week's.
  local url="http://localhost:$PORT/?v=$STAMP"
  local prof="${XDG_DATA_HOME:-$HOME/.local/share}/slaidy/browser"
  local b
  for b in google-chrome chromium chromium-browser brave-browser microsoft-edge; do
    if command -v "$b" >/dev/null 2>&1; then
      # Your ordinary browser profile by default, because that is where the decks
      # this browser is holding actually are — an isolated profile is a window
      # that cannot see your own work. SLAIDY_OWN_PROFILE=1 gives it one anyway,
      # which is what makes the window file under its own icon rather than under
      # the browser: a Chrome already running opens the window itself otherwise,
      # and the window is then that Chrome's.
      if [ -n "${SLAIDY_OWN_PROFILE:-}" ]; then
        mkdir -p "$prof"
        "$b" --app="$url" --class=SlAIdy --user-data-dir="$prof" \
             --no-first-run --no-default-browser-check >/dev/null 2>&1 &
      else
        "$b" --app="$url" --class=SlAIdy >/dev/null 2>&1 &
      fi
      return
    fi
  done
  (xdg-open "$url" || open "$url") >/dev/null 2>&1 || true
}
open_window &
exec "$PY" scripts/serve.py "$WORK" "$PORT" "$DECK"
