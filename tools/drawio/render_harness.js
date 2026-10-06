/* Render draw.io drawings to SVG, in the browser draw.io itself draws in.
 *
 * The one thing this does that draw.io's own export does not: labels come back
 * as real SVG <text>. draw.io lays labels out as HTML inside <foreignObject>,
 * which gives it word wrapping — but a <foreignObject> is stripped from any
 * figure SlAIdy mounts, and turning it off (foEnabled = false) costs the
 * wrapping, so long labels run off the side of the drawing.
 *
 * So the labels are laid out as HTML, measured where they landed, and rewritten
 * as <text> at those exact positions: one <text> per wrapped line, one <tspan>
 * per run of like-styled words inside it, each placed by its measured left edge
 * so the original alignment survives without being reasoned about.
 */
'use strict';

function modelNode(xml) {
  var doc = mxUtils.parseXml(xml), root = doc.documentElement;
  if (root.nodeName === 'mxGraphModel') return root;
  return root.getElementsByTagName('diagram')[0].getElementsByTagName('mxGraphModel')[0];
}

var SVGNS = 'http://www.w3.org/2000/svg';

/* A label wrapped in $$…$$ is TeX: draw.io renders it with MathJax when the
 * drawing has math turned on, and every one of these drawings has. The formula
 * is typeset into the label where it sits, so the browser positions it, and
 * then lifted into the drawing as plain SVG paths at the size and place it was
 * measured at. A <br> inside the TeX is what draw.io ignores, so it goes too. */
var TEX = /^\s*\$\$?([\s\S]*?)\$\$?\s*$/;

function typesetMath(fo) {
  var m = TEX.exec(fo.textContent || '');
  if (!m || !m[1].trim()) return false;
  var walk = document.createTreeWalker(fo, NodeFilter.SHOW_TEXT), node, host = null, box = null;
  while ((node = walk.nextNode())) {
    if (!node.nodeValue.trim()) continue;
    if (!host) host = node.parentElement;
    var range = document.createRange();
    range.selectNodeContents(node);
    var r = range.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    box = box ? { left: Math.min(box.left, r.left), top: Math.min(box.top, r.top),
                  right: Math.max(box.right, r.right), bottom: Math.max(box.bottom, r.bottom) }
              : { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
  }
  if (!host || !box) return false;
  var colour = getComputedStyle(host).color;
  var out;
  try {
    out = MathJax.tex2svg(m[1].replace(/\u00a0/g, ' '), { display: false });
  } catch (e) {
    return false;
  }
  host.textContent = '';
  host.appendChild(out);
  var svg = out.querySelector('svg');
  if (!svg) return false;
  // Where the label's own text sat, measured before it was replaced. The box the
  // label is laid out in was sized for one line of text, so a formula taller than
  // that line spills out of the bottom of it and reads as having crept upwards.
  // draw.io re-centres after typesetting; centring on the text it replaced is the
  // same answer and needs no second layout pass.
  fo.__math = { svg: svg, colour: colour, was: box };
  return true;
}

/* The formula is written in the coordinates of the group it replaces, so that
 * group's own rotation carries it round exactly as it carried the text. The
 * measured box is in screen coordinates and therefore upright even when the
 * label is not, so its four corners are mapped back through that group's
 * transform: for the quarter-turns draw.io uses, the box that comes back is the
 * label's true one. */
function placeMath(holder, fo, toParent) {
  var svg = fo.__math.svg;
  var vb = (svg.getAttribute('viewBox') || '').split(/\s+/).map(Number);
  if (vb.length !== 4 || !vb[2]) return null;
  var box = svg.getBoundingClientRect();
  if (!box.width) return null;
  var now = toParent(box), was = toParent(fo.__math.was);
  var w = now.w, h = now.h;
  var x = was.x + was.w / 2 - w / 2;
  var y = was.y + was.h / 2 - h / 2;
  var scale = w / vb[2];
  var g = document.createElementNS(SVGNS, 'g');
  g.setAttribute('transform', 'translate(' + round(x) + ',' + round(y) + ') scale('
    + (Math.round(scale * 1e6) / 1e6) + ') translate(' + (-vb[0]) + ',' + (-vb[1]) + ')');
  // MathJax paints with currentColor, which beats a fill on an ancestor — so the
  // colour has to be set as the CSS property, or every white formula turns black.
  g.setAttribute('fill', fo.__math.colour);
  g.setAttribute('style', 'color:' + fo.__math.colour);
  g.setAttribute('stroke', 'none');
  while (svg.firstChild) g.appendChild(svg.firstChild);
  return g;
}

function round(n) { return Math.round(n * 100) / 100; }
var canvas = document.createElement('canvas').getContext('2d');
var ascentCache = {};

function ascent(font) {                    // where the baseline sits in a line box
  if (!(font in ascentCache)) {
    canvas.font = font;
    var m = canvas.measureText('Hxdgp');
    ascentCache[font] = {
      a: m.fontBoundingBoxAscent || m.actualBoundingBoxAscent || 0,
      d: m.fontBoundingBoxDescent || m.actualBoundingBoxDescent || 0
    };
  }
  return ascentCache[font];
}

/* Every word of a label, with where it landed and how it is painted. */
function words(root) {
  var out = [], walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), node;
  while ((node = walk.nextNode())) {
    var text = node.nodeValue;
    if (!text || !text.trim()) continue;
    var style = getComputedStyle(node.parentElement);
    var look = [style.fontFamily, style.fontSize, style.fontWeight,
                style.fontStyle, style.color].join('|');
    var re = /\S+/g, m;
    while ((m = re.exec(text))) {
      var range = document.createRange();
      range.setStart(node, m.index);
      range.setEnd(node, m.index + m[0].length);
      var box = range.getBoundingClientRect();
      if (!box.width && !box.height) continue;
      out.push({
        text: m[0], look: look, box: box, style: style,
        lineHeight: parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2,
        font: style.fontStyle + ' ' + style.fontWeight + ' ' + style.fontSize + ' ' + style.fontFamily
      });
    }
  }
  return out;
}

