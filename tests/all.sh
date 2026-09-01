#!/usr/bin/env bash
# Everything CI runs, in one command, so that what passes here passes there.
#
#   tests/all.sh
#
# The workflow calls this same script. That is the point: a check that only
# exists in the workflow is a check nobody runs before pushing, and the first
# anyone hears of it is an email saying the build is red.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
step(){ printf '\n\033[1m%s\033[0m\n' "$1"; }

step "Names the test hook uses, and the browser floor"
python3 tests/preflight.py || fail=1

step "The markdown round trip"
python3 scripts/test_roundtrip.py | tail -3 || fail=1

step "Publishing a deck to the web"
python3 scripts/test_publish.py | tail -3 || fail=1

step "The browser suite"
tests/run.sh || fail=1

step "One file, no dependencies"
if grep -q "<script src=" slaidy.html; then echo "  external script found"; fail=1; fi
if grep -qE '<link[^>]+href="https?:' slaidy.html; then echo "  external stylesheet"; fail=1; fi
if [ "$(ls *.html | wc -l)" -ne 1 ]; then echo "  more than one html at the root"; fail=1; fi
echo "  slaidy.html is $(du -h slaidy.html | cut -f1), on its own"

step "It looks like an application"
for f in slaidy.svg install.sh; do
  [ -f "$f" ] || { echo "  missing $f"; fail=1; }
done
for s in 16 24 32 48 64 128 256; do
  [ -f "icons/slaidy-$s.png" ] || { echo "  missing icons/slaidy-$s.png"; fail=1; }
done
# the icon in the tab and the icon in the launcher are the same drawing
if ! grep -q 'rel="icon" href="data:image/svg%2Bxml' slaidy.html &&
   ! grep -q 'rel="icon" href="data:image/svg+xml' slaidy.html; then
  echo "  the page has no favicon"; fail=1
fi
if command -v desktop-file-validate >/dev/null 2>&1; then
  tmp=$(mktemp -d)
  sed -e "s|\$BIN|/usr/bin/true|" -e "s|Exec=.*|Exec=/usr/bin/true %f|" \
      -e "s|Icon=.*|Icon=slaidy|" > "$tmp/slaidy.desktop" <<DESK
$(sed -n '/^\[Desktop Entry\]/,/^DESKTOP$/p' install.sh | sed '$d')
DESK
  desktop-file-validate "$tmp/slaidy.desktop" || fail=1
  rm -rf "$tmp"
fi
python3 -c "import ast;ast.parse(open('scripts/window.py').read())" || { echo "  window.py does not parse"; fail=1; }
grep -q "scripts/window.py" studio.sh || { echo "  studio.sh does not open the application window"; fail=1; }
echo "  icon at 7 sizes, a desktop entry, its own window, and the same mark in the tab"

printf '\n'
[ "$fail" = 0 ] && echo "all good" || echo "SOMETHING FAILED"
exit "$fail"
