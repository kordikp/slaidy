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

step "The browser suite"
tests/run.sh || fail=1

step "One file, no dependencies"
if grep -q "<script src=" slaidy.html; then echo "  external script found"; fail=1; fi
if grep -qE '<link[^>]+href="https?:' slaidy.html; then echo "  external stylesheet"; fail=1; fi
if [ "$(ls *.html | wc -l)" -ne 1 ]; then echo "  more than one html at the root"; fail=1; fi
echo "  slaidy.html is $(du -h slaidy.html | cut -f1), on its own"

printf '\n'
[ "$fail" = 0 ] && echo "all good" || echo "SOMETHING FAILED"
exit "$fail"
