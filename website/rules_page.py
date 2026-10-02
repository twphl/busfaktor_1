"""Render the canonical rules (docs/10-spielregeln.md) into regeln.html.

The rules use a small, fixed part of Markdown: ATX headings, paragraphs, flat
bullet and numbered lists, block quotes, pipe tables, bold, italics, inline
code and links. This module converts exactly that and refuses anything else
(nested lists, code blocks, raw HTML, deeper headings), so a new construct in
the rules stops the build instead of rendering wrong.

On top of the plain conversion it adds what the page needs:

- every `##` chapter becomes a <section> with a German slug and a TOC entry;
- `§4` links to that chapter, `ADR 0010` to the ADR in the repository;
- inline code is sorted: repository files link to GitHub, card names link to
  their detail view in karten.html, all-caps keywords get the keyword style;
- `### Beispiel` subsections are set off as examples.

prepare.py writes the result between the `<!-- regeln:NAME -->` and
`<!-- /regeln:NAME -->` markers in regeln.html; the page shell around them
stays hand-written like index.html and generator.html.
"""
import html
import re

import page_markers

REPOSITORY_BLOB = 'https://github.com/twphl/busfaktor_1/blob/main/'

HEADING = re.compile(r'(#{1,6})\s+(.+?)\s*#*\s*$')
BULLET = re.compile(r'[-*+]\s+(.*)')
ORDERED = re.compile(r'(\d+)[.)]\s+(.*)')
THEMATIC_BREAK = re.compile(r'(?:-{3,}|\*{3,}|_{3,})\s*$')
META = re.compile(r'([A-ZÄÖÜ][\wäöüß]*):\s+(.+)')

CHAPTER = re.compile(r'(\d+)\.\s+(.+)')
SUBHEADING_LABEL = re.compile(r'(\d+(?:\.\d+)+|E\d+)\s+(?:[–-]\s+)?(.+)')

CODE = re.compile(r'`([^`]+)`')
LINK = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)')
BOLD = re.compile(r'\*\*(.+?)\*\*')
ITALIC = re.compile(r'(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])')
SECTION_REF = re.compile(r'§\s?(\d+)')
ADR_REF = re.compile(r'\bADR (\d{4})\b')
KEYWORD = re.compile(r'[A-ZÄÖÜ]{3,}')
FILE_LIKE = re.compile(r'[\w./-]+\.[a-z]{2,4}')

_UMLAUTS = str.maketrans({
    'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue',
})


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.translate(_UMLAUTS).lower()).strip('-')


def _external(url, label):
    return (
        f'<a class="link" href="{html.escape(url)}" target="_blank" rel="noopener">'
        f'{label} ↗</a>'
    )


# ---------- blocks ----------

def _starts_block(line):
    ordered = ORDERED.match(line)
    return bool(
        HEADING.match(line) or BULLET.match(line) or (ordered and ordered[1] == '1')
        or line.startswith(('>', '|')) or THEMATIC_BREAK.match(line)
    )


def _parse_list(lines, i, ordered):
    marker = ORDERED if ordered else BULLET
    start = int(ORDERED.match(lines[i])[1]) if ordered else 1
    items = []
    while i < len(lines):
        line = lines[i]
        match = marker.match(line)
        if match:
            items.append([match[match.lastindex]])
        elif line.strip():
            stripped = line.strip()
            indented = line[0] in ' \t'
            if indented and (BULLET.match(stripped) or ORDERED.match(stripped)):
                raise ValueError(
                    f'Zeile {i + 1}: verschachtelte Listen sind in den Regeln nicht vorgesehen'
                )
            if not indented and _starts_block(line):
                break
            items[-1].append(stripped)
        elif i + 1 < len(lines) and marker.match(lines[i + 1]):
            pass  # blank line between two items of the same list
        else:
            break
        i += 1
    return items, start, i


def parse_blocks(text):
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith(('```', '~~~', '    ', '\t', '<')):
            raise ValueError(
                f'Zeile {i + 1}: Codeblöcke und HTML sind in den Regeln nicht vorgesehen: {line!r}'
            )
        elif match := HEADING.match(line):
            blocks.append(('heading', len(match[1]), match[2]))
            i += 1
        elif THEMATIC_BREAK.match(line):
            blocks.append(('break',))
            i += 1
        elif line.startswith('>'):
            quote = []
            while i < len(lines) and lines[i].startswith('>'):
                quote.append(lines[i][1:].strip())
                i += 1
            blocks.append(('quote', quote))
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i])
                i += 1
            blocks.append(('table', rows))
        elif BULLET.match(line) or ORDERED.match(line):
            ordered = bool(ORDERED.match(line))
            items, start, i = _parse_list(lines, i, ordered)
            blocks.append(('list', ordered, start, items))
        else:
            paragraph = []
            while i < len(lines) and lines[i].strip():
                if paragraph and _starts_block(lines[i]):
                    break
                paragraph.append(lines[i].strip())
                i += 1
            blocks.append(('paragraph', paragraph))
    return blocks


# ---------- inline ----------

