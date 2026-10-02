# Busfaktor: 1 — Website

Eine eigenständige, scrollbare Projektwebsite für das Sammelkartenspiel.
Inhalt und Trade Dress folgen der Präsentation in `keynote-neustart/`: Jede
übernommene Folie wird zu einem Abschnitt mit derselben Überschrift. Die
Folien verteilen sich auf zwei Seiten: Die Startseite erzählt, woher das
Spiel kommt und wie man mitmacht, die Seite
[`spielprinzip.html`](spielprinzip.html) erklärt eine Partie. Was ins Deck
nicht gehört, steht auf eigenen Seiten: die vollständigen Regeln
([`regeln.html`](regeln.html)), die durchsuchbare Kartensammlung
([`karten.html`](karten.html)), der Kartendesigner
([`generator.html`](generator.html)) und die spielbare Partie
([`spielen.html`](spielen.html)).

## Start

```bash
make website-serve     # oder: python3 -m http.server 8000 --directory website
```

Dann `http://localhost:8000/` öffnen. Startseite, Regeln, Kartensammlung und
die Partie funktionieren auch direkt aus dem Dateisystem; der Generator
braucht einen Server, weil er Schriften und Illustrationen per `fetch` lädt.
Der Online-Modus der Partie braucht zusätzlich den Signaling-Server aus
[`../server/`](../server/).

## Linkvorschauen

Alle sieben Seiten besitzen Open-Graph- und Twitter-Card-Metadaten sowie
eine kanonische URL. Titel und Beschreibung werden aus dem jeweiligen
HTML-Kopf übernommen. Die öffentliche Basisadresse steht in
`site-config.json`: `https://busfaktor-eins.de/`. Bei einem anderen Host oder
Unterverzeichnis dort die vollständige Basisadresse ändern.

Das gemeinsame Vorschaubild `assets/social-preview.png` ist 1200 × 630 Pixel
groß. `social_preview.py` setzt Wortmarke, Slogan und weißes Siegel neben einen
Fächer aus den vorhandenen Karten KAT-C03, KAT-M03 und KAT-U21. Schriften und
Farben entsprechen der Website; die Grafik braucht keine externen Assets.

`make website` erneuert Grafik und Metadaten automatisch. Nur die Linkvorschau
lässt sich ohne Aufbereitung der übrigen Website aktualisieren:

```bash
uv run python website/social_preview.py
python3 website/social_meta.py
```

Beim Veröffentlichen die geänderten HTML-Dateien und `assets/social-preview.png`
mit übertragen. Die Metadaten stehen direkt im HTML und sind ohne JavaScript
lesbar. Bereits zwischengespeicherte Vorschauen können beim jeweiligen Dienst
noch den vorherigen Stand zeigen.

## Startseite und Spielprinzip

| Seite und Abschnitt | Entspricht im Deck |
| --- | --- |
| Start · Auftakt: Wortmarke, „Endlich spielend scheitern.“, Kartenfächer, Siegel, Ottermarke | Folie 1 |
| Start · 01 Die Entstehungsgeschichte: Bingo-Entwurf mit Stempel „IDEE VERWORFEN“ und Sammelkarten | Folie 2 |
| Start · 02 Zwerge auf den Schultern von Riesen: PHYLO Process of Science, Deckvorbilder, drei Beispielkarten, eigene Umsetzung (nur Website), Credits | Folie 3 |
| Start · 03 Die Anti-Konferenz-Edition: Motive, Booster und Druckvorlage in Fließtext, verdeckte Mythic | Folie 9 |
| Start · 04 Mitmachen: Einladung zu eigenen Karten, Kartendesigner, Blanko-Karten und offene Quellen | Folien 10 und 11 |
| Spielprinzip · 01 Die Kartenarten: drei Kartenarten, vier Faktortypen | Folie 4 |
| Spielprinzip · 02 Der Spielaufbau: zwei Stapel, zwei Ablagen, Starthand | Folie 5 |
| Spielprinzip · 03 Der Spielablauf: drei Schritte, Beispiel „47 Mails“ | Folie 6 |
| Spielprinzip · 04 Synergien finden: ein gemeinsamer Faktor für zwei Projekte | Folie 7 |
| Spielprinzip · 05 Der Spielabschluss: Wertung, Beispielrechnung, Gleichstand | Folie 8 |

Die Nummern zählen je Seite; die Kopfzeilen tragen die Titel des Decks. Nur
die Website hat die Verweise auf Regeln, Partie, Sammlung und Kartendesigner.

