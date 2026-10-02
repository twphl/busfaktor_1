#!/usr/bin/env python3
"""Erzeuge zehn A4-Druckbogen mit allen kanonischen Kartenmotiven.

Die Sammlung enthält jedes Motiv einmal, ohne Rückseiten oder Auflagenmengen.
Die geprüften 600-dpi-Druckbilder werden am Endformat beschnitten und für den
Download auf 300 dpi verkleinert. Schnittmarken und Hinweise bleiben Vektoren.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import tempfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'build/print-run/motifs/cards'
DEFAULT_OUTPUT = ROOT / 'output/pdf/busfaktor-1-karten-a4.pdf'
PAGE_WIDTH, PAGE_HEIGHT = 210.0, 297.0
COLUMNS, ROWS, GAP = 3, 3, 2.5
DPI = 300


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_sources() -> tuple[list[dict], dict, dict[str, str]]:
    """Reject stale artwork, text, geometry or render assets before imposing."""
    manifest_path = SOURCE / 'manifest.json'
    if not manifest_path.exists():
        raise ValueError('Druckbilder fehlen. Zuerst `make print-run` ausführen.')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('proof') is not False or manifest.get('mode') != 'print':
        raise ValueError('Die Vorlage benötigt finale Druckbilder ohne Prüfraster.')
    hashes = {}

    def check(path: Path, expected: str | None = None) -> None:
        actual = digest(path)
        if expected is not None and actual != expected:
            raise ValueError(f'Druckquelle veraltet: {path}. Zuerst `make print-run` ausführen.')
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        hashes[key] = actual

    for field, relative in {
        'source_csv_sha256': 'data/cards.csv',
        'layout_config_sha256': 'data/card_layout.json',
        'profile_sha256': 'data/render_profile.json',
        'renderer_sha256': 'scripts/render_cards.py',
    }.items():
        check(ROOT / relative, manifest[field])
    check(manifest_path)
    check(Path(__file__).resolve())
    profile = json.loads((ROOT / 'data/render_profile.json').read_text())
    check(ROOT / profile['source_template']['path'], manifest['source_template_sha256'])
    with (ROOT / 'data/cards.csv').open(newline='', encoding='utf-8') as handle:
        cards = list(csv.DictReader(handle))
    ids = [card['card_id'] for card in cards]
    rendered = {card['card_id']: card for card in manifest['cards']}
    if len(set(ids)) != len(ids) or set(ids) != set(rendered):
        raise ValueError('Kanonische Motive und Druckmanifest stimmen nicht überein.')
    for card in cards:
        card_id = card['card_id']
        check(SOURCE / f'{card_id}.png', rendered[card_id]['png_sha256'])
        check(ROOT / f'data/cards/{card_id}.png', rendered[card_id]['artwork_sha256'])
    for asset in manifest['icons']['assets'].values():
        check(ROOT / asset['file'], asset['sha256'])
    for font in manifest['fonts'].values():
        check(Path('/usr/share/fonts/noto') / font['name'], font['sha256'])
    return cards, profile, hashes


def crop_marks(x: float, y: float, width: float, height: float) -> str:
    """Short marks outside the artwork; no lines are printed across cards."""
    lines = []
    offset, length = 0.25, 1.35
    for cx in (x, x + width):
        direction = -1 if cx == x else 1
        for cy in (y, y + height):
            vertical = -1 if cy == y else 1
            lines.append(f'<path d="M {cx + direction * offset} {cy} '
                         f'h {direction * length} M {cx} {cy + vertical * offset} '
                         f'v {vertical * length}"/>')
    return ''.join(lines)


def document(cards: list[dict], profile: dict, work: Path) -> tuple[str, list[dict]]:
    trim = profile['physical_mm']['trim']
    width, height = trim['width'], trim['height']
    left = (PAGE_WIDTH - COLUMNS * width - (COLUMNS - 1) * GAP) / 2
    top = (PAGE_HEIGHT - ROWS * height - (ROWS - 1) * GAP) / 2
    if left < 6 or top < 11:
        raise ValueError('Das Kartenformat passt nicht mit Druckrändern ins A4-Raster.')
    pixels = profile['upload_png']['rectangles']['trim']
    box = (pixels['x'], pixels['y'], pixels['x'] + pixels['width'], pixels['y'] + pixels['height'])
    size = (round(width / 25.4 * DPI), round(height / 25.4 * DPI))
    for card in cards:
        with Image.open(SOURCE / f"{card['card_id']}.png") as source:
            expected = (profile['upload_png']['width'], profile['upload_png']['height'])
            if source.size != expected:
                raise ValueError(f"Falsche Bildgröße: {card['card_id']} ({source.size})")
            image = source.crop(box).convert('RGB').resize(size, Image.Resampling.LANCZOS)
            image.save(work / f"{card['card_id']}.jpg", 'JPEG', quality=95,
                       subsampling=0, optimize=True, dpi=(DPI, DPI))
    page_count = math.ceil(len(cards) / (COLUMNS * ROWS))
    pages, placement_pages = [], []
    for page_index in range(page_count):
        subset = cards[page_index * 9:(page_index + 1) * 9]
        images, marks, placements = [], [], []
        for slot, card in enumerate(subset):
            x = left + (slot % COLUMNS) * (width + GAP)
            y = top + (slot // COLUMNS) * (height + GAP)
            card_id = card['card_id']
            image_path = work / f'{card_id}.jpg'
            images.append(f'<img class="card" alt="{html.escape(card_id)}" '
                          f'src="{image_path.as_uri()}" style="left:{x}mm;top:{y}mm;'
                          f'width:{width}mm;height:{height}mm">')
            marks.append(crop_marks(x, y, width, height))
            placements.append({'card_id': card_id, 'x_mm': x, 'y_mm': y,
                               'width_mm': width, 'height_mm': height,
                               'image_sha256': digest(image_path)})
        notes = ''
        if len(subset) == 1:
            notes = '''<aside>
<h2>Drucken &amp; zuschneiden</h2>
<p>A4, Hochformat, einseitig. Im Druckdialog <b>100 % / tatsächliche Größe</b>
wählen und die automatische Seitenanpassung ausschalten.</p>
<p>Zuerst einen Bogen zur Probe drucken. Die Kontrolllinie unten muss genau
50 mm lang sein. Dann entlang der Schnittmarken zuschneiden.</p>
<p>Die Vorlage enthält jedes der 82 Motive einmal, ohne Rückseiten.
Für eine Partie gelten die Zusammenstellung und Kartenmengen im Regelblatt.</p>
<p>Mythic-Motive sind hier als Papierausdruck enthalten; ein Foileffekt lässt
sich mit dieser Vorlage nicht drucken.</p>
<svg width="55mm" height="12mm" viewBox="0 0 55 12" aria-label="Kontrolllinie 50 mm">
<path d="M 2 2 v 4 M 2 4 h 50 M 52 2 v 4" fill="none" stroke="#333" stroke-width="0.2"/>
<text x="27" y="10" text-anchor="middle" font-family="sans-serif" font-size="3">50 mm</text>
</svg></aside>'''
        pages.append(f'''<section class="sheet">
<header><b>Busfaktor: 1 · Alle {len(cards)} Kartenmotive</b><span>Bogen {page_index + 1} / {page_count}</span></header>
<p class="settings">A4 · 100 % / tatsächliche Größe · keine Seitenanpassung · Endformat {str(width).replace('.', ',')} × {str(height).replace('.', ',')} mm</p>
{''.join(images)}
<svg class="marks" width="210mm" height="297mm" viewBox="0 0 210 297" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="#333" stroke-width="0.12">{''.join(marks)}</g></svg>
{notes}
<footer>
<div>Busfaktor: 1 · Otters of the Coast · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a> · <a href="https://github.com/twphl/busfaktor_1">github.com/twphl/busfaktor_1</a></div>
<div>Mechanik: <a href="https://phylogame.org/licenses/">PHYLO Process of Science · CC BY-SA 4.0</a> · Sydney Ang, Genevieve Leduc-Robert, Lu Li, and Sam MacKinnon.</div>
</footer></section>''')
        placement_pages.append({'page': page_index + 1, 'cards': placements})
    font = Path('/usr/share/fonts/noto/NotoSans-Regular.ttf').as_uri()
    bold = Path('/usr/share/fonts/noto/NotoSans-Bold.ttf').as_uri()
    markup = f'''<!doctype html><html lang="de"><head><meta charset="utf-8">
<title>Busfaktor: 1 - Alle Kartenmotive zum Drucken auf A4</title>
<meta name="author" content="Otters of the Coast">
<meta name="description" content="82 Kartenvorderseiten, zehn A4-Bogen mit Schnittmarken, Originalformat 63,5 × 88,9 mm, 300 dpi.">
<style>
@font-face {{font-family:Noto;src:url('{font}')}}
@font-face {{font-family:Noto;src:url('{bold}');font-weight:700}}
@page {{size:A4 portrait;margin:0}}
* {{box-sizing:border-box}}
html,body {{margin:0;padding:0;font-family:Noto,sans-serif;color:#222}}
.sheet {{width:210mm;height:297mm;position:relative;break-after:page}}
.sheet:last-child {{break-after:auto}}
header {{position:absolute;top:4.1mm;left:7.25mm;right:7.25mm;font-size:8pt;line-height:1.2}}
header span {{float:right}}
.settings {{position:absolute;top:8.1mm;left:7.25mm;margin:0;font-size:6.5pt;line-height:1.2}}
.card,.marks {{position:absolute;display:block}}
.marks {{left:0;top:0}}
footer {{position:absolute;top:287.5mm;left:7.25mm;right:7.25mm;font-size:5.8pt;line-height:2.7mm}}
a {{color:inherit;text-decoration:none}}
aside {{position:absolute;left:76mm;top:18mm;width:118mm;font-size:10pt;line-height:1.55}}
aside h2 {{font-size:15pt;margin:0 0 5mm}}
aside p {{margin:0 0 4mm}}
</style></head><body>{''.join(pages)}</body></html>'''
    return markup, placement_pages


def build(output: Path) -> dict:
    cards, profile, hashes = verified_sources()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='busfaktor-a4-') as temporary:
        work = Path(temporary)
        markup, placements = document(cards, profile, work)
        pdf = work / output.name
        HTML(string=markup, base_url=str(ROOT)).write_pdf(pdf)
        reader = PdfReader(pdf)
        if len(reader.pages) != len(placements):
            raise ValueError('Unerwartete Seitenzahl im A4-Export.')
        for page, placement in zip(reader.pages, placements):
            if any(abs(actual - expected * 72 / 25.4) > 0.01 for actual, expected in
                   zip((float(page.mediabox.width), float(page.mediabox.height)),
                       (PAGE_WIDTH, PAGE_HEIGHT))):
                raise ValueError('PDF-Seite entspricht nicht DIN A4.')
            drawn_images = []

            def collect_images(operator, operands, matrix, text_matrix):
                if operator == b'Do':
                    image = page['/Resources']['/XObject'][operands[0]].get_object()
                    if image.get('/Subtype') == '/Image':
                        drawn_images.append((image, matrix.copy()))

            page.extract_text(visitor_operand_before=collect_images)
            if len(drawn_images) != len(placement['cards']):
                raise ValueError('PDF enthält nicht die erwartete Anzahl Kartenbilder.')
            for (image, matrix), card in zip(drawn_images, placement['cards']):
                a, b, c, d, e, f = matrix
                actual = (min(e, e + a), min(f, f + d), abs(a), abs(d))
                expected = (card['x_mm'], PAGE_HEIGHT - card['y_mm'] - card['height_mm'],
                            card['width_mm'], card['height_mm'])
                if abs(b) > 0.001 or abs(c) > 0.001 or any(
                    abs(value - target * 72 / 25.4) > 0.01
                    for value, target in zip(actual, expected)
                ):
                    raise ValueError(f"Falsche PDF-Platzierung: {card['card_id']} ({actual})")
                if hashlib.sha256(image.get_data()).hexdigest() != card['image_sha256']:
                    raise ValueError(f"PDF-Bild stimmt nicht mit Motiv überein: {card['card_id']}")
        output.write_bytes(pdf.read_bytes())
    manifest = {
        'schema': 'busfaktor-print-and-play/v1',
        'pdf_file': output.name, 'pdf_sha256': digest(output),
        'card_count': len(cards), 'page_count': len(placements),
        'card_ids': [card['card_id'] for card in cards],
        'page_mm': [PAGE_WIDTH, PAGE_HEIGHT], 'dpi': DPI,
        'sources_sha256': hashes, 'pages': placements,
    }
    output.with_suffix('.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        manifest = build(args.output.resolve())
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(str(error)) from error
    print(f"OK: {manifest['card_count']} Motive auf {manifest['page_count']} A4-Seiten: {args.output}")


if __name__ == '__main__':
    main()
