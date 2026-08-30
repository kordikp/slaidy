#!/usr/bin/env python3
"""Every name the test hook exposes must exist in the app.

Cutting a block out of the app by index has twice swallowed a neighbouring
definition. The only symptom was that window.__api never got assigned, so every
assertion in every file failed with "cannot read properties of undefined" and
said nothing about why. This says why, before the browser starts.
"""
import re, sys, os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = open(os.path.join(root, "slide-studio.html"), encoding="utf-8").read()
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
