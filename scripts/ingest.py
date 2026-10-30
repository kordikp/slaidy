#!/usr/bin/env python3
"""A presentation to convert, laid out for whoever converts it.

    python3 scripts/ingest.py talk.pptx sources/          PowerPoint (.ppt, .odp, .key go through LibreOffice)
    python3 scripts/ingest.py talk.pdf sources/           a PDF, one page a slide
    python3 scripts/ingest.py talk.pptx sources/ --no-render
    python3 scripts/ingest.py --missing sources/ decks/talk.json

It writes into the folder:

  inventory.md    every slide: its title, its text in reading order, its tables, the numbers
                  behind its charts, its pictures with their sizes and alt text, how much of it is
                  drawn with shapes, and its speaker notes. This is what a model reads instead of
                  the file: a few kB a slide where the XML is a hundred.
  inventory.json  the same, for a script
  render/s01.png  each slide as it looks, 1000 px wide, to look at once (LibreOffice turns a .pptx
                  into a PDF, poppler's pdftoppm draws the pages)
  media/s01-1.png the pictures of each slide, as they are in the file

`--missing` reads the inventory against a finished deck and lists, slide by slide, the numbers
of the original that appear nowhere in the deck: its text, its notes or its figures. A number
that was dropped on purpose is fine; one dropped by accident is a fact lost.

docs/CONVERT.md is the procedure this is the first step of. Nothing here needs more than the
standard library; Pillow, if present, adds the pixel sizes of the pictures.
"""
import hashlib, io, json, os, posixpath, re, shutil, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}
Q = lambda tag: "{%s}%s" % (NS[tag.split(":")[0]], tag.split(":")[1])
MAX_PART = 30_000_000          # an XML part or a picture larger than this is not read
SKIP_PH = {"dt", "ftr", "sldNum", "hdr", "sldImg"}
RENDER_W = 1000


def tool(name):
    return shutil.which(name)


