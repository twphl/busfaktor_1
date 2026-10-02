#!/usr/bin/env python3
"""Setzt `docs/10-spielregeln.md` als Regelheft im Kartenformat oder in 10 × 15 cm.

Der Markdown-Parser ist derselbe, den die Website benutzt
(`website/rules_page.py`): dieselbe strenge Teilmenge, dieselbe Fehlermeldung,
wenn in den Regeln ein neues Konstrukt auftaucht.  Nur die Inline-Auszeichnung
ist ausgetauscht, weil auf Papier keine Links funktionieren.

Es entstehen zwei PDF:

    regelheft-lesefolge.pdf    eine Buchseite je PDF-Seite, zum Lesen und Prüfen
    regelheft-druckbogen.pdf   je Bogenseite zwei Buchseiten, Rückstichfolge

`--format 10x15` setzt dasselbe Heft auf 100 × 150 mm; die Dateien heißen dann
`regelheft-10x15-…`.  Beide Doppelseiten passen auf A4 quer.

Die Trennung ist Absicht und folgt `export_print_run.py`: erst setzen, dann
ausschießen.  Die Lesefolge ist das Original, der Druckbogen eine Ableitung.

§18 Kurzreferenz steht nicht im Textteil, sondern auf der Außenseite des
hinteren Umschlags — sie liegt damit beim Spielen neben dem Tisch, ohne dass
das Heft aufgeschlagen werden muss (der Druckplan streicht Spielerhilfen als
Karten, nicht als Umschlagseite).
"""

from __future__ import annotations

import argparse
import base64
import functools
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "website") not in sys.path:
    sys.path.insert(0, str(ROOT / "website"))

import rules_page  # noqa: E402

CSS_PATH = Path(__file__).resolve().parent / "rulebook" / "booklet.css"
LOGO_PATH = ROOT / "data" / "assets" / "otters_of_the_coast_logo_light.png"
SIEGEL_PATH = ROOT / "build" / "seal" / "siegel-reinweiss.svg"
FONT_DIR = ROOT / "website" / "assets" / "fonts"
RULES_PATH = ROOT / "docs" / "10-spielregeln.md"
DEFAULT_OUTPUT = ROOT / "build" / "regelheft"

MM = 72.0 / 25.4

KURZREFERENZ = "18"

# Das Stylesheet ist fuer das Kartenformat geschrieben.  Seine festen Masze
# laufen im Textteil mit der Grundschrift mit (--massstab), auf den beiden
# Umschlagseiten mit der Seitenbreite (--massstab-umschlag).
BASIS_SCHRIFTGRAD = 7.5
BASIS_BREITE = 62.0

# Seitenformat, Stege in mm und Grundschrift in pt je Heftformat.
FORMATE = {
    "karte": {
        "praefix": "regelheft",
        "breite": 62.0, "hoehe": 88.0,
        "innen": 7.0, "aussen": 5.0, "oben": 6.0, "unten": 7.0,
        "schriftgrad": 7.5, "durchschuss": 10.0,
    },
    "10x15": {
        "praefix": "regelheft-10x15",
        "breite": 100.0, "hoehe": 150.0,
        "innen": 11.0, "aussen": 8.0, "oben": 10.0, "unten": 11.0,
        # 9,75/13 pt fuellt genau sieben Bogen, ohne leere Fuellerseiten.
        "schriftgrad": 9.75, "durchschuss": 13.0,
    },
}


class RulebookError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Marken auf dem Umschlag: reinweisses Siegel und helles Logo


def _data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


@functools.lru_cache(maxsize=1)
def _siegel_png(breite=760):
    """Die reinweisse Siegelfassung der Sticker, wie sie auch die Website fuehrt.

    Sie ist das Siegel der Kartenrueckseite (ADR 0017) mit Weiss statt Creme;
    auf dem schwarzen Umschlag steht sie damit im selben Weiss wie das Logo.
    Gesetzt wird die Datei unveraendert, nicht nachgefaerbt.
    """
    import resvg_py

    if not SIEGEL_PATH.is_file():
        raise RulebookError(f"Reinweißes Siegel fehlt: {SIEGEL_PATH}")
    svg = SIEGEL_PATH.read_text(encoding="utf-8")
    return bytes(resvg_py.svg_to_bytes(svg_string=svg, width=breite))


