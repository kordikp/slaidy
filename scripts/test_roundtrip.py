#!/usr/bin/env python3
r"""Guard the markdown -> bundle path against silent content loss.

Written after a regex for the layout suffix used \s*, which crosses a blank line:
the **Figure:** line then swallowed the paragraph after it and 3539 words
disappeared from a deck without any error.

    python3 scripts/test_roundtrip.py
"""
import importlib.util, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("bb", os.path.join(ROOT, "scripts", "build_bundle.py"))
bb = importlib.util.module_from_spec(spec); spec.loader.exec_module(bb)

fails = []
def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name}{'  ' + detail if detail else ''}")
    if not cond:
        fails.append(name)

# --- the metadata lines must never reach past their own line ---
sample = """### 1. `[S]` T

**Figure:** `fig-x` · split-r

**Explicit** — this paragraph must survive.

*Summary:* one line.

Another paragraph.

*Delivery note:* say it slowly.
"""
for name in ("FIG_RE", "SUM_RE", "NOTE_RE", "FIG_NONE_RE"):
    rx = getattr(bb, name)
    over = [m.group(0) for m in rx.finditer(sample) if "\n" in m.group(0)]
    check(f"{name} stays on its own line", not over, repr(over[:1])[:70] if over else "")

slides = bb.parse_slides(sample, "G")
check("one slide parsed", len(slides) == 1, str(len(slides)))
s = slides[0]
check("figure read", s["fig"] == "fig-x", str(s["fig"]))
check("layout read", s["layout"] == "split-r", s["layout"])
check("summary read", s["summary"] == "one line.", repr(s["summary"]))
check("note read", s["notes"] == "say it slowly.", repr(s["notes"]))
check("paragraph after the figure survives", "must survive" in s["body"])
check("paragraph after the summary survives", "Another paragraph" in s["body"])
check("no metadata left in the body",
      not re.search(r"\*\*Figure:|\*Summary:|\*Delivery note:", s["body"]))

# --- nothing is lost across the real deck ---
src = os.path.join(ROOT, "example", "slides")
md_words = 0
for f in sorted(os.listdir(src)):
    if not f.endswith(".md"):
        continue
    t = open(os.path.join(src, f), encoding="utf-8").read()
    for sl in bb.parse_slides(t, "x") if bb.SLIDE_RE.search(t) else []:
        md_words += len(sl["body"].split())

out = os.path.join(tempfile.mkdtemp(), "d.json")
subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_bundle.py"),
                "--src", src, "--figs", os.path.join(ROOT, "example", "images"), "--out", out],
               check=True, capture_output=True)
bundle = json.load(open(out))
words = sum(len(x["body"].split()) for x in bundle["slides"])
check("the bundle carries every word the parser found", words == md_words, f"{words} vs {md_words}")
# prose lives in the notes now, so the invariant is the total, not the bodies
total = words + sum(len((x.get("notes") or "").split()) for x in bundle["slides"])
check("no content went missing overall", total > 200, f"{total} words on slides and in notes")
check("every slide has a body or a figure",
      all(x["body"].strip() or x["fig"] for x in bundle["slides"]),
      str(sum(1 for x in bundle["slides"] if not x["body"].strip() and not x["fig"])) + " empty")

print(f"\n{len(fails)} failed" if fails else "\nall good")
sys.exit(1 if fails else 0)
