#!/usr/bin/env python3
"""The theme library: themes/<name>/ in, one self-contained CSS per theme out.

    python3 scripts/themes.py                 # → themes/index.json, themes/<name>.css, themes/<name>/deck.json
    python3 scripts/themes.py --out _site/themes
    python3 scripts/themes.py --check         # only say what is wrong, write nothing

A theme is a folder: theme.css (every rule for html[data-slaidy-theme="<name>"]),
theme.json (label, description, author, licence, and the deck style it sets),
the fonts and pictures the CSS points to by relative url(), and a licence for
every font. The build turns each url() into a data: URI, because a deck carries
its theme inside it and a deck fetches nothing. It writes the list the editor
offers (index.json) and, for each theme, the sample deck in that theme, which
the site publishes at themes/<name>/.

What the editor keeps of a theme is decided in the app (themeSafe in
slaidy.html), and tests/37-themes.html loads every theme built here through it:
a rule it would leave out fails the suite. The checks below are the ones that
need the folder: names, files, licences, size.
"""
import base64, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "themes")
SAMPLE = os.path.join(SRC, "sample.json")
MIME = {".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf",
        ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".gif": "image/gif"}
FONTS = {".woff2", ".woff", ".ttf", ".otf"}
NAME = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
STYLE_KEYS = {"accent", "ink", "paper", "titleSize", "bodySize", "header"}
LIMIT = 900 * 1024            # a theme rides in every deck that uses it


def themes():
    return sorted(d for d in os.listdir(SRC)
                  if os.path.isdir(os.path.join(SRC, d)) and os.path.exists(os.path.join(SRC, d, "theme.css")))


def build(name):
    """(css with every url() inlined, theme.json, problems)"""
    d, bad = os.path.join(SRC, name), []
    if not NAME.match(name):
        bad.append("the folder name must be lower case letters, digits and dashes")
    try:
        meta = json.load(open(os.path.join(d, "theme.json"), encoding="utf-8"))
    except (OSError, ValueError) as e:
        return "", {}, [f"theme.json: {e}"]
    if meta.get("name") != name:
        bad.append(f'theme.json says "name": {meta.get("name")!r}, the folder is {name!r}')
    for k in ("label", "description", "author", "licence"):
        if not str(meta.get(k) or "").strip():
            bad.append(f"theme.json has no {k}")
    st = meta.get("style") or {}
    if set(st) - STYLE_KEYS:
        bad.append(f"theme.json style knows only {sorted(STYLE_KEYS)}, not {sorted(set(st) - STYLE_KEYS)}")
    for k in ("accent", "ink", "paper"):
        if not re.match(r"^#[0-9a-fA-F]{6}$", str(st.get(k, ""))):
            bad.append(f"theme.json style.{k} must be a colour like #1E1B4B")
    css = open(os.path.join(d, "theme.css"), encoding="utf-8").read()
    if f'html[data-slaidy-theme="{name}"]' not in css:
        bad.append(f'theme.css has no rule for html[data-slaidy-theme="{name}"]')
    others = sorted(set(re.findall(r'data-slaidy-theme="([^"]*)"', css)) - {name})
    if others:
        bad.append(f"theme.css styles other themes too: {others}")
    fonts = False

    def inline(m):
        nonlocal fonts
        ref = m.group(1).strip("'\" ")
        if ref.startswith("data:"):
            return m.group(0)
        if re.match(r"^[a-z]+:|^/|\.\.", ref):
            bad.append(f"url({ref}): only files in the theme's own folder")
            return m.group(0)
        p = os.path.join(d, ref)
        ext = os.path.splitext(ref)[1].lower()
        if not os.path.isfile(p):
            bad.append(f"url({ref}): no such file")
            return m.group(0)
        if ext not in MIME:
            bad.append(f"url({ref}): not a font or a picture ({', '.join(sorted(MIME))})")
            return m.group(0)
        fonts = fonts or ext in FONTS
        return f"url(data:{MIME[ext]};base64,{base64.b64encode(open(p, 'rb').read()).decode('ascii')})"

    out = re.sub(r"url\(([^)]*)\)", inline, css)
    if fonts and not any(re.match(r"(OFL|LICEN[CS]E)", f, re.I) for _, _, fs in os.walk(d) for f in fs):
        bad.append("fonts without a licence: put OFL.txt (or LICENSE) next to them")
    if re.search(r"@import", out):
        bad.append("@import: a theme brings everything it needs inside its own CSS")
    if len(out.encode("utf-8")) > LIMIT:
        bad.append(f"{len(out.encode('utf-8')) // 1024} kB built — keep a theme under {LIMIT // 1024} kB "
                   "(fewer font weights, latin subsets, smaller pictures)")
    return out, meta, bad


def main(argv):
    check = "--check" in argv
    out = argv[argv.index("--out") + 1] if "--out" in argv else SRC
    sample = json.load(open(SAMPLE, encoding="utf-8"))
    index, failed = [], 0
    for name in themes():
        css, meta, bad = build(name)
        for b in bad:
            print(f"FAIL themes/{name}: {b}")
        failed += bool(bad)
        if bad:
            continue
        if check:
            print(f"ok  themes/{name}  {len(css.encode('utf-8')) // 1024} kB")
            continue
        os.makedirs(os.path.join(out, name), exist_ok=True)
        open(os.path.join(out, name + ".css"), "w", encoding="utf-8").write(css)
        deck = dict(sample, id="theme-" + name, title=f"{meta['label']} — a SlAIdy theme",
                    style=dict(meta.get("style") or {}, theme=name), themeCss=css)
        deck["meta"] = dict(sample.get("meta") or {}, theme=meta["label"])
        json.dump(deck, open(os.path.join(out, name, "deck.json"), "w", encoding="utf-8"), ensure_ascii=False)
        preview = os.path.exists(os.path.join(SRC, name, "preview.png"))
        if preview and os.path.abspath(out) != os.path.abspath(SRC):
            import shutil
            shutil.copy(os.path.join(SRC, name, "preview.png"), os.path.join(out, name, "preview.png"))
        index.append({k: meta[k] for k in ("name", "label", "description", "author", "licence")} |
                     {"style": meta.get("style") or {}, "css": name + ".css", "sample": name + "/",
                      **({"preview": name + "/preview.png"} if preview else {})})
        print(f"themes/{name}  {len(css.encode('utf-8')) // 1024} kB")
    if not check:
        json.dump({"themes": index}, open(os.path.join(out, "index.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