Nichts bewegt sich beim Scrollen. Wo das Deck etwas enthüllt, steht auf der
Website der Endzustand: Der Stempel liegt schon auf dem Bingo-Entwurf, die
Karten sind aufgefächert, das Zugbeispiel zeigt „47 Mails“ auf dem Projekt, der
Server liegt zwischen beiden Projekten. Einzige Ausnahme ist die Mythic-Karte
unter „Anti-Konferenz-Edition“: Sie liegt verdeckt und dreht sich erst, wenn
jemand auf sie klickt, als Easter Egg (`app.js`). Ohne JavaScript liegt sie
offen.

Die drei PHYLO-Beispielkarten sind unverändert übernommen und stehen nicht
unter CC BY-SA, sondern unter CC BY-NC-ND 4.0. Ihr Credit steht in der
Fußzeile des Abschnitts, auf `lizenzen.html` und in `assets/QUELLEN.txt`
(siehe auch `docs/09-licensing-and-attribution.md`).

## Regeln

`regeln.html` zeigt `docs/10-spielregeln.md` als Webseite: Inhaltsverzeichnis
als mitlaufende Spalte (auf schmalen Bildschirmen zum Aufklappen), jedes
Kapitel mit eigenem Anker (`regeln.html#kooperation`), Beispiele und
Kurzreferenz abgesetzt, eine Druckfassung in Schwarz auf Weiß. Die Kopfzeile
nennt Version und Stand aus dem Kopf der Regeln.

Der Knopf „Als PDF“ neben „Als Markdown“ öffnet ein Menü mit dem Regelheft zum
Herunterladen: die Lesefolge im Kartenformat, die Druckbögen (A4 quer,
beidseitig) und für Drucker ohne Duplexdruck Vorder- und Rückseiten getrennt
samt Probebogen. Das Menü ist ein `<details>`; `regeln.js` schließt es bei
einem Klick daneben, mit Escape oder nach der Auswahl.
`prepare.py` übernimmt sie aus `build/regelheft/` nach `assets/druck/` und
bricht ab, wenn sie fehlen oder älter als `docs/10-spielregeln.md` sind; dann
zuerst `make rulebook`.

Die Seite wird nicht von Hand gepflegt. `prepare.py` übergibt die Regeln an
`rules_page.py`, und das schreibt Kopfzeilenstand, Inhaltsverzeichnis und Text
zwischen die Markierungen `<!-- regeln:NAME -->` und `<!-- /regeln:NAME -->`
in `regeln.html`; Titel, Einleitung und Rahmen drumherum bleiben von Hand
gesetzt. `rules_page.py` setzt genau das Markdown um, das die Regeln benutzen
(Überschriften bis `###`, Absätze, flache Listen, Zitate, Tabellen, Fett,
Kursiv, Code, Links), und bricht bei allem anderen ab, statt es falsch zu
zeigen. Dazu kommen Verweise:

- `§4` wird zum Link auf Kapitel 4, `ADR 0010` zum ADR auf GitHub.
- Code mit einem Dateinamen aus dem Repository (`../data/cards.csv`) verlinkt
  die Datei auf GitHub.
- Code mit einem Kartennamen öffnet die Karte in der Sammlung
  (`karten.html#KAT-C02`). Code, der wie ein Kartenname aussieht, aber zu
  keiner Karte passt, meldet `make website` als Hinweis.
- Schlüsselwörter in Großbuchstaben (`MEHRAUFWAND`) erscheinen wie auf den
  Karten.

Neben der Seite liegt `SPIELREGELN.md` als unveränderte Kopie zum Herunterladen.

## Kartensammlung

`karten.html` zeigt alle 82 Motive mit Suche über Titel, Kartennummer,
Regeltext, Pointe und redaktionelle Tags sowie Filtern nach Seltenheit und
Bereich. Das Kartendetail zeigt Regeltext, Pointe und Illustration und öffnet
die Karte als Vorlage im Generator. Jede Karte hat eine eigene Adresse
(`karten.html#KAT-C03`), die das Detail direkt öffnet.

Der Download „Alle 82 Motive als A4-PDF“ enthält jedes Motiv einmal, nur die
Vorderseiten: 10 A4-Seiten mit bis zu neun Karten und Schnittmarken.
Die Karten bleiben im Endformat von 63,5 × 88,9 mm bei 300 dpi.
Beim Drucken „Tatsächliche Größe“ beziehungsweise 100 % wählen und die
Seitenanpassung ausschalten.

