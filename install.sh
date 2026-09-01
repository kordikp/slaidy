#!/usr/bin/env bash
# Put SlAIdy in the launcher, on Linux.
#
#   ./install.sh            # install
#   ./install.sh --remove   # take it out again
#
# Three files in your home directory and nothing else: a launcher script, a
# desktop entry, and an icon. No root, no package manager, no daemon. The
# application is still this folder — the entry only knows where it is.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/slaidy"
APP="$HOME/.local/share/applications/slaidy.desktop"
ICON="$HOME/.local/share/icons/hicolor/scalable/apps/slaidy.svg"

if [ "${1:-}" = "--remove" ]; then
  rm -f "$BIN" "$APP" "$ICON"
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
cp "$HERE/slaidy.svg" "$ICON"

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
MimeType=application/json;text/markdown;
StartupNotify=true
DESKTOP

command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$APP")" 2>/dev/null || true

echo "SlAIdy is in your launcher."
echo "  $BIN      — also on the command line, if ~/.local/bin is on your PATH"
echo "  $APP"
echo "  $ICON"
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