/* Words -> lines -> runs of one look, so a bold word inside a line stays bold. */
function linesOf(ws) {
  var lines = [];
  ws.forEach(function (w) {
    var line = lines[lines.length - 1];
    if (!line || Math.abs(line.top - w.box.top) > 2) {
      lines.push({ top: w.box.top, runs: [{ look: w.look, w: w, words: [w.text], right: w.box.right }] });
      return;
    }
    var run = line.runs[line.runs.length - 1];
    if (run.look === w.look && Math.abs(w.box.left - run.right) < w.box.height) {
      run.words.push(w.text);
      run.right = w.box.right;
    } else {
      line.runs.push({ look: w.look, w: w, words: [w.text], right: w.box.right });
    }
  });
  return lines;
}

function replaceLabels(svg) {
  var holders = [].slice.call(svg.getElementsByTagName('switch'));
  holders.forEach(function (holder) {
    var fo = holder.getElementsByTagName('foreignObject')[0];
    if (!fo) {
      holder.parentNode.removeChild(holder);      // draw.io's "text is not SVG" notice
      return;
    }
    /* Everything is written in the coordinates of the group the label sits in,
     * not the drawing's, because that group may be turning the label — a column
     * heading in these figures is usually on its side. A measured box is upright
     * in screen coordinates whatever the label is doing, so its corners are
     * mapped back through that group's transform, which un-turns them: for the
     * quarter-turns draw.io uses, the box that comes back is the label's own,
     * and drawing into it upright lets the group turn it exactly as before. */
    var parent = holder.parentNode;
    var ctm = parent.getScreenCTM && parent.getScreenCTM();
    if (!ctm) return;
    var inv = ctm.inverse(), pt = holder.ownerSVGElement.createSVGPoint();
    function toParent(box) {
      var xs = [], ys = [];
      [[box.left, box.top], [box.right, box.top],
       [box.right, box.bottom], [box.left, box.bottom]].forEach(function (c) {
        pt.x = c[0]; pt.y = c[1];
        var p = pt.matrixTransform(inv);
        xs.push(p.x); ys.push(p.y);
      });
      var x = Math.min.apply(null, xs), y = Math.min.apply(null, ys);
      return { x: x, y: y, w: Math.max.apply(null, xs) - x, h: Math.max.apply(null, ys) - y };
    }

    if (fo.__math) {
      var math = placeMath(holder, fo, toParent);
      if (math) { holder.parentNode.replaceChild(math, holder); return; }
    }
    var lines = linesOf(words(fo));
    if (!lines.length) return;                    // never silently drop a label
    var frag = document.createDocumentFragment();
    lines.forEach(function (line) {
      var first = line.runs[0].w;
      var m = ascent(first.font);
      var text = document.createElementNS(SVGNS, 'text');
      var s = first.style;
      text.setAttribute('font-family', s.fontFamily);
      text.setAttribute('font-size', parseFloat(s.fontSize) + 'px');
      text.setAttribute('fill', s.color);
      text.setAttribute('text-anchor', 'start');
      text.setAttribute('xml:space', 'preserve');
      if (s.fontWeight === 'bold' || +s.fontWeight >= 600) text.setAttribute('font-weight', 'bold');
      if (s.fontStyle === 'italic') text.setAttribute('font-style', 'italic');
      line.runs.forEach(function (run) {
        var at = toParent(run.w.box);
        // the baseline sits inside the line box by half the leading plus the ascent;
        // lengths survive a rotation, so this offset is the same in either frame
        var baseline = at.y + (run.w.lineHeight - (m.a + m.d)) / 2 + m.a;
        var span = document.createElementNS(SVGNS, 'tspan');
        span.setAttribute('x', round(at.x));
        span.setAttribute('y', round(baseline));
        var rs = run.w.style;
        if (rs.color !== s.color) span.setAttribute('fill', rs.color);
        if (rs.fontWeight !== s.fontWeight) {
          span.setAttribute('font-weight', (+rs.fontWeight >= 600 || rs.fontWeight === 'bold') ? 'bold' : 'normal');
        }
        if (rs.fontStyle !== s.fontStyle) span.setAttribute('font-style', rs.fontStyle);
        if (parseFloat(rs.fontSize) !== parseFloat(s.fontSize)) {
          span.setAttribute('font-size', parseFloat(rs.fontSize) + 'px');
        }
        span.textContent = run.words.join(' ');
        text.appendChild(span);
      });
      frag.appendChild(text);
    });
    holder.parentNode.replaceChild(frag, holder);
  });
}