`make cards-a4` erzeugt `output/pdf/busfaktor-1-karten-a4.pdf` aus der geprüften
Druckstrecke sowie ein Prüfmanifest mit SHA-256-Prüfsummen.
`prepare.py` prüft vor dem Kopieren die PDF und alle im Manifest erfassten
Quelldateien und übernimmt sie nach `assets/druck/`. Bei fehlenden oder
veralteten Dateien bricht der Website-Build mit einem Hinweis auf
`make cards-a4` ab.

## Kartendesigner

`generator.html` gestaltet eine Karte im Layout der gedruckten Karten und
lädt sie als PNG (1500 × 2100 px, geschnitten), als Druck-PNG mit Beschnitt
(1644 × 2244 px, 600 dpi, sRGB), als SVG mit eingebetteten Schriften oder
als CSV-Zeile mit den Spalten von `data/cards.csv` herunter. Nichts wird
hochgeladen; der Entwurf bleibt im Browser (`localStorage`).

Die Formularlogik folgt `docs/11-community-expansion.md` und dem
Tischaushang: Projektfaktor mit Faktortyp (oder Joker mit zwei Typen),
Ereignis über die Bausteine E1–E8 mit Ziel, Projekt mit zwei bis vier
Anforderungen und Punktwert gleich Anforderungszahl. Der Regeltext entsteht
aus diesen Bausteinen; mit ihnen entstehen die Regeltexte von 72 der 82
Set-Karten wortgleich. Frei formulierbar ist er nur über einen Schalter, für
Forks und eigene Varianten. Community-Karten tragen `KAT-X`-Nummern und statt
einer Seltenheit „COMMUNITY“ mit leeren Pips, wie die Blanko-Karten „BLANKO“.
Ohne hochgeladenes Bild zeigt das Bildfenster die Papierfläche der Blankos.
Jede Set-Karte lässt sich als Vorlage laden, auch aus dem Kartendetail der
Sammlung (`generator.html?vorlage=KAT-C03`).

### Renderer im Browser

`renderer.js` ist eine Portierung von `scripts/render_cards.py`
(`build_card_svg` und alles, was es zeichnet). Die Funktionsnamen folgen dem
Python-Original. Layout, Renderprofil, Konstanten, deutsche Wortlisten,
Icongeometrie und FreeType-Schriftmetriken exportiert `prepare.py` direkt aus
dem Python-Renderer nach `renderer-data.js`; dort steht keine Zahl von Hand.
Textbreiten misst `canvas.measureText` mit den fünf Noto-Dateien des Renderers
bei vierfacher Größe, wie Pillows RAQM-Layout.

`make website-parity` rendert alle 82 Karten mit beiden Renderern und
vergleicht die SVG-Bäume Element für Element. Ergebnis: 82/82 Karten mit
identischer Struktur, identischen Textzeilen und Geometrie. Übrig bleiben
Zahlenschreibweisen (`74.0` gegenüber `74`) und Positionen aus der Textmessung,
die um höchstens 0,0048 Einheiten (0,5 µm) abweichen: Pillow rundet jede
Glyphenbreite auf 1/64 Pixel, der Browser nicht. Nicht verglichen wird das
Einbetten der Illustration; ein Sichtvergleich mit den gedruckten
Bildschirmassets zeigt dort keinen Unterschied.

Der Generator ersetzt nicht die Druckstrecke: Druckdateien fürs Set kommen
aus `scripts/render_cards.py` mit Preflight und Review-Gates.

## Spielen

[`spielen.html`](spielen.html) spielt eine vollständige Partie im Browser,
nach `docs/10-spielregeln.md` Version 1.0 mit dem Bühnensatz aus 74 Karten
(16 Projekte, 46 Projektfaktoren, 12 Ereignisse). Es gibt drei Besetzungen:

- **Allein gegen Bots.** Ein bis drei Bots, jeder mit einem eigenen Profil.
- **Zu mehreren an einem Gerät.** Zwischen zwei Zügen deckt ein Übergabe-
  schirm den Tisch ab; die Hand der nächsten Person wird erst nach ihrer
  Bestätigung sichtbar. Er erscheint auch mitten im Zug, wenn eine andere
  Person entscheiden muss — etwa über eine Absicherung.
- **Online über WebRTC.** Ein Raumcode, die Partie läuft direkt zwischen den
  Browsern. Dazu gehören [`network.js`](network.js) und der
  Signaling-Server unter [`../server/`](../server/); dessen Betrieb steht in
  `server/README.md`.

