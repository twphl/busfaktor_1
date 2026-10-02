"""Checks for deployment URLs, page-specific copy, and repeatable generation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

WEBSITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEBSITE))
import social_meta


class SocialMetaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.here = Path(self.temp.name)
        self.config = {'base_url': 'https://example.org/game', 'site_name': 'Busfaktor: 1', 'locale': 'de_DE'}
        self.write_config()
        for name in social_meta.PAGES:
            (self.here / name).write_text(
                '<html><head>\n'
                f'<title>{name} &amp; „Karten“</title>\n'
                '<meta name="description" content="Forschung &amp; &quot;Spiel&quot;">\n'
                '<!-- social:meta -->\n<!-- /social:meta -->\n'
                '</head><body>Unverändert.</body></html>'
            )

    def write_config(self):
        (self.here / 'site-config.json').write_text(json.dumps(self.config))

    def test_subpath_page_copy_escaping_and_idempotence(self):
        self.assertEqual(social_meta.build(self.here), sorted(social_meta.PAGES))
        index = (self.here / 'index.html').read_text()
        cards = (self.here / 'karten.html').read_text()
        self.assertIn('rel="canonical" href="https://example.org/game/"', index)
        self.assertIn('property="og:url" content="https://example.org/game/karten.html"', cards)
        self.assertIn('property="og:image" content="https://example.org/game/assets/social-preview.png"', cards)
        self.assertIn('property="og:title" content="karten.html &amp; „Karten“"', cards)
        self.assertIn('name="twitter:description" content="Forschung &amp; &quot;Spiel&quot;"', cards)
        self.assertIn('property="og:image:width" content="1200"', cards)
        self.assertIn('property="og:image:height" content="630"', cards)
        self.assertIn('</head><body>Unverändert.</body></html>', cards)
        before = {name: (self.here / name).read_bytes() for name in social_meta.PAGES}
        social_meta.build(self.here)
        self.assertEqual(before, {name: (self.here / name).read_bytes() for name in social_meta.PAGES})

    def test_override_and_root_url(self):
        social_meta.build(self.here, base_url='https://example.net/')
        self.assertIn(
            'rel="canonical" href="https://example.net/"',
            (self.here / 'index.html').read_text(),
        )
        self.assertIn(
            'property="og:image" content="https://example.net/assets/social-preview.png"',
            (self.here / 'index.html').read_text(),
        )

    def test_missing_or_invalid_url_does_not_write(self):
        before = {name: (self.here / name).read_bytes() for name in social_meta.PAGES}
        for value in [None, '', '/game/', 'https://example.org/?preview=1',
                      'https://user:secret@example.org/', 'https://example.org/#top']:
            with self.subTest(value=value):
                self.config['base_url'] = value
                self.write_config()
                with self.assertRaises(ValueError):
                    social_meta.build(self.here)
        self.assertEqual(before, {name: (self.here / name).read_bytes() for name in social_meta.PAGES})

    def test_invalid_last_page_does_not_partially_write(self):
        last = sorted(social_meta.PAGES)[-1]
        path = self.here / last
        path.write_text(path.read_text().replace('<!-- /social:meta -->', ''))
        before = {name: (self.here / name).read_bytes() for name in social_meta.PAGES}
        with self.assertRaises(ValueError):
            social_meta.build(self.here)
        self.assertEqual(before, {name: (self.here / name).read_bytes() for name in social_meta.PAGES})


if __name__ == '__main__':
    unittest.main()
