"""Navigation and footer for every page of the website.

Both are written from here into the `<!-- site:nav -->` and `<!-- site:footer -->`
markers of each page, the way `rules_page.py` fills the rules. The pages keep
only their own content, so a new menu entry reaches all of them at once
instead of drifting apart. Lizenzen und Credits stehen ausgeschrieben auf
`lizenzen.html`; die Fußzeile verlinkt die Seite, statt sie zu wiederholen.

The menu has three doors; every page and every section of the landing page
hangs under one of them; the repository is reachable from the footer, not from
the menu. `PAGES` adds what differs per page: which entry is current, and the
one line in the footer that says where this page's content comes from.

Only an entry that is a whole page is marked here. The entries that point at a
section of the landing page would all be current at once on that page, so
which of them is current is decided while reading, by `app.js`.
"""
import page_markers

REPOSITORY = 'https://github.com/twphl/busfaktor_1'

MENU = [
    ('Das Spiel', [
        ('spielprinzip.html', 'Spielprinzip'),
        ('regeln.html', 'Regeln'),
        ('spielen.html', 'Im Browser spielen'),
    ]),
    ('Die Karten', [
        ('karten.html', 'Alle 82 Motive'),
        ('generator.html', 'Kartendesigner'),
        ('index.html#auflage', 'Anti-Konferenz-Edition'),
    ]),
    ('Das Projekt', [
        ('index.html#entstehung', 'Entstehung'),
        ('index.html#herkunft', 'Herkunft: PHYLO'),
        ('index.html#mitmachen', 'Mitmachen'),
        ('lizenzen.html', 'Lizenzen'),
        ('../keynote-neustart/index.html', 'Präsentation'),
    ]),
]

FOOTER_LINKS = [
    ('spielprinzip.html', 'Spielprinzip'),
    ('regeln.html', 'Regeln'),
    ('spielen.html', 'Spielen'),
    ('karten.html', 'Karten'),
    ('generator.html', 'Kartendesigner'),
    ('lizenzen.html', 'Lizenzen'),
    (REPOSITORY, 'GitHub'),
]

# Die Herkunftszeile der Fußzeile: was auf dieser Seite steht und woher es kommt.
PAGES = {
    'index.html': None,
    'spielprinzip.html': None,
    'lizenzen.html': None,
    'regeln.html': None,
    'spielen.html': (
        'Regeln aus <code>docs/10-spielregeln.md</code>, Kartentexte aus '
        '<code>data/cards.csv</code>, Bots nach der Regelsimulation in <code>scripts/sim/</code>.'
    ),
    'karten.html': (
        'Kartentexte aus <code>data/cards.csv</code>, Kartenbilder aus der geprüften '
        'Druckstrecke des Repositorys.'
    ),
    'generator.html': (
        'Der Kartendesigner ist eine JavaScript-Portierung von <code>scripts/render_cards.py</code>. '
        'Layout, Farben, Icons und Schriftmetriken kommen unverändert aus dem Python-Renderer.'
    ),
}

EXTERNAL = ' target="_blank" rel="noopener"'


def _slug(label):
    table = {'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss', ' ': '-'}
    return ''.join(table.get(c, c) for c in label.lower() if c.isalnum() or c in table)


def _href(target, page):
    """Anchors of the landing page stay on the page when that page is the landing page."""
    if page == 'index.html' and target.startswith('index.html#'):
        return target[len('index.html'):]
    return target


def _is_external(target):
    return target.startswith('http') or target.startswith('../')


def nav(page):
    lines = [
        '<header class="site-header">',
        f'  <a href="{_href("index.html#top", page)}" class="wordmark"'
        ' aria-label="Busfaktor: 1, zur Startseite">Busfaktor:<em>1</em></a>',
        '  <button class="nav-toggle" id="nav-toggle" aria-expanded="false"'
        ' aria-controls="site-nav" aria-label="Menü öffnen">',
        '    <span></span><span></span><span></span>',
        '  </button>',
        '  <nav class="site-nav" id="site-nav" aria-label="Hauptnavigation">',
    ]
    for title, entries in MENU:
        slug = _slug(title)
        current = any(target == page for target, _ in entries)
        lines += [
            '    <div class="nav-group">',
            f'      <button type="button" class="nav-top{" active" if current else ""}"'
            f' id="{slug}-button" aria-expanded="false" aria-controls="{slug}">{title}</button>',
            f'      <div class="nav-menu" id="{slug}" aria-labelledby="{slug}-button">',
        ]
        for target, label in entries:
            mark = ' class="active" aria-current="page"' if target == page else ''
            suffix = ' ↗' if _is_external(target) else ''
            lines.append(
                f'        <a href="{_href(target, page)}"{mark}'
                f'{EXTERNAL if target.startswith("http") else ""}>{label}{suffix}</a>'
            )
        lines += ['      </div>', '    </div>']
    lines += ['  </nav>', '</header>']
    return '\n'.join(lines)


def footer(page):
    links = []
    for target, label in FOOTER_LINKS:
        external = _is_external(target) or target.endswith('.txt')
        suffix = ' ↗' if _is_external(target) else ''
        mark = ' aria-current="page"' if target == page else ''
        links.append(
            f'      <a class="link" href="{_href(target, page)}"{mark}'
            f'{EXTERNAL if external else ""}>{label}{suffix}</a>'
        )
    source = PAGES[page]
    credits = [
        '        <p class="footer-credits">',
        f'          {source}',
        '        </p>',
    ] if source else []
    return '\n'.join([
        '<footer class="site-footer">',
        '  <div class="container">',
        '    <div class="footer-grid">',
        '      <div class="footer-brand">',
        '        <img class="footer-seal" src="assets/seal-white.svg" alt="" loading="lazy">',
        f'        <a href="{_href("index.html#top", page)}" class="wordmark"'
        ' aria-label="Busfaktor: 1, zur Startseite">Busfaktor:<em>1</em></a>',
        '      </div>',
        '      <div class="footer-middle">',
        '        <nav class="footer-links" aria-label="Weitere Links">',
        *[line.replace('      <a', '          <a') for line in links],
        '        </nav>',
        *credits,
        '      </div>',
        '      <img class="otc-logo" src="assets/otc-logo-full.png"'
        ' alt="Otters of the Coast" loading="lazy">',
        '    </div>',
        '  </div>',
        '</footer>',
    ])


def build(here):
    """Write navigation and footer into every page; returns the pages touched."""
    for page in PAGES:
        path = here / page
        if not path.exists():
            raise ValueError(f'site_chrome: {page} fehlt.')
        filled = page_markers.fill(
            path.read_text(), 'site', {'nav': nav(page), 'footer': footer(page)}, page
        )
        path.write_text(filled)
    return sorted(PAGES)
