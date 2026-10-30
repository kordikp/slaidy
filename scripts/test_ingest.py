#!/usr/bin/env python3
"""A PowerPoint file read into an inventory, and a deck checked against it.

The .pptx is written here by hand, as the few XML parts ingest.py reads: a title,
a box of bullets, a picture with alt text, a table, a chart with its numbers, and
speaker notes. No LibreOffice is needed (--no-render).
"""
import base64, json, os, subprocess, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bad = 0


def check(name, cond, detail=""):
    global bad
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        bad += 1


P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" ' \
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ' \
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
REL = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>'
T = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def sp(text, ph=None, y=0, paras=None):
    nv = f'<p:nvPr><p:ph type="{ph}"/></p:nvPr>' if ph else '<p:nvPr/>'
    ps = "".join(f'<a:p><a:pPr lvl="{lvl}"/><a:r><a:t>{t}</a:t></a:r></a:p>' for lvl, t in (paras or [(0, text)]))
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="s"/><p:cNvSpPr/>{nv}</p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="0" y="{y}"/><a:ext cx="100" cy="100"/></a:xfrm></p:spPr>'
            f'<p:txBody>{ps}</p:txBody></p:sp>')


slide = (f'<p:sld {P}><p:cSld><p:spTree>'
         + sp("", y=5000000, paras=[(0, "Grow the pilots"), (1, "nine regions"), (1, "ten countries")])
         + sp("Agents in the field", ph="title", y=100)
         + sp("7", ph="sldNum", y=6000000)
         + '<p:pic><p:nvPicPr><p:cNvPr id="4" name="p" descr="A tractor\nin a field"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
           '<p:blipFill><a:blip r:embed="rId2"/></p:blipFill>'
           '<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="6096000" cy="6858000"/></a:xfrm></p:spPr></p:pic>'
         + '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="5" name="t"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
           '<p:xfrm><a:off x="0" y="3000000"/><a:ext cx="10" cy="10"/></p:xfrm><a:graphic><a:graphicData>'
           '<a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>Pilot</a:t></a:r></a:p></a:txBody></a:tc>'
           '<a:tc><a:txBody><a:p><a:r><a:t>Farms</a:t></a:r></a:p></a:txBody></a:tc></a:tr>'
           '<a:tr><a:tc><a:txBody><a:p><a:r><a:t>Cuenca</a:t></a:r></a:p></a:txBody></a:tc>'
           '<a:tc><a:txBody><a:p><a:r><a:t>412</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl>'
           '</a:graphicData></a:graphic></p:graphicFrame>'
         + '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="6" name="c"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
           '<p:xfrm><a:off x="0" y="4000000"/><a:ext cx="10" cy="10"/></p:xfrm><a:graphic><a:graphicData>'
           '<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" r:id="rId3"/>'
           '</a:graphicData></a:graphic></p:graphicFrame>'
         + '<p:cxnSp/></p:spTree></p:cSld></p:sld>')
C = 'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"'
chart = (f'<c:chartSpace {C}><c:chart><c:plotArea><c:barChart><c:ser><c:tx><c:strRef><c:strCache><c:pt idx="0"><c:v>Users</c:v></c:pt></c:strCache></c:strRef></c:tx>'
         '<c:cat><c:strRef><c:strCache><c:pt idx="1"><c:v>2025</c:v></c:pt><c:pt idx="0"><c:v>2024</c:v></c:pt></c:strCache></c:strRef></c:cat>'
         '<c:val><c:numRef><c:numCache><c:pt idx="0"><c:v>1250</c:v></c:pt><c:pt idx="1"><c:v>3875</c:v></c:pt></c:numCache></c:numRef></c:val>'
         '</c:ser></c:barChart></c:plotArea></c:chart></c:chartSpace>')
notes = f'<p:notes {P}><p:cSld><p:spTree>' + sp("Say the 47.6 % adoption.", ph="body") + '</p:spTree></p:cSld></p:notes>'

tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "talk.pptx")
with zipfile.ZipFile(src, "w") as z:
    z.writestr("ppt/presentation.xml", f'<p:presentation {P}><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>'
               '<p:sldSz cx="12192000" cy="6858000"/></p:presentation>')
    z.writestr("ppt/_rels/presentation.xml.rels", REL % f'<Relationship Id="rId1" Type="{T}slide" Target="slides/slide1.xml"/>')
    z.writestr("ppt/slides/slide1.xml", slide)
    z.writestr("ppt/slides/_rels/slide1.xml.rels", REL % (
        f'<Relationship Id="rId2" Type="{T}image" Target="../media/image1.png"/>'
        f'<Relationship Id="rId3" Type="{T}chart" Target="../charts/chart1.xml"/>'
        f'<Relationship Id="rId4" Type="{T}notesSlide" Target="../notesSlides/notesSlide1.xml"/>'))
    z.writestr("ppt/media/image1.png", PNG)
    z.writestr("ppt/charts/chart1.xml", chart)
    z.writestr("ppt/notesSlides/notesSlide1.xml", notes)

out = os.path.join(tmp, "sources")
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ingest.py"), src, out, "--no-render"],
                   capture_output=True, text=True)
check("ingest runs", r.returncode == 0, r.stderr[-300:])
inv = json.load(open(os.path.join(out, "inventory.json")))
s = inv["slides"][0]
kinds = [b["kind"] for b in s["blocks"]]
check("the title comes from the title placeholder", s["title"] == "Agents in the field", s["title"])
check("the slide number placeholder is left out",
      not any(t == "7" for b in s["blocks"] for _, t in b.get("lines", [])))
check("reading order is top to bottom", kinds.index("picture") < kinds.index("table") < kinds.index("chart")
      < kinds.index("text"), str(kinds))
text = next(b for b in s["blocks"] if b["kind"] == "text")
check("bullets keep their level", [lvl for lvl, _ in text["lines"]] == [0, 1, 1], str(text["lines"]))
pic = next(b for b in s["blocks"] if b["kind"] == "picture")
check("the picture is written out", os.path.isfile(os.path.join(out, pic["file"])), pic["file"])
check("alt text comes along, on one line", pic["alt"] == "A tractor in a field", repr(pic["alt"]))
check("how much of the slide the picture covers", pic["cover"] == 0.5, str(pic["cover"]))
tbl = next(b for b in s["blocks"] if b["kind"] == "table")
check("a table keeps its cells", tbl["rows"] == [["Pilot", "Farms"], ["Cuenca", "412"]], str(tbl["rows"]))
ch = next(b for b in s["blocks"] if b["kind"] == "chart")
check("a chart gives its numbers, in order", ch["series"][0]["categories"] == ["2024", "2025"]
      and ch["series"][0]["values"] == ["1250", "3875"], str(ch))
check("speaker notes", s["notes"] == "Say the 47.6 % adoption.", repr(s["notes"]))
check("connectors are counted", s["connectors"] == 1)
md = open(os.path.join(out, "inventory.md")).read()
check("the inventory shows the chart as a table", "| 2025 | 3875 |" in md)

deck = os.path.join(tmp, "deck.json")
json.dump({"title": "t", "slides": [{"title": "Agents", "body": "| Cuenca | 412 |\n\n1 250 users in 2024, 3 875 in 2025", "notes": "47,6 %"}],
           "figs": {"f": "<svg><text>2025</text></svg>"}}, open(deck, "w"))
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ingest.py"), "--missing", out, deck],
                   capture_output=True, text=True)
check("--missing finds nothing missing when every number is there", "every number" in r.stdout, r.stdout)
json.dump({"title": "t", "slides": [{"title": "Agents", "body": "412", "notes": ""}], "figs": {}}, open(deck, "w"))
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ingest.py"), "--missing", out, deck],
                   capture_output=True, text=True)
check("--missing names the numbers a deck lost", "1250" in r.stdout and "3875" in r.stdout and "47.6%" in r.stdout
      and "412" not in r.stdout.split(":", 1)[1], r.stdout)

print(f"{bad} failed" if bad else "all passed")
sys.exit(1 if bad else 0)