@functools.lru_cache(maxsize=1)
def _logo_png():
    """Die helle Logofassung fuer den dunklen Umschlag, auf das Sichtbare beschnitten.

    `otters_of_the_coast_logo_light.png` ist die Fassung fuer dunkle Flaechen:
    Wortmarke und Sterne weiss, der Otter mit heller Kontur.  Die dunkle Fassung
    `_dark` gehoert auf Papier und helle Flaechen.
    """
    import io

    from PIL import Image

    if not LOGO_PATH.is_file():
        raise RulebookError(f"Logo fehlt: {LOGO_PATH}")
    with Image.open(LOGO_PATH) as quelle:
        ergebnis = quelle.convert("RGBA")
    # Die Vorlage bringt rundum durchsichtigen Rand mit, unten allein 105 von 848
    # Pixeln. Ungetrimmt meint eine Breitenangabe im Layout etwas anderes als das
    # Sichtbare, und das Logo haengt neben dem Siegel in der Luft.
    rahmen = ergebnis.getchannel("A").getbbox()
    if rahmen:
        ergebnis = ergebnis.crop(rahmen)
    puffer = io.BytesIO()
    ergebnis.save(puffer, format="PNG", optimize=True)
    return puffer.getvalue()


# --------------------------------------------------------------------------
# Inline-Auszeichnung fuer Papier


class BookletInline(rules_page.Inline):
    """Wie die Website, aber ohne Links: Papier kann sie nicht aufloesen."""

    def code(self, text):
        if rules_page.KEYWORD.fullmatch(text):
            return f'<span class="keyword">{html.escape(text)}</span>'
        return f"<code>{html.escape(text)}</code>"

    def _section_ref(self, match):
        slug = self.chapters.get(match[1])
        if not slug:
            raise RulebookError(f"{match[0]} verweist auf keinen Abschnitt der Regeln")
        # Die Seitenzahl haengt das Stylesheet per target-counter an.
        return f'<a class="regel-ref" href="#{slug}">§ {match[1]}</a>'

    def _adr_ref(self, match):
        return f'<span class="adr">{match[0]}</span>'

    def _link(self, match):
        label, target = match[1], html.unescape(match[2])
        if target.startswith(("http://", "https://")):
            sichtbar = re.sub(r"^https?://", "", target).rstrip("/")
            return f'{label} <span class="url">{html.escape(sichtbar)}</span>'
        return label


# --------------------------------------------------------------------------
# HTML


def _blocks_html(blocks, inline, indent="  "):
    lines = []
    offen = False
    for block in blocks:
        if block[0] == "subheading":
            if offen:
                lines.append(f"{indent}</div>")
                offen = False
            label, titel = rules_page._heading_label(block[1])
            beispiel = " beispiel" if "beispiel" in titel.lower() else ""
            nummer = f'<span class="nr">{html.escape(label)}</span> ' if label else ""
            lines.append(f'{indent}<div class="unterabschnitt{beispiel}">')
            lines.append(f"{indent}  <h3>{nummer}{inline(titel)}</h3>")
            offen = True
        else:
            tiefe = indent + ("  " if offen else "")
            lines += [tiefe + zeile for zeile in rules_page._render_block(block, inline)]
    if offen:
        lines.append(f"{indent}</div>")
    return lines


def _cover(meta, titel):
    stand = f'Version {meta["Version"]} · {rules_page._format_date(meta["Stand"])}'
    return [
        '<section class="umschlag-vorn">',
        "  <div>",
        f"    <h1>{html.escape(titel)}</h1>",
        '    <div class="untertitel">Vollständige Spielregeln</div>',
        "  </div>",
        "  <div>",
        '    <div class="sockel">',
        f'      <img class="siegel" alt="Siegel" src="{_data_uri(_siegel_png())}">',
        f'      <img class="logo" alt="Otters of the Coast" src="{_data_uri(_logo_png())}">',
        "    </div>",
        f'    <div class="stand">{html.escape(stand)}</div>',
        "  </div>",
        "</section>",
    ]


