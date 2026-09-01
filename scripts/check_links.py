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
import json, re, ssl, sys, time, urllib.error, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) slaidy-link-check"
CTX = ssl.create_default_context()


LAST = {}


def get(url, accept=None, timeout=30, tries=2):
    """(status, body). status 0 means nobody answered — which is not the same
    as an answer of "no such thing", and the difference is the whole point of
    this script. arXiv rate-limits, and a checker that reads a throttled reply
    as a dead paper reports twenty dead references that are all fine."""
    host = url.split("/")[2]
    for attempt in range(tries):
        gap = 1.2 - (time.time() - LAST.get(host, 0))   # one host, one at a time
        if gap > 0:
            time.sleep(gap)
        LAST[host] = time.time()
        r = urllib.request.Request(url, headers={"User-Agent": UA,
                                                 **({"Accept": accept} if accept else {})})
        try:
            with urllib.request.urlopen(r, timeout=timeout, context=CTX) as f:
                body = f.read(400000)
                if body or f.status != 200:
                    return f.status, body
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception as e:
            if attempt + 1 == tries:
                return 0, str(e).encode()
        time.sleep(3)
    return 0, b"no answer"


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
    """(state, what) — ok, dead (the host said no such thing), or ?? (it would
    not say). Only a real "no" counts as dead."""
    # doi.org, and the publishers whose own pages refuse scripts but whose URL
    # carries the DOI anyway — ask the registry rather than the bot wall
    m = re.search(r"(?:doi\.org|dl\.acm\.org/doi(?:/[a-z]+)?|"
                  r"ieeexplore\.ieee\.org/document)/(10\.\d{4,9}/[^\s?#]+)", url)
    if m:
        code, body = get("https://doi.org/" + m.group(1),
                         "application/vnd.citationstyles.csl+json")
        if code == 404:
            return "dead", "no such DOI — doi.org does not know it"
        if not body.lstrip().startswith(b"{"):
            return "??", "doi.org answered %s, not a record" % (code or "nothing")
        j = json.loads(body)
        who = ", ".join((a.get("family") or a.get("literal", "")) for a in j.get("author", [])[:3])
        year = (j.get("issued", {}).get("date-parts") or [[None]])[0][0]
        title = j.get("title")
        if isinstance(title, list):
            title = title[0] if title else ""
        return "ok", "%s — %s, %s" % (title, who or "?", year or "?")

    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9.]+v?\d*)", url)
    if m:
        # the abs page, not the API: the API throttles hard and answers a burst
        # with silence, which is indistinguishable from a missing paper
        code, body = get("https://arxiv.org/abs/" + m.group(1))
        if code in (404, 410):
            return "dead", "no such arXiv id"
        t = re.search(r"<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace"), re.S)
        if code == 200 and t:
            return "ok", re.sub(r"^\[[\d.v]+\]\s*", "", " ".join(t.group(1).split()))
        return "??", "arXiv answered %s" % (code or "nothing")

    code, body = get(url)
    if code in (200, 201):
        t = re.search(r"<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace"), re.S)
        return "ok", " ".join(t.group(1).split())[:90] if t else "(no title)"
    if code in (404, 410):
        return "dead", "HTTP %d" % code
    # a publisher refusing a script, or a server that would not answer, is not
    # evidence that the link is broken
    return "??", ("HTTP %d — check it in a browser" % code if code
                  else body.decode("utf-8", "replace")[:70])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip())
    deck = json.load(open(sys.argv[1], encoding="utf-8"))
    found = links(deck)
    print("%s — %d slides, %d distinct links\n" % (deck.get("title", "deck"),
                                                   len(deck.get("slides", [])), len(found)))
    bad, unsure = [], []
    for url in sorted(found):
        e = found[url]
        state, what = describe(url)
        mark = {"ok": "  ok  ", "??": "  ??  ", "dead": " DEAD "}[state]
        where = ",".join(str(n) for n in sorted(x for x in e["slides"] if x is not None))
        print("%s %s" % (mark, url))
        print("       %s   ·   slide %s" % (" / ".join(sorted(e["labels"])), where))
        print("       %s" % what)
        if state == "dead":
            bad.append(url)
        elif state == "??":
            unsure.append(url)
    print()
    if unsure:
        print("%d could not be checked from a script — open them yourself:" % len(unsure))
        for u in unsure:
            print("  " + u)
        print()
    if bad:
        print("%d dead:" % len(bad))
        for u in bad:
            print("  " + u)
        sys.exit(1)
    print("nothing is dead. Read the titles above against the labels — a link that")
    print("works and cites the wrong paper is the one that bites in the room.")


if __name__ == "__main__":
    main()
