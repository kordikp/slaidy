#!/usr/bin/env python3
"""Every name the test hook exposes must exist in the app.

Cutting a block out of the app by index has twice swallowed a neighbouring
definition. The only symptom was that window.__api never got assigned, so every
assertion in every file failed with "cannot read properties of undefined" and
said nothing about why. This says why, before the browser starts.
"""
import re, sys, os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = open(os.path.join(root, "slaidy.html"), encoding="utf-8").read()
src = app[app.index("<script>") + 8:app.rindex("</script>")]
hook = open(os.path.join(root, "tests", "run.sh"), encoding="utf-8").read()
a = hook.index("window.__api={")
b = hook.index('"""', a)
names = re.findall(r"(?:^|[,{]\s*)([A-Za-z_]\w*)\s*(?=[,}])", hook[a:b], re.M)

missing = [n for n in names
           if not re.search(r"\b(?:function|const|let|var|class)\s+" + re.escape(n) + r"\b", src)]
if missing:
    print("  the hook names things the app does not define: " + ", ".join(missing))
    sys.exit(1)

# A second, looser check was tried here and thrown away: scanning for functions
# the app calls but never defines. It cannot tell a call from a parameter name,
# a CSS string or a word inside a prompt, so it cried wolf about two dozen
# innocent names. A check that has to be ignored is worse than no check.


# ---------------------------------------------------------------------------
# The browser floor.
#
# A regex literal is parsed with the script, so one (?<!\s) in a markdown rule
# did not make italics wrong on Safari before 16.4 — it stopped the file
# parsing, and every button on the page was dead. Nothing in the test suite
# could catch that: the suite runs in Chrome, where it parses fine.
#
# So the syntax and APIs that arrived late are listed here and refused. Raise
# the floor deliberately, by editing this list, not by accident.
BROWSER_FLOOR = [
    (r"\(\?<[=!]",            "regex lookbehind — Safari 16.4; a parse error, not a bug"),
    (r"\bstructuredClone\(",  "structuredClone — Safari 15.4; use clone()"),
    (r"\bObject\.groupBy\(",  "Object.groupBy — Safari 17.4"),
    (r"\.toSorted\(|\.toReversed\(|\.toSpliced\(", "change-by-copy arrays — Safari 16.4"),
    (r"\.findLast\(|\.findLastIndex\(", "findLast — Safari 15.4"),
    (r"\bObject\.hasOwn\(",   "Object.hasOwn — Safari 15.4"),
    (r":has\(",               "CSS :has() — Safari 15.4"),
    (r"\bat\(-\d",            "Array.at(-1) — Safari 15.4; use [len-1]"),
]


def check_browser_floor(src):
    bad = []
    for pat, why in BROWSER_FLOOR:
        for m in re.finditer(pat, src):
            line = src.count("\n", 0, m.start()) + 1
            bad.append(f"line {line}: {m.group(0)!r} — {why}")
    return bad


bad = check_browser_floor(app)
if bad:
    print("  syntax or APIs newer than the browser floor:")
    for b in bad:
        print("    " + b)
    sys.exit(1)