def _front_matter(meta, preamble, inline):
    """Seite 2: Vorspann der Regeln, falls es einen gibt; die Versionszeile steht unten."""
    lines = ['<section class="titelei">']
    if preamble:
        lines += ['  <div class="vorspann-text">', "    <h2>Zu diesen Regeln</h2>"]
        for block in preamble:
            lines += ["    " + zeile for zeile in rules_page._render_block(block, inline)]
        lines.append("  </div>")
    stand = [f'Version {meta["Version"]}', f'Stand {rules_page._format_date(meta["Stand"])}']
    lines += [
        f'  <p class="lizenz">{html.escape(" · ".join(stand))}</p>',
        "</section>",
    ]
    return lines


def _toc(chapters):
    lines = ['<nav class="inhalt">', "  <h2>Inhalt</h2>", "  <ol>"]
    for kapitel in chapters:
        lines.append(
            f'    <li><span class="nr">{kapitel["number"]}</span>'
            f'<a class="titel" href="#{kapitel["slug"]}">'
            f'{html.escape(kapitel["title"])}</a>'
            f'<a class="seite" href="#{kapitel["slug"]}"></a></li>'
        )
    return lines + ["  </ol>", "</nav>"]


def _quickref(kapitel, inline):
    """§18 auf die Aussenseite des hinteren Umschlags."""
    lines = [
        '<section class="umschlag-hinten">',
        f'  <h2>{html.escape(kapitel["title"])}</h2>',
    ]
    lines += _blocks_html(kapitel["blocks"], inline, indent="  ")
    lines += [
        '  <div class="fuss">Busfaktor: 1 · Vollständige Regeln im Heft und auf der Website.</div>',
        "</section>",
    ]
    return lines


def _font_face(name, datei, gewicht="400", stil="normal"):
    pfad = (FONT_DIR / datei).resolve()
    if not pfad.is_file():
        raise RulebookError(f"Schrift fehlt: {pfad}")
    return (
        f"@font-face {{ font-family: '{name}'; src: url('file://{pfad}') format('truetype');"
        f" font-weight: {gewicht}; font-style: {stil}; }}"
    )


def _variables(seite):
    return "\n".join(
        [
            ":root {",
            f'  --seite-breite: {seite["breite"]}mm;',
            f'  --seite-hoehe: {seite["hoehe"]}mm;',
            f'  --rand-innen: {seite["innen"]}mm;',
            f'  --rand-aussen: {seite["aussen"]}mm;',
            f'  --rand-oben: {seite["oben"]}mm;',
            f'  --rand-unten: {seite["unten"]}mm;',
            f'  --satz-hoehe: {seite["hoehe"] - seite["oben"] - seite["unten"]:.2f}mm;',
            f'  --grundschrift: {seite["schriftgrad"]}pt;',
            f'  --durchschuss: {seite["durchschuss"]}pt;',
            f'  --massstab: {seite["schriftgrad"] / BASIS_SCHRIFTGRAD:.4f};',
            f'  --massstab-umschlag: {seite["breite"] / BASIS_BREITE:.4f};',
            "}",
        ]
    )


def build_html(markdown, seite, *, kapitelumbruch=False, fueller=0, ohne_kurzreferenz=False):
    meta, preamble, chapters = rules_page._outline(markdown)
    titel = "Busfaktor: 1"

    nummern = {k["number"]: k["slug"] for k in chapters}
    inline = BookletInline(nummern, {}, ROOT)

    quickref = next((k for k in chapters if k["number"] == KURZREFERENZ), None)
    if quickref is None:
        raise RulebookError("§18 Kurzreferenz fehlt; die Umschlagrückseite braucht sie.")

    textteil = [k for k in chapters if k["number"] != KURZREFERENZ]

    schriften = "\n".join(
        [
            _font_face("DHK Serif", "NotoSerif-Regular.ttf"),
            _font_face("DHK Serif", "NotoSerif-Bold.ttf", "700"),
            _font_face("DHK Serif", "NotoSerif-Italic.ttf", "400", "italic"),
            _font_face("DHK Sans", "NotoSans-Regular.ttf"),
            _font_face("DHK Sans", "NotoSans-Bold.ttf", "700"),
        ]
    )

    body = _cover(meta, titel)
    body += _front_matter(meta, preamble, inline)
    body += _toc(textteil)
    body.append('<article class="regeln">')
    for kapitel in textteil:
        body.append(f'<section class="regel" id="{kapitel["slug"]}">')
        body.append(
            f'  <h2><span class="nr">§\u00a0{kapitel["number"]}</span>'
            f'{html.escape(kapitel["title"])}</h2>'
        )
        body += _blocks_html(kapitel["blocks"], inline, indent="  ")
        body.append("</section>")
    body.append("</article>")
    body += ['<div class="fueller"></div>' for _ in range(fueller)]
    if not ohne_kurzreferenz:
        body += _quickref(quickref, inline)

    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="de">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{html.escape(titel)} — Regelheft</title>",
            "<style>",
            schriften,
            _variables(seite),
            CSS_PATH.read_text(encoding="utf-8"),
            "</style>",
            "</head>",
            f'<body class="{"kapitelumbruch" if kapitelumbruch else ""}">',
            *body,
            "</body>",
            "</html>",
        ]
    )


