#!/usr/bin/env python3
"""What publishing a deck does, checked rather than described.

The web side of this project is a folder convention and a workflow step, which
means it is exactly the kind of thing that breaks quietly and is noticed by
somebody following a dead link.
"""
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bad = 0


def check(name, cond, detail=""):
    global bad
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        bad += 1


deck = {"id": "x", "title": "A Talk", "slides": [{"n": 1, "title": "One", "body": "Hello."}],
        "figs": {"fig-a": "<svg/>"}, "meta": {"author": "Someone"}, "style": {}}
tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "d.json")
json.dump(deck, open(src, "w", encoding="utf-8"))

out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "publish.py"), src, "ISD 2026 Keynote"],
                     capture_output=True, text=True)
check("it runs", out.returncode == 0, out.stderr.strip()[:120])
name = "isd-2026-keynote"
where = os.path.join(ROOT, "site", name, "deck.json")
try:
    check("the name becomes a url-shaped folder", os.path.isfile(where), where)
    got = json.load(open(where, encoding="utf-8"))
    check("the slides are all there", len(got["slides"]) == len(deck["slides"]))
    check("and the figures with them", got["figs"] == deck["figs"])
    check("what was already in the metadata survives", got["meta"].get("author") == "Someone")
    check("and it is marked as published", got["meta"].get("shared") is True,
          json.dumps(got["meta"]))
    check("the url it printed is the one it wrote",
          ("/slaidy/%s/" % name) in out.stdout, out.stdout.strip().splitlines()[-4:][0][:70])
    check("it says the deck is not on the web until it is pushed",
          "git add" in out.stdout and "push" in out.stdout)

    # the workflow's own step, run here
    site = tempfile.mkdtemp()
    for d in sorted(os.listdir(os.path.join(ROOT, "site"))):
        p = os.path.join(ROOT, "site", d, "deck.json")
        if not os.path.isfile(p):
            continue
        os.makedirs(os.path.join(site, d), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, "slaidy.html"), os.path.join(site, d, "index.html"))
        shutil.copyfile(p, os.path.join(site, d, "deck.json"))
    check("laying out the site gives every deck a page of its own",
          os.path.isfile(os.path.join(site, name, "index.html")) and
          os.path.isfile(os.path.join(site, name, "deck.json")))
    check("and the page is the same single file as everywhere else",
          os.path.getsize(os.path.join(site, name, "index.html")) ==
          os.path.getsize(os.path.join(ROOT, "slaidy.html")))

    app = open(os.path.join(ROOT, "slaidy.html"), encoding="utf-8").read()
    check("the app opens a published deck ready to watch", "meta.shared" in app)
    check("and #present goes straight to the projector",
          re.search(r"location\.hash[^;]*present", app) is not None)
finally:
    shutil.rmtree(os.path.join(ROOT, "site", name), ignore_errors=True)

print()
print("all good" if not bad else "%d failed" % bad)
sys.exit(1 if bad else 0)
