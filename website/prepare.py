"""Build the standalone website assets.

The website reuses the already-prepared, already source-checked screen
assets from `keynote-neustart/assets/` (cards, illustrations, back, icons,
fonts, seal, Otters of the Coast mark, repository QR code) instead of
re-running the print renderer. Run `python3 keynote-neustart/prepare.py`
first if that directory is missing or outdated. Card data is read directly
from the canonical `data/cards.csv`.
The pure-white seal for favicons and footers is copied unchanged from
`build/seal/siegel-reinweiss.svg`, the seal variant used for the stickers.

The rules page `regeln.html` is filled from `docs/10-spielregeln.md` by
`rules_page.py`; the Markdown itself is copied alongside as `SPIELREGELN.md`.

Navigation and footer come from `site_chrome.py` and are written into the
`<!-- site:nav -->` and `<!-- site:footer -->` markers of every page, so the
menu and the credits exist once instead of six times.

For the card generator, `renderer-data.js` is exported from the Python
renderer itself: layout configuration, render profile, numeric constants,
German phrase lists, the allowlisted icon geometry and FreeType font metrics.
`renderer.js` holds only the ported drawing logic, so a changed layout value
reaches the browser without touching JavaScript. The renderer's own five Noto
files are copied next to the other fonts.
"""
import csv
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
KEYNOTE_ASSETS = ROOT / 'keynote-neustart/assets'
ASSETS = HERE / 'assets'

COPY_DIRS = ['cards', 'art', 'icons', 'fonts', 'blank', 'inspiration']
COPY_FILES = ['back.webp', 'seal.svg', 'otc-logo-full.png', 'repository-qr.svg', 'LICENSE.txt']

sys.path.insert(0, str(ROOT / 'scripts'))
import render_cards as rc  # noqa: E402
import rules_page  # noqa: E402
import site_chrome  # noqa: E402
import social_meta  # noqa: E402
import social_preview  # noqa: E402


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


# The rule booklet as print files (scripts/render_rulebook.py, `make rulebook`),
# offered for download on regeln.html.
RULEBOOK = ROOT / 'build/regelheft'
PRINT_PDFS = [
    'regelheft-lesefolge.pdf', 'regelheft-druckbogen.pdf',
    'regelheft-vorderseiten.pdf', 'regelheft-rueckseiten.pdf',
    'regelheft-rueckseiten-umgekehrt.pdf',
    'kalibrierung-vorderseiten.pdf', 'kalibrierung-rueckseiten.pdf',
]


CARDS_A4 = ROOT / 'output/pdf/busfaktor-1-karten-a4.pdf'
CARDS_A4_MANIFEST = CARDS_A4.with_suffix('.json')
CARDS_A4_REQUIRED_SOURCES = {
    'scripts/render_print_and_play.py',
    'data/cards.csv',
    'data/render_profile.json',
    'data/card_layout.json',
    'scripts/render_cards.py',
    'build/print-run/motifs/cards/manifest.json',
}


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_cards_a4():
    """Only publish a PDF whose recorded inputs still match the repository."""
    rebuild = 'Zuerst `make cards-a4` ausführen.'
    if not CARDS_A4.is_file() or not CARDS_A4_MANIFEST.is_file():
        raise SystemExit(f'Die A4-Kartendruckvorlage oder ihr Prüfmanifest fehlt. {rebuild}')
    try:
        manifest = json.loads(CARDS_A4_MANIFEST.read_text())
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Das Prüfmanifest der A4-Kartendruckvorlage ist ungültig. {rebuild}') from exc
    if not isinstance(manifest, dict):
        raise SystemExit(f'Das Prüfmanifest der A4-Kartendruckvorlage ist ungültig. {rebuild}')
    sources = manifest.get('sources_sha256')
    if not isinstance(sources, dict) or not CARDS_A4_REQUIRED_SOURCES <= sources.keys():
        raise SystemExit(f'Das Prüfmanifest der A4-Kartendruckvorlage ist unvollständig. {rebuild}')
    if manifest.get('pdf_file') != CARDS_A4.name or manifest.get('pdf_sha256') != _sha256(CARDS_A4):
        raise SystemExit(f'Die A4-Kartendruckvorlage stimmt nicht mit ihrem Prüfmanifest überein. {rebuild}')
    for name, expected in sources.items():
        source = ROOT / name
        if not source.is_file() or _sha256(source) != expected:
            raise SystemExit(f'Die A4-Kartendruckvorlage ist nicht aktuell ({name}). {rebuild}')