# --------------------------------------------------------------------------
# PDF


def render_pdf(markdown, seite, ziel, *, kapitelumbruch):
    """Zweimal setzen: erst zaehlen, dann auf ein Vielfaches von vier auffuellen."""
    from weasyprint import HTML

    def satz(fueller=0, ohne_kurzreferenz=False):
        return HTML(
            string=build_html(
                markdown, seite, kapitelumbruch=kapitelumbruch, fueller=fueller,
                ohne_kurzreferenz=ohne_kurzreferenz,
            )
        ).render()

    erste = satz()
    seiten = len(erste.pages)

    # Die Kurzreferenz ist die Aussenseite des hinteren Umschlags. Laeuft sie
    # ueber, landet die Haelfte davon auf der Innenseite und ist beim Spielen
    # unsichtbar -- das muss der Build merken, nicht das Auge beim Korrekturlesen.
    textteil = len(satz(ohne_kurzreferenz=True).pages)
    if seiten != textteil + 1:
        raise RulebookError(
            f"Kurzreferenz belegt {seiten - textteil} Seiten statt einer; "
            "sie muss auf die Umschlagrückseite passen."
        )

    fueller = (-seiten) % 4
    dokument = satz(fueller) if fueller else erste
    if len(dokument.pages) % 4:
        raise RulebookError(
            f"Seitenzahl {len(dokument.pages)} ist kein Vielfaches von vier; "
            "Füller greifen nicht."
        )
    dokument.write_pdf(ziel)
    return seiten, len(dokument.pages)


def _marks_pdf(bogen_b, bogen_h, spread_b, spread_h, beschriftungen, schnitt=4.0):
    """Ein Bogen je Beschriftung: Schnittmarken, Falzmarke und Bogennummer.

    Die Beschriftung steht ausserhalb des Spreads und faellt beim Schneiden weg.
    Sie ist der einzige Weg, nach zwei Druckdurchgaengen zu sehen, ob Vorder-
    und Rueckseite desselben Bogens wirklich auf demselben Blatt gelandet sind.
    """
    from weasyprint import HTML

    links = (bogen_b - spread_b) / 2
    oben = (bogen_h - spread_h) / 2
    strich = "position:absolute;background:#000;"

    def marken():
        teile = []
        for x in (links, links + spread_b / 2, links + spread_b):
            for y0 in (oben - schnitt - 2, oben + spread_h + 2):
                teile.append(
                    f'<div style="{strich}left:{x:.3f}mm;top:{y0:.3f}mm;'
                    f'width:0.15mm;height:{schnitt}mm"></div>'
                )
        for y in (oben, oben + spread_h):
            for x0 in (links - schnitt - 2, links + spread_b + 2):
                teile.append(
                    f'<div style="{strich}left:{x0:.3f}mm;top:{y:.3f}mm;'
                    f'height:0.15mm;width:{schnitt}mm"></div>'
                )
        return "".join(teile)

    seiten = []
    for text in beschriftungen:
        seiten.append(
            f'<div class="bogen">{marken()}'
            f'<div class="schild" style="left:{links:.3f}mm;top:{oben - 9:.3f}mm">'
            f"{html.escape(text)}</div></div>"
        )
    doc = (
        f"<!DOCTYPE html><html><head><style>"
        f"@page{{size:{bogen_b}mm {bogen_h}mm;margin:0}}"
        f"body{{margin:0}}"
        f".bogen{{position:relative;width:{bogen_b}mm;height:{bogen_h}mm;"
        f"page-break-after:always;overflow:hidden}}"
        f".schild{{position:absolute;font-family:sans-serif;font-size:7pt;"
        f"letter-spacing:0.08em;color:#444}}"
        f"</style></head><body>{''.join(seiten)}</body></html>"
    )
    return HTML(string=doc).render().write_pdf()


