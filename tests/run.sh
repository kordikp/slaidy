#!/usr/bin/env bash
# The browser suite. Each tests/NN-*.html loads the app in an iframe, drives it,
# and prints PASS/FAIL lines that this script collects.
#
#   tests/run.sh                 # everything
#   tests/run.sh 05-selection-and-groups   # just that one
#
# Needs google-chrome (or chromium) and python3. Nothing else.
set -uo pipefail
cd "$(dirname "$0")/.."

CHROME=$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)
[ -n "$CHROME" ] || { echo "No Chrome or Chromium on PATH."; exit 1; }
PORT="${PORT:-8931}"

WORK="$(mktemp -d)"
cleanup(){ [ -n "${SRV:-}" ] && kill "$SRV" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT
cp slide-studio.html "$WORK/index.html"
python3 tests/make-fixture.py >/dev/null
cp tests/fixture.json "$WORK/deck.json"
cp tests/*.html "$WORK/"

# expose the internals the tests drive, without shipping that hook in the app
python3 - "$WORK/index.html" <<'PY'
import sys
p = sys.argv[1]; s = open(p, encoding="utf-8").read()
i = s.rfind("\n})();")
hook = """
window.__api={figEdit,feSelect,feTranslate,fePush,feCommit,feGroup,feUngroup,feUnnest,feDel,feResolve,feHtml,
  feUndo,feDup,feAdd,feBounds,feResize,feParentScale,feZoom,feRect,feBox,feDown,feMarquee,
  present,paint,moveSlide,checkFit,shortcuts,snap,undo,insertBlock,insertMenu,blocks,where,slideMd,
  importMarkdown,deckSettings,applyStyle,style,hdrHtml,paintNav,paintBody,paintSide,editMarkdown,stats,
  mdParse,mdPreview,mdNormalise,llm,stageHtml,stageClass,scaleStage,printSlide,paintDeck,paintGrid,
  fig,measureStage,toggleSkip,liveIdx,liveStats,planTrim,scoreSlide,trimDialog,clock,
  get S(){return S},set S(v){S=v},get cur(){return cur},set cur(v){cur=v},get FE(){return FE},
  get UNDO(){return UNDO},get showHidden(){return showHidden},set showHidden(v){showHidden=v},
  pickFigure,figRef,figMark,notesHtml,tidyAllDialog,askSummary,
  feArm,feConnect,arrowGeom,makeArrow,arrowEnds,setEnds,isArrow,reroute,rerouteAll,feTab,
  srcHtml,srcSync,feId,edgePoint,figChrome,LAYNAME,tidyDeck,get feDraw(){return feDraw},set feDraw(v){feDraw=v}};"""
open(p, "w", encoding="utf-8").write(s[:i] + hook + s[i:])
PY

# exec, so $SRV is the server itself — killing the subshell leaves the child
# holding the port, and the next run then talks to a server whose root is gone
(cd "$WORK" && exec python3 -m http.server "$PORT" >/dev/null 2>&1) & SRV=$!
sleep 1

FILES=("$@")
[ ${#FILES[@]} -eq 0 ] && FILES=($(cd tests && ls [0-9]*.html | sed 's/\.html$//'))
pass=0; fail=0
for t in "${FILES[@]}"; do
  out=$(timeout 180 "$CHROME" --headless --disable-gpu --no-sandbox --virtual-time-budget=30000 \
        --dump-dom "http://localhost:$PORT/$t.html" 2>/dev/null \
        | sed -n '/<pre id="out">/,/<\/pre>/p' | sed 's/<[^>]*>//g')
  p=$(grep -cE '^PASS' <<<"$out"); f=$(grep -cE '^(FAIL|ERROR)' <<<"$out")
  pass=$((pass+p)); fail=$((fail+f))
  printf '  %-32s %3d passed  %d failed\n' "$t" "$p" "$f"
  grep -E '^(FAIL|ERROR)' <<<"$out" | sed 's/^/       /'
done
echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ]