class Inline:
    """Inline Markdown plus the page's own links; collects doubtful card names."""

    def __init__(self, chapters, cards, root):
        self.chapters = chapters
        self.cards = cards
        self.root = root
        self.unknown = []

    def __call__(self, text):
        parts = CODE.split(text)
        return ''.join(
            self.code(part) if index % 2 else self.text(part) for index, part in enumerate(parts)
        )

    def text(self, text):
        text = html.escape(text, quote=False)
        text = SECTION_REF.sub(self._section_ref, text)
        text = ADR_REF.sub(self._adr_ref, text)
        text = LINK.sub(self._link, text)
        text = BOLD.sub(r'<strong>\1</strong>', text)
        return ITALIC.sub(r'<em>\1</em>', text)

    def code(self, text):
        path = self._repository_file(text)
        if path:
            return _external(REPOSITORY_BLOB + path, html.escape(path))
        if text in self.cards:
            card_id = self.cards[text]
            return f'<a class="card-ref" href="karten.html#{card_id}">{html.escape(text)}</a>'
        if KEYWORD.fullmatch(text):
            return f'<span class="keyword">{html.escape(text)}</span>'
        if FILE_LIKE.fullmatch(text) or not re.search(r'\d', text):
            self.unknown.append(text)
        return f'<code>{html.escape(text)}</code>'

    def _repository_file(self, text):
        if not FILE_LIKE.fullmatch(text):
            return None
        for base in (self.root / 'docs', self.root):
            candidate = (base / text).resolve()
            if candidate.is_file() and candidate.is_relative_to(self.root):
                return candidate.relative_to(self.root).as_posix()
        return None

    def _section_ref(self, match):
        slug = self.chapters.get(match[1])
        if not slug:
            raise ValueError(f'{match[0]} verweist auf keinen Abschnitt der Regeln')
        return f'<a class="rule-ref" href="#{slug}">§ {match[1]}</a>'

    def _adr_ref(self, match):
        found = sorted((self.root / 'docs/adr').glob(f'{match[1]}-*.md'))
        if len(found) != 1:
            return match[0]
        return _external(REPOSITORY_BLOB + found[0].relative_to(self.root).as_posix(), match[0])

    def _link(self, match):
        label, target = match[1], html.unescape(match[2])
        if target.startswith(('http://', 'https://')):
            return _external(target, label)
        if target.startswith('#'):
            return f'<a class="link" href="{html.escape(target)}">{label}</a>'
        path = self._repository_file(target)
        if not path:
            raise ValueError(f'Link auf {target} führt zu keiner Datei im Repository')
        return _external(REPOSITORY_BLOB + path, label)


# ---------- rendering ----------

def _split_row(row):
    return [cell.strip() for cell in row.strip().strip('|').split('|')]


def _alignment(cell):
    if cell.startswith(':') and cell.endswith(':'):
        return 'center'
    return 'right' if cell.endswith(':') else None


def _render_table(rows, inline):
    header, rule, *body = [_split_row(row) for row in rows]
    if len(rule) != len(header) or not all(re.fullmatch(r':?-{3,}:?', cell) for cell in rule):
        raise ValueError(f'Tabelle ohne gültige Trennzeile: {rows[1]!r}')
    align = [_alignment(cell) for cell in rule]

    def row_html(tag, cells):
        scope = ' scope="col"' if tag == 'th' else ''
        out = ''
        for column, text in enumerate(cells):
            style = f' style="text-align:{align[column]}"' if align[column] else ''
            out += f'<{tag}{scope}{style}>{inline(text)}</{tag}>'
        return f'<tr>{out}</tr>'

    lines = ['<div class="rule-table">', '<table>', f'<thead>{row_html("th", header)}</thead>']
    lines.append('<tbody>')
    for row in body:
        if len(row) != len(header):
            raise ValueError(f'Tabellenzeile mit {len(row)} statt {len(header)} Spalten: {row!r}')
        lines.append(row_html('td', row))
    return lines + ['</tbody>', '</table>', '</div>']


def _render_block(block, inline):
    kind = block[0]
    if kind == 'paragraph':
        return [f'<p>{inline(" ".join(block[1]))}</p>']
    if kind == 'list':
        _, ordered, start, items = block
        tag = 'ol' if ordered else 'ul'
        start_attr = f' start="{start}"' if ordered and start != 1 else ''
        entries = [f'  <li>{inline(" ".join(item))}</li>' for item in items]
        return [f'<{tag}{start_attr}>', *entries, f'</{tag}>']
    if kind == 'quote':
        paragraphs = ' '.join(line or '\n' for line in block[1]).split('\n')
        entries = [f'  <p>{inline(p.strip())}</p>' for p in paragraphs if p.strip()]
        return ['<blockquote>', *entries, '</blockquote>']
    if kind == 'table':
        return _render_table(block[1], inline)
    if kind == 'break':
        return ['<hr>']
    raise ValueError(f'Unbekannter Block: {kind}')


def _heading_label(text):
    match = SUBHEADING_LABEL.fullmatch(text)
    return (match[1], match[2]) if match else (None, text)


