"""Generate canonical and social metadata from each page's existing copy."""
import argparse
import json
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import page_markers
from site_chrome import PAGES

IMAGE_PATH = 'assets/social-preview.png'
IMAGE_ALT = (
    'Wortmarke Busfaktor: 1, der Satz Endlich spielend scheitern, '
    'Ottersiegel und drei Karten aus dem Set.'
)


class _HeadCopy(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.in_title = False
        self.titles = []
        self.descriptions = []

    def handle_starttag(self, tag, attrs):
        if tag == 'head':
            self.in_head = True
        if not self.in_head:
            return
        attrs = dict(attrs)
        if tag == 'title':
            self.in_title = True
            self.titles.append('')
        elif tag == 'meta' and attrs.get('name', '').lower() == 'description':
            self.descriptions.append(attrs.get('content', ''))

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        elif tag == 'head':
            self.in_head = False

    def handle_data(self, data):
        if self.in_head and self.in_title:
            self.titles[-1] += data


def _page_copy(page, label):
    parser = _HeadCopy()
    parser.feed(page)
    if len(parser.titles) != 1 or not parser.titles[0].strip():
        raise ValueError(f'{label}: Genau ein nicht leerer Seitentitel ist erforderlich.')
    if len(parser.descriptions) != 1 or not parser.descriptions[0].strip():
        raise ValueError(f'{label}: Genau eine nicht leere description ist erforderlich.')
    return parser.titles[0].strip(), parser.descriptions[0].strip()


def _base_url(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            'social_meta: Öffentliche Basis-URL fehlt. '
            'base_url in website/site-config.json setzen oder --base-url übergeben.'
        )
    value = value.strip()
    parts = urlsplit(value)
    if (
        parts.scheme not in ('https', 'http') or not parts.hostname
        or parts.username is not None or parts.password is not None
        or parts.query or parts.fragment or '?' in value or '#' in value
        or any(char.isspace() for char in value)
        or any(segment in ('.', '..') for segment in parts.path.split('/'))
    ):
        raise ValueError('social_meta: Basis-URL muss eine absolute HTTP(S)-URL ohne Zugangsdaten, Query oder Fragment sein.')
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip('/') + '/', '', ''))


def _fragment(title, description, canonical, image_url, config):
    def meta(key, value, *, property=False):
        attribute = 'property' if property else 'name'
        return f'<meta {attribute}="{key}" content="{escape(str(value), quote=True)}">'

    return '\n'.join([
        f'<link rel="canonical" href="{escape(canonical, quote=True)}">',
        meta('og:title', title, property=True),
        meta('og:type', 'website', property=True),
        meta('og:url', canonical, property=True),
        meta('og:site_name', config['site_name'], property=True),
        meta('og:locale', config['locale'], property=True),
        meta('og:description', description, property=True),
        meta('og:image', image_url, property=True),
        meta('og:image:type', 'image/png', property=True),
        meta('og:image:width', 1200, property=True),
        meta('og:image:height', 630, property=True),
        meta('og:image:alt', IMAGE_ALT, property=True),
        meta('twitter:card', 'summary_large_image'),
        meta('twitter:title', title),
        meta('twitter:description', description),
        meta('twitter:image', image_url),
        meta('twitter:image:alt', IMAGE_ALT),
    ])


def build(here, *, base_url=None):
    """Fill all productive pages; preserve a deployment subpath in every URL."""
    here = Path(here)
    config = json.loads((here / 'site-config.json').read_text())
    base = _base_url(base_url if base_url is not None else config.get('base_url'))
    for key in ('site_name', 'locale'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f'social_meta: {key} fehlt in website/site-config.json.')
    image_url = base + IMAGE_PATH
    pages = {}
    for name in sorted(PAGES):
        path = here / name
        page = path.read_text()
        title, description = _page_copy(page, name)
        canonical = base if name == 'index.html' else base + name
        fragment = _fragment(title, description, canonical, image_url, config)
        pages[path] = page_markers.fill(page, 'social', {'meta': fragment}, name)
    # Validate every page before changing any of them.
    for path, page in pages.items():
        if path.read_text() != page:
            path.write_text(page)
    return sorted(PAGES)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Open-Graph- und Canonical-Metadaten der Website erzeugen.')
    parser.add_argument('--base-url', help='Öffentliche Basis-URL, einschließlich eines optionalen Unterpfads')
    args = parser.parse_args()
    print('Social-Metadaten: ' + ', '.join(build(Path(__file__).resolve().parent, base_url=args.base_url)))
