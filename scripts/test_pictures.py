#!/usr/bin/env python3
"""Pictures in the source folder reach the deck, and come back out of it.

The folder is what an assistant edits — markdown, SVG, and pictures as files with
what each shows in assets.json — so the round trip through build_bundle.py and
assets.py is checked, and so is the notes page, which must carry the bytes.
"""
import base64, importlib.util, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bad = 0


def check(name, cond, detail=""):
    global bad
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        bad += 1


# a 1×1 PNG
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
PID = "img-0123456789abcdef01234567"
tmp = tempfile.mkdtemp()
src, figs, ad = (os.path.join(tmp, x) for x in ("slides", "figures", "figures/assets"))
os.makedirs(src); os.makedirs(ad)
open(os.path.join(src, "01-a.md"), "w").write("## A photo\n\n![[fig-photo]]\n\n## Plain\n\nNothing.\n")
open(os.path.join(figs, "fig-photo.svg"), "w").write(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450"><image href="asset:{PID}" width="800" height="450"/></svg>')
open(os.path.join(ad, PID + ".png"), "wb").write(PNG)
open(os.path.join(ad, "img-ffffffffffffffffffffffff.png"), "wb").write(PNG)   # used by nothing
json.dump({PID: {"desc": "the test rig", "source": "lab"}}, open(os.path.join(ad, "assets.json"), "w"))
out = os.path.join(tmp, "deck.json")
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_bundle.py"), "--src", src,
                    "--figs", figs, "--out", out, "--id", "t", "--force"], capture_output=True, text=True)
check("the folder builds", r.returncode == 0, r.stderr.strip()[-200:])
deck = json.load(open(out))
a = (deck.get("assets") or {}).get(PID) or {}
check("a picture a figure places is in the deck", a.get("type") == "image/png" and base64.b64decode(a.get("data", "")) == PNG)
check("with what it shows", a.get("desc") == "the test rig" and a.get("source") == "lab")
check("and only that one", list(deck["assets"]) == [PID], ",".join(deck["assets"]))
check("the pictures come after the slides in the file", list(deck)[-1] == "assets", ",".join(deck))

r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "assets.py"), "list", out], capture_output=True, text=True)
check("list names it, says what it shows and where", PID in r.stdout and "the test rig" in r.stdout and "fig-photo" in r.stdout, r.stdout)
check("and never prints the bytes", deck["assets"][PID]["data"][:16] not in r.stdout)
back = os.path.join(tmp, "back")
subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "assets.py"), "extract", out, back], check=True, capture_output=True)
check("extract writes the file back", open(os.path.join(back, "assets", PID + ".png"), "rb").read() == PNG)
check("and what it shows beside it", json.load(open(os.path.join(back, "assets", "assets.json")))[PID]["desc"] == "the test rig")
subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "assets.py"), "describe", out, PID, "the rig, sensor left"],
               check=True, capture_output=True)
check("describe sets it", json.load(open(out))["assets"][PID]["desc"] == "the rig, sensor left")

spec = importlib.util.spec_from_file_location("publish", os.path.join(ROOT, "scripts", "publish.py"))
pub = importlib.util.module_from_spec(spec); spec.loader.exec_module(pub)
page = pub.notes_page(json.load(open(out)), "t")
check("the notes page carries the picture itself", "data:image/png;base64," in page and "asset:" not in page)

# --- add: picture files into a source folder, named as the app would name them ---
spec2 = importlib.util.spec_from_file_location("assets", os.path.join(ROOT, "scripts", "assets.py"))
assets = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(assets)
app = open(os.path.join(ROOT, "slaidy.html"), encoding="utf-8").read()
fn = app[app.index("function picHash(s){"):]
fn = fn[:fn.index("\n}\n") + 3]
samples = ["", "AAAA", base64.b64encode(PNG).decode(), "x" * 5000]
node = subprocess.run(["node", "-e", fn + "process.stdout.write(JSON.stringify(%s.map(picHash)))" % json.dumps(samples)],
                      capture_output=True, text=True)
if node.returncode == 0:
    check("the Python picHash names a picture exactly as the app does",
          json.loads(node.stdout) == [assets.pic_hash(x) for x in samples], node.stdout[:120])
else:
    print("SKIP no node to compare picHash with")
figs2 = os.path.join(tmp, "figs2")
src_png = os.path.join(tmp, "dot.png"); open(src_png, "wb").write(PNG)
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "assets.py"), "add", figs2, src_png, "--desc", "a dot"],
                   capture_output=True, text=True)
pid = assets.pic_hash(base64.b64encode(PNG).decode())
check("add keeps a small picture's own bytes, under the app's name for them",
      os.path.isfile(os.path.join(figs2, "assets", pid + ".png")), r.stdout + r.stderr)
check("and records what it shows", json.load(open(os.path.join(figs2, "assets", "assets.json")))[pid]["desc"] == "a dot")
check("and prints the <image> that places it", 'href="asset:%s"' % pid in r.stdout)
try:
    from PIL import Image
    big = os.path.join(tmp, "big.png"); Image.new("RGB", (4000, 1000), (200, 30, 30)).save(big)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "assets.py"), "add", figs2, big],
                       capture_output=True, text=True)
    made = [f for f in os.listdir(os.path.join(figs2, "assets")) if f.endswith(".webp")]
    w = json.load(open(os.path.join(figs2, "assets", "assets.json")))[made[0][:-5]]["w"] if made else 0
    check("a large picture is shrunk to the longest edge the app keeps, as WebP", made and w == 1920, r.stdout)
except ImportError:
    print("SKIP no Pillow: shrinking is not tested here")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{'all good' if not bad else f'{bad} failed'}")
sys.exit(1 if bad else 0)