def copy_print_pdfs():
    missing = [name for name in PRINT_PDFS if not (RULEBOOK / name).exists()]
    if missing:
        raise SystemExit(
            f'build/regelheft unvollständig ({", ".join(missing)}). Zuerst `make rulebook` ausführen.'
        )
    rules = ROOT / 'docs/10-spielregeln.md'
    if (RULEBOOK / 'regelheft-lesefolge.pdf').stat().st_mtime < rules.stat().st_mtime:
        raise SystemExit(
            'Das Regelheft ist älter als docs/10-spielregeln.md. Zuerst `make rulebook` ausführen.'
        )
    validate_cards_a4()
    dst = ASSETS / 'druck'
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir()
    for name in PRINT_PDFS:
        shutil.copyfile(RULEBOOK / name, dst / name)
    shutil.copyfile(CARDS_A4, dst / CARDS_A4.name)


# The game table shows cards at 80–190 CSS px; 360 px covers that at 2x
# without loading the 750 px screen assets for every card on the table.
THUMB_WIDTH = 360


def build_thumbnails():
    from PIL import Image

    dst = ASSETS / 'cards-sm'
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir()
    for path in [*sorted((ASSETS / 'cards').glob('*.webp')), ASSETS / 'back.webp']:
        with Image.open(path) as image:
            height = round(image.height * THUMB_WIDTH / image.width)
            image.resize((THUMB_WIDTH, height), Image.LANCZOS).save(
                dst / path.name, 'WEBP', quality=84, method=6
            )
    return dst


def _icon_tree(element):
    return {
        'tag': element.tag.rsplit('}', 1)[-1],
        'attrs': dict(element.attrib),
        'children': [_icon_tree(child) for child in element],
    }


def _constants():
    """Every module-level constant the drawing code reads, straight from Python."""
    constants = {}
    for name, value in vars(rc).items():
        if not name.isupper() or name.startswith('_'):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float, str, frozenset, tuple)):
            continue
        if isinstance(value, (frozenset, tuple)):
            if not all(isinstance(item, (int, float, str)) for item in value):
                continue
            value = sorted(value) if isinstance(value, frozenset) else list(value)
        constants[name] = value
    return constants


def export_renderer_data():
    layout = rc._load_layout()
    manifest = rc._load_icon_manifest()
    profile = rc.load_profile()
    fonts = rc._resolve_fonts()

    font_files = {}
    sizes = sorted({
        float(step['size'])
        for role in layout['typography'].values()
        for step in role['steps']
    })
    for role, path in fonts.items():
        shutil.copyfile(path, ASSETS / 'fonts' / path.name)
        metrics = {}
        for size in sizes:
            ascent, descent = rc._font(fonts, role, size).getmetrics()
            metrics[rc._attr_number(size)] = [ascent, descent]
        font_files[role] = {'file': f'assets/fonts/{path.name}', 'metrics': metrics}

    icons = {}
    for key in sorted(manifest['icons']):
        children, metadata = rc._load_icon_asset(key)
        icons[key] = {**metadata, 'children': [_icon_tree(child) for child in children]}

    data = {
        'renderer': {
            'version': rc.RENDERER_VERSION,
            'sha256': rc._renderer_sha256(),
        },
        'constants': _constants(),
        'layout': layout,
        'profile': {
            'master_svg': profile['master_svg'],
            '_sha256': profile['_sha256'],
        },
        'icon_manifest_sha256': manifest['_sha256'],
        'icons': icons,
        'fonts': font_files,
    }
    (HERE / 'renderer-data.js').write_text(
        '// Generated by website/prepare.py from scripts/render_cards.py. Do not edit.\n'
        'window.CARD_RENDERER_DATA = '
        + json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        + ';\n'
    )
    return len(icons)