Solo und am selben Gerät bleibt alles lokal: Der Spielstand liegt in
`localStorage` und wird beim Neuladen als „Laufende Partie“ angeboten. Im
Online-Modus vermitteln Signaling- und STUN-Server den Verbindungsaufbau, die
Züge selbst laufen zwischen den Browsern.

Am Tisch liegen die gerenderten Karten selbst: Handkarten, Projekte, die
oberste Karte der Ablage und die Auswahl beim Sichten zeigen das Kartenbild.
Weil dessen Druck in Tischgröße nicht lesbar ist, steht der Name darunter, und
beim Überfahren mit der Maus erscheint die Karte groß. Was ein Projekt noch
braucht, steht als Liste der Anforderungen neben der Projektkarte; an den
anderen Plätzen als Farbsymbole, deren Karten beim Überfahren erscheinen.

Während der Partie treten Einleitung und Fußzeile zurück. Ab 901 px Breite ist
der Tisch genau so hoch wie das Fenster unter der Kopfleiste, die Seite scrollt
nicht: Protokoll und Entscheidungsfeld scrollen in der rechten Spalte, ein zu
voller Tisch wird verkleinert (bis 80 %), eine zu lange Projektreihe ebenso
(bis 70 %). Erst darüber hinaus scrollt der Tisch selbst. Auf dem Handy bleibt
er eine lange, scrollende Seite.

Karten, die ihren Platz wechseln, fliegen dorthin: gezogen, begonnen,
angelegt, ausgespielt, abgeworfen, abgeschlossen, auch bei Bots und anderen
Personen. Vom Stapel und aus fremden Händen kommen sie verdeckt und drehen sich
um, sobald sie offen liegen; ein Abschluss zeigt die Punkte. Dafür vergleicht
`spielen.js` bei jedem Zeichnen, wo jede Karte liegt, mit dem Zeichnen davor.
Mit reduzierter Bewegung im System entfallen die Flüge.

### Aufbau

| Datei | Rolle |
| --- | --- |
| [`game-engine.js`](game-engine.js) | die Regeln als Zustandsmaschine |
| [`game-bots.js`](game-bots.js) | die Bots |
| [`spielen.js`](spielen.js) | Tisch, Auswahl, Übergabe, Takt der Bots |
| [`network.js`](network.js) | Räume, Host-Client-Abgleich (Online) |

Die Engine entscheidet nichts selbst: `legalActions(state)` zählt alle Züge
auf, die die gerade entscheidende Person machen darf, `apply(state, action)`
führt einen davon aus und weist alles andere zurück. Entscheidungen, die im
Simulator noch die Maschine getroffen hat — Ziele von Ereignissen,
Absicherungen, Kooperationen —, sind hier eigene Züge. Der Zustand ist reines
JSON, deshalb lässt er sich speichern und über das Netz schicken.

Wer am Zug ist, steht in `actor(state)`: normalerweise die aktive Person, bei
einer offenen Entscheidung (`state.pending`) diejenige, die sie treffen muss.
So laufen Reaktionsfenster (§12), die Zustimmung zu einer Kooperation (§11)
und die Wahl des Faktortyps bei `KAT-U02` durch dieselbe Schleife.

`playerView(state, seat)` erzeugt die Sicht einer einzelnen Person für den
Online-Modus: fremde Hände, beide Nachziehstapel, der Verbrauchsstapel und der
Zufallsgenerator werden maskiert, die Längen bleiben erhalten, damit Anzeige
und Zugprüfung weiterarbeiten. Der Host ist maßgeblich; er prüft bei jedem
Zug, ob er von der Person kommt, die gerade entscheiden darf.

### Bots

Die Profile sind eine Portierung von `scripts/sim/strategies.py`; die
Heuristiken für Ereignisziele, Absicherungen und Kooperationen kommen aus
`scripts/sim/engine.py`.

| Profil | Entspricht | Verhalten |
| --- | --- | --- |
| Umsichtig | `open-1-safe` | ein Projekt nach dem anderen |
| Abwartend | `hoard` | legt ein Projekt erst aus, wenn es im selben Zug fertig wird |
| Kooperativ | `coop` | zwei Projekte zugleich, bietet Kooperationen an |

