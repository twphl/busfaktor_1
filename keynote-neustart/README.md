# Busfaktor: 1 — Präsentation

Der einzige Einstieg ist **[index.html](index.html)**. Alle benötigten Dateien liegen hier; die
Präsentation braucht zum Vorführen keine Internetverbindung. Die externen Links auf Website
und GitHub benötigen beim Öffnen Internet.
Entwurf, Implementierung und Prüfung der Präsentation stammen von einem
KI-Agenten.

## Start

`index.html` im Browser öffnen. Zum Weitergeben das gesamte ZIP entpacken und
dann die darin enthaltene `index.html` öffnen. Einzelne Dateien nicht aus ihrem
Ordner herausziehen: Die relativen Verbindungen zu den Assets gehören dazu.

Die Präsentation hat elf Folien im Format 16:9. Fünf Folien besitzen eine
Enthüllung: Titel, Tagline und Karten auf Folie 1, Stempel und Sammelkarten als
zwei Schritte auf Folie 2, Beispielprojekt, Teamfaktor und „47 Mails“ als drei Schritte auf Folie 6, das
Anlegen des gemeinsamen Servers auf Folie 7 und das Mythic Foil auf Folie 9. Die Schlussfolie steht sofort ganz. Die Weiter-Taste enthüllt zuerst die Karten oder
die Pointe und wechselt erst beim nächsten Drücken zur nächsten Folie. Zurück
durchläuft diese Schritte in umgekehrter Reihenfolge.

| Bedienung | Funktion |
| --- | --- |
| → / Bild ab / Leertaste | Weiter oder Pointe enthüllen |
| ← / Bild auf | Zurück oder Enthüllung zurücknehmen |
| Klick auf die Folie | Weiter oder Pointe enthüllen |
| Wischen nach links / rechts | Weiter / zurück |
| Pos1 / Ende | Erste / letzte Folie |
| O | Folienübersicht als Inhaltsverzeichnis |
| Esc | Folienübersicht schließen |

Die Präsentation zeigt keine Bedienelemente: Auf dem Beamer steht nur die Folie.
Klicks auf Schaltflächen und Links behalten ihre eigene Funktion und blättern
nicht weiter; eine fokussierte Schaltfläche wird mit Leertaste regulär ausgelöst.
Wo im Vortrag man gerade steht, zeigt die Folienübersicht mit O.

Für Vollbild die Funktion des Browsers verwenden (meist F11). Bei Fenstern, die
nicht 16:9 sind, nimmt der Rand um die Folie deren Grundton an. Die
Kartensammlung ist nicht Teil der Präsentation; sie steht auf der Website in
[`website/`](../website/).

## Inhalt

Der Fünf-Minuten-Vortrag verbindet die Entstehungsgeschichte mit einem
Regelüberblick:

1. Titel: Wortmarke, Tagline „Endlich spielend scheitern.“ und Kartenfächer.
2. Herkunft: Ein DH-Katastrophen-Bingo gab es schon; statt mitzumachen wird daraus ein eigenes Kartenspiel. „Scheitern, aber jetzt mit Sammelwert.“
3. Adaption: PHYLO Process of Science, eigene DH-Themen und Gestaltung, Attribution.
4. Kartenarten: Projekt, Projektfaktor, Ereignis und die vier Faktortypen Team, Daten, Betrieb, Methode.
5. Aufbau: 74 Karten, zwei Nachziehstapel, Starthand, zwei bis vier Personen.
6. Spielzug: ziehen, Aktionen, Handlimit; Ereignis-Beispiel „47 Mails“.
7. Kooperation: Voraussetzungen, gemeinsamer Faktor, eigener Projektabschluss.
8. Abschluss und Wertung: sofort fertig, Punkte und unfertige Projekte nach sechs Runden.
9. Auflage und Foil-Enthüllung: die unbefristete Stelle als institutionelles Wunder.
10. Community: Blanko-Karten und eigene Geschichten.
11. Open Source: Dank ans Publikum, Einladung zum Spielen, Forken und Weiterentwickeln, mit Website und Repository.

Die Schlussfolie nennt die öffentliche Website **https://www.busfaktor-eins.de**
und verlinkt **https://github.com/twphl/busfaktor_1** mit einem lokal erzeugten,
geprüften QR-Code; unten rechts steht die Ottermarke wie auf der Titelfolie,
unten links das Siegel. Links steht die Adresse unter einer goldenen Linie noch
einmal ausgeschrieben, darunter was dort wartet: Kartendesigner und Spielen im
Browser, allein gegen Bots, zu mehreren an einem Gerät oder online. Die beiden
QR-Karten rechts tragen nur noch „Weitere Informationen“ und „Repository auf
GitHub“.
Die vollständigen Regeln liegen als unveränderte Kopie von
`docs/10-spielregeln.md` in [SPIELREGELN.md](SPIELREGELN.md) bei; die Folie
selbst verweist dafür auf die Website. Sonderfälle stehen im Regelblatt.

