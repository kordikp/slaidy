#!/usr/bin/env python3
r"""
Generate one animated explanatory SVG per concept, from a contract file.

The canvas, palette and text zones are locked in the system prompt, so the model
spends its effort on the explanation rather than on the design, and a validator
rejects anything that would be unreadable at projection size.

The contract file is {"audience": "...", "concepts": [{"id", "title", "takeaway",
"brief"}, ...]}. "audience" is one sentence saying who is in the room; it is the
only part of the prompt that changes between decks.

Usage:
  python3 scripts/generate_figures.py --concepts content/figures.json --all
  python3 scripts/generate_figures.py --only cascade,two-tower
  python3 scripts/generate_figures.py --all --missing-only --concurrency 4
  python3 scripts/generate_figures.py --retry feedback.json

Env: OPENAI_KEY (or OPENAI_API_KEY), FIGURE_MODEL (default gpt-5.6-sol)
"""

import argparse, json, os, re, sys, time, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONCEPTS = os.path.join(ROOT, "content", "figures.json")
OUTDIR = os.path.join(ROOT, "images")

MODEL = os.environ.get("FIGURE_MODEL", "gpt-5.6-sol")
BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
KEY = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY")

PALETTE = {
    "#1E1B4B", "#6B7280", "#7C3AED", "#EDE9FE", "#10B981", "#D1FAE5",
    "#D97706", "#FEF3C7", "#EF4444", "#FEE2E2", "#0EA5E9", "#E0F2FE",
    "#FAFAF7", "#E5E7EB", "#FFFFFF", "#4C1D95", "#075985", "#065F46",
    "#92400E", "#991B1B", "#374151", "#9CA3AF", "#F3F4F6", "#111827",
    "none", "transparent",
}

AUDIENCE_DEFAULT = "a technical audience who are not specialists in this particular field"
AUDIENCE = AUDIENCE_DEFAULT

SYSTEM = """You are the staff illustrator for a talk. The audience is {audience}. Your figures carry the explanation.

You draw ONE animated explanatory SVG per concept. Readers should understand the mechanism from the picture alone.

OUTPUT: reply with ONE complete <svg> element and NOTHING else. Valid XML (escape & as &amp;, < as &lt;, > as &gt; inside text). No markdown fences, no commentary.

LOCKED CANVAS (do not deviate):
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" font-family="system-ui,sans-serif">
  first child: <rect width="800" height="450" rx="14" fill="#FAFAF7" stroke="#E5E7EB"/>
  title:   centered x=400 y=34, font-size 19, font-weight 700, fill #1E1B4B, max 58 chars
  drawing: lives between y=52 and y=396
  takeaway: centered x=400 y=428, font-size 12.5, fill #6B7280, max 100 chars, ONE line —
            a plain sentence stating the mechanism. This line teaches; the drawing shows.

PALETTE — use ONLY these hex values:
  ink #1E1B4B · gray #6B7280 · white #FFFFFF · bg #FAFAF7 · line #E5E7EB
  blue #0EA5E9 (light #E0F2FE, dark #075985)      -> SEARCH, the query, explicit intent
  purple #7C3AED (light #EDE9FE, dark #4C1D95)    -> RECOMMENDATION, the user profile, implicit intent
  green #10B981 (light #D1FAE5, dark #065F46)     -> the unified/shared layer, the correct answer
  amber #D97706 (light #FEF3C7, dark #92400E)     -> cost, latency, compute, constraints
  red #EF4444 (light #FEE2E2, dark #991B1B)       -> failure, bias, risk, what breaks
Those colour meanings are consistent across the whole deck. Honour them.

DRAWING RULES:
- Boxes: rounded rect rx=10, stroke-width 2, light palette fill + matching dark stroke.
- Arrows: define <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10" fill="#6B7280"/></marker></defs> and use marker-end="url(#a)". Give every arrow a short label when the relation is not obvious.
- LABEL THE ARROWS. An unlabelled arrow means "related somehow"; "writes", "retrieves 10³", "gradient" is information.
- A label that sits on top of a line MUST first get its own background chip: <rect fill="#FAFAF7" stroke="none"/> sized to the text, drawn immediately before the <text>. Otherwise the line strikes through the words. Alternatively offset the label clear of the line.
- Person = circle head r=9..11 + 2-3 stroke lines, stroke-width 2.5, stroke-linecap round. No faces.
- Text: body 12.5px, small labels 11px, never below 11px. Use text-anchor for alignment.
- Keep every glyph at least 14px inside the canvas edge. Never overlap text with shapes or other text.
- Align to a grid. Shared baselines, even gaps. Eyeballed offsets read as noise.
- MAXIMUM 22 drawn elements. Generous whitespace. Wrong: an inventory of a system. Right: the one mechanism the slide turns on.
- No gradients, no filters, no <image>, no <foreignObject>, no external refs, no transforms on <text>.
- Monospace only for code/IDs: font-family="ui-monospace,monospace".

ANIMATION — CSS keyframes inside a single <style> element. Never SMIL.
- 6s loop, ease-in-out, infinite.
- Animate ONLY transform, opacity, stroke-dashoffset or fill. Never animate SVG geometry attributes (x, y, width, r, cx) through CSS — browser support is inconsistent. To move something, wrap it in a <g> and animate transform: translate(...).
- Hold both states so a viewer can read them: e.g. @keyframes m{0%,18%{...}52%,88%{...}100%{...}}
- At most 3 animated groups.
- The animation must CARRY MEANING: show the thing moving, the mask closing, the candidate set shrinking, the gradient flowing back. Never animate for decoration.
- CRITICAL: the figure must be fully legible in its 0% (unanimated) state, because it will also be exported as a static image for slides and print. Animation adds a second reading, never the only one.

STYLE: calm, precise, engineering-diagram. Think a very good textbook figure, not a marketing graphic."""


