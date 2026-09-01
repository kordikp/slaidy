#!/usr/bin/env bash
# Put SlAIdy in the launcher, on Linux.
#
#   ./install.sh            # install, and pin it to the dock
#   ./install.sh --no-pin   # install without touching the dock
#   ./install.sh --remove   # take it out again, dock included
#
# Three files in your home directory and nothing else: a launcher script, a
# desktop entry, and an icon. No root, no package manager, no daemon. The
# application is still this folder — the entry only knows where it is.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/slaidy"
APP="$HOME/.local/share/applications/slaidy.desktop"
ICONS="$HOME/.local/share/icons/hicolor"
ICON="$ICONS/scalable/apps/slaidy.svg"

# The dock, on GNOME. It is one entry in one list and this puts it back the way
# it found it on --remove, but it is still your desktop, so --no-pin skips it.
pin() {                              # pin add|remove
  command -v gsettings >/dev/null 2>&1 || return 0
  local key=org.gnome.shell now
  now=$(gsettings get $key favorite-apps 2>/dev/null) || return 0
  now=${now#@as }                    # an empty list comes back as: @as []
  case "$now" in \[*\]) ;; *) return 0;; esac
  if [ "$1" = add ]; then
    case "$now" in *"'slaidy.desktop'"*) echo "  already on the dock"; return 0;; esac
    if [ "$now" = "[]" ]; then now="['slaidy.desktop']"
    else now=$(printf '%s' "$now" | sed "s|]$|, 'slaidy.desktop']|"); fi
    gsettings set $key favorite-apps "$now" 2>/dev/null && echo "  pinned to the dock"
  else
    case "$now" in *"'slaidy.desktop'"*) ;; *) return 0;; esac
    now=$(printf '%s' "$now" | sed -e "s|'slaidy.desktop', ||" -e "s|, 'slaidy.desktop'||" -e "s|'slaidy.desktop'||")
    gsettings set $key favorite-apps "$now" 2>/dev/null && echo "  taken off the dock"
  fi
}

if [ "${1:-}" = "--remove" ]; then
  pin remove
  rm -f "$BIN" "$APP" "$ICON"
  for s in 16 24 32 48 64 128 256; do rm -f "$ICONS/${s}x${s}/apps/slaidy.png"; done
  command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "$ICONS" 2>/dev/null || true
  command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$APP")" 2>/dev/null || true
  echo "Removed. The folder itself is untouched."
  exit 0
fi

mkdir -p "$(dirname "$BIN")" "$(dirname "$APP")" "$(dirname "$ICON")"

cat > "$BIN" <<SH
#!/usr/bin/env bash
# SlAIdy — written by install.sh, points at the folder it was run from
exec "$HERE/studio.sh" "\$@"
SH
chmod +x "$BIN"
# The svg is the icon; the pngs are for the parts of the desktop that would
# rather have one at exactly the size they are drawing.
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
Categories=Office;Presentation;Graphics;
Keywords=slides;presentation;markdown;svg;deck;talk;
StartupWMClass=SlAIdy
MimeType=application/json;text/markdown;
StartupNotify=true
DESKTOP

command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$APP")" 2>/dev/null || true
[ "${1:-}" = "--no-pin" ] || pin add

echo "SlAIdy is in your launcher."
echo "  $BIN      — also on the command line, if ~/.local/bin is on your PATH"
echo "  $APP"
echo "  $ICON  (and png at 16…256)"
echo
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo "  ~/.local/bin is not on your PATH — add it to ~/.profile to type 'slaidy' anywhere."; echo;;
esac
if [ -r "$HERE/.env" ]; then
  echo "  AI: .env is in place."
else
  echo "  AI: copy .env.example to .env and put a key in it, or start a local model"
  echo "      (Ollama, LM Studio, llama.cpp, vLLM) — studio.sh finds one that is running."
fi
