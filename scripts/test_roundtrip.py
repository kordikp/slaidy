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
for name in ("FIG_RE", "SUM_RE", "FIG_NONE_RE"):
    rx = getattr(bb, name)
    over = [m.group(0) for m in rx.finditer(sample) if "\n" in m.group(0)]
    check(f"{name} stays on its own line", not over, repr(over[:1])[:70] if over else "")
# A note is the one field that may run on — it has paragraphs, and a part per
# click — but only forward, to the end of the slide or the next structural line.
notes = [m.group(1).strip() for m in bb.NOTE_RE.finditer(sample)]
check("a note takes nothing from before it", notes == ["say it slowly."], repr(notes))

slides = bb.parse_slides(sample, "G")
check("one slide parsed", len(slides) == 1, str(len(slides)))
s = slides[0]
# A figure is a block in the body now, not a field with a layout to place it.
# The old **Figure:** line still reads, and is translated on the way through.
check("no slide carries a figure field", "fig" not in s, str(s.get("fig")))
check("the figure is in the body", "![[fig-x]]" in s["body"], s["body"][:60])
check("split-r became two columns", s["layout"] == "two", s["layout"])
check("with the drawing after the break, which is what split-r meant",
      s["body"].index("<!-- col -->") < s["body"].index("![[fig-x]]"), s["body"][:80])
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

# Notes with paragraphs and clicks, and data the editor has no field for, travel through markdown.
md2 = """### 1. `[S]` A chatbot slide

- the question

*Data:* {"tiny": {"bot": "co-kdyby", "minutes": 5}}

*Delivery note:* First, the question.

A second paragraph.

<!-- step -->

Then the twist.
"""
s2 = bb.parse_slides(md2, "G")[0]
check("data travels as one JSON line", s2.get("tiny") == {"bot": "co-kdyby", "minutes": 5}, repr(s2.get("tiny")))
check("notes keep their paragraphs and clicks",
      s2["notes"] == "First, the question.\n\nA second paragraph.\n\n<!-- step -->\n\nThen the twist.", repr(s2["notes"]))
check("the body is only the body", s2["body"] == "- the question", repr(s2["body"]))

# A deck names its own sections in deck.meta.json instead of inheriting another deck's table.
gtmp = tempfile.mkdtemp()
open(os.path.join(gtmp, "01-the-shift.md"), "w").write("### 1. `[S]` One\n\nbody\n")
open(os.path.join(gtmp, "02-closing.md"), "w").write("### 2. `[S]` Two\n\nbody\n")
json.dump({"title": "T", "groups": {"01-the-shift.md": "The shift"}}, open(os.path.join(gtmp, "deck.meta.json"), "w"))
gout = os.path.join(gtmp, "d.json")
subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_bundle.py"), "--src", gtmp, "--figs", gtmp,
                "--out", gout, "--force"], check=True, capture_output=True)
groups = [x["group"] for x in json.load(open(gout))["slides"]]
check("sections are named by the deck's own deck.meta.json", groups == ["The shift", "Closing"], repr(groups))

print(f"\n{len(fails)} failed" if fails else "\nall good")
sys.exit(1 if fails else 0)