def run(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


class Media:
    """The pictures, written once each: a logo on every slide is one file, said to repeat."""
    def __init__(self, out):
        self.dir = os.path.join(out, "media")
        os.makedirs(self.dir, exist_ok=True)
        self.seen = {}

    def put(self, data, name):
        h = hashlib.sha1(data).hexdigest()
        if h in self.seen:
            return self.seen[h], True
        with open(os.path.join(self.dir, name), "wb") as f:
            f.write(data)
        self.seen[h] = "media/" + name
        return self.seen[h], False


# ---------- PowerPoint ----------

class Pptx:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.names = set(self.z.namelist())

    def read(self, name):
        if name not in self.names or self.z.getinfo(name).file_size > MAX_PART:
            return None
        return self.z.read(name)

    def xml(self, name):
        b = self.read(name)
        return ET.fromstring(b) if b else None

    def rels(self, part):
        d, f = posixpath.split(part)
        root = self.xml(posixpath.join(d, "_rels", f + ".rels"))
        out = {}
        for r in (root if root is not None else []):
            kind = r.get("Type", "").rsplit("/", 1)[-1]
            tgt = r.get("Target", "")
            if r.get("TargetMode") != "External":
                tgt = posixpath.normpath(posixpath.join(d, tgt))
            out[r.get("Id")] = (kind, tgt, r.get("TargetMode") == "External")
        return out


def para_text(p):
    out = []
    for el in p:
        tag = el.tag.split("}")[1]
        if tag in ("r", "fld"):
            if tag == "fld" and el.get("type", "") == "slidenum":
                continue
            out.append("".join(t.text or "" for t in el.iter(Q("a:t"))))
        elif tag == "br":
            out.append(" / ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def body_lines(tx):
    lines = []
    for p in tx.iter(Q("a:p")):
        t = para_text(p)
        if not t:
            continue
        ppr = p.find("a:pPr", NS)
        lvl = int(ppr.get("lvl", 0)) if ppr is not None else 0
        lines.append((lvl, t))
    return lines


def xfrm(el):
    """The shape's offset and size in EMU, wherever this kind of shape keeps them."""
    for path in ("p:spPr/a:xfrm", "p:xfrm", "p:grpSpPr/a:xfrm"):
        x = el.find(path, NS)
        if x is not None:
            off, ext = x.find("a:off", NS), x.find("a:ext", NS)
            if off is not None and ext is not None:
                return (int(off.get("x", 0)), int(off.get("y", 0)),
                        int(ext.get("cx", 0)), int(ext.get("cy", 0)))
    return None


def chart_data(px, part):
    root = px.xml(part)
    if root is None:
        return None
    plot = root.find(".//c:plotArea", NS)
    if plot is None:
        return None
    kinds = [el.tag.split("}")[1] for el in plot if el.tag.endswith("Chart")]
    title = " ".join(t.text or "" for t in root.findall("./c:chart/c:title//a:t", NS)).strip()

    def pts(el):
        if el is None:
            return []
        got = {}
        for pt in el.iter(Q("c:pt")):
            v = pt.find("c:v", NS)
            got[int(pt.get("idx", 0))] = v.text if v is not None else ""
        return [got[i] for i in sorted(got)]

    series = []
    for ser in plot.iter(Q("c:ser")):
        name = " ".join(v.text or "" for v in ser.findall("c:tx//c:v", NS)).strip()
        cats = pts(ser.find("c:cat", NS)) or pts(ser.find("c:xVal", NS))
        vals = pts(ser.find("c:val", NS)) or pts(ser.find("c:yVal", NS))
        series.append({"name": name, "categories": cats, "values": vals})
    return {"type": kinds, "title": title, "series": series}


def diagram_text(px, part):
    root = px.xml(part)
    if root is None:
        return []
    out = []
    for pt in root.iter(Q("dgm:pt")):
        t = " ".join((x.text or "").strip() for x in pt.iter(Q("a:t"))).strip()
        if t:
            out.append(t)
    return out


def pic_size(data):
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            return im.size
    except Exception:
        return None


def pptx_slides(path, out):
    px = Pptx(path)
    pres_part = "ppt/presentation.xml"
    pres = px.xml(pres_part)
    if pres is None:
        sys.exit(f"{path}: no ppt/presentation.xml, so not a PowerPoint file")
    sz = pres.find("p:sldSz", NS)
    sw, sh = (int(sz.get("cx")), int(sz.get("cy"))) if sz is not None else (12192000, 6858000)
    prels = px.rels(pres_part)
    order = [prels[s.get(Q("r:id"))][1] for s in pres.findall("p:sldIdLst/p:sldId", NS)
             if s.get(Q("r:id")) in prels]
    media = Media(out)
    slides = []
    for n, part in enumerate(order, 1):
        root = px.xml(part)
        if root is None:
            continue
        rels = px.rels(part)
        s = {"n": n, "title": "", "hidden": root.get("show") == "0", "blocks": [], "notes": "",
             "shapes": 0, "connectors": 0}
        k = [0]

        def picture(rid, box, alt="", background=False):
            kind, tgt, ext = rels.get(rid, ("", "", False))
            if ext or not tgt:
                s["blocks"].append({"kind": "picture", "file": None, "linked": tgt, "alt": alt})
                return
            data = px.read(tgt)
            if data is None:
                return
            k[0] += 1
            file, again = media.put(data, f"s{n:02d}-{k[0]}{os.path.splitext(tgt)[1].lower()}")
            cover = 1.0 if background else (box[2] * box[3] / (sw * sh) if box else None)
            s["blocks"].append({"kind": "picture", "file": file, "again": again, "bytes": len(data),
                                "px": pic_size(data), "cover": round(cover, 2) if cover else None,
                                "alt": alt, "background": background})

        bg = root.find("p:cSld/p:bg//a:blip", NS)
        if bg is not None:
            picture(bg.get(Q("r:embed")), None, background=True)

        def walk(container, top):
            items = []
            for el in container:
                tag = el.tag.split("}")[1]
                if tag in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp"):
                    items.append(el)
            if top:   # reading order: the title first, then top to bottom, left to right
                def key(el):
                    ph = el.find(".//p:nvPr/p:ph", NS)
                    is_title = ph is not None and ph.get("type") in ("title", "ctrTitle")
                    b = xfrm(el) or (0, 0, 0, 0)
                    return (0 if is_title else 1, b[1] // max(1, sh // 12), b[0])
                items.sort(key=key)
            for el in items:
                tag = el.tag.split("}")[1]
                if tag == "grpSp":
                    walk(el, False)
                elif tag == "cxnSp":
                    s["connectors"] += 1
                elif tag == "sp":
                    ph = el.find("p:nvSpPr/p:nvPr/p:ph", NS)
                    ptype = ph.get("type", "body") if ph is not None else None
                    if ptype in SKIP_PH:
                        continue
                    tx = el.find("p:txBody", NS)
                    lines = body_lines(tx) if tx is not None else []
                    if ph is None:
                        s["shapes"] += 1
                    blip = el.find("p:spPr/a:blipFill/a:blip", NS)
                    if blip is not None:
                        picture(blip.get(Q("r:embed")), xfrm(el))
                    if not lines:
                        continue
                    if ptype in ("title", "ctrTitle") and not s["title"]:
                        s["title"] = " ".join(t for _, t in lines)
                    else:
                        s["blocks"].append({"kind": "subtitle" if ptype == "subTitle" else "text",
                                            "lines": lines})
                elif tag == "pic":
                    blip = el.find(".//a:blip", NS)
                    cnv = el.find("p:nvPicPr/p:cNvPr", NS)
                    alt = re.sub(r"\s+", " ", cnv.get("descr") or "").strip() if cnv is not None else ""
                    media = el.find("p:nvPicPr/p:nvPr/*", NS)
                    if media is not None and media.tag.split("}")[1] in ("videoFile", "audioFile"):
                        kind, tgt, _ = rels.get(media.get(Q("r:link")), ("", "", False))
                        s["blocks"].append({"kind": media.tag.split("}")[1].replace("File", ""),
                                            "target": tgt})
                    if blip is not None:
                        picture(blip.get(Q("r:embed")), xfrm(el), alt)
                elif tag == "graphicFrame":
                    tbl = el.find(".//a:tbl", NS)
                    if tbl is not None:
                        rows = [[" ".join(t for _, t in body_lines(tc)) for tc in tr.findall("a:tc", NS)]
                                for tr in tbl.findall("a:tr", NS)]
                        s["blocks"].append({"kind": "table", "rows": rows})
                        continue
                    ch = el.find(".//c:chart", NS)
                    if ch is not None:
                        kind, tgt, _ = rels.get(ch.get(Q("r:id")), ("", "", False))
                        d = chart_data(px, tgt) if tgt else None
                        if d:
                            s["blocks"].append({"kind": "chart", **d})
                        continue
                    dg = el.find(".//dgm:relIds", NS)
                    if dg is not None:
                        kind, tgt, _ = rels.get(dg.get(Q("r:dm")), ("", "", False))
                        s["blocks"].append({"kind": "smartart", "items": diagram_text(px, tgt) if tgt else []})
                        continue
                    s["blocks"].append({"kind": "object"})

        tree = root.find("p:cSld/p:spTree", NS)
        if tree is not None:
            walk(tree, True)
        for kind, tgt, ext in rels.values():
            if kind == "notesSlide" and not ext:
                nroot = px.xml(tgt)
                if nroot is None:
                    continue
                lines = []
                for sp in nroot.iter(Q("p:sp")):
                    ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
                    if ph is not None and ph.get("type") == "body":
                        tx = sp.find("p:txBody", NS)
                        lines += [t for _, t in body_lines(tx)] if tx is not None else []
                s["notes"] = "\n".join(lines)
        slides.append(s)
    return slides, {"width_emu": sw, "height_emu": sh}


# ---------- PDF ----------

def pdf_slides(path, out):
    for t in ("pdfinfo", "pdftotext", "pdfimages"):
        if not tool(t):
            sys.exit(f"{t} is missing: install poppler (apt install poppler-utils, brew install poppler)")
    info = run(["pdfinfo", path]).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    m = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+)", info, re.M)
    size = {"width_pt": float(m.group(1)), "height_pt": float(m.group(2))} if m else {}
    listing = run(["pdfimages", "-list", path]).stdout.splitlines()[2:]
    kinds = {}
    for row in listing:
        c = row.split()
        if len(c) > 4 and c[1].isdigit():
            kinds[int(c[1])] = (int(c[0]), c[2], int(c[3]), int(c[4]))   # num → page, type, w, h
    tmp = tempfile.mkdtemp()
    run(["pdfimages", "-png", path, os.path.join(tmp, "i")])
    media = Media(out)
    files = sorted(os.listdir(tmp))
    slides = []
    for n in range(1, pages + 1):
        text = run(["pdftotext", "-layout", "-f", str(n), "-l", str(n), path, "-"]).stdout
        lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
        s = {"n": n, "title": lines[0].strip() if lines else "", "hidden": False, "notes": "",
             "blocks": [{"kind": "page", "lines": [(0, ln.strip()) for ln in lines[1:]]}] if len(lines) > 1 else [],
             "shapes": None, "connectors": None}
        k = 0
        for f in files:
            num = int(re.search(r"-(\d+)\.png$", f).group(1))
            page, typ, w, h = kinds.get(num, (0, "", 0, 0))
            if page != n or typ != "image" or w * h < 32 * 32:
                continue
            k += 1
            data = open(os.path.join(tmp, f), "rb").read()
            file, again = media.put(data, f"s{n:02d}-{k}.png")
            s["blocks"].append({"kind": "picture", "file": file, "again": again, "px": (w, h),
                                "bytes": len(data), "cover": None, "alt": "", "background": False})
        if not lines and k:
            s["blocks"].append({"kind": "note", "text": "no text layer: the words are in the picture"})
        slides.append(s)
    shutil.rmtree(tmp, ignore_errors=True)
    return slides, size


# ---------- renders ----------

def to_pdf(path, workdir):
    soffice = tool("soffice") or tool("libreoffice")
    if not soffice:
        return None
    prof = tempfile.mkdtemp()
    r = run([soffice, f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "pdf",
             "--outdir", workdir, path], timeout=600)
    shutil.rmtree(prof, ignore_errors=True)
    pdf = os.path.join(workdir, os.path.splitext(os.path.basename(path))[0] + ".pdf")
    return pdf if r.returncode == 0 and os.path.isfile(pdf) else None


def render(pdf, out):
    if not (pdf and tool("pdftoppm")):
        return False
    d = os.path.join(out, "render")
    os.makedirs(d, exist_ok=True)
    run(["pdftoppm", "-png", "-scale-to-x", str(RENDER_W), "-scale-to-y", "-1", pdf, os.path.join(d, "s")],
        timeout=900)
    for f in os.listdir(d):    # pdftoppm pads to the page count's width: s-1.png, s-01.png, s-001.png
        m = re.match(r"s-0*(\d+)\.png$", f)
        if m:
            os.replace(os.path.join(d, f), os.path.join(d, f"s{int(m.group(1)):02d}.png"))
    return True


# ---------- the inventory ----------

def kb(b):
    return f"{b / 1024:.0f} kB" if b < 1024 * 1024 else f"{b / 1024 / 1024:.1f} MB"


def md_table(rows):
    if not rows:
        return []
    w = max(len(r) for r in rows)
    rows = [[c.replace("|", "\\|") for c in r] + [""] * (w - len(r)) for r in rows]
    return ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w] + ["| " + " | ".join(r) + " |" for r in rows[1:]]


def write_md(src, slides, size, rendered, out):
    L = [f"# {os.path.basename(src)}: {len(slides)} slides", "",
         "Read with docs/CONVERT.md. Text is in reading order; `-` lines were paragraphs of one box,",
         "indented by their level. Look at a slide's render once before deciding what it becomes.", ""]
    uses = {}
    for s in slides:
        for b in s["blocks"]:
            if b["kind"] == "picture" and b.get("file"):
                uses.setdefault(b["file"], set()).add(s["n"])
    common = sorted(f for f, ns in uses.items() if len(ns) >= 3)
    if common:
        L += ["Pictures on three slides or more, most likely the template's (a logo, a strip): leave them",
              "to the theme, which draws its own header and footer.", ""]
        L += [f"- {f}: on {len(uses[f])} slides" for f in common] + [""]
    for s in slides:
        L.append(f"## s{s['n']:02d} · {s['title'] or '(no title)'}" + ("  [hidden]" if s["hidden"] else ""))
        if rendered:
            L.append(f"render: render/s{s['n']:02d}.png")
        L.append("")
        for b in s["blocks"]:
            k = b["kind"]
            if k == "page":
                L += [t for _, t in b["lines"]] + [""]
            elif k in ("text", "subtitle"):
                many = len(b["lines"]) > 1
                for lvl, t in b["lines"]:
                    L.append(("  " * lvl + "- " + t) if many else t)
                L.append("")
            elif k == "table":
                L += ["**Table**", ""] + md_table(b["rows"]) + [""]
            elif k == "chart":
                L.append(f"**Chart** {', '.join(b['type']) or '?'}" + (f": {b['title']}" if b["title"] else ""))
                L.append("")
                cats = max((x["categories"] for x in b["series"]), key=len, default=[])
                rows = [[""] + [x["name"] or f"series {i + 1}" for i, x in enumerate(b["series"])]]
                for i in range(max([len(cats)] + [len(x["values"]) for x in b["series"]])):
                    rows.append([cats[i] if i < len(cats) else str(i + 1)] +
                                [x["values"][i] if i < len(x["values"]) else "" for x in b["series"]])
                L += md_table(rows) + [""]
            elif k == "smartart":
                L += ["**SmartArt**: " + " · ".join(b["items"]), ""]
            elif k == "picture":
                if not b.get("file"):
                    L += [f"**Picture** linked from outside the file: {b.get('linked')}", ""]
                    continue
                bits = [b["file"] + (" again" if b.get("again") else "")]
                if b.get("again"):
                    L += ["**Picture** " + bits[0], ""]
                    continue
                if b.get("px"):
                    bits.append(f"{b['px'][0]}×{b['px'][1]}")
                if b.get("bytes"):
                    bits.append(kb(b["bytes"]))
                if b.get("background"):
                    bits.append("the slide's background")
                elif b.get("cover"):
                    bits.append(f"covers {b['cover']:.0%} of the slide")
                if b["file"].endswith((".emf", ".wmf")):
                    bits.append("a vector drawing (EMF/WMF): inkscape or soffice turns it into SVG to redraw from")
                if b.get("alt"):
                    bits.append(f"alt: {b['alt']}")
                L += ["**Picture** " + " · ".join(bits), ""]
            elif k in ("video", "audio"):
                L += [f"**{k.title()}** {b.get('target', '')}: SlAIdy plays neither; a still and a link", ""]
            elif k == "object":
                L += ["**Object** an embedded object the inventory cannot read: look at the render", ""]
            elif k == "note":
                L += [f"**Note** {b['text']}", ""]
        if s.get("shapes"):
            L += [f"**Drawn** {s['shapes']} shapes, {s['connectors']} connectors"
                  + (": a diagram, redraw it as SVG" if s["shapes"] >= 4 or s["connectors"] else ""), ""]
        if s["notes"]:
            L += ["**Notes**", "", s["notes"], ""]
    with open(os.path.join(out, "inventory.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L).rstrip() + "\n")
    with open(os.path.join(out, "inventory.json"), "w", encoding="utf-8") as f:
        json.dump({"source": os.path.basename(src), "size": size, "rendered": rendered, "slides": slides},
                  f, ensure_ascii=False, indent=1)


# ---------- what a finished deck lost ----------

# a number as people write it: 1 250 and 1,250.5 and 47.6 % are one number each; "2024, 2025" is two
NUM_RE = re.compile(r"(?<![\w.])[-−+]?\d+(?:[.,:]\d+|[ \u00a0\u202f]\d{3}(?!\d))*(?: ?%)?")


def numbers(text):
    out = set()
    for m in NUM_RE.finditer(text or ""):
        tok = re.sub(r"[ \u00a0\u202f]", "", m.group(0)).replace("−", "-")
        digits = re.sub(r"\D", "", tok)
        if len(digits) >= 2 or "%" in tok:
            out.add(tok)
    return out


def norm(tok):
    """1 234,5 and 1,234.5 and 1234.5 are the same number to a reader; compare digits and the %."""
    return re.sub(r"[^\d%]", "", tok)


def slide_text(s):
    parts = [s["title"], s["notes"]]
    for b in s["blocks"]:
        parts += [t for _, t in b.get("lines", [])]
        parts += [c for r in b.get("rows", []) for c in r]
        for x in b.get("series", []):
            parts += [x["name"]] + list(x["categories"]) + list(x["values"])
        parts += b.get("items", [])
    return "\n".join(p or "" for p in parts)


def missing(folder, deck_path):
    inv = json.load(open(os.path.join(folder, "inventory.json"), encoding="utf-8"))
    deck = json.load(open(deck_path, encoding="utf-8"))
    hay = [deck.get("title") or ""]
    for s in deck.get("slides", []):
        hay += [s.get("title") or "", s.get("body") or "", s.get("notes") or ""]
    for svg in (deck.get("figs") or {}).values():
        hay.append(re.sub(r"<[^>]+>", " ", svg))
    have = {norm(t) for t in numbers("\n".join(hay))}
    lost = 0
    for s in inv["slides"]:
        gone = sorted(t for t in numbers(slide_text(s)) if norm(t) not in have)
        if gone:
            lost += len(gone)
            print(f"s{s['n']:02d} {s['title'][:50]!r}: " + ", ".join(gone))
    print(f"{lost} numbers of the original are not in the deck" if lost else
          "every number of the original is somewhere in the deck")


def main(argv):
    if argv[:1] == ["--missing"] and len(argv) == 3:
        return missing(argv[1], argv[2])
    no_render = "--no-render" in argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    src, out = args
    os.makedirs(out, exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    work = tempfile.mkdtemp()
    try:
        if ext in (".ppt", ".odp", ".key", ".pps", ".ppsx", ".pptm"):
            soffice = tool("soffice") or tool("libreoffice")
            if not soffice:
                sys.exit(f"{ext} needs LibreOffice to become a .pptx; or save it as .pptx or .pdf yourself")
            prof = tempfile.mkdtemp()
            run([soffice, f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "pptx",
                 "--outdir", work, src], timeout=600)
            shutil.rmtree(prof, ignore_errors=True)
            src_x = os.path.join(work, os.path.splitext(os.path.basename(src))[0] + ".pptx")
            if not os.path.isfile(src_x):
                sys.exit(f"LibreOffice could not open {src}; save it as .pptx or .pdf")
        else:
            src_x = src
        if ext == ".pdf":
            slides, size = pdf_slides(src, out)
            rendered = False if no_render else render(src, out)
        else:
            slides, size = pptx_slides(src_x, out)
            rendered = False if no_render else render(to_pdf(src_x, work), out)
        write_md(src, slides, size, rendered, out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    pics = sum(1 for s in slides for b in s["blocks"] if b["kind"] == "picture")
    print(f"{len(slides)} slides, {pics} pictures → {os.path.join(out, 'inventory.md')}"
          + ("" if rendered or no_render else
             "\nno renders: LibreOffice (for a .pptx) or poppler's pdftoppm is missing; export a PDF and ingest that too"))


if __name__ == "__main__":
    main(sys.argv[1:])
