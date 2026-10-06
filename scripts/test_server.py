#!/usr/bin/env python3
import urllib.parse
"""What the local server does with the deck file.

It owns the one thing that cannot be recovered — the file on disk — and it has
grown: it writes the deck, opens another, remembers which for next time, and
keeps a copy when a different deck lands on top of one. None of that was covered
by the browser suite, which never starts it.
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8999
bad = 0


def check(name, cond, detail=""):
    global bad
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        bad += 1


def call(method, path, body=None):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path),
                               data=json.dumps(body).encode() if body is not None else None,
                               method=method,
                               headers={"Content-Type": "application/json",
                                        "Origin": "http://localhost:%d" % PORT})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def deck(n=1, title="A deck", ident="d"):
    return {"id": ident, "title": title, "figs": {},
            "slides": [{"n": i + 1, "title": "Slide %d" % (i + 1)} for i in range(n)]}


tmp = tempfile.mkdtemp()
state = os.path.join(tmp, "state")
first = os.path.join(tmp, "first.json")
json.dump(deck(9, "First", "first"), open(first, "w", encoding="utf-8"))

env = dict(os.environ, XDG_STATE_HOME=state)
srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "scripts", "serve.py"),
                        tmp, str(PORT), first],
                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        time.sleep(0.1)
        try:
            call("GET", "/api/deck"); break
        except Exception:
            pass

    last = os.path.join(state, "slaidy", "last-deck")
    check("it remembers the deck it was given", os.path.isfile(last) and
          open(last).read().strip() == first, open(last).read().strip() if os.path.isfile(last) else "no file")

    # save as
    other = os.path.join(tmp, "renamed.json")
    st, j = call("PUT", "/api/deck?as=" + urllib.parse.quote(other), deck(3, "Renamed", "renamed"))
    check("save as writes the file it was given", st == 200 and os.path.isfile(other), str(st))
    check("and that file is the deck from now on", call("GET", "/api/deck")[1]["abs"] == other,
          call("GET", "/api/deck")[1]["abs"])
    check("and it is what the next launch will open",
          open(last).read().strip() == other, open(last).read().strip())
    check("the one it started with is untouched",
          len(json.load(open(first))["slides"]) == 9, "still 9 slides")

    # open another by path
    st, _ = call("GET", "/deck.json?path=" + urllib.parse.quote(first))
    check("opening one by path switches to it", call("GET", "/api/deck")[1]["abs"] == first)
    check("and that is remembered too", open(last).read().strip() == first)

    # a deck that is not this deck keeps a copy of what was there
    st, _ = call("PUT", "/api/deck", deck(1, "Something else", "else"))
    check("a different deck landing on it is written", st == 200, str(st))
    check("but the old one is kept beside it", os.path.isfile(first + ".bak"), first + ".bak")
    check("with everything that was in it",
          len(json.load(open(first + ".bak"))["slides"]) == 9, "9 slides kept")

    # the few before it
    st, j = call("GET", "/api/deck")
    paths = [r["abs"] for r in (j.get("recent") or [])]
    check("it lists the decks opened lately", other in paths and first in paths,
          " | ".join(paths))
    check("newest first", paths and paths[0] == first, " | ".join(paths[:2]))
    check("with how big each one is",
          all(isinstance(r.get("n"), int) and r.get("at") for r in j["recent"]),
          json.dumps(j["recent"][:1]))
    os.remove(other)
    st, j = call("GET", "/api/deck")
    check("and a file that has gone is not offered",
          other not in [r["abs"] for r in (j.get("recent") or [])],
          " | ".join(r["abs"] for r in (j.get("recent") or [])))

    # what it refuses
    check("it refuses a path that is not a deck",
          call("PUT", "/api/deck?as=" + urllib.parse.quote(os.path.join(tmp, "x.txt")), deck())[0] == 400)
    check("and a directory that is not there",
          call("PUT", "/api/deck?as=" + urllib.parse.quote("/nope/nowhere/x.json"), deck())[0] == 400)
    check("and something with no slides in it",
          call("PUT", "/api/deck", {"id": "x", "slides": []})[0] == 400)
    # ── what is not worth remembering ───────────────────────────────────
    # the bundled example is the launcher's fallback, not a choice; and a deck
    # that has since vanished must drop out of the list rather than stand in
    # front of the real one. Both are how a fresh example.json opened in front
    # of someone who had been working on their own deck the evening before.
    import importlib.util as _iu
    spec = _iu.spec_from_file_location("srv", os.path.join(ROOT, "scripts", "serve.py"))
    srvmod = _iu.module_from_spec(spec); spec.loader.exec_module(srvmod)
    ex = os.path.join(tmp, "example.json")
    json.dump(deck(2, "Example", "example"), open(ex, "w", encoding="utf-8"))
    before = open(os.path.join(state, "slaidy", "last-deck"), encoding="utf-8").read().strip()
    srvmod.remember(ex)
    after = open(os.path.join(state, "slaidy", "last-deck"), encoding="utf-8").read().strip()
    check("the bundled example is never remembered as the last deck", before == after and not after.endswith("example.json"), after)
    gone = os.path.join(tmp, "gone.json")
    json.dump(deck(2, "Gone", "gone"), open(gone, "w", encoding="utf-8"))
    srvmod.remember(gone)
    os.remove(gone)
    srvmod.remember(first)
    rec = json.load(open(os.path.join(state, "slaidy", "recent-decks"), encoding="utf-8"))
    check("a deck that no longer exists drops out of the recent list", gone not in rec and rec[0] == os.path.abspath(first), str(rec))
    env2 = dict(os.environ); env2.pop("SLAIDY_STATE", None); env2.pop("XDG_STATE_HOME", None)
    tmpdeck = os.path.join(tempfile.gettempdir(), "slaidy-probe-%d.json" % os.getpid())
    json.dump(deck(2, "Probe", "probe"), open(tmpdeck, "w", encoding="utf-8"))
    r = subprocess.run([sys.executable, "-c",
        "import importlib.util,sys;s=importlib.util.spec_from_file_location('srv',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(m.worth_remembering(sys.argv[2]))",
        os.path.join(ROOT, "scripts", "serve.py"), tmpdeck], env=env2, capture_output=True, text=True)
    os.remove(tmpdeck)
    check("with the real state, a deck in a temporary directory is a test's and is not remembered", r.stdout.strip() == "False", r.stdout.strip() or r.stderr[-200:])

    # a PDF straight from the server, with no print dialog in the way
    page = ("<!doctype html><style>@page{size:297mm 167mm;margin:0}body{margin:0}"
            ".p{width:297mm;height:167mm;break-after:page;background:#10223A;"
            "print-color-adjust:exact;-webkit-print-color-adjust:exact}</style>"
            + "<div class=p></div>" * 3).encode()
    def post_pdf(origin):
        r = urllib.request.Request("http://127.0.0.1:%d/api/pdf" % PORT, data=page, method="POST",
                                   headers={"Content-Type": "text/html", "Origin": origin})
        try:
            with urllib.request.urlopen(r, timeout=200) as resp:
                return resp.status, resp.headers.get("Content-Type"), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type"), e.read()
    st, _, _ = post_pdf("http://evil.example")
    check("the PDF route only answers the page it serves", st == 403, str(st))
    has = call("GET", "/api/deck")[1].get("pdf")
    if has:
        st, ct, b = post_pdf("http://localhost:%d" % PORT)
        check("the PDF route answers with a PDF", st == 200 and ct == "application/pdf" and b[:5] == b"%PDF-",
              "%s %s %r" % (st, ct, b[:40]))
        pages = len(__import__("re").findall(rb"/Type\s*/Page[^s]", b))
        check("one page per page it was sent", pages == 3, "%d pages" % pages)
        check("and nothing is left waiting to be printed", not call("GET", "/__print/x.html")[0] == 200)
    else:
        print("SKIP no Chrome or Chromium here, so the PDF route falls back to the print dialog")

    # a browser with no usable sandbox (Ubuntu 23.10+ without an AppArmor profile,
    # GitHub's runners) is started once more without it, and the export still works
    real = srv_chrome = __import__("shutil").which("google-chrome") or __import__("shutil").which("chromium") \
        or os.environ.get("CHROME_BIN") and __import__("shutil").which(os.environ["CHROME_BIN"])
    if has and real:
        nosb = os.path.join(tmp, "chrome-without-sandbox")
        open(nosb, "w").write('#!/bin/sh\ncase " $* " in *" --no-sandbox "*) exec "%s" "$@";; esac\n'
                              'echo "[0101/000000:FATAL:zygote_host_impl_linux.cc(127)] No usable sandbox!" >&2\n'
                              'echo "#0 0x55d0 base::debug::CollectStackTrace()" >&2\nexit 133\n' % real)
        os.chmod(nosb, 0o755)
        srv3 = subprocess.Popen([sys.executable, os.path.join(ROOT, "scripts", "serve.py"), tmp, str(PORT + 2), first],
                                env=dict(env, CHROME_BIN=nosb, SLAIDY_CHROME=""),
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen("http://127.0.0.1:%d/api/deck" % (PORT + 2), timeout=2); break
                except Exception:
                    time.sleep(0.2)
            r = urllib.request.Request("http://127.0.0.1:%d/api/pdf" % (PORT + 2), data=page, method="POST",
                                       headers={"Content-Type": "text/html", "Origin": "http://localhost:%d" % (PORT + 2)})
            try:
                with urllib.request.urlopen(r, timeout=200) as resp:
                    st3, b3 = resp.status, resp.read()
            except urllib.error.HTTPError as e:
                st3, b3 = e.code, e.read()
            check("a browser with no usable sandbox is started once more without it",
                  st3 == 200 and b3[:5] == b"%PDF-", "%s %r" % (st3, b3[:120]))
        finally:
            srv3.terminate()

    # a browser that breaks says why, to the page and to the terminal
    fake = os.path.join(tmp, "fake-chrome")
    open(fake, "w").write("#!/bin/sh\necho 'the fake browser broke' >&2\nexit 3\n")
    os.chmod(fake, 0o755)
    srv2 = subprocess.Popen([sys.executable, os.path.join(ROOT, "scripts", "serve.py"), tmp, str(PORT + 1), first],
                            env=dict(env, CHROME_BIN=fake, SLAIDY_CHROME=""),
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        # wait until it answers, rather than a fixed pause a slow machine overruns
        for _ in range(50):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/api/deck" % (PORT + 1), timeout=2); break
            except Exception:
                time.sleep(0.2)
        r = urllib.request.Request("http://127.0.0.1:%d/api/pdf" % (PORT + 1), data=page, method="POST",
                                   headers={"Content-Type": "text/html", "Origin": "http://localhost:%d" % (PORT + 1)})
        try:
            urllib.request.urlopen(r, timeout=30); st, j = 200, {}
        except urllib.error.HTTPError as e:
            st, j = e.code, json.load(e)
        check("a browser that fails is a 500 that says why",
              st == 500 and "the fake browser broke" in j.get("error", ""), "%s %s" % (st, j))
    finally:
        srv2.terminate()
    err = srv2.stderr.read().decode()
    check("and the terminal says so too", "pdf failed" in err and "fake browser broke" in err, err[-200:])

finally:
    srv.terminate()
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("all good" if not bad else "%d failed" % bad)
sys.exit(1 if bad else 0)