## Typografie und Siegel

Die gesamte Titelwortmarke „BUSFAKTOR:1“ verwendet die lokal mitgelieferte
**Noto Sans Bold** unter dem CSS-Alias `Sans`, mit 112px, 116,48px
Zeilenhöhe, Gewicht 700 und −0,01em Laufweite in einem 761,6px breiten
Satzblock. Die Metadaten stehen in einer 680px breiten Zeile, der Untertitel
ist 44px groß. Die obere Linie hält Abstand zur Schrift; die untere Linie
steht am Titel.
Wort und Doppelpunkt sind cremefarben, die Ziffer golden und eng mit dem
Doppelpunkt verbunden. Alle Zeichen einschließlich der fußlosen „1“ sind
normaler Text und bleiben direkt vorlesbar und kopierbar.
Künstliche Schriftschnitte sind deaktiviert.

Die übrigen großen Folienüberschriften und der Auftaktuntertitel verwenden
**Bitter** als markante Slab-Serif. Ihre goldenen Betonungen sind
aufrecht und im gleichen Gewicht und Schriftgrad gesetzt. Die kleineren
Begleittexte bleiben in **Noto Sans**; fette Zwischenüberschriften gliedern die
Regelabschnitte. Kleine goldene Textbetonungen bleiben ebenfalls in Noto Sans,
aufrecht und mit Gewicht 400. **Noto Serif** erscheint ausschließlich im
Bingo-Objekt einschließlich seines kursiven Freifelds. Bitter und die Noto-Schriften
liegen lokal bei. Noto Sans Bold, Bitter und Noto Sans Regular werden bereits im HTML
per Font-Preload vorbereitet; dafür ist keine Internetverbindung nötig.

Die Typografierollen in `deck.css` verwenden 14px für Randinformationen,
16px für Labels, 18px für Notizen, 22px für Fließtext, 28px für
Teilüberschriften, 44px für den Auftaktuntertitel und einheitlich 84px für alle
Inhaltsüberschriften. Diese verwenden Bitter 750, Zeilenhöhe 1,14 und −0,025em
Laufweite; einzelne betonte Wörter werden nicht vergrößert. Auch der
Auftaktuntertitel verwendet Gewicht 750. Große Stapel- und Druckzahlen sowie die
Wertungsrechnung verwenden ebenfalls Bitter 750 bei 84px. Text unter den
Headlines besteht aus acht Inhaltstypen (Absatz, Liste, Ablauf, Teilüberschrift,
Zuordnung, Kennzahl, Label, Notiz); Noto Sans
verwendet die vorhandenen Schnitte Regular und Bold.

Die Inhaltsüberschriften beginnen einheitlich bei x74/y140px, mit 28px Abstand
zum folgenden Text oder Inhalt. Ganze Textgruppen folgen dieser Ausrichtung;
Karten, andere Ausstellungsobjekte und die Schlusslinks haben eigene Positionen.
Der Textblock der Kooperationsfolie ist 820px breit, damit die Überschrift
„Ein Faktor. Gemeinsam ans Ziel.“ zweizeilig bleibt; das Diagramm bleibt an
seinem Platz.
Die Kartenartenfolie stellt drei Karten von 236px Breite in Spalten von 300px
mit 48px Abstand nebeneinander; rechts steht der 400px breite Schlüssel der vier
Faktortypen unter einer goldenen Linie. Ihre Typ- und Faktorsymbole stammen aus
`assets/icons/` und liegen zusätzlich als `<symbol>`-Sprite im HTML. Nur so
erscheinen sie auch beim Öffnen über `file://`: als Maske oder `<img>` lädt der
Browser die lokalen SVG-Dateien dort nicht.
Die Titelgruppe auf Folie 1 beginnt ebenfalls bei x74/y140px.

Diese Pixelwerte gelten auf der **unskalierten Bühne mit 1600 × 900px**.
Fließtext und Nebenregeln verwenden meist die Zeilenhöhe 1,5. Die Übersicht
liegt außerhalb der skalierten Bühne; ihr Titel, ihre Einträge und Nummern
sind in `rem` gesetzt und passen sich den bestehenden Fenster-Breakpoints an.