Gegenprobe gegen den Simulator, je 2000 Partien mit den Parametern der
Fassung 1.0 (`minus_mode="flat1"`, Kooperation mit Einzelabschluss), mittlere
Punktzahl pro Person: 4,38 gegen 4,35 (umsichtig / `open-1-safe`, vier
Personen), 4,58 gegen 4,56 (abwartend / `hoard`), 4,39 gegen 4,31
(kooperativ / `coop`), 4,19 gegen 4,14 (umsichtig, zwei Personen). Die
Differenzen liegen im Rauschen dieser Stichprobe; verglichen wurden Mittelwerte,
nicht einzelne Partien.

### Bewusste Vereinfachungen

- **Nur der Bühnensatz.** Die 16 Motive außerhalb des Bühnensatzes und die
  Foil-Mythics sind nicht im Stapel; ihre Texte stehen in der Sammlung.
- **Umverteilen (`KAT-R15`)** verschiebt nur Faktoren, die an einem eigenen
  Projekt liegen, keinen gemeinsamen Faktor einer Kooperation.
- **Ein verschobener Faktor behält seinen Faktortyp**, auch eine Wildcard
  (§4: die Wahl bleibt bestehen, solange die Karte angelegt ist).
- **Erzwungene Entscheidungen mit genau einer Möglichkeit** lösen sich selbst
  auf, etwa bei `KAT-R16`, wenn jemand nur einen angelegten Faktor hat.
- **Das Reaktionsfenster fragt nur, wer eine passende Absicherung hält.** An
  einem Gerät verrät die Übergabe damit, dass diese Person eine hat; am Tisch
  aus Papier bliebe das verborgen.
- **Abgelehnte Angebote** (Kooperation, gemeinsamer Faktor) werden im selben
  Zug nicht noch einmal angeboten. Die Regeln verbieten das Nachfragen nicht.

### Prüfen

```bash
make website-game       # Regeln, Bots und playerView, 33 Tests
make website-game-ui    # spielt spielen.html in Chromium durch (Playwright)
```

`website-game` prüft den Bühnensatz, den Zugablauf, Ereignisse, Kooperation und
Wertung gegen die Paragrafen der Regeln und spielt 1200 Partien mit zufälligen
zulässigen Zügen sowie 600 Bot-Partien; nach jedem Zug muss jede der 74 Karten
genau an einem Ort liegen. `website-game-ui` spielt drei Partien über die
Oberfläche: allein gegen Bots, zu zweit an einem Gerät — dabei darf beim
Übergabeschirm keine Handkarte sichtbar sein — und einmal mit Neuladen.
Der Online-Modus ist von diesen Tests nicht abgedeckt.

## Gestaltung

Farben und Schriften folgen `keynote-neustart/deck.css`: Alle
Hintergrundfarben stehen als Tokens in `:root` (`--black-rgb`, `--mist-rgb`,
`--mist-lift-rgb`, `--shade-rgb`, `--void-rgb`). Ein Abschnitt mit Nebel
setzt nur `--mist-x`/`--mist-y`; der Verlauf blendet nach `transparent` aus.
`--mist-y` bleibt nahe 50 %, damit an den Abschnittsgrenzen keine Kanten
entstehen.

Die Wortmarke „BUSFAKTOR:1“ steht in Noto Sans Bold mit goldener Ziffer,
Überschriften in Bitter 750 mit aufrechter goldener Betonung, Fließtext in
Noto Sans. Kleine goldene Betonungen bleiben in der umgebenden Schrift.
Noto Serif gibt es auf der Seite nur auf dem Bingo-Blatt; in den gerenderten
Karten setzt der Renderer seine eigenen Noto-Schnitte. Große Zahlen stehen in
Bitter, kleine Regelzahlen in Noto Sans Bold. Alle Überschriften haben
dieselbe Größe; nur der lange Abschlusstitel wird bis 350 px Bildschirmbreite
leicht verkleinert, damit er vollständig in die Textspalte passt.

Favicon und Footer verwenden die reinweiße Stickerfassung des Siegels:
`prepare.py` übernimmt `build/seal/siegel-reinweiss.svg` unverändert als
`assets/seal-white.svg`. Das Siegel im Auftakt bleibt `assets/seal.svg`
aus den Keynote-Assets.

Text unter einer Überschrift besteht wie im Deck aus acht Inhaltstypen:
Absatz `.text`, Liste `ul.list`,
Ablauf `ol.steps`, Teilüberschrift `.subhead`, Zuordnung `dl.map` (mit
`.arrow` oder `.values`), Kennzahl `.figure`, Label `.label` und Notiz `.note`.
Dazu kommen wie in `keynote-neustart/deck.css` die Textblöcke `ul.text-blocks`
(Teilüberschrift mit Absatz, ohne Nummer).
Textspalten tragen `.copy`; die Abstände dazwischen stehen als `--heading-gap`,
`--space-*`, `--marker-w` und `--map-key` in `:root`, auf die Webgrößen
umgerechnet. Unter Überschriften stehen nur `cream`, `soft`, `quiet` und
`gold`. Neue Abschnitte, auch auf den Unterseiten, verwenden diese Klassen
statt eigener Größen, Farben oder Abstände.

