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

CHROME="${CHROME_BIN:-$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)}"
[ -n "$CHROME" ] || { echo "No Chrome or Chromium on PATH."; exit 1; }
PORT="${PORT:-8931}"

WORK="$(mktemp -d)"
cleanup(){ [ -n "${SRV:-}" ] && kill "$SRV" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT
cp slaidy.html "$WORK/index.html"
python3 tests/make-fixture.py >/dev/null
cp tests/*.html "$WORK/"

# expose the internals the tests drive, without shipping that hook in the app
python3 - "$WORK/index.html" <<'PY'
import sys
p = sys.argv[1]; s = open(p, encoding="utf-8").read()
i = s.rindex("</script>")
hook = """
window.__api={figEdit,feSelect,feTranslate,fePush,feCommit,feGroup,feUngroup,feUnnest,feDel,feResolve,feHtml,
  feUndo,feDup,feAdd,feBounds,feResize,feParentScale,feZoom,feRect,feBox,feDown,feMarquee,
  present,paint,moveSlide,checkFit,shortcuts,snap,undo,insertBlock,insertMenu,blocks,where,slideMd,
  importMarkdown,deckSettings,applyStyle,style,hdrHtml,paintNav,paintBody,paintSide,editMarkdown,stats,
  mdParse,mdPreview,mdNormalise,llm,stageHtml,blocks,stageClass,scaleStage,printSlide,paintDeck,paintGrid,
  fig,measureStage,toggleSkip,liveIdx,liveStats,clock,
  get S(){return S},set S(v){S=v},get cur(){return cur},set cur(v){cur=v},get FE(){return FE},
  get UNDO(){return UNDO},get showHidden(){return showHidden},set showHidden(v){showHidden=v},get showing(){return showing},
  pickFigure,figRef,figMark,figBlocks,firstFig,figIds,setFigSize,bodyParts,notesHtml,tidyAllDialog,askSummary,importWizard,boot,slideKind,KINDS,
  feArm,feConnect,arrowGeom,makeArrow,arrowEnds,setEnds,isArrow,reroute,rerouteAll,feTab,
  srcHtml,srcSync,feId,stampApp,edgePoint,figChrome,layName,LAY,LAYS,layOf,areaGroups,areasHtml,soloFig,figAR,tidyDeck,get feDraw(){return feDraw},set feDraw(v){feDraw=v},
  progress,propose,blankSlide,keepFigures,queueDesign,withStop,jobOf,jobBox,jobsPrune,wantedFigures,drawFigure,fulfilFigures,designSlide,suggestSlides,ask,
  aiHost,DESIGN_SEEDS,STUB,FIGREF,persist,probeServer,writeServer,touch,setStatus,
  get srvDeck(){return srvDeck},get srvLinked(){return srvLinked},set srvLinked(v){srvLinked=v},get dirty(){return dirty},get fileName(){return fileName},
  snapDiff,history_,snapshot,downloadDeck,recentDecks,heldDecks,banner,deckLinks,DESIGN_SYS,get SUGG(){return SUGG},
  deleteSlide,duplicateSlide,sectionMenu,newSection,runOf,srcEditor,feEditText,scalePreview,tex2mml,slideRanges,block,inl,
  get BLOCKIX(){return BLOCKIX},set BLOCKIX(v){BLOCKIX=v},SNIP,analyseSlide,briefWizard,
  splitBody,trimSvg,feContentBox,feTrimCanvas,feResetCanvas,feSetCanvas,checkSvg,fePanel,figSys,FIG_SYS,configure,feCropToSelection,
  copySlides,cutSlides,pasteSlides,mergeFigs,figsOf,picked,PICKED,slideStyle,sstyle,styleVars,
  parseStyle,STYLE_KEYS,normalise,slideMd,style,slideMenu,newDeck,renameDeck,unbanner,hush,hushed,checkFit,useLoad,useNote,useReset,usageHtml,
  KIND_LABEL,nfmt,safeUrl,askReplace,writeServer,writeServerAs,aiSays,nativeFile,canFile,saveDeckAs,openDeckFile,disarmSvg,scopeSvg,put,get,cfgUrl,DEMO_AI,DEMO_HOSTS,demoLimitsHtml,llmOnce,llm2,transient,RETRY,swipes,step};"""
ready = """
/* Transitions never settle under Chrome's virtual time, so getComputedStyle
   reads the value a property is animating *from* — an assertion about a drawer
   that has slid open then measures it closed. The app keeps its transitions;
   the suite measures without them. */
(function(){const s=document.createElement('style');
  s.textContent='*{transition:none !important}';
  (document.head||document.documentElement).appendChild(s);})();
window.__ready=new Promise(r=>{const t=setInterval(()=>{
  try{ if(S&&S.slides&&S.slides.length){clearInterval(t);r();} }catch(e){}
},40);setTimeout(()=>{clearInterval(t);r();},9000);});"""
open(p, "w", encoding="utf-8").write(s[:i] + hook + ready + "\n" + s[i:])
PY

python3 tests/preflight.py || { echo "  preflight failed — the suite would report nothing useful"; exit 1; }

# exec, so $SRV is the server itself — killing the subshell leaves the child
# holding the port, and the next run then talks to a server whose root is gone
# the real server, so the tests exercise the save path the app actually uses
cp tests/fixture.json "$WORK/real-deck.json"
SERVE="$PWD/scripts/serve.py"
(cd "$WORK" && exec python3 "$SERVE" . "$PORT" real-deck.json >/dev/null 2>&1) & SRV=$!
sleep 1

FILES=("$@")
[ ${#FILES[@]} -eq 0 ] && FILES=($(cd tests && ls [0-9]*.html | sed 's/\.html$//'))
pass=0; fail=0
for t in "${FILES[@]}"; do
  # a fresh profile per test: the app now prefers what the browser already holds,
  # which is right for a person and wrong for a suite that must start from the file
  # the app really writes the deck now, so give every test the same fixture
  # rather than whatever the previous one left behind
  cp tests/fixture.json "$WORK/real-deck.json"
  prof="$WORK/prof-$t"
  out=$(timeout 180 "$CHROME" --headless --disable-gpu --no-sandbox --virtual-time-budget=70000 \
        --user-data-dir="$prof" \
        --dump-dom "http://localhost:$PORT/$t.html" 2>/dev/null \
        | sed -n '/<pre id="out">/,/<\/pre>/p' | sed 's/<[^>]*>//g')
  p=$(grep -cE '^PASS' <<<"$out"); f=$(grep -cE '^(FAIL|ERROR)' <<<"$out")
  # a file that asserts nothing is a broken file, not a clean run — a syntax
  # error in a test used to report "0 passed, 0 failed" and read as success
  if [ "$p" -eq 0 ] && [ "$f" -eq 0 ]; then
    f=1; out="ERROR $t produced no assertions — syntax error, or it never loaded"
  fi
  pass=$((pass+p)); fail=$((fail+f))
  printf '  %-32s %3d passed  %d failed\n' "$t" "$p" "$f"
  grep -E '^(FAIL|ERROR)' <<<"$out" | sed 's/^/       /'
done
echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ]
