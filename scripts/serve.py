#!/usr/bin/env python3
r"""Serve Slide Studio, and give it an AI endpoint.

Without this the app falls back to POSTing /api/generate, a plain file server
answers with index.html, and the browser reports a JSON parse error that says
nothing useful. Here that route is real: it forwards to OpenAI using the key
from the environment, so the key stays on this machine and never reaches the page.

    OPENAI_KEY=sk-... .venv/bin/python scripts/serve.py <dir> <port>

Env: OPENAI_KEY (or OPENAI_API_KEY), OPENAI_BASE_URL, STUDIO_MODEL (default gpt-5.6-sol)
"""
import json, os, sys, urllib.error, urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial

BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
KEY = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("STUDIO_MODEL") or os.environ.get("FIGURE_MODEL") or "gpt-5.6-sol"


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a):
        if "/api/" in (self.path or ""):
            sys.stderr.write("  ai: %s\n" % (fmt % a))

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

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
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    print("  AI: " + (f"on, {MODEL} via {BASE}" if KEY
                      else "off — no OPENAI_KEY, so the AI panels will say so plainly"),
          flush=True)   # stdout is a pipe when started detached; without this it is never seen
    ThreadingHTTPServer(("", port), partial(Handler, directory=root)).serve_forever()


if __name__ == "__main__":
    main()
