#!/usr/bin/env python3
"""Check every link in a deck.

    scripts/check_links.py ../keynote/decks/kordik-keynote.json

A talk with citations in it has a failure mode of its own: the link is there,
it looks right, and it 404s in front of the room. This resolves every one of
them and says what it actually points at, so a wrong digit in a DOI shows up
as a wrong title rather than as a dead link on the projector.

DOIs are asked of doi.org itself, in CSL JSON — that answers with the
registered title and author, and never with a publisher's bot wall. arXiv is
asked of the arXiv API for the same reason. Everything else is fetched.

Exit code is 1 if anything is genuinely dead.
"""
import json, re, ssl, sys, urllib.error, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) slaidy-link-check"
CTX = ssl.create_default_context()


def get(url, accept=None, timeout=30):
    r = urllib.request.Request(url, headers={"User-Agent": UA,
                                             **({"Accept": accept} if accept else {})})
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=CTX) as f:
            return f.status, f.read(400000)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()


def links(deck):
    """Every [label](url) in the deck, with the slides it appears on."""
    out = {}
    for s in deck.get("slides", []):
        text = "\n".join(str(s.get(k) or "") for k in ("body", "notes", "summary", "title"))
        for lab, url in re.findall(r"\[([^\]\[]{1,160})\]\((https?://[^)\s]+)\)", text):
            e = out.setdefault(url, {"labels": set(), "slides": set()})
            e["labels"].add(lab.strip())
            e["slides"].add(s.get("n"))
    return out


def describe(url):
    """(state, what) — state is ok / dead / blocked."""
    m = re.search(r"doi\.org/(10\.[^\s?#]+)", url)
    if m:
        code, body = get("https://doi.org/" + m.group(1),
                         "application/vnd.citationstyles.csl+json")
        if code == 404 or not body.lstrip().startswith(b"{"):
            return "dead", "no such DOI"
        j = json.loads(body)
        who = ", ".join((a.get("family") or a.get("literal", "")) for a in j.get("author", [])[:3])
        year = (j.get("issued", {}).get("date-parts") or [[None]])[0][0]
        title = j.get("title")
        if isinstance(title, list):
            title = title[0] if title else ""
        return "ok", "%s — %s, %s" % (title, who or "?", year or "?")

    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9.]+v?\d*)", url)
    if m:
        code, body = get("https://export.arxiv.org/api/query?max_results=1&id_list="
                         + m.group(1))
        t = re.findall(r"<title>(.*?)</title>", body.decode("utf-8", "replace"), re.S)
        if len(t) < 2:
            return "dead", "no such arXiv id"
        return "ok", " ".join(t[1].split())

    code, body = get(url)
    if code in (200, 201):
        t = re.search(r"<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace"), re.S)
        return "ok", " ".join(t.group(1).split())[:90] if t else "(no title)"
    if code in (401, 202, 403, 429, 503):
        # a publisher refusing a script is not a broken link
        return "blocked", "HTTP %d — refuses scripts, check it in a browser" % code
    return "dead", "HTTP %d" % code if code else body.decode("utf-8", "replace")[:70]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip())
    deck = json.load(open(sys.argv[1], encoding="utf-8"))
    found = links(deck)
    print("%s — %d slides, %d distinct links\n" % (deck.get("title", "deck"),
                                                   len(deck.get("slides", [])), len(found)))
    bad = []
    for url in sorted(found):
        e = found[url]
        state, what = describe(url)
        mark = {"ok": "  ok  ", "blocked": "  ??  ", "dead": " DEAD "}[state]
        where = ",".join(str(n) for n in sorted(x for x in e["slides"] if x is not None))
        print("%s %s" % (mark, url))
        print("       %s   ·   slide %s" % (" / ".join(sorted(e["labels"])), where))
        print("       %s" % what)
        if state == "dead":
            bad.append(url)
    print()
    if bad:
        print("%d dead:" % len(bad))
        for u in bad:
            print("  " + u)
        sys.exit(1)
    print("every link resolves. Read the titles above against the labels — a link")
    print("that works and cites the wrong paper is the one that bites in the room.")


if __name__ == "__main__":
    main()
