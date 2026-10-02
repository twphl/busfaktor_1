"""Build the standalone keynote assets from canonical repository sources."""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / 'assets'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def web_image(source, destination, card=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = image.convert('RGB')
        if card:
            image = image.crop((72, 72, 1572, 2172)).resize((750, 1050), Image.Resampling.LANCZOS)
        image.save(destination, 'WEBP', quality=90 if card else 86, method=6)


def otc_logo(destination, padding=12):
    """Light logo version for the dark slides, trimmed to its visible area plus a small margin."""
    with Image.open(ROOT / 'data/assets/otters_of_the_coast_logo_light.png') as image:
        image = image.convert('RGBA')
        left, top, right, bottom = image.getchannel('A').getbbox()
        image = image.crop((left - padding, top - padding, right + padding, bottom + padding))
        image.save(destination, 'PNG', optimize=True)


def main():
    manifest = json.loads((ROOT / 'build/print-run/motifs/cards/manifest.json').read_text())
    expected = {'source_csv_sha256': 'data/cards.csv', 'layout_config_sha256': 'data/card_layout.json',
                'profile_sha256': 'data/render_profile.json', 'renderer_sha256': 'scripts/render_cards.py'}
    for key, path in expected.items():
        if manifest[key] != digest(ROOT / path):
            raise SystemExit(f'Druckrender veraltet: {path}. Bitte die Karten zuerst neu rendern.')
    cards = list(csv.DictReader((ROOT / 'data/cards.csv').open()))
    by_id = {entry['card_id']: entry for entry in manifest['cards']}
    for card in cards:
        card_id = card['card_id']
        art = ROOT / f'data/cards/{card_id}.png'
        rendered = ROOT / f'build/print-run/motifs/cards/{card_id}.png'
        if digest(art) != by_id[card_id]['artwork_sha256'] or digest(rendered) != by_id[card_id]['png_sha256']:
            raise SystemExit(f'Druckrender stimmt nicht mit der Quelle überein: {card_id}')
        web_image(rendered, ASSETS / f'cards/{card_id}.webp', True)
        web_image(art, ASSETS / f'art/{card_id}.webp')
    for i in range(1, 7):
        web_image(ROOT / f'build/print-run/motifs/blank/KAT-B{i:02d}.png', ASSETS / f'blank/KAT-B{i:02d}.webp', True)
    back_dir = HERE / '.build/back'
    subprocess.run([sys.executable, str(ROOT / 'scripts/render_card_back.py'), '--output', str(back_dir), '--no-svg'], cwd=ROOT, check=True)
    web_image(back_dir / 'card-back.png', ASSETS / 'back.webp', True)
    fonts = ASSETS / 'fonts'
    fonts.mkdir(exist_ok=True)
    for name in ['NotoSans-Regular.ttf', 'NotoSans-Bold.ttf', 'NotoSerif-Regular.ttf', 'NotoSerif-Italic.ttf']:
        shutil.copyfile(ROOT / 'data/assets/fonts' / name, fonts / name)
    shutil.copyfile(ROOT / 'data/assets/fonts/OFL.txt', fonts / 'OFL.txt')
    icons = ASSETS / 'icons'
    icons.mkdir(exist_ok=True)
    icon_manifest = json.loads((ROOT / 'data/assets/icons/manifest.json').read_text())
    for name, icon in icon_manifest['icons'].items():
        shutil.copyfile(ROOT / 'data/assets/icons' / icon['file'], icons / f'{name}.svg')
    shutil.copyfile(ROOT / 'data/assets/icons/phosphor/LICENSE.phosphor.txt', icons / 'LICENSE.txt')
    shutil.copyfile(ROOT / 'build/seal/siegel.svg', ASSETS / 'seal.svg')
    otc_logo(ASSETS / 'otc-logo-full.png')
    shutil.copyfile(ROOT / 'LICENSE', ASSETS / 'LICENSE.txt')
    shutil.copyfile(ROOT / 'docs/10-spielregeln.md', HERE / 'SPIELREGELN.md')
    (HERE / 'cards.js').write_text('window.CARDS = ' + json.dumps(cards, ensure_ascii=False, indent=2) + ';\n')
    (ASSETS / 'QUELLEN.txt').write_text('''BUSFAKTOR: 1 — Originalassets der eigenständigen Keynote

Kanonische Texte: data/cards.csv
Karten: build/print-run/motifs/cards/*.png, geprüft gegen Daten, Renderer und Illustrationen.
Illustrationen: data/cards/*.png, alle 82 Motive.
Blankos: build/print-run/motifs/blank/*.png, sechs Motive.
Rückseite: frisch mit scripts/render_card_back.py gerendert.
Siegel: build/seal/siegel.svg, unverändert als assets/seal.svg übernommen.
Ottermarke: data/assets/otters_of_the_coast_logo_light.png, auf das Sichtbare
beschnitten als assets/otc-logo-full.png.
Bildschirmaufbereitung: physischer Endbeschnitt nach data/render_profile.json,
dann 750 × 1050 Pixel und WebP. Kartentexte und Layout bleiben unverändert.

KI-generierte Illustrationen, erstellt vom Redaktionsteam mit ChatGPT.
Nutzung im Rahmen der OpenAI-Nutzungsbedingungen. Keine fremden Stilbilder
oder Franchise-Assets übernommen.

PHYLO-Beispielkarten (Folie 3, inspiration/, fest abgelegt, nicht von
prepare.py erzeugt): drei unveränderte Karten aus den Originaldecks. Sie
gehören nicht zu diesem Projekt und stehen nicht unter CC BY-SA, sondern unter
CC BY-NC-ND 4.0 (https://phylogame.org/licenses/): GSA/PHYLO „Lose Funding!“
(Art: Maki Naro), WWEST/WISE „Rosalind Franklin“ (Art: Ping Zhu), Ingenium
„Jocelyn Bell Burnell“ (Grafik: nineSixteen Creative Inc.). Alle Decks:
https://phylogame.org/decks/

Eigene Regeln, Kartendaten, Illustrationen, Gestaltung, Dokumentation und
Code: CC BY-SA 4.0.
Siehe LICENSE.txt und docs/09-licensing-and-attribution.md im Repository.
Mechanik nach PHYLO Process of Science, CC BY-SA 4.0.
Pflicht-Credit: Sydney Ang, Genevieve Leduc-Robert, Lu Li, and Sam MacKinnon.
https://phylogame.org/licenses/

Phosphor Icons 2.1.1 Bold, unveränderte semantische Zuordnung des Repositorys.
MIT-Lizenz: icons/LICENSE.txt.
Noto Sans und Noto Serif, unverändert aus data/assets/fonts/; SIL OFL 1.1: fonts/OFL.txt.
Die gesamte Titelwortmarke einschließlich der goldenen Ziffer 1 verwendet
die lokal mitgelieferte Noto Sans Bold: fonts/NotoSans-Bold.ttf.
Bitter von Sol Matas: unveränderte variable Schrift aus dem Google-Fonts-Repository.
Quelle, Prüfsumme und Lizenz: fonts/Bitter-SOURCE.txt und fonts/Bitter-OFL.txt.
Die mitgelieferte Bitter-Datei bleibt bei erneuter Asset-Aufbereitung erhalten.

Produktion: geplante Auflage 234-plus-18, ADR 0019.
Die Investorenrhetorik gehört zur Vortragssatire.
''')
    print(f'OK: {len(cards)} Karten + Illustrationen, 6 Blankos, Rückseite, Fonts und Icons.')


if __name__ == '__main__':
    main()