def _bogenseiten(lesefolge, *, bogen, papierdicke):
    """Rueckstich: Bogen i traegt aussen [n-2i | 1+2i] und innen [2+2i | n-1-2i].

    Der Bund waechst nach innen mit: zehn ineinander gelegte Bogen schieben die
    inneren Seiten rund einen Millimeter zur Vorderkante.  Deshalb ruecken die
    inneren Seiten hier um `i * papierdicke` zum Bund hin -- nach dem Beschnitt
    stehen dann alle Seiten gleich.
    """
    import io

    from pypdf import PageObject, PdfReader, Transformation

    quelle = PdfReader(lesefolge)
    n = len(quelle.pages)
    if n % 4:
        raise RulebookError(f"{n} Seiten lassen sich nicht im Rückstich ausschießen")
    seiten_b = float(quelle.pages[0].mediabox.width)
    seiten_h = float(quelle.pages[0].mediabox.height)
    spread_b, spread_h = 2 * seiten_b, seiten_h

    bogen_b, bogen_h = bogen[0] * MM, bogen[1] * MM
    if bogen_b < spread_b or bogen_h < spread_h:
        raise RulebookError(
            f"Doppelseite {spread_b / MM:.0f}×{spread_h / MM:.0f} mm passt nicht "
            f"auf {bogen[0]}×{bogen[1]} mm"
        )

    bogenzahl = n // 4
    schilder = []
    for i in range(bogenzahl):
        schilder += [f"Bogen {i + 1} · Vorderseite", f"Bogen {i + 1} · Rückseite"]
    marken = PdfReader(
        io.BytesIO(_marks_pdf(bogen[0], bogen[1], spread_b / MM, spread_h / MM, schilder))
    )

    links = (bogen_b - spread_b) / 2
    unten = (bogen_h - spread_h) / 2

    def bogenseite(links_nr, rechts_nr, i, markenseite):
        blatt = PageObject.create_blank_page(width=bogen_b, height=bogen_h)
        blatt.merge_page(marken.pages[markenseite])
        versatz = i * papierdicke * MM
        for nr, x, richtung in (
            (links_nr, links, +1),       # linke Seite rueckt nach rechts zum Bund
            (rechts_nr, links + seiten_b, -1),
        ):
            blatt.merge_transformed_page(
                quelle.pages[nr - 1],
                Transformation().translate(tx=x + richtung * versatz, ty=unten),
            )
        return blatt

    return [
        (
            bogenseite(n - 2 * i, 1 + 2 * i, i, 2 * i),
            bogenseite(2 + 2 * i, n - 1 - 2 * i, i, 2 * i + 1),
        )
        for i in range(bogenzahl)
    ]


def _schreibe(seiten, ziel):
    from pypdf import PdfWriter

    writer = PdfWriter()
    for seite in seiten:
        writer.add_page(seite)
    with open(ziel, "wb") as fh:
        writer.write(fh)


def impose(lesefolge, ziel, *, bogen, papierdicke):
    """Ein PDF mit abwechselnd Vorder- und Rueckseite, fuer echten Duplexdruck."""
    paare = _bogenseiten(lesefolge, bogen=bogen, papierdicke=papierdicke)
    _schreibe([seite for paar in paare for seite in paar], ziel)
    return len(paare)


def impose_duplex(lesefolge, ziel_vorn, ziel_hinten, ziel_hinten_umgekehrt, *,
                  bogen, papierdicke, drehen=False):
    """Drei PDF fuer den Druck von Hand: erst alle Vorderseiten, dann alle Rueckseiten.

    Zwei Dinge haengen am Drucker und nicht am Dokument:

    Reihenfolge  -- viele Laserdrucker legen mit der Schrift nach unten ab, der
                    Stapel kommt also verkehrt herum zurueck.  Deshalb gibt es
                    die Rueckseiten in beiden Reihenfolgen; welche passt, zeigt
                    der erste Durchgang, ohne neu zu setzen.
    `drehen`     -- die Vorlage ist fuer das Wenden um die kurze Kante gerechnet
                    (links/rechts, wie beim Umblaettern).  Wer um die lange Kante
                    wendet, dreht damit die Rueckseiten um 180 Grad.

    Welche Kombination der eigene Drucker braucht, sagt `--kalibrierung` mit zwei
    Blatt Papier statt mit dem ganzen Heft.
    """
    paare = _bogenseiten(lesefolge, bogen=bogen, papierdicke=papierdicke)
    vorn = [paar[0] for paar in paare]
    hinten = [paar[1] for paar in paare]
    if drehen:
        for seite in hinten:
            seite.rotate(180)
    _schreibe(vorn, ziel_vorn)
    _schreibe(hinten, ziel_hinten)
    _schreibe(hinten[::-1], ziel_hinten_umgekehrt)
    return len(paare)