def main():
    if not KEYNOTE_ASSETS.exists():
        raise SystemExit(
            'keynote-neustart/assets fehlt. Zuerst `python3 keynote-neustart/prepare.py` ausführen.'
        )
    ASSETS.mkdir(exist_ok=True)
    for name in COPY_DIRS:
        copy_tree(KEYNOTE_ASSETS / name, ASSETS / name)
    for name in COPY_FILES:
        shutil.copyfile(KEYNOTE_ASSETS / name, ASSETS / name)
    shutil.copyfile(ROOT / 'build/seal/siegel-reinweiss.svg', ASSETS / 'seal-white.svg')
    build_thumbnails()
    copy_print_pdfs()

    cards = list(csv.DictReader((ROOT / 'data/cards.csv').open()))
    (HERE / 'cards.js').write_text(
        'window.CARDS = ' + json.dumps(cards, ensure_ascii=False, indent=2) + ';\n'
    )

    rules = ROOT / 'docs/10-spielregeln.md'
    shutil.copyfile(rules, HERE / 'SPIELREGELN.md')
    unknown_names = rules_page.build(
        HERE / 'regeln.html',
        rules.read_text(),
        {card['name']: card['card_id'] for card in cards},
        ROOT,
    )
    pages = site_chrome.build(HERE)
    icon_count = export_renderer_data()
    social_preview.build(HERE)
    social_meta.build(HERE)

    (ASSETS / 'QUELLEN.txt').write_text('''BUSFAKTOR: 1 — Website-Assets

Kanonische Texte: data/cards.csv
Bildschirmassets (Karten, Illustrationen, Rückseite, Siegel,
Ottermarke, Icons, Fonts, Repository-QR-Code) sind unverändert aus keynote-neustart/assets/
übernommen. Deren Herkunft und Prüfung stehen in
keynote-neustart/assets/QUELLEN.txt.

Reinweißes Siegel für Favicon und Footer: build/seal/siegel-reinweiss.svg,
unverändert als seal-white.svg übernommen. Dies ist die Siegelfassung der
Stickervorlage, ohne Beschnitt und Produktionsmarkierungen.

Linkvorschau: social-preview.png wird mit website/social_preview.py aus den
vorhandenen Karten KAT-C03, KAT-M03 und KAT-U21, dem reinweißen Siegel sowie
Noto Sans und Bitter gesetzt. Format: 1200 × 630 Pixel; keine neue Illustration.
Open-Graph- und Twitter-Metadaten kommen aus website/social_meta.py;
öffentliche Basisadresse und Seitennamen stehen in website/site-config.json.

Kartendesigner: renderer.js ist eine JavaScript-Portierung von
scripts/render_cards.py. Layout, Profil, Konstanten, Icongeometrie und
Schriftmetriken in renderer-data.js stammen unverändert aus dem Python-Renderer.
Die fünf Noto-Schnitte des Renderers liegen unter fonts/.

A4-Kartendruckvorlage: scripts/render_print_and_play.py setzt die 82 geprüften
Kartenmotive auf A4-Bögen mit Schnittmarken. Das Prüfmanifest unter
output/pdf/busfaktor-1-karten-a4.json dokumentiert die verwendeten Quellen.

blank/: die sechs Blanko-Motive, wie in der Keynote.
inspiration/: drei unveränderte PHYLO-Beispielkarten und der QR-Code zu
phylogame.org/decks. Sie sind nicht Teil dieses Projekts und stehen nicht
unter CC BY-SA, sondern unter CC BY-NC-ND 4.0 (phylogame.org/licenses):
GSA/PHYLO „Lose Funding!“ (Art: Maki Naro), WWEST/WISE „Rosalind Franklin“
(Art: Ping Zhu), Ingenium „Jocelyn Bell Burnell“ (Grafik: nineSixteen
Creative Inc.).

Eigene Regeln, Kartendaten, Illustrationen, Gestaltung, Dokumentation und
Code: CC BY-SA 4.0.
Siehe LICENSE.txt und docs/09-licensing-and-attribution.md im Repository.
Mechanik nach PHYLO Process of Science, CC BY-SA 4.0.
Pflicht-Credit: Sydney Ang, Genevieve Leduc-Robert, Lu Li, and Sam MacKinnon.
https://phylogame.org/licenses/

Phosphor Icons 2.1.1 Bold, unveränderte semantische Zuordnung des Repositorys.
MIT-Lizenz: icons/LICENSE.txt.
Noto Sans und Noto Serif, unverändert aus data/assets/fonts/; SIL OFL 1.1: fonts/OFL.txt.
Bitter von Sol Matas: unveränderte variable Schrift aus dem Google-Fonts-Repository.
Quelle, Prüfsumme und Lizenz: fonts/Bitter-SOURCE.txt und fonts/Bitter-OFL.txt.

Produktion: geplante Auflage 234-plus-18, ADR 0019.
''')
    for name in unknown_names:
        print(f'Hinweis: Die Regeln nennen `{name}`, aber keine Karte im Set heißt so.')
    print(
        f'OK: {len(cards)} Karten, Bildschirmassets aus keynote-neustart/assets übernommen, '
        f'Regelseite aus docs/10-spielregeln.md gesetzt, '
        f'Navigation und Fußzeile auf {len(pages)} Seiten geschrieben, '
        f'Rendererdaten mit {icon_count} Icons exportiert; Linkvorschaugrafik und Social-Metadaten aktualisiert.'
    )


if __name__ == '__main__':
    main()
