#!/usr/bin/env python3
r"""Serve Slide Studio, and give it an AI endpoint.

Without this the app falls back to POSTing /api/generate, a plain file server
answers with index.html, and the browser reports a JSON parse error that says
nothing useful. Here that route is real: it forwards to OpenAI using the key
from the environment, so the key stays on this machine and never reaches the page.

    OPENAI_KEY=sk-... .venv/bin/python scripts/serve.py <dir> <port>

Env: OPENAI_KEY (or OPENAI_API_KEY), OPENAI_BASE_URL, STUDIO_MODEL (default gpt-5.6-sol)
"""
import json, os, shutil, sys, tempfile, urllib.error, urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial

BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
KEY = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("STUDIO_MODEL") or os.environ.get("FIGURE_MODEL") or "gpt-5.6-sol"

# The real deck on disk. The app saves straight to it, so there is no second
# copy to disagree with it and nothing to re-permission after a restart.
DECK = None


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a):
        if "/api/generate" in (self.path or ""):
            sys.stderr.write("  ai: %s\n" % (fmt % a))

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    # ---- the deck file itself -------------------------------------------
    # GET /deck.json streams the real file rather than a copy, so its
    # Last-Modified is the truth. Copying it into a temp directory used to
    # stamp it with the current time, which made every restart look like the
    # file had just changed — and the "your unsaved edits are newer" rescue
    # could then never fire.
    def do_GET(self):
        if DECK and self.path.split("?")[0].rstrip("/") in ("/deck.json", "/api/deck"):
            if self.path.split("?")[0].rstrip("/") == "/api/deck":
                st = os.stat(DECK) if os.path.exists(DECK) else None
                return self._json(200, {
                    "path": os.path.relpath(DECK, os.getcwd()), "abs": DECK,
                    "writable": os.access(os.path.dirname(DECK) or ".", os.W_OK),
                    "mtime": int(st.st_mtime * 1000) if st else 0,
                    "size": st.st_size if st else 0})
            try:
                with open(DECK, "rb") as f:
                    b = f.read()
            except OSError as e:
                return self._json(404, {"error": str(e)})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Last-Modified", self.date_time_string(os.stat(DECK).st_mtime))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)
            return
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_HEAD(self):
        # a HEAD has its own handler in the base class, so it would otherwise
        # 404 on the very path GET serves
        if DECK and self.path.split("?")[0].rstrip("/") in ("/deck.json", "/api/deck"):
            return self.do_GET()
        return SimpleHTTPRequestHandler.do_HEAD(self)

    def do_PUT(self):
        if not DECK or self.path.rstrip("/") != "/api/deck":
            return self._json(404, {"error": "no such endpoint"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n)
            d = json.loads(raw or b"{}")
            if not isinstance(d.get("slides"), list) or not d["slides"]:
                raise ValueError("that is not a deck — no slides in it")
        except Exception as e:
            return self._json(400, {"error": "refused: %s" % e})

        # If the client tells us which version it started from and the file has
        # moved since, something else wrote it — another tab, or a script. Say
        # so instead of overwriting; losing work silently is the one outcome
        # worth failing a save over.
        seen = self.headers.get("X-Deck-Mtime")
        if seen and os.path.exists(DECK):
            now = int(os.stat(DECK).st_mtime * 1000)
            if abs(now - int(seen)) > 1000:
                return self._json(409, {
                    "error": "%s changed on disk since this deck was loaded" % os.path.basename(DECK),
                    "mtime": now})

        # write beside the target and rename, so a failure half way through
        # cannot leave a truncated deck where the real one was
        try:
            dirn = os.path.dirname(DECK) or "."
            fd, tmp = tempfile.mkstemp(dir=dirn, prefix=".deck-", suffix=".tmp")
            with os.fdopen(fd, "wb") as f:
                f.write(raw)
            os.replace(tmp, DECK)
        except Exception as e:
            try: os.unlink(tmp)
            except Exception: pass
            return self._json(500, {"error": "could not write %s: %s" % (DECK, e)})
        sys.stderr.write("  saved %s  (%d slides, %.1f MB)\n"
                         % (os.path.relpath(DECK, os.getcwd()), len(d["slides"]), len(raw) / 1e6))
        sys.stderr.flush()
        return self._json(200, {"ok": True, "mtime": int(os.stat(DECK).st_mtime * 1000)})

    def do_POST(self):
        if self.path.rstrip("/") != "/api/generate":
            return self._json(404, {"error": "no such endpoint"})
        if not KEY:
            return self._json(503, {"error":
                "No OPENAI_KEY on the machine running studio.sh. Either export it and restart, "
                "or set an endpoint yourself under ⋯ → AI endpoint."})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._json(400, {"error": "could not read the request: %s" % e})

        body = json.dumps({
            "model": req.get("model") or MODEL,
            "messages": [{"role": "system", "content": req.get("system", "")},
                         {"role": "user", "content": req.get("user", "")}],
            "max_completion_tokens": int(req.get("maxTok") or 4000),
        }).encode()
        r = urllib.request.Request(
            BASE + "/chat/completions", data=body,
            headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=600) as resp:
                d = json.loads(resp.read().decode())
            return self._json(200, {"text": d["choices"][0]["message"]["content"]})
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:400]
            try:
                detail = json.loads(detail)["error"]["message"]
            except Exception:
                pass
            return self._json(502, {"error": "%s says: %s" % (BASE, detail)})
        except Exception as e:
            return self._json(502, {"error": "%s: %s" % (type(e).__name__, e)})


def main():
    global DECK
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    if len(sys.argv) > 3 and sys.argv[3]:
        DECK = os.path.abspath(sys.argv[3])
    print("  AI: " + (f"on, {MODEL} via {BASE}" if KEY
                      else "off — no OPENAI_KEY, so the AI panels will say so plainly"),
          flush=True)   # stdout is a pipe when started detached; without this it is never seen
    if DECK:
        print("  deck: %s  (the app saves straight to it)" % os.path.relpath(DECK, os.getcwd()),
              flush=True)
    # 127.0.0.1, not every interface: this now writes a file on request, and
    # that is not something to offer the local network.
    ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=root)).serve_forever()


if __name__ == "__main__":
    main()
