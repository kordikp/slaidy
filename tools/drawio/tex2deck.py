#!/usr/bin/env python3
r"""Turn a Beamer lecture into a SlAIdy deck: markdown and SVG.

Written for the uic-beamer macros of the Matrix Factorization lecture (FIT CTU);
a macro it does not know is left visible rather than guessed, so teach it the
next lecture's macros here and import again.

The mapping, in short:

  \begin{frame}{T}          a slide
  \simpleFigure*{s}{png}    the SVG rendered from that PNG, as the slide's figure
  \HO{…}                    the lecture's step-by-step frames. The frames *outside*
                            it are the handout, so those are marked Bestseller
                            and SlAIdy's short run becomes that handout
  \centerBox{…}             the key line — `>` — which is what projects
  \begin{columns}           *Layout:* two, with `<!-- col -->` between them
  pmatrix                   a markdown table: SlAIdy's TeX has no matrix
                            environment, and a rating matrix is a table anyway —
                            rows are users, columns are items
  \pause                    <!-- step -->: what follows waits for the next click
                            (dropped inside braces, where it would split a word)

Speaker notes say what each click adds, read off the labels of the draw.io cells
that appear at that step — one part per click, so the projector's notes show
what is being pointed at while clicking.

    python3 <slaidy>/tools/drawio/tex2deck.py [sources/lecture.tex]   # in the lecture folder
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from steps import cells, series_steps                      # noqa: E402

ROOT = os.getcwd()                      # the lecture folder this is run in


def default_tex(root):
    """The lecture's .tex: the one in sources/, if there is exactly one."""
    import glob as _g
    found = sorted(_g.glob(os.path.join(root, 'sources', '*.tex')))
    return found[0] if len(found) == 1 else None


# ------------------------------------------------------------------ reading

