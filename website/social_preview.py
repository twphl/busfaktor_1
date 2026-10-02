"""Render the website's share image from its existing brand and card assets.

Uses the same local fonts, seal and rendered cards as the website. No new
illustration or generated lettering is introduced. Run with the project's
Python environment: `uv run python website/social_preview.py`.
"""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import resvg_py

SIZE = (1200, 630)
SCALE = 2
BACKGROUND = '#111513'
CREAM = '#f0eadb'
GOLD = '#c9ae73'
SOFT = '#b8c0b0'


def font(assets, name, size, weight=None):
    face = ImageFont.truetype(str(assets / 'fonts' / name), round(size * SCALE))
    if weight is not None:
        face.set_variation_by_axes([weight])
    return face


def label(canvas, value, xy, face, color=CREAM):
    ImageDraw.Draw(canvas).text(
        tuple(round(v * SCALE) for v in xy), value, font=face,
        fill=color, anchor='ls',
    )


def card(canvas, assets, card_id, center, width, angle):
    height = width * 1.4
    size = (round(width * SCALE), round(height * SCALE))
    with Image.open(assets / 'cards' / f'{card_id}.webp') as source:
        face = source.convert('RGBA').resize(size, Image.Resampling.LANCZOS)
    corners = Image.new('L', size)
    ImageDraw.Draw(corners).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1), radius=11 * SCALE, fill=255,
    )
    face.putalpha(corners)
    face = face.rotate(angle, Image.Resampling.BICUBIC, expand=True)
    left = round(center[0] * SCALE - face.width / 2)
    top = round(center[1] * SCALE - face.height / 2)
    shadow = Image.new('RGBA', canvas.size)
    shadow.paste((0, 0, 0, 165), (left, top + 15 * SCALE), face.getchannel('A'))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(17 * SCALE)))
    canvas.alpha_composite(face, (left, top))


def build(here):
    assets = here / 'assets'
    canvas = Image.new('RGBA', tuple(v * SCALE for v in SIZE), BACKGROUND)

    # The website's warm, fading stage light behind the physical cards.
    light = Image.new('L', SIZE)
    light.putdata([
        round(190 * max(0, 1 - (((x - 940) / 1000) ** 2 + ((y - 300) / 660) ** 2) ** .5) ** 1.5)
        for y in range(SIZE[1]) for x in range(SIZE[0])
    ])
    glow = Image.new('RGBA', canvas.size, '#655c49')
    glow.putalpha(light.resize(canvas.size, Image.Resampling.BICUBIC))
    canvas.alpha_composite(glow)

    card(canvas, assets, 'KAT-C03', (828, 311), 254, 17)
    card(canvas, assets, 'KAT-M03', (1033, 275), 242, -13)
    card(canvas, assets, 'KAT-U21', (933, 374), 270, 6)

    sans = font(assets, 'NotoSans-Regular.ttf', 24)
    small = font(assets, 'NotoSans-Regular.ttf', 20)
    bold = font(assets, 'NotoSans-Bold.ttf', 24)
    wordmark = font(assets, 'NotoSans-Bold.ttf', 80)
    headline = font(assets, 'Bitter-variable.ttf', 54, 750)

    # Preserve the site's framed wordmark and upright golden numeral.
    draw = ImageDraw.Draw(canvas)
    rule_color = '#766b50'
    for y in (54, 156):
        draw.line((60 * SCALE, y * SCALE, 599 * SCALE, y * SCALE), fill=rule_color, width=SCALE)
    label(canvas, 'BUSFAKTOR:', (58, 136), wordmark)
    number_x = 58 + wordmark.getlength('BUSFAKTOR:') / SCALE
    label(canvas, '1', (number_x, 136), wordmark, GOLD)

    label(canvas, 'Endlich spielend', (60, 237), headline)
    label(canvas, 'scheitern.', (60, 301), headline, GOLD)
    label(canvas, 'Ein Kartenspiel über den', (62, 370), sans, SOFT)
    label(canvas, 'DH-, RDM- und RSE-Projektalltag.', (62, 403), sans, SOFT)
    label(canvas, 'Und alles, was nicht im Förderantrag stand.', (62, 450), sans, SOFT)

    seal = resvg_py.svg_to_bytes(
        svg_string=(assets / 'seal-white.svg').read_text(),
        width=88 * SCALE, height=88 * SCALE, skip_system_fonts=True,
    )
    with Image.open(BytesIO(seal)) as image:
        canvas.alpha_composite(image.convert('RGBA'), (62 * SCALE, 489 * SCALE))
    label(canvas, '82 Motive.', (172, 523), bold)
    label(canvas, 'Spielen. Forken. Weiterentwickeln.', (172, 555), small, GOLD)

    destination = assets / 'social-preview.png'
    canvas = canvas.convert('RGB').resize(SIZE, Image.Resampling.LANCZOS)
    canvas.save(destination, optimize=True)
    return destination


if __name__ == '__main__':
    output = build(Path(__file__).resolve().parent)
    print(f'OK: {output.name}, {SIZE[0]} × {SIZE[1]} px, {output.stat().st_size / 1024:.0f} KiB')