def user_prompt(c, feedback=None):
    must = "\n".join("- " + m["point"] for m in c.get("mustCover", []))
    anim = c.get("animate", "")
    parts = [
        f"CONCEPT: {c['title']}  (id: {c['id']})",
        f"WHAT THE AUDIENCE MUST UNDERSTAND: {c['objective']}",
    ]
    if must:
        parts.append("THE FIGURE MUST SHOW:\n" + must)
    if anim:
        parts.append(f"WHAT TO ANIMATE, AND WHY IT MATTERS: {anim}")
    if c.get("takeaway"):
        parts.append(f"SUGGESTED TAKEAWAY LINE (rewrite if you can do better, keep under 100 chars): {c['takeaway']}")
    if c.get("avoid"):
        parts.append("DO NOT: " + "; ".join(c["avoid"]))
    parts.append("Draw it now. Output only the <svg>.")
    if feedback:
        parts.append(f"\nA previous attempt failed review: \"{feedback}\". Fix exactly that and keep what worked.")
    return "\n\n".join(parts)


def call_model(messages, max_tokens=20000, timeout=600):
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_completion_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        BASE + "/chat/completions", data=body,
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    return d["choices"][0]["message"]["content"]


def extract_svg(text):
    t = text.strip()
    t = re.sub(r"^```(?:svg|xml|html)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    i, j = t.find("<svg"), t.rfind("</svg>")
    if i == -1 or j == -1:
        return None
    return t[i:j + 6]


def validate(svg):
    """Return list of problems; empty list means the figure passed."""
    problems = []
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as e:
        return [f"SVG is not valid XML: {e}"]

    vb = root.get("viewBox", "")
    if vb.split() != ["0", "0", "800", "450"]:
        problems.append(f'viewBox must be exactly "0 0 800 450", got "{vb}"')

    # palette
    used = set()
    for el in root.iter():
        for attr in ("fill", "stroke", "stop-color"):
            v = (el.get(attr) or "").strip()
            if v.startswith("#"):
                used.add(v.upper())
        style = el.get("style") or ""
        for m in re.finditer(r"#[0-9A-Fa-f]{3,6}", style):
            used.add(m.group(0).upper())
    for m in re.finditer(r"#[0-9A-Fa-f]{6}", svg):
        used.add(m.group(0).upper())
    stray = sorted(c for c in used if c not in {p.upper() for p in PALETTE})
    if stray:
        problems.append("colours outside the locked palette: " + ", ".join(stray[:8]))

    # forbidden constructs
    for bad, why in (("<image", "raster images"), ("foreignObject", "foreignObject"),
                     ("<animate", "SMIL animation (use CSS keyframes)"),
                     ("filter=", "filters"), ("Gradient", "gradients")):
        if bad in svg:
            problems.append(f"contains {why}")

    # text bounds + size
    ns = "{http://www.w3.org/2000/svg}"
    for t in root.iter(ns + "text"):
        if t.get("x") is None and t.get("y") is None:
            continue          # positioned via its tspans, not itself
        try:
            x, y = float(t.get("x", 0)), float(t.get("y", 0))
        except ValueError:
            continue
        if not (8 <= x <= 792) or not (14 <= y <= 442):
            problems.append(f'text "{(t.text or "")[:22]}" at ({x:.0f},{y:.0f}) is outside the safe area')
            break
        try:
            if t.get("font-size") and float(re.sub(r"[^\d.]", "", t.get("font-size"))) < 10.5:
                problems.append("font-size below 10.5px — unreadable when projected")
                break
        except ValueError:
            pass

    if "@keyframes" not in svg:
        problems.append("no CSS @keyframes animation")

    n_drawn = sum(1 for el in root.iter()
                  if el.tag.split("}")[-1] in ("rect", "circle", "line", "path", "polygon", "polyline", "ellipse"))
    if n_drawn > 60:
        problems.append(f"{n_drawn} drawn elements — too busy, simplify to the one mechanism")
    return problems


def generate(c, feedback=None, attempts=3):
    msgs = [{"role": "system", "content": SYSTEM.format(audience=AUDIENCE)},
            {"role": "user", "content": user_prompt(c, feedback)}]
    last = None
    for k in range(attempts):
        try:
            out = call_model(msgs)
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:200]
            if e.code in (429, 500, 502, 503, 504) and k < attempts - 1:
                time.sleep(4 * (k + 1)); continue
            return None, [f"HTTP {e.code}: {detail}"]
        except Exception as e:
            if k < attempts - 1:
                time.sleep(4 * (k + 1)); continue
            return None, [f"request failed: {e}"]

        svg = extract_svg(out)
        if not svg:
            msgs.append({"role": "assistant", "content": out[:400]})
            msgs.append({"role": "user", "content": "That was not a bare <svg> element. Output only the SVG."})
            continue
        problems = validate(svg)
        last = (svg, problems)
        if not problems:
            return svg, []
        msgs.append({"role": "assistant", "content": svg[:1500]})
        msgs.append({"role": "user", "content":
                     "The figure failed automated review:\n- " + "\n- ".join(problems) +
                     "\nRegenerate the complete SVG with those fixed. Output only the SVG."})
    return (last if last else (None, ["gave up"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only"); ap.add_argument("--all", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--retry"); ap.add_argument("--missing-only", action="store_true")
    ap.add_argument("--concepts", default=CONCEPTS)
    a = ap.parse_args()

    if not KEY:
        sys.exit("Set OPENAI_KEY (or OPENAI_API_KEY).")
    os.makedirs(OUTDIR, exist_ok=True)

    spec = json.load(open(a.concepts, encoding="utf-8"))
    global AUDIENCE
    AUDIENCE = spec.get("audience") or AUDIENCE_DEFAULT
    concepts = spec["concepts"]
    feedback = json.load(open(a.retry, encoding="utf-8")) if a.retry else {}

    if a.only:
        want = set(a.only.split(","))
        concepts = [c for c in concepts if c["id"] in want]
    elif a.retry:
        concepts = [c for c in concepts if c["id"] in feedback]
    elif not a.all:
        sys.exit("Pass --all, --only <ids> or --retry <file>.")

    if a.missing_only:
        concepts = [c for c in concepts
                    if not os.path.exists(os.path.join(OUTDIR, f"fig-{c['id']}.svg"))]

    print(f"model {MODEL} · {len(concepts)} figures · concurrency {a.concurrency}", flush=True)
    done, failed = 0, []
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(generate, c, feedback.get(c["id"])): c for c in concepts}
        for f in as_completed(futs):
            c = futs[f]
            svg, problems = f.result()
            if svg:
                path = os.path.join(OUTDIR, f"fig-{c['id']}.svg")
                open(path, "w", encoding="utf-8").write(svg)
                done += 1
                tag = "OK  " if not problems else "WARN"
                note = "" if not problems else "  ! " + "; ".join(problems)[:110]
                print(f"{tag} {c['id']:<36} {len(svg)//1024 or 1}kB{note}", flush=True)
                if problems:
                    failed.append((c["id"], problems))
            else:
                print(f"FAIL {c['id']:<36} {problems}", flush=True)
                failed.append((c["id"], problems))
    print(f"\n{done}/{len(concepts)} written to images/")
    if failed:
        open(os.path.join(ROOT, "figure-issues.json"), "w", encoding="utf-8").write(
            json.dumps({i: "; ".join(p) for i, p in failed}, ensure_ascii=False, indent=2))
        print(f"{len(failed)} with issues -> figure-issues.json (feed back with --retry)")


if __name__ == "__main__":
    main()