async function renderAll(drawings, host, stage) {
  var out = { res: {}, errs: {} };
  await MathJax.startup.promise;
  await document.fonts.load("20px 'Architects Daughter'");
  await document.fonts.load("bold 20px 'Architects Daughter'");
  await document.fonts.ready;
  for (var name in drawings) {
    try {
      host.innerHTML = '';
      var holder = document.createElement('div');
      host.appendChild(holder);
      var graph = new Graph(holder);
      graph.setEnabled(false);
      var node = modelNode(drawings[name]);
      new mxCodec(node.ownerDocument).decode(node, graph.getModel());
      var b = graph.getGraphBounds();
      var svg = graph.getSvg(null, 1, 0, true, null, true, true, null, null, false, true);
      stage.innerHTML = '';
      stage.appendChild(svg);              // needs layout before it can be measured
      var fos = [].slice.call(svg.getElementsByTagName('foreignObject'));
      var math = fos.filter(typesetMath).length;
      if (math) await MathJax.startup.promise;    // let the typeset settle before measuring
      replaceLabels(svg);
      var content = svg.getBBox();               // what is really drawn, labels included
      out.res[name] = {
        svg: new XMLSerializer().serializeToString(svg),
        bx: b.x, by: b.y, bw: b.width, bh: b.height,
        cx: content.x, cy: content.y, cw: content.width, ch: content.height,
        math: math
      };
      graph.destroy();
    } catch (e) {
      out.errs[name] = String(e) + ' | ' + (e.stack || '').slice(0, 300);
    }
  }
  stage.innerHTML = '';
  return out;
}

window.addEventListener('load', function () {
  renderAll(window.DIA, document.getElementById('host'), document.getElementById('stage'))
    .then(function (out) { document.getElementById('out').textContent = JSON.stringify(out); })
    .catch(function (e) {
      document.getElementById('out').textContent = JSON.stringify({ res: {}, errs: { _: String(e) } });
    });
});
