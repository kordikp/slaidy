#!/usr/bin/env python3
"""The commented deck: every slide as it projects, with a reading of it beside.

    scripts/commentary.py site/<name>/deck.json commentary.md slides_dir site/<name>

Writes site/<name>/commentary/index.html and copies slides_dir/slide-N.png to
site/<name>/slides/. The commentary is markdown with one "## N. Title" block per
slide and, inside it, "### What the slide says", "### The argument",
"### Evidence and further reading", "### If short on time"; a closing
"## Sources" block is carried over whole. The speaker's own note comes from the
deck. Links are the only markdown that matters here, so the converter is small
and does exactly that much."""
import html, json, os, re, shutil, sys

CSS = """
:root{--ink:#1E1B4B;--gray:#6B7280;--line:#E5E7EB;--paper:#FFFFFF;--acc:#7C3AED;--accbg:#EDE9FE;--soft:#FAFAF7}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:40px 28px 80px}
h1{font-size:30px;line-height:1.15;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--gray);margin:0 0 28px}
.sub a{color:var(--acc);text-decoration:none}
.toc{columns:2;column-gap:28px;font-size:14px;margin:0 0 36px;padding:16px 20px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}
.toc a{color:var(--ink);text-decoration:none;display:block;padding:2px 0;break-inside:avoid}
.toc a:hover{color:var(--acc)}
.toc .g{font:650 10.5px/1.2 system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--gray);margin:8px 0 4px;break-inside:avoid}
.sec{font:650 11px/1.2 system-ui;letter-spacing:.14em;text-transform:uppercase;color:var(--gray);margin:56px 0 12px;padding-top:24px;border-top:1px solid var(--line)}
.slide{margin:0 0 44px;scroll-margin-top:16px}
.slide h2{font-size:21px;line-height:1.25;margin:0 0 12px;letter-spacing:-.01em}
.slide h2 .n{color:var(--gray);font-weight:500;font-family:ui-monospace,SFMono-Regular,monospace;font-size:13px;margin-right:10px;vertical-align:2px}
.shot{display:block;width:100%;border:1px solid var(--line);border-radius:8px;box-shadow:0 1px 3px rgba(30,27,75,.06);margin:0 0 16px;background:#111}
.slide h3{font:650 11px/1.2 system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--gray);margin:18px 0 6px}
.slide p{margin:0 0 10px;max-width:72ch}
.slide ul{margin:0 0 10px;padding-left:20px;max-width:80ch}
.slide li{margin:0 0 5px}
.slide a{color:var(--acc);text-decoration:none;border-bottom:1px solid var(--accbg)}
.slide a:hover{border-bottom-color:var(--acc)}
.slide code{font:.88em ui-monospace,SFMono-Regular,monospace;background:#F1F2F5;padding:1px 5px;border-radius:4px}
.note{border-left:4px solid var(--acc);background:var(--soft);padding:10px 14px;margin:14px 0 4px;color:#3F3A6B;max-width:76ch;border-radius:0 6px 6px 0}
.note b{font:650 10.5px/1.2 system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--gray);display:block;margin-bottom:4px}
.sources{margin-top:60px;padding-top:24px;border-top:1px solid var(--line)}
.sources h2{font-size:21px;margin:0 0 12px}
.sources ul{padding-left:20px;max-width:90ch}
.sources li{margin:0 0 6px}
.sources a{color:var(--acc);text-decoration:none}
@media print{.shot{break-inside:avoid}.slide{break-inside:avoid-page}.toc{display:none}body{font-size:12px}.wrap{max-width:none;padding:0}}
@media (max-width:640px){.toc{columns:1}.wrap{padding:24px 16px 60px}}
"""

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", t)
    return t

def block_html(md):
    """paragraphs, bullet lists and ### headings — nothing else is used"""
    out, para, lst = [], [], []
    def flush():
        nonlocal para, lst
        if para: out.append("<p>%s</p>" % inline(" ".join(para))); para = []
        if lst: out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(x) for x in lst)); lst = []
    for line in md.split("\n"):
        s = line.rstrip()
        if not s.strip(): flush(); continue
        if s.startswith("### "): flush(); out.append("<h3>%s</h3>" % inline(s[4:].strip())); continue
        if re.match(r"^\s*[-•]\s+", s):
            if para: flush()
            lst.append(re.sub(r"^\s*[-•]\s+", "", s)); continue
        if lst: flush()
        para.append(s.strip())
    flush()
    return "\n".join(out)

def main():
    deck_p, md_p, shots, out_dir = sys.argv[1:5]
    deck = json.load(open(deck_p, encoding="utf-8"))
    md = open(md_p, encoding="utf-8").read()
    blocks = re.split(r"(?m)^## ", md)
    per, sources = {}, ""
    for b in blocks[1:]:
        head, _, body = b.partition("\n")
        m = re.match(r"(\d+)\.\s+(.*)$", head.strip())
        if m: per[int(m.group(1))] = (m.group(2).strip(), body)
        elif head.strip().lower().startswith("sources"): sources = body
    os.makedirs(os.path.join(out_dir, "commentary"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "slides"), exist_ok=True)
    title = deck.get("title", "Deck")
    toc, body_html, group = [], [], None
    missing = []
    for s in deck["slides"]:
        n = s["n"]
        if s.get("group") != group:
            group = s.get("group") or ""
            toc.append('<div class="g">%s</div>' % html.escape(group))
            body_html.append('<div class="sec">%s</div>' % html.escape(group))
        src = os.path.join(shots, "slide-%d.png" % n)
        if os.path.isfile(src): shutil.copyfile(src, os.path.join(out_dir, "slides", "slide-%d.png" % n))
        toc.append('<a href="#s%d">%s</a>' % (n, html.escape("%d · %s" % (n, s["title"]))))
        txt = per.get(n)
        if not txt: missing.append(n)
        parts = ['<section class="slide" id="s%d"><h2><span class="n">%03d</span>%s</h2>' % (n, n, html.escape(s["title"])),
                 '<img class="shot" src="../slides/slide-%d.png" alt="%s" loading="lazy">' % (n, html.escape("Slide %d: %s" % (n, s["title"])))]
        if txt:
            body_md, _, take = txt[1].partition("### Takeaway")
            parts.append(block_html(body_md))
            if take.strip():
                parts.append('<div class="note"><b>Takeaway</b>%s</div>' % inline(" ".join(l.strip() for l in take.strip().split("\n") if l.strip())))
        parts.append("</section>")
        body_html.append("\n".join(parts))
    page = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s · the deck, read</title><style>%s</style></head><body><div class=\"wrap\">"
            "<h1>%s</h1><p class=\"sub\">%d slides, read slide by slide — what each shows, the concepts behind it, the evidence, and one thing to take away · <a href=\"../\">the deck</a> · <a href=\"../#present\">present it</a></p>"
            "<nav class=\"toc\">%s</nav>%s%s</div></body></html>") % (
        html.escape(title), CSS, html.escape(title), len(deck["slides"]), "\n".join(toc), "\n".join(body_html),
        ('<div class="sources"><h2>Sources</h2>%s</div>' % block_html(sources)) if sources else "")
    p = os.path.join(out_dir, "commentary", "index.html")
    open(p, "w", encoding="utf-8").write(page)
    print("%s — %d slides commented, %d KB%s" % (p, len(per), len(page)//1024, ("; NO COMMENTARY for slides %s" % missing) if missing else ""))
    if missing: sys.exit(1)

if __name__ == "__main__":
    main()
