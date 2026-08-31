#!/usr/bin/env python3
r"""Serve Slide Studio, and give it an AI endpoint.

Without this the app falls back to POSTing /api/generate, a plain file server
answers with index.html, and the browser reports a JSON parse error that says
nothing useful. Here that route is real: it forwards to OpenAI using the key
from the environment, so the key stays on this machine and never reaches the page.

    OPENAI_KEY=sk-... .venv/bin/python scripts/serve.py <dir> <port>

A local model is a first-class case: point OPENAI_BASE_URL at Ollama, LM Studio,
llama.cpp or vLLM and no key is needed, because there is nobody to authenticate to.
Then nothing leaves the machine — the deck, the figures and the prompts all stay here.

    OPENAI_BASE_URL=http://localhost:11434/v1 STUDIO_MODEL=qwen3:14b \
        .venv/bin/python scripts/serve.py <dir> <port>

Env: OPENAI_KEY (or OPENAI_API_KEY), OPENAI_BASE_URL, STUDIO_MODEL (default gpt-5.6-sol)
"""
import json, os, random, shutil, sys, tempfile, time, urllib.error, urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial

BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
KEY = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY")
# A model on this machine has nobody to authenticate to, so a missing key is
# the normal state rather than a misconfiguration. Ollama and llama.cpp ignore
# the header entirely; LM Studio and vLLM accept anything.
LOCAL = any(h in BASE for h in ("://localhost", "://127.0.0.1", "://[::1]", "://0.0.0.0",
                                "://host.docker.internal"))
MODEL = os.environ.get("STUDIO_MODEL") or os.environ.get("FIGURE_MODEL") or "gpt-5.6-sol"
# e-INFRA caps concurrent calls; going past it earns a 429 rather than a queue
MAXPAR = int(os.environ.get("STUDIO_MAX_CONCURRENCY") or ("4" if "e-infra" in BASE else "0") or 0)
GATE = __import__("threading").Semaphore(MAXPAR) if MAXPAR else None

# Models that spend most of their budget thinking before they say anything.
# Learned the expensive way on CESNET's qwen3.5: it answers with
# `content: null`, `reasoning_content` full, and `finish_reason: "length"` —
# the thinking consumed the whole allowance before a visible word was produced,
# and every caller saw an empty completion that looked like an outage.
REASONERS = ("qwen3", "deepseek-r1", "o1", "o3", "o4-mini", "gpt-5")
# reasoning cost scales with the INPUT, not with how long an answer you asked
# for, so a multiplier alone is the wrong instrument — the floor is what makes
# small requests survivable.
THINK_FLOOR, THINK_MULT, THINK_CEIL = 4000, 8, 32000


def budget(model, asked):
    asked = int(asked or 4000)
    if any(m in (model or "").lower() for m in REASONERS):
        return min(THINK_CEIL, max(THINK_FLOOR, asked * THINK_MULT))
    return asked

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
            # a deck is a megabyte or two; anything near a hundred is not one, and
            # reading it into memory on request is how a local server falls over
            if n > 256 * 1024 * 1024:
                return self._json(413, {"error": "that is far too large to be a deck"})
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
        # the proxy exists to keep the key off the page; it is not an open relay
        if self.headers.get("Origin") and self.headers.get("Origin") not in (
                "http://localhost:%d" % self.server.server_address[1],
                "http://127.0.0.1:%d" % self.server.server_address[1]):
            return self._json(403, {"error": "this endpoint only answers the page it serves"})
        if not KEY and not LOCAL:
            return self._json(503, {"error":
                "No OPENAI_KEY on the machine running studio.sh. Put one in .env, or point "
                "OPENAI_BASE_URL at a model running on this machine — Ollama, LM Studio, "
                "llama.cpp and vLLM all need no key. See .env.example."})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._json(400, {"error": "could not read the request: %s" % e})

        model = req.get("model") or MODEL
        # OpenAI renamed the field; everyone else still wants max_tokens, and a
        # gateway that does not know the new name simply ignores the limit
        cap = "max_completion_tokens" if "api.openai.com" in BASE else "max_tokens"
        body = json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": req.get("system", "")},
                         {"role": "user", "content": req.get("user", "")}],
            cap: budget(model, req.get("maxTok")),
        }).encode()
        headers = {"Content-Type": "application/json"}
        if KEY:
            headers["Authorization"] = "Bearer " + KEY

        # e-INFRA is shared and not always there, and its failures are mostly the
        # passing kind: a 429 from the cap, a 5xx, or a body with choices: null.
        # Retried here so one person waits a few seconds rather than pressing the
        # button again. A refusal is not retried — a 400 will be a 400 again.
        last = "unknown"
        for attempt in range(3):
            if attempt:
                time.sleep(0.7 * (2 ** (attempt - 1)) + random.random() * 0.4)
            r = urllib.request.Request(BASE + "/chat/completions", data=body, headers=headers)
            try:
                if GATE:
                    GATE.acquire()
                try:
                    with urllib.request.urlopen(r, timeout=600) as resp:
                        d = json.loads(resp.read().decode())
                finally:
                    if GATE:
                        GATE.release()
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:400]
                try:
                    detail = json.loads(detail)["error"]["message"]
                except Exception:
                    pass
                if e.code < 500 and e.code != 429:
                    return self._json(502, {"error": "%s says: %s" % (BASE, detail)})
                last = "%s says: %s" % (BASE, detail)
                continue
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, e)
                continue

            # `choices` is not guaranteed to be there: under load the e-INFRA
            # gateway answers with choices: null instead of an HTTP error, and
            # indexing that gives a TypeError several layers away from the cause
            choices = d.get("choices") or []
            if not choices:
                last = "the model returned no choices"
                continue
            msg = choices[0].get("message") or {}
            text = msg.get("content")
            if not text and msg.get("reasoning_content"):
                return self._json(502, {"error": "the model spent its whole budget thinking and "
                                                 "never wrote an answer — ask for less, or raise "
                                                 "STUDIO_MAX_TOKENS"})
            # pass the token counts through: the app cannot know what a call cost
            # unless the endpoint says, and a usage panel that guesses is worthless
            return self._json(200, {"text": text or "",
                                    "usage": d.get("usage") or {},
                                    "model": d.get("model") or model,
                                    "attempts": attempt + 1})

        return self._json(502, {"error": "%s — tried 3 times over a few seconds. The endpoint is "
                                         "not always there; give it a moment." % last})

def main():
    global DECK
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    if len(sys.argv) > 3 and sys.argv[3]:
        DECK = os.path.abspath(sys.argv[3])
    print("  AI: " + (f"on, {MODEL} via {BASE}" + (f", {MAXPAR} at a time" if MAXPAR else "")
                      + (" — nothing leaves this machine" if LOCAL else "") if (KEY or LOCAL)
                      else "off — no key and no local model, so the AI panels will say so plainly"),
          flush=True)   # stdout is a pipe when started detached; without this it is never seen
    if DECK:
        print("  deck: %s  (the app saves straight to it)" % os.path.relpath(DECK, os.getcwd()),
              flush=True)
    # 127.0.0.1, not every interface: this now writes a file on request, and
    # that is not something to offer the local network.
    ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=root)).serve_forever()


if __name__ == "__main__":
    main()
