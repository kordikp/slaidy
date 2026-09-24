#!/usr/bin/env python3
"""A deck written into the page opens from a disk, at the slide and click asked for.

This is the file that gets e-mailed and double-clicked, so it is checked the way
it is used: over file://, with no server anywhere.
"""
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bad = 0


def check(name, cond, detail=""):
    global bad
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        bad += 1


chrome = os.environ.get("CHROME_BIN") or shutil.which("google-chrome") or shutil.which("chromium")
deck = {"id": "onefile-check", "title": "Closing </script> <!-- in a title",
        "slides": [{"n": 1, "title": "One", "body": "Plain."},
                   {"n": 2, "title": "Two", "body": "- a\n\n<!-- step -->\n\n- b\n\n<!-- step -->\n\n- c"}],
        "figs": {}, "meta": {}, "style": {}}
tmp = tempfile.mkdtemp()
src, page = os.path.join(tmp, "d.json"), os.path.join(tmp, "talk.html")
json.dump(deck, open(src, "w", encoding="utf-8"))
out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "onefile.py"), src, page],
                     capture_output=True, text=True)
check("it builds", out.returncode == 0, out.stderr.strip())
s = open(page, encoding="utf-8").read()
check("the deck is in the page", 'id="slaidy-deck"' in s)
body = s.split('id="slaidy-deck"', 1)[1].split("</script>", 1)[0]
check("nothing in the deck closes its element early", "</script" not in body and "<!--" not in body)
check("the title is escaped", "<title>Closing &lt;/script&gt;" in s)


def count(query):
    """What the projector's counter says after opening the file at this address."""
    for _ in range(3):   # headless timing: the first paint can miss the budget
        dom = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                              "--user-data-dir=" + tempfile.mkdtemp(), "--virtual-time-budget=8000",
                              "--dump-dom", "file://" + page + query],
                             capture_output=True, text=True, timeout=120).stdout
        m = re.search(r'<div id="count"[^>]*>([^<]*)</div>', dom)
        if m and m.group(1):
            return m.group(1)
    return ""


if chrome:
    got = count("#present")
    check("over file:// it presents the deck in the page", got.startswith("1 / 2"), got)
    got = count("?s=2&step=2#present")
    check("?s=2&step=2 opens at the second click of the second slide", got == "2 / 2 · 2/3", got)
    got = count("?s=9&step=9#present")
    check("an address past the end settles on the last click there is", got == "2 / 2 · 3/3", got)
else:
    print("SKIP no Chrome on PATH — the page was built but not opened")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{'all good' if not bad else f'{bad} failed'}")
sys.exit(1 if bad else 0)