## Dateien

- `index.html`, `app.js`: die Startseite.
- `spielprinzip.html`: eine Partie von den Kartenarten bis zur Abrechnung.
- `spielen.html`, `spielen.js`: die Partie im Browser.
- `game-engine.js`, `game-bots.js`: Regeln und Bots der Partie.
- `network.js`: Räume und Abgleich für den Online-Modus; Server unter `../server/`.
- `regeln.html`, `regeln.js`: die Regeln; der Text darin kommt aus `rules_page.py`.
- `karten.html`, `karten.js`: die Kartensammlung.
- `generator.html`, `generator.js`: der Kartendesigner.
- `lizenzen.html`: Pflicht-Credit, Lizenzen der eigenen und fremden Teile.
- `style.css`, `site.js`: Gestaltung und Navigation für alle Seiten.
- `renderer.js`: der portierte Kartenrenderer.
- `renderer-data.js`: aus dem Python-Renderer exportierte Daten, nicht von Hand bearbeiten.
- `cards.js`: aus `data/cards.csv` generierte Kartendaten.
- `SPIELREGELN.md`: unveränderte Kopie von `docs/10-spielregeln.md`.
- `rules_page.py`: setzt `docs/10-spielregeln.md` in `regeln.html` um.
- `assets/`: Karten, Illustrationen, Rückseite, Siegel, Ottermarke,
  Icons, Fonts und Repository-QR-Code aus `keynote-neustart/assets/`, dazu
  die fünf Noto-Schnitte des Renderers (siehe `assets/QUELLEN.txt`), die
  Blanko-Motive (`assets/blank/`), die PHYLO-Beispielkarten
  (`assets/inspiration/`), die Regelheft-PDF (`assets/druck/`) und
  unter `assets/cards-sm/` die Karten und die Rückseite in 360 px Breite für
  den Spieltisch.
- `prepare.py`: baut `assets/`, `cards.js`, `renderer-data.js`, `SPIELREGELN.md`
  und den Regeltext in `regeln.html` neu auf.
- `tests/`: Paritätstest der beiden Renderer (`check_renderer_parity.mjs`,
  `parity.html`, `parity.js`, `python_reference.py`).

Es gibt keine Laufzeitabhängigkeit zu `keynote-neustart/`; der Verweis auf
die Keynote im Abschnitt „Open Science, Open Source“ ist ein einfacher
relativer Link (`../keynote-neustart/index.html`) und setzt voraus, dass
beide Ordner gemeinsam ausgeliefert werden.

## Quellen aktualisieren

```bash
python3 keynote-neustart/prepare.py   # falls dessen assets/ fehlt oder veraltet ist
make rulebook                         # nach Änderungen an den Regeln: Regelheft-PDF
make cards-a4                         # nach neuen Druckrendern: A4-Kartendruckvorlage
make website                          # validate + website/prepare.py
make website-parity                   # nach Änderungen an scripts/render_cards.py
```

`website/prepare.py` rendert keine Karten neu; es übernimmt die bereits
geprüften Bildschirmassets aus `keynote-neustart/assets/`, liest die
Kartendaten frisch aus `data/cards.csv`, setzt die Regeln aus
`docs/10-spielregeln.md` in `regeln.html`, exportiert die Rendererdaten und
verkleinert die Kartenbilder für den Spieltisch nach `assets/cards-sm/`.
Nach jeder Änderung an den Regeln reicht `make website`.
Nach Änderungen an Kartendaten, Illustrationen oder Kartenlayout zuerst die
Druckbilder mit `make print-run` und die A4-Vorlage mit `make cards-a4` erneuern.
Anschließend die Bildschirmassets mit `python3 keynote-neustart/prepare.py`
aktualisieren und `make website` ausführen. Ändert sich Zeichenlogik, muss sie in
`renderer.js` nachgezogen werden, bis `make website-parity` wieder 82/82
meldet. Ändern sich Folientexte im Deck, die entsprechenden Abschnitte in
`index.html` und `spielprinzip.html` von Hand nachziehen.