def schreibe_kalibrierung(ziel_vorn, ziel_hinten, *, bogen):
    """Zwei Blatt, die denselben Weg gehen wie das Heft und den Drucker verraten."""
    from weasyprint import HTML

    def blatt(bogennr, seite, hinweis):
        # Derselbe Pfeil auf beiden Seiten: steht er hinten unten und kopfueber,
        # wendet der Drucker um die andere Kante als angenommen.
        return f"""
        <div class="b">
          <div class="kopf">▲ OBEN</div>
          <div class="mitte">
            <div class="gross">BOGEN {bogennr}</div>
            <div class="art">{seite.upper()}</div>
            <div class="haelften"><span>linke Hälfte</span><span>rechte Hälfte</span></div>
          </div>
          <div class="fuss">{hinweis}</div>
        </div>"""

    anleitung = (
        "1. Diese Datei drucken (2 Blatt). 2. Stapel wenden, wieder einlegen. "
        "3. Die Rückseiten-Datei drucken. 4. Ergebnis prüfen: Steht hinter "
        "„BOGEN 1 · Vorderseite“ auch „BOGEN 1 · Rückseite“, passt "
        "regelheft-rueckseiten.pdf — sonst regelheft-rueckseiten-umgekehrt.pdf. "
        "Steht die Rückseite auf dem Kopf, mit --rueckseiten-drehen neu setzen."
    )
    stil = f"""
    @page{{size:{bogen[0]}mm {bogen[1]}mm;margin:0}}
    body{{margin:0;font-family:sans-serif}}
    .b{{position:relative;width:{bogen[0]}mm;height:{bogen[1]}mm;
       page-break-after:always;display:flex;flex-direction:column;
       justify-content:space-between;padding:10mm;box-sizing:border-box}}
    .kopf{{text-align:center;font-size:12pt;letter-spacing:0.3em;color:#333}}
    .mitte{{text-align:center}}
    .gross{{font-size:44pt;font-weight:700;line-height:1}}
    .art{{font-size:16pt;letter-spacing:0.22em;margin-top:3mm;color:#333}}
    .haelften{{display:flex;justify-content:space-between;margin-top:12mm;
       font-size:10pt;color:#666}}
    .fuss{{font-size:8pt;line-height:1.5;color:#444}}
    """
    for ziel, art in ((ziel_vorn, "Vorderseite"), (ziel_hinten, "Rückseite")):
        seiten = "".join(
            blatt(nr, art, anleitung if (nr == 1 and art == "Vorderseite") else "")
            for nr in (1, 2)
        )
        HTML(
            string=f"<!DOCTYPE html><html><head><style>{stil}</style></head>"
            f"<body>{seiten}</body></html>"
        ).write_pdf(ziel)


# --------------------------------------------------------------------------


def _anzeige(pfad):
    """Pfad relativ zum Repository, sonst absolut (etwa bei --output /tmp/...)."""
    pfad = pfad.resolve()
    return pfad.relative_to(ROOT) if pfad.is_relative_to(ROOT) else pfad