Das Original-Siegel aus `build/seal/siegel.svg` trägt den Kaltstart: Folie 1
zeigt es zunächst groß in der Bildmitte und ruhig pulsierend über einem langsam
driftenden Hintergrund. Links unten steht der Name „TIM WESTPHAL“. Beim Reveal
wird der Name ausgeblendet und das Siegel rückt als kleinere Marke an seinen
Platz. Beim Zurückgehen erscheint der Name wieder. Das Siegel dient außerdem
als Browser-Icon. Titel, Tagline und Karten bleiben bis zur Enthüllung verborgen.
Auf der letzten Folie steht dasselbe Siegel dauerhaft links unten, in gleicher
Größe und Position wie nach der Auftaktenthüllung. Die Eingangsanimation gilt
nur für die Titelfolie. Die Umschrift der Siegelgrafik stammt aus **Noto Sans Bold**, aufrecht mit Gewicht 700, und ist im
SVG als Pfade gespeichert. Die gerenderten Karten werden unverändert verwendet.

## Vortragen

Die Präsentation zeigt keine Notizen und keinen Timer: Auf dem Beamer landet
nur die Folie. Sprechtext, Regiehinweise und Zeiten liegen getrennt von
der Präsentation und gehören nicht zum Repository. Der Vortrag ist auf fünf
Minuten angelegt.

## Farben

Alle Hintergrundfarben stehen als Tokens in `:root` und sonst nirgends. Jede
Regel im Deck greift darauf zu, statt einen Hexwert zu wiederholen:

- `--black-rgb` — der Bühnengrund, auf dem alle elf Folien liegen.
- `--mist-rgb` — der Nebel, den sechs Folien hinter ihrem Blickfang tragen.
- `--mist-lift-rgb` — der hellere Schleier über dem Nebel (Auftakt, Gründung).
- `--shade-rgb` — der Schleier, der die Fotofolien abdunkelt.
- `--void` — der Rahmen um die Bühne außerhalb des 1600 × 900-Formats.

Es gibt genau zwei Farbtöne: Grund und Bildschleier liegen auf 150°, der Nebel
auf 41° — dem Farbton von `--gold`. Innerhalb eines Tokens ändert sich nur
Helligkeit und Deckkraft, und jeder Verlauf blendet nach `transparent` aus statt
auf eine zweite Farbe. Dadurch bleibt der Ton über die ganze Fläche gleich.

Eine Folie mit Nebel setzt nur ihre Position, nie eine Farbe:

```css
.lineage{--mist-x:82%;--mist-y:50%}
```

## Dateien

- `index.html`: einzige Präsentation, elf Folien.
- `deck.css` und `deck.js`: Gestaltung und Bedienung.
- `SPIELREGELN.md`: vollständige Regeln, offline lesbar.
- `assets/`: 82 Karten, 82 Illustrationen, sechs Blankos, Rückseite, Schriften,
  Icons, Ottersiegel und Quellenhinweise.
- `prepare.py`: erstellt die Bildschirmassets aus den Originalquellen.
- `bundle.py`: erstellt das Offline-Paket und prüft dessen Vollständigkeit.
- `.build/`: temporäre Renderer- und Prüfausgaben; gehört nicht ins ZIP.

## Quellen aktualisieren

Aus dem Repository-Verzeichnis:

```bash
python3 keynote-neustart/prepare.py
python3 scripts/validate_cards.py
python3 keynote-neustart/bundle.py
```

Die Aufbereitung verwendet die verfügbaren Python-Renderer-Abhängigkeiten
(Pillow, resvg_py) und die lokalen Noto-Schriften. Vor dem Übernehmen prüft sie
die gerenderten Karten gegen die kanonischen Daten, Illustrationen und
Rendererdateien. Veraltete Kartenrender müssen zuvor regulär erneuert werden.

Der Spielsatz enthält 74 physische Karten; das Gesamtset enthält 82 Motive.
Die Zahlen sind unterschiedliche Größen. Die zwölf Blanko-Karten beziehen sich
auf den Druckplan `234-plus-18` (ADR 0019).
Die Schlussfolie zeigt beide Adressen als QR-Code untereinander. Bei einer
Änderung der öffentlichen Adressen neu erzeugen:

```bash
qrencode -t SVG -l Q -m 4 -o keynote-neustart/assets/website-qr.svg \
  'https://www.busfaktor-eins.de'
qrencode -t SVG -l Q -m 4 -o keynote-neustart/assets/repository-qr.svg \
  'https://github.com/twphl/busfaktor_1'
```

Die Einladung zu Community-Ideen sagt keine Veröffentlichung oder weitere
Auflage zu. Die Systemeinstellung für reduzierte Bewegung wird respektiert.

Quellen und Bildnachweise: [assets/QUELLEN.txt](assets/QUELLEN.txt).