def balanced(s, i):
    """The braced group starting at s[i] == '{': (body, index just after)."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '{' and (j == 0 or s[j - 1] != '\\'):
            depth += 1
        elif s[j] == '}' and s[j - 1] != '\\':
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
    raise ValueError('unbalanced braces')


def frames(tex):
    """[(title, body, stepwise)] in order. stepwise = inside \\HO{…}."""
    spans = []
    for m in re.finditer(r'\\HO\s*\{', tex):
        try:
            spans.append((m.start(), balanced(tex, m.end() - 1)[1]))
        except ValueError:
            pass
    out = []
    for m in re.finditer(r'\\begin\{frame\}', tex):
        i = m.end()
        title = ''
        if i < len(tex) and tex[i] == '{':
            title, i = balanced(tex, i)
        end = tex.find(r'\end{frame}', i)
        if end < 0:
            continue
        out.append((title.strip(), tex[i:end],
                    any(a <= m.start() < b for a, b in spans)))
    return out


# ------------------------------------------------------------------ writing

FIG = re.compile(r'\\simpleFigure(?:Transition)?\s*\{([\d.]+)\}\s*\{([^}]+)\}')
INCLUDE = re.compile(r'\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}')
MATRIX = re.compile(r'\\begin\{pmatrix\}([\s\S]*?)\\end\{pmatrix\}')

INLINE = [(re.compile(r'\\%s\s*\{' % name), a, b) for name, a, b in
          [('emphred', '**', '**'), ('textbf', '**', '**'), ('texttt', '`', '`'),
           ('textit', '*', '*'), ('emph', '*', '*')]]

# Commands that carry nothing a slide needs. The counter ones take TWO braced
# arguments — eating only the first leaves "{-1}" sitting on the slide.
DROP = re.compile(
    r'\\(?:addtocounter|setcounter)\s*\{[^{}]*\}\s*\{[^{}]*\}'
    r'|\\(?:vspace|hspace|footnotesize|normalsize|small|scriptsize|justifying'
    r'|pause|code|HP|HO)\s*(?:\*?\{[^{}]*\})?\*?'
    r'|\\(?:begin|end)\{center\}|\\\\(?=\s*$)')


def unwrap(text, pattern, before, after):
    out, i = [], 0
    while True:
        m = pattern.search(text, i)
        if not m:
            return ''.join(out) + text[i:]
        out.append(text[i:m.start()])
        try:
            body, end = balanced(text, m.end() - 1)
        except ValueError:
            return ''.join(out) + text[m.start():]
        out.append(before + body.strip() + after)
        i = end


# \color survives into the table as bold, so prose that points at "the red
# numbers" has to point at the bold ones instead — otherwise the slide names a
# colour that is no longer on it.
RECOLOURED = ((r'\bred numbers\b', 'numbers in bold'),
              (r'\bnumbers in red\b', 'numbers in bold'))


def recoloured(text):
    for pattern, said in RECOLOURED:
        text = re.sub(pattern, said, text)
    return text


def _cell(text):
    """One matrix entry. \\color{red}{2.3} becomes **2.3**: the slide that uses it
    says the coloured numbers are the predictions, and bold is what a table has."""
    marked = bool(re.search(r'\\color\s*\{[a-z]+\}', text))
    text = re.sub(r'\\color\s*\{[a-z]+\}', '', text).strip().strip('{} ').strip()
    if not text:
        return ' '
    return f'**{text}**' if marked else text


def matrix_table(body, label=''):
    rows = [r.strip() for r in body.split(r'\\') if r.strip()]
    grid = [[_cell(c) for c in r.split('&')] for r in rows]
    width = max(len(r) for r in grid)
    head = '| ' + ' | '.join([label] + [''] * (width - 1)) + ' |'
    return '\n'.join([head, '|' + '---|' * width]
                     + ['| ' + ' | '.join(r + [''] * (width - len(r))) + ' |' for r in grid])


def lift_matrices(inner):
    """A display holding matrices becomes one table per matrix, each labelled."""
    out, last = [], 0
    for hit in MATRIX.finditer(inner):
        label = inner[last:hit.start()]
        label = re.sub(r'\\quad|\\text\s*\{[^}]*\}|\band\b', ' ', label)
        label = re.sub(r'\\\\|\\!|~', ' ', label)
        label = re.sub(r'^[\s.=]+|[\s.=]+$', '', label.strip()).strip()
        out.append(matrix_table(hit.group(1), f'${label}$' if label else ''))
        last = hit.end()
    tail = re.sub(r'[\s.]+', '', inner[last:])
    return '\n\n' + '\n\n'.join(out) + '\n\n' + (f'{tail}\n\n' if tail else '')


def convert_math(text):
    def display(m):
        return lift_matrices(m.group(1)) if MATRIX.search(m.group(1)) else m.group(0)
    text = re.sub(r'\$\$([\s\S]*?)\$\$', display, text)
    text = re.sub(r'\\begin\{multline\*?\}([\s\S]*?)\\end\{multline\*?\}',
                  lambda m: lift_matrices(m.group(1)) if MATRIX.search(m.group(1))
                  else '$$' + m.group(1).replace('\\\\', ' ') + '$$', text)
    text = MATRIX.sub(lambda m: '\n\n' + matrix_table(m.group(1)) + '\n\n', text)
    # SlAIdy's TeX has no \{ …    say it in words instead of showing broken TeX
    text = text.replace(r'\mathbb{R} \cup \{ ? \}', r'\mathbb{R}')
    # "$5$ stars" renders as the literal $5$: SlAIdy leaves `$5` alone so that a
    # price is not read as a formula. A bare number does not need to be one.
    text = re.sub(r'(?<![\w$])\$(-?\d+(?:\.\d+)?)\$(?!\$)', r'\1', text)
    # "$\forall i \in \mathcal{U}, $" — a space before the closing $ stops SlAIdy
    # reading it as maths at all, and the TeX shows through on the slide.
    text = re.sub(r'(?<!\$)\$[ \t]*([^$\n]+?)[ \t]*\$(?!\$)', r'$\1$', text)
    return text


PAUSE = '\n\n<!-- step -->\n\n'


def split_pauses(text, keep=True):
    r"""\pause becomes a step marker — but only where a block can start.

    The lecture writes `\textbf{Fernando Pessoa\pause :}`, and a marker inside
    the braces of an inline command cuts the command in half: the slide then
    shows `**Fernando Pessoa` and `:**` as two broken items. Inside a group the
    pause is dropped instead, which is what the reader sees anyway.
    """
    out, depth, i = [], 0, 0
    for m in re.finditer(r'\\pause\b\s*|[{}]', text):
        token = m.group(0)
        if token == '{':
            depth += 1
        elif token == '}':
            depth = max(0, depth - 1)
        else:
            out.append(text[i:m.start()])
            out.append(PAUSE if (keep and depth == 0) else '')
            i = m.end()
    return ''.join(out) + text[i:]


def clean(text, pauses=True):
    text = split_pauses(text, pauses)
    if re.search(r'\\color\s*\{red\}', text):
        text = recoloured(text)
    text = convert_math(text)
    for pattern, a, b in INLINE:
        text = unwrap(text, pattern, a, b)
    text = unwrap(text, re.compile(r'\\centerBox\s*\{'), '\n\n> ', '\n\n')
    text = unwrap(text, re.compile(r'\\normalBox\s*\{'), '\n\n> ', '\n\n')
    text = re.sub(r'\\hrefcol\s*\{([^}]*)\}\s*\{([^}]*)\}', r'[\2](\1)', text)
    text = re.sub(r'\\href\s*\{([^}]*)\}\s*\{([^}]*)\}', r'[\2](\1)', text)
    text = re.sub(r'\\begin\{block\}\s*\{([^}]*)\}', r'\n\n#### \1\n\n', text)
    text = text.replace(r'\end{block}', '\n\n')
    text = DROP.sub('', text)
    text = re.sub(r'(?<!\\)\{\s*\}', '', text)      # what a dropped command left behind
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def bullets(body):
    r"""\begin{itemize} … \item … as markdown bullets, nesting kept.

    Split before anything is cleaned: \item is one of the commands `clean`
    drops, so cleaning first turns every list in the lecture into one paragraph.
    """
    lines, depth, pending = [], 0, None
    for chunk in re.split(r'(\\begin\{itemize\}|\\end\{itemize\}|\\item\b)', body):
        token = chunk.strip()
        if token == r'\begin{itemize}':
            depth += 1
        elif token == r'\end{itemize}':
            depth = max(0, depth - 1)
        elif token == r'\item':
            pending = max(depth, 1)
        else:
            text = clean(chunk)
            if not text:
                continue
            if pending:
                pad = '  ' * (pending - 1)
                # a marker inside an item ends the list and starts another after
                # it: the marker has to be a block of its own to hold anything back
                head, sep, tail = text.partition(PAUSE.strip())
                first, *rest = head.split('\n')
                lines.append(f'{pad}- {first}')
                lines += [(pad + '  ' + r if r.strip() else '') for r in rest]
                if sep:
                    lines.append(PAUSE.strip())
                    if tail.strip():
                        lines.append(f'{pad}- {tail.strip()}')
                pending = None
            else:
                lines.append(text)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def tidy_steps(md):
    """A step marker only means something with content on both sides of it.

    The lecture opens a frame with a bare \\pause before the picture — "title
    first, then the drawing" — which leaves a marker with nothing before it, and
    a slide whose body is only markers is a slide with no body at all.
    """
    marker = PAUSE.strip()
    md = re.sub(r'(?:%s\s*)+' % re.escape(marker), marker + '\n\n', md)
    md = re.sub(r'^\s*(?:%s\s*)+' % re.escape(marker), '', md)
    md = re.sub(r'(?:\s*%s)+\s*$' % re.escape(marker), '', md)
    return md.strip()


def body_markdown(body):
    """(markdown, is_two_column)"""
    columns = [balanced(body, m.end() - 1)[0]
               for m in re.finditer(r'\\columnSlide\s*\{[\d.]+\}\s*\{', body)]
    if columns:
        return tidy_steps('\n\n<!-- col -->\n\n'.join(bullets(c) for c in columns)), True
    return tidy_steps(bullets(re.sub(r'\\(?:begin|end)\{columns\}', '', body))), False


# ------------------------------------------------- what each click reveals

# A speaker note is read, not typeset, so the TeX in a label is spelled out.
TEX_TEXT = [
    (r'\\sqrt\s*\{([^{}]*)\}', r'√\1'), (r'\\hat\s*\{([^{}]*)\}', '\\1\u0302'),
    (r'\\mathcal\s*\{([^{}]*)\}', r'\1'), (r'\\mathbf\s*\{([^{}]*)\}', r'\1'),
    (r'\\text\s*\{([^{}]*)\}', r'\1'),
    (r'\\times', '×'), (r'\\top', '⊤'), (r'\\Omega', 'Ω'), (r'\\lambda', 'λ'),
    (r'\\approx', '≈'), (r'\\rho', 'ρ'), (r'\\langle', '⟨'), (r'\\rangle', '⟩'),
    (r'\\min', 'min'), (r'\\sum', 'Σ'), (r'\\in\b', '∈'),
]


def spell_out(label):
    """`$$R_{\\Omega^i}$$` reads as R_Ω^i in a note, not as TeX."""
    text = re.sub(r'^\s*\$\$?|\$\$?\s*$', '', label.strip())
    for pattern, said in TEX_TEXT:
        text = re.sub(pattern, said, text)
    text = re.sub(r'[{}]', '', text).replace('\\', '')
    return re.sub(r'\s+', ' ', text).strip()


def reveal_notes(drawio_dir, index):
    """{figure id: [what each click adds, one entry per step]}.

    Read off the labels of the draw.io cells that appear at each step, so the
    note under a slide is the thing being pointed at while clicking.
    """
    notes = {}
    for fid, meta in index.items():
        sources = meta.get('sources') or ([meta['source']] if meta.get('source') else [])
        if meta.get('bitmap') or len(sources) < 2:
            notes[fid] = []
            continue
        paths = [os.path.join(drawio_dir, src[:-4] + '.drawio') for src in sources]
        said = []
        for i, (path, fresh) in enumerate(series_steps(paths), 1):
            model, labels = cells(path), []
            for cid in fresh:
                value = re.sub(r'<[^>]+>', ' ', model.get(cid, {}).get('value', ''))
                value = re.sub(r'\s+', ' ', value.replace('&nbsp;', ' ')).strip()
                if '$' in value:
                    value = spell_out(value)
                if value and value not in labels:
                    labels.append(value)
            said.append(click_note(labels, i, len(paths)))
        notes[fid] = said
    return notes


def order_of(sections):
    """Every slide written so far, so the next one can be numbered."""
    return [c for chunks in sections.values() for c in chunks]


def click_note(labels, step, of):
    """One line saying what this click puts on the slide."""
    if step == 1:
        return f'It opens with the drawing as it stands; {of - 1} clicks build it up.'
    if not labels:
        return f'Click {step}: the same shapes, drawn differently — a change of emphasis.'
    shown = [x for x in labels if 0 < len(x) < 70][:6]
    if not shown:
        return f'Click {step} brings in {len(labels)} more parts of the drawing.'
    more = f' — and {len(labels) - len(shown)} more' if len(labels) > len(shown) else ''
    said = f'Click {step} adds: ' + ' · '.join(shown) + more
    return said if said[-1] in '.!?' else said + '.'


# ---------------------------------------------------------------- assembly

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tex', nargs='?', default=default_tex(ROOT))
    ap.add_argument('--figures', default=os.path.join(ROOT, 'figures'))
    ap.add_argument('--drawio', default=os.path.join(ROOT, 'drawio'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'deck', 'slides'))
    ap.add_argument('--outline', default=os.path.join(ROOT, 'deck', 'outline.json'))
    ap.add_argument('--force', action='store_true',
                    help='overwrite slides that already exist (they may be hand-edited)')
    a = ap.parse_args()

    existing = [f for f in os.listdir(a.out) if f.endswith('.md')] if os.path.isdir(a.out) else []
    if existing and not a.force:
        sys.exit(f'{a.out} already holds {len(existing)} markdown files. This importer runs '
                 'once; after it, the markdown is the deck. Re-run with --force to replace it.')

    index = json.load(open(os.path.join(a.figures, 'index.json')))
    # a merged figure answers to every PNG it was built from
    by_source = {src: fid for fid, meta in index.items()
                 for src in (meta.get('sources') or [meta.get('source')]) if src}
    notes = reveal_notes(a.drawio, index)
    outline = json.load(open(a.outline)) if os.path.exists(a.outline) else {}

    whole = re.sub(r'(?<!\\)%.*', '', open(a.tex).read())
    preamble = whole[:whole.index(r'\begin{document}')]

    def field(name, default=''):
        m = re.search(r'\\' + name + r'\s*\{', preamble)
        return balanced(preamble, m.end() - 1)[0].strip() if m else default

    tex = whole[whole.index(r'\begin{document}'):]

    os.makedirs(a.out, exist_ok=True)
    for old in os.listdir(a.out):
        if old.endswith('.md'):
            os.remove(os.path.join(a.out, old))

    author = clean(field('author', ''))
    cover = ['### 1. `[S]` ' + field('title', 'Lecture'), '', '*Layout:* cover', '',
             '#### ' + field('subtitle', ''), '', author + ' · ' + field('date', ''), '',
             '*Delivery note:* Imported from ' + os.path.basename(a.tex)
             + '. Every picture is the drawing draw.io left inside the slide PNG, '
               'rendered back to SVG; a click is a step of that drawing.', '']
    sections, section = {'Cover': ['\n'.join(cover)]}, 'Cover'
    section = None
    # A merged figure holds the whole series, so the run of frames that used to
    # be one PNG each is one slide the projector clicks through. The frames after
    # the first one carry nothing new — their picture is already on the slide.
    last_fig, n = None, 1        # 1 is the cover, so the outline counts frames from 2
    for title, body, stepwise in frames(tex):
        n += 1
        section = outline.get(str(n), section) or 'Lecture'
        pictures = ([(name if name.endswith('.png') else name + '.png')
                     for _, name in FIG.findall(body)]
                    + [g for g in INCLUDE.findall(body)])
        figs = [by_source[p] for p in pictures if p in by_source]
        text, two_column = body_markdown(FIG.sub('', INCLUDE.sub('', body)))
        has_code = bool(re.search(r'\\code\b', title))
        title = re.sub(r'\\code\b', '', title).strip()

        if figs and figs == [last_fig] and not text:
            continue                       # another click of the slide already written
        last_fig = figs[0] if len(figs) == 1 and not text else None

        out = [f'### {len(order_of(sections)) + 1}. `[{"D" if text else "S"}]` {title}', '']
        if two_column:
            out += ['*Layout:* two', '']
        for png in pictures:
            out += [f'![[{by_source.get(png, png[:-4])}|100%]]', '']
        if text:
            out += [text, '']
        said = []
        for fid in figs:
            said += [x for x in notes.get(fid, []) if x]
        code = ['The original lecture has code for this one.'] if has_code else []
        clicks = notes.get(figs[0], []) if len(figs) == 1 else []
        if len(clicks) > 1:
            # one part per click, so the projector's notes follow the clicking
            out += ['*Delivery note:* ' + '\n\n<!-- step -->\n\n'.join(clicks) + ''.join(' ' + c for c in code), '']
        elif said or code:
            out += ['*Delivery note:* ' + ' ¶ '.join(said + code), '']
        sections.setdefault(section, []).append('\n'.join(out))

    for i, (name, chunks) in enumerate(sections.items(), 1):
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:48]
        path = os.path.join(a.out, f'{i:02d}-{slug}.md')
        open(path, 'w').write(f'# {name}\n\n' + '\n'.join(chunks).rstrip() + '\n')
        print(f'  {len(chunks):3d}  {os.path.basename(path)}')
    written = sum(len(c) for c in sections.values())
    print(f'{written} slides in {len(sections)} sections, from {n - 1} frames of LaTeX.')


if __name__ == '__main__':
    main()
