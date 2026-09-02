#!/usr/bin/env bash
# Put SlAIdy in the launcher, on Linux.
#
#   ./install.sh            # install, pin it to the dock, and start it
#   ./install.sh --no-pin   # install without touching the dock
#   ./install.sh --no-run   # install without starting it
#   ./install.sh --remove   # take it out again, dock included
#
# Three files in your home directory and nothing else: a launcher script, a
# desktop entry, and an icon. No root, no package manager, no daemon. The
# application is still this folder — the entry only records where it is.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/slaidy"
# The entry is named after the application id the window sets, because that is
# how a Wayland desktop matches a window to its icon. slaidy.desktop was the old
# name and is removed if it is still lying about.
APPID="io.github.kordikp.slaidy"
APP="$HOME/.local/share/applications/$APPID.desktop"
OLDAPP="$HOME/.local/share/applications/slaidy.desktop"
ICONS="$HOME/.local/share/icons/hicolor"
ICON="$ICONS/scalable/apps/slaidy.svg"

pin() {                              # pin add|remove
  command -v gsettings >/dev/null 2>&1 || return 0
  local key=org.gnome.shell now
  now=$(gsettings get $key favorite-apps 2>/dev/null) || return 0
  now=${now#@as }
  case "$now" in \[*\]) ;; *) return 0;; esac
  if [ "$1" = add ]; then
    case "$now" in *"'$APPID.desktop'"*) return 0;; esac
    now=$(printf '%s' "$now" | sed -e "s|'slaidy.desktop', ||" -e "s|, 'slaidy.desktop'||")
    if [ "$now" = "[]" ]; then now="['$APPID.desktop']"
    else now=$(printf '%s' "$now" | sed "s|]$|, '$APPID.desktop']|"); fi
    gsettings set $key favorite-apps "$now" 2>/dev/null && echo "  pinned to the dock"
  else
    now=$(printf '%s' "$now" | sed -e "s|'$APPID.desktop', ||" -e "s|, '$APPID.desktop'||" -e "s|'$APPID.desktop'||" \
      -e "s|'slaidy.desktop', ||" -e "s|, 'slaidy.desktop'||" -e "s|'slaidy.desktop'||")
    gsettings set $key favorite-apps "$now" 2>/dev/null && echo "  taken off the dock"
  fi
}

if [ "${1:-}" = "--remove" ]; then
  pin remove
  rm -f "$BIN" "$APP" "$OLDAPP" "$ICON"
  for s in 16 24 32 48 64 128 256; do rm -f "$ICONS/${s}x${s}/apps/slaidy.png"; done
  command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "$ICONS" 2>/dev/null || true
  command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$APP")" 2>/dev/null || true
  echo "Removed. The folder itself is untouched."
  exit 0
fi

# ── is this actually the application, and which copy of it ───────────────────
[ -f "$HERE/slaidy.html" ] || { echo "slaidy.html is not here: $HERE"; exit 1; }
SHA=$(sha1sum "$HERE/slaidy.html" | cut -c1-7)
missing=""
for marker in "function areaGroups" "function figAR" "function recentDecks" "function stampApp"; do
  grep -qF "$marker" "$HERE/slaidy.html" || missing="$missing\n    $marker"
done
if [ -n "$missing" ]; then
  echo "This slaidy.html is missing things it should have:"
  printf "%b\n" "$missing"
  echo "  Run: git -C \"$HERE\" pull"
  exit 1
fi

mkdir -p "$(dirname "$BIN")" "$(dirname "$APP")" "$(dirname "$ICON")"

# ── the launcher ─────────────────────────────────────────────────────────────
# A SlAIdy already on the port is one of two things. With a window open on it,
# it is somebody's work — a second launch takes the next port, so two decks can
# sit side by side and slides can be carried between them. Without a window it
# is a leftover, and leaving that up while opening a new window is how you end
# up looking at last week's application and swearing at the person who wrote it.
cat > "$BIN" <<SH
#!/usr/bin/env bash
# SlAIdy — written by install.sh, points at the folder it was run from
set -uo pipefail
HERE="$HERE"
PORT="\${PORT:-8080}"
busy(){ ss -ltnp 2>/dev/null | grep -q ":\$1 "; }
serving(){ ss -ltnp 2>/dev/null | grep ":\$1 " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u; }
while busy "\$PORT"; do
  stale=1
  for pid in \$(serving "\$PORT"); do
    tr '\0' ' ' < "/proc/\$pid/cmdline" 2>/dev/null | grep -q 'serve\.py' || { stale=0; continue; }
    pgrep -f "window.py http://localhost:\$PORT/" >/dev/null 2>&1 && stale=0
  done
  if [ "\$stale" = 1 ]; then
    for pid in \$(serving "\$PORT"); do kill "\$pid" 2>/dev/null && echo "  stopped a SlAIdy left on port \$PORT with no window"; done
    sleep 0.3; break
  fi
  echo "  port \$PORT has a SlAIdy with a window open — taking the next one"
  PORT=\$((PORT+1))
done
export PORT
exec "\$HERE/studio.sh" "\$@"
SH
chmod +x "$BIN"

cp "$HERE/slaidy.svg" "$ICON"
for s in 16 24 32 48 64 128 256; do
  [ -f "$HERE/icons/slaidy-$s.png" ] || continue
  mkdir -p "$ICONS/${s}x${s}/apps"
  cp "$HERE/icons/slaidy-$s.png" "$ICONS/${s}x${s}/apps/slaidy.png"
done
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "$ICONS" 2>/dev/null || true

cat > "$APP" <<DESKTOP
[Desktop Entry]
Type=Application
Name=SlAIdy
GenericName=Slide editor
Comment=Slides that stay markdown and SVG
Exec=$BIN %f
Icon=slaidy
Terminal=false
Categories=Office;Presentation;
Keywords=slides;presentation;markdown;svg;deck;talk;
MimeType=application/json;text/markdown;
StartupNotify=true
StartupWMClass=SlAIdy
DESKTOP
rm -f "$OLDAPP"
command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$APP")" 2>/dev/null || true
[ "${1:-}" = "--no-pin" ] || pin add

echo "SlAIdy $SHA is installed."
echo "  $BIN"
echo "  $APP"
echo "  $ICON  (and png at 16…256)"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo "  ~/.local/bin is not on your PATH — add it to ~/.profile to type 'slaidy' anywhere.";;
esac
if [ -r "$HERE/.env" ]; then echo "  AI: .env is in place."
else echo "  AI: copy .env.example to .env, or start a local model — studio.sh finds one."; fi

# ── start it, and check that what is being served is what was installed ──────
if [ "${1:-}" != "--no-run" ] && [ "${2:-}" != "--no-run" ]; then
  echo
  ( setsid "$BIN" >/tmp/slaidy-launch.log 2>&1 < /dev/null & ) || true
  for i in $(seq 1 40); do
    sleep 0.25
    got=$(curl -s -m 2 "http://localhost:${PORT:-8080}/" 2>/dev/null | sha1sum | cut -c1-7) || true
    [ "$got" = "$SHA" ] && break
  done
  if [ "${got:-}" = "$SHA" ]; then
    echo "  Running on http://localhost:${PORT:-8080}  — serving $SHA, which is what is installed."
  else
    echo "  Started, but the page being served is ${got:-nothing} and $SHA was installed."
    echo "  See /tmp/slaidy-launch.log"
  fi
fi