def _render_chapter(chapter, inline, used_ids):
    slug = chapter['slug']
    classes = 'rule rule-quickref' if slug == 'kurzreferenz' else 'rule'
    lines = [
        f'<section class="{classes}" id="{slug}">',
        (
            f'  <h2><a class="rule-no" href="#{slug}">§ {chapter["number"]}</a> '
            f'<span>{html.escape(chapter["title"])}</span></h2>'
        ),
    ]
    open_sub = False
    for block in chapter['blocks']:
        if block[0] == 'subheading':
            if open_sub:
                lines.append('  </div>')
            label, title = _heading_label(block[1])
            sub_slug = f'{slug}-{slugify(title)}'
            if sub_slug in used_ids:
                raise ValueError(
                    f'Doppelte Zwischenüberschrift in §{chapter["number"]}: {block[1]}'
                )
            used_ids.add(sub_slug)
            example = ' rule-example' if 'beispiel' in title.lower() else ''
            number = f'<span class="rule-no">{html.escape(label)}</span> ' if label else ''
            lines.append(f'  <div class="rule-sub{example}">')
            lines.append(f'    <h3 id="{sub_slug}">{number}{inline(title)}</h3>')
            open_sub = True
        else:
            indent = '    ' if open_sub else '  '
            lines += [indent + line for line in _render_block(block, inline)]
    if open_sub:
        lines.append('  </div>')
    return lines + ['</section>']


def _format_date(value):
    match = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', value)
    return f'{match[3]}.{match[2]}.{match[1]}' if match else value


def _outline(markdown):
    """Split the rules into title, metadata lines, preamble blocks and chapters."""
    title, meta, preamble, chapters = None, {}, [], []
    for block in parse_blocks(markdown):
        if block[0] == 'heading':
            level, text = block[1], block[2]
            if level == 1 and title is None and not chapters:
                title = text
            elif level == 2:
                match = CHAPTER.fullmatch(text)
                if not match:
                    raise ValueError(f'Kapitel ohne Nummer: {text!r}')
                chapters.append({
                    'number': match[1], 'title': match[2], 'slug': slugify(match[2]), 'blocks': [],
                })
            elif level == 3 and chapters:
                chapters[-1]['blocks'].append(('subheading', text))
            else:
                raise ValueError(f'Überschrift hier nicht vorgesehen: {"#" * level} {text}')
        elif chapters:
            chapters[-1]['blocks'].append(block)
        elif (
            block[0] == 'paragraph' and len(block[1]) == 1 and not preamble
            and (match := META.fullmatch(block[1][0]))
        ):
            meta[match[1]] = match[2]
        else:
            preamble.append(block)

    if title is None or not chapters:
        raise ValueError('Die Regeln brauchen eine Hauptüberschrift und nummerierte Kapitel.')
    if 'Version' not in meta or 'Stand' not in meta:
        raise ValueError('Version und Stand fehlen am Anfang der Regeln.')
    slugs = [chapter['slug'] for chapter in chapters]
    if len(set(slugs)) != len(slugs):
        raise ValueError('Zwei Kapitel ergeben denselben Anker.')
    return meta, preamble, chapters


def render(markdown, cards, root):
    """Return the page fragments ({marker name: HTML}) and doubtful inline code."""
    meta, preamble, chapters = _outline(markdown)
    inline = Inline({chapter['number']: chapter['slug'] for chapter in chapters}, cards, root)
    used_ids = {chapter['slug'] for chapter in chapters}

    toc = [
        '<nav class="rules-toc" aria-label="Inhalt der Regeln">',
        '  <details open>',
        '    <summary>Inhalt</summary>',
        '    <ol>',
    ]
    for chapter in chapters:
        toc.append(
            f'      <li><a href="#{chapter["slug"]}"><span>{chapter["number"]}</span>'
            f'{html.escape(chapter["title"])}</a></li>'
        )
    toc += ['    </ol>', '  </details>', '</nav>']

    article = ['<article class="rules-body">']
    if preamble:
        article.append('  <div class="rules-preamble">')
        for block in preamble:
            article += ['    ' + line for line in _render_block(block, inline)]
        article.append('  </div>')
    for chapter in chapters:
        article += ['  ' + line for line in _render_chapter(chapter, inline, used_ids)]
    article.append('</article>')

    stand = [f'Version {meta["Version"]}', f'Stand {_format_date(meta["Stand"])}']
    fragments = {
        'stand': html.escape(' · '.join(stand)),
        'inhalt': '\n'.join(toc + article),
    }
    return fragments, sorted(set(inline.unknown))


def build(page_path, markdown, cards, root):
    """Fill regeln.html in place; returns inline code that looks like an unknown card name."""
    fragments, unknown = render(markdown, cards, root)
    page = page_markers.fill(page_path.read_text(), 'regeln', fragments, 'regeln.html')
    ids = set(re.findall(r'\sid="([^"]+)"', page))
    missing = sorted(set(re.findall(r'href="#([^"]+)"', page)) - ids)
    if missing:
        raise ValueError(f'regeln.html verlinkt Anker, die es nicht gibt: {", ".join(missing)}')
    page_path.write_text(page)
    return unknown