def main(argv=None):
    p = argparse.ArgumentParser(description="Setzt die Spielregeln als Regelheft.")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument(
        "--format",
        choices=tuple(FORMATE),
        default="karte",
        help="Heftformat: karte (62 × 88 mm) oder 10x15 (100 × 150 mm)",
    )
    # Ohne Angabe gilt der Wert des Formats.
    p.add_argument("--breite", type=float, help="Seitenbreite in mm")
    p.add_argument("--hoehe", type=float, help="Seitenhöhe in mm")
    p.add_argument("--innen", type=float, help="Bundsteg in mm")
    p.add_argument("--aussen", type=float, help="Außensteg in mm")
    p.add_argument("--oben", type=float)
    p.add_argument("--unten", type=float)
    p.add_argument("--schriftgrad", type=float, help="Grundschrift in pt")
    p.add_argument("--durchschuss", type=float, help="Zeilenabstand in pt")
    p.add_argument("--bogen", default="297x210", help="Druckbogen in mm, etwa 297x210")
    p.add_argument("--papierdicke", type=float, default=0.11, help="mm je Blatt, für den Bundzuwachs")
    p.add_argument(
        "--duplex",
        action="store_true",
        help="zusätzlich: alle Vorderseiten, dann alle Rückseiten in beiden Reihenfolgen",
    )
    p.add_argument(
        "--rueckseiten-drehen",
        action="store_true",
        help="Rückseiten um 180° drehen; nötig beim Wenden um die lange Kante",
    )
    p.add_argument(
        "--kalibrierung",
        action="store_true",
        help="zwei Testblätter schreiben, die Wendeart und Reihenfolge des Druckers zeigen",
    )
    p.add_argument(
        "--kapitelumbruch",
        action="store_true",
        help="jedes Kapitel auf einer neuen Seite beginnen (kostet rund neun Seiten)",
    )
    args = p.parse_args(argv)

    seite = dict(FORMATE[args.format])
    praefix = seite.pop("praefix")
    for name in seite:
        if getattr(args, name) is not None:
            seite[name] = getattr(args, name)
    bogen = tuple(float(v) for v in args.bogen.lower().split("x"))

    args.output.mkdir(parents=True, exist_ok=True)
    lesefolge = args.output / f"{praefix}-lesefolge.pdf"
    druckbogen = args.output / f"{praefix}-druckbogen.pdf"

    markdown = RULES_PATH.read_text(encoding="utf-8")
    roh, gesamt = render_pdf(
        markdown, seite, lesefolge, kapitelumbruch=args.kapitelumbruch,
    )
    bogenzahl = impose(lesefolge, druckbogen, bogen=bogen, papierdicke=args.papierdicke)

    ruecken = bogenzahl * args.papierdicke + 0.3
    print(f"Format    {seite['breite']:g} × {seite['hoehe']:g} mm, "
          f"{seite['schriftgrad']:g}/{seite['durchschuss']:g} pt")
    print(f"Satz      {roh} Seiten → {gesamt} mit Füllern ({gesamt - roh} leer)")
    print(f"Rückstich {bogenzahl} Bogen, Rücken rund {ruecken:.1f} mm")
    print(f"Bundzuwachs bis {(bogenzahl - 1) * args.papierdicke:.2f} mm, ausgeglichen")
    print(f"  {_anzeige(lesefolge)}")
    print(f"  {_anzeige(druckbogen)}")

    if args.duplex:
        vorn = args.output / f"{praefix}-vorderseiten.pdf"
        hinten = args.output / f"{praefix}-rueckseiten.pdf"
        hinten_umgekehrt = args.output / f"{praefix}-rueckseiten-umgekehrt.pdf"
        impose_duplex(
            lesefolge, vorn, hinten, hinten_umgekehrt,
            bogen=bogen, papierdicke=args.papierdicke,
            drehen=args.rueckseiten_drehen,
        )
        wende = "lange Kante" if args.rueckseiten_drehen else "kurze Kante"
        print(f"\nDuplex von Hand, {bogenzahl} Blatt, Wenden um die {wende}:")
        print(f"  1. {_anzeige(vorn)} drucken ({bogenzahl} Seiten)")
        print("  2. Stapel wenden und wieder einlegen")
        print(f"  3. {_anzeige(hinten)} drucken (Bogen 1 zuerst)")
        print(f"     oder {_anzeige(hinten_umgekehrt)} (Bogen {bogenzahl} zuerst),")
        print("     wenn der Drucker den Stapel verkehrt herum ablegt")
        print("  Probe: auf jedem Blatt muss vorn und hinten dieselbe Bogennummer stehen.")

    if args.kalibrierung:
        kv = args.output / "kalibrierung-vorderseiten.pdf"
        kh = args.output / "kalibrierung-rueckseiten.pdf"
        schreibe_kalibrierung(kv, kh, bogen=bogen)
        print("\nKalibrierung (2 Blatt, gleicher Weg wie das Heft):")
        print(f"  {_anzeige(kv)}")
        print(f"  {_anzeige(kh)}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RulebookError as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        sys.exit(1)
