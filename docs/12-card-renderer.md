# Programmatischer Kartenrenderer

Der Produktionsrenderer erzeugt Karten direkt aus `data/cards.csv`, der
eigenständigen Layoutkonfiguration und den Illustrationen unter `data/cards/`.
Figma ist weder Eingabe noch Laufzeitabhängigkeit. Die Entscheidung ist in
ADR 0012 dokumentiert.

Die aktuellen Versionsnummern stehen in `data/card_layout.json` (Layout) und
`scripts/render_cards.py` (`RENDERER_VERSION`).

## Ausgabeformat

`data/render_profile.json` ist der maschinenlesbare Vertrag. Die Ausgabe wird
nicht nachträglich hochskaliert: Das SVG wird unmittelbar in der endgültigen
Rastergröße gerendert.

| Bereich | SVG-Master | Upload-PNG | Physisches Maß |
|---|---:|---:|---:|
| Außenformat/Bleed | 822 × 1122 | 1644 × 2244 | 69,6 × 95,0 mm |
| Schnitt | `(36, 36, 750, 1050)` | `(72, 72, 1500, 2100)` | 63,5 × 88,9 mm |
| Lieferanten-Safe | `(66, 66, 690, 990)` | `(132, 132, 1380, 1980)` | 58,4 × 83,8 mm |
| internes DHK-Safe | `(78, 78, 666, 966)` | `(156, 156, 1332, 1932)` | 1 mm innerhalb des Lieferanten-Safe |

Die Rechtecke verwenden `(x, y, Breite, Höhe)` mit Ursprung links oben. Das
PNG ist opakes 8-Bit-RGB, enthält ein sRGB-ICC-Profil und 600-dpi-Metadaten.
Die Portalgrenze von 32 MB wird für jede Karte einzeln geprüft.

## Abgleich mit den Druckvorlagen

Die verbindliche Quelle ist `data/templates/poker-size.pdf`. Ihre Seite misst
197,28 × 269,279 pt beziehungsweise 69,6 × 95,0 mm; die Vorlage nennt selbst
822 × 1122 Pixel bei 300 dpi. Ihr SHA-256-Hash ist im Renderprofil festgehalten
und wird vor jedem Build geprüft.

Die Anbietervorlagen `American-poker-size.ai` und `American-poker-size.psd`
(nicht im Repository) gehören zu einem
abweichenden Raster mit 816 × 1110 Pixeln bei 300 dpi. Sie sind im Profil
ausdrücklich als nicht passend dokumentiert und dürfen für diesen
822×1122-Upload nicht verwendet werden.

Der Renderer zeichnet keinen schnittempfindlichen Außenrahmen, weil ein
umlaufender Rahmen in die Sicherheitsmarge fiele. Die Lieferanten-Safe-Zone
bleibt die technische Referenz der Druckerei. Das interne DHK-Safe liegt auf
allen vier Seiten weitere 1 mm innerhalb dieser Referenz. Titelplatte,
Bildplatte, Typplatte, Inhaltsplatte und Footer liegen einschließlich ihrer
Konturen und Schatten vollständig im DHK-Safe. Die Zone außerhalb der Schnittlinie ist eine
ruhige hellgraue Vollfläche (`#D7DADD`). Der Ring zwischen Schnittlinie und
Lieferanten-Safe ist tiefschwarz (`#090B0D`). Die anthrazitfarbene
Kartenfläche wird 0,25 mm innerhalb des Lieferanten-Safe angelegt; ihr
Mittelton bleibt `#20252A`. Die eigentliche Kartengestaltung wird exakt an der
Schnittlinie beschnitten.

Der Upload beim Druckdienst zeigte, dass dessen rote Sicherheitsmarke damit
genau auf der Kante dieser Anthrazitfläche zu liegen kam: Der schwarze Rand
hatte im Schnitttoleranzfall nichts mehr herzugeben. Die gesamte Kartenfläche —
das abgerundete Feld und alles, was darauf steht — wird deshalb als Ganzes um
den Mittelpunkt des Schnitts mit dem einheitlichen Faktor 0,9736842 verkleinert
(`CARD_FACE_SAFE_CLEARANCE`, 12 Mastereinheiten). Auf der schmalen Achse endet
das Feld danach exakt auf dem internen DHK-Safe, also 1,0 mm innerhalb der
Marke; auf der langen Achse sind es 1,35 mm. Der schwarze Rand misst am Schnitt
3,56 mm an den Längsseiten und 3,89 mm oben und unten. Weil ein einziger,
gleichmäßiger Faktor wirkt, bleiben sämtliche Proportionen und alle inneren
Randverhältnisse unverändert; der Eckenradius des Feldes beträgt danach rund
1,32 mm. Die Rückseite bleibt unberührt: Ihr Feld ist tiefschwarz wie der Ring,
und ihr sichtbarer Rahmen liegt ohnehin innerhalb des DHK-Safe.

## Installation und Schnelltest

Python 3.11 oder neuer und `uv` werden vorausgesetzt:

```bash
uv sync
make cards-test
make cards-goldens
```

`make cards-goldens` rendert vier bewusst verschiedene Prüfkarten:

- `KAT-C12`: Common-Projektfaktor/Daten
- `KAT-R12`: Rare-Projekt mit vier Anforderungen
- `KAT-U26`: positives Uncommon-Ereignis
- `KAT-M07`: positives Mythic-Foil-Ereignis

Die Ausgabe liegt unter `build/cards-preview/`. PNGs liegen direkt in diesem
Verzeichnis, SVG-Master unter `build/cards-preview/svg/`; `manifest.json`
enthält die Hashes von CSV, Profil, Layout, Schriften, Illustrationen, SVGs und
PNGs.

## Vollsatz und einzelne Karten

Alle 82 Motive:

```bash
make cards
```

Eine Auswahl:

```bash
uv run python scripts/render_cards.py \
  --card KAT-C12 \
  --card KAT-R12 \
  --output build/cards-preview
```

Nur PNGs, ohne die größeren eingebetteten SVG-Master:

```bash
uv run python scripts/render_cards.py \
  --all \
  --no-svg \
  --output build/cards-preview
```

## Preview, Proof und Print

Der Standardmodus ist `preview`. Der Modus und der CSV-Hash bleiben im
SVG-Metadatenblock und im Manifest nachvollziehbar, erscheinen aber nicht in
der sichtbaren Kartenfußzeile. Review-gesperrte Illustrationen werden nicht
eingebettet, sondern durch einen sichtbaren Platzhalter ersetzt. Offene
Inhaltsreviews erhalten ebenfalls ein Badge.

Ein Proof ergänzt farbige technische Guides und darf nicht als Druckdatei
verwendet werden:

```bash
make cards-proof
```

Dieser Proof ist ein technischer Layoutproof, kein farbverbindlicher
Druckproof. Farbentscheidungen benötigen einen physischen Andruck.

Der Printmodus ist ein absichtlich strenges Gate:

```bash
uv run python scripts/render_cards.py \
  --all \
  --mode print \
  --output build/cards-print
```

Er akzeptiert nur die kanonische `data/cards.csv`, führt deren vollständige
Produktionsvalidierung aus und bricht bei einem Layoutstatus anders als
`final`, offenen Content- oder Artwork-Reviews, fehlenden Illustrationen sowie
technischen PNG-Abweichungen ab. Die
Druckreife einer einzelnen Karte ergibt sich aus den `review_gates` in
`data/card_layout.json` und der vorhandenen Illustration. Das Layout steht auf
`final`; offene Bildreviews sperren den Druckmodus kartenweise. Ein
Preview-Erfolg ist keine Druckfreigabe.

## Typografie

Der Renderer verwendet ausschließlich die freien Familien Noto Serif und
Noto Sans. Erwartet werden diese fünf Schnitte:

- `NotoSerif-Regular.ttf`
- `NotoSerif-Bold.ttf`
- `NotoSerif-Italic.ttf`
- `NotoSans-Bold.ttf`
- `NotoSans-Regular.ttf`

Sie liegen unter `data/assets/fonts/`, zusammen mit ihrem Lizenztext
(`OFL.txt`, SIL Open Font License 1.1). Fehlen sie dort, verwendet der
Renderer die gleichnamigen Dateien aus `/usr/share/fonts/noto/`. Alle fünf Schnitte werden dem Rasterizer explizit als Fontdateien
übergeben und mit Name und SHA-256 im Build-Manifest festgehalten.

`NotoSans-Regular.ttf` bildet dabei den ruhigen funktionalen Schnitt für
Domänen- und Familiennamen, Ereignisschlüsselwörter, Zielangaben und die
Marken-/Copyright-Zeile. Strukturelle Angaben wie Kartentyp,
Abschnittslabels, Punkte sowie Karten-ID und Seltenheit bleiben in Noto Sans
Bold. Titel, Regeltext und Flavor Text verwenden
Noto Serif Bold, Regular beziehungsweise Italic.

### Feste Typografiestufen

Größe und Zeilenhöhe kommen ausschließlich aus `typography` in
`data/card_layout.json`. Die Werte sind SVG-Layout-Einheiten bei zehn Einheiten
pro Millimeter, keine typografischen Punktgrößen. Für sichtbare Kartentexte
gelten diese Stufen:

| Rolle | Größe/Zeilenhöhe | Schnitt |
|---|---:|---|
| Titel | 26/36 | Noto Serif Bold |
| Kartentyp | 22/28 | Noto Sans Bold |
| Domäne, Familie oder Ereignisschlüsselwort | 14/18 | Noto Sans Regular |
| Abschnittslabel | 14/18 | Noto Sans Bold |
| Projektfaktor-Regeltext | 27/38 | Noto Serif Regular |
| Ereignis-Regeltext | 25/35 | Noto Serif Regular |
| Projektanforderungstext | 23/32 | Noto Serif Regular |
| Projektziel | 20/28 | Noto Serif Regular |
| Flavor Text | 16/23 | Noto Serif Italic |
| Projektpunkte | 14/18 | Noto Sans Bold |
| Karten-ID und Seltenheit | 14/18 | Noto Sans Bold |
| Marke und Copyright | 12/15 | Noto Sans Regular |

Auch Platzhalter, Review-Badge und Proof-Beschriftung besitzen feste
Konfigurationsstufen. Der Fit-Algorithmus probiert eine Rolle nur in der dort
angegebenen absteigenden Reihenfolge. Er erzeugt keine 0,5-Einheiten-
Zwischenwerte mehr. Das SVG protokolliert die tatsächlich gewählte Größe,
Zeilenhöhe und den Status der Stufe in `data-type-size-step`,
`data-line-height` und `data-type-step-status`.

Das Tracking ist ebenfalls deterministisch und wird sowohl beim Messen als
auch beim Ausgeben berücksichtigt. Noto Serif erhält ab 36 Einheiten
minus 0,75 Prozent; die einheitlich 26 Einheiten großen Kartentitel laufen
ohne zusätzliches Tracking. Versalien in Noto Sans
erhalten größenabhängig plus 1,5 Prozent oberhalb von 20 Einheiten, plus vier
Prozent oberhalb von 14, plus sechs Prozent zwischen 12 und 14 und darunter
plus acht Prozent. Gemischte Schreibweisen und übriger Mengentext bleiben bei
null. Der Renderer rechnet diese Prozentsätze auf zwei Dezimalstellen in
absolute SVG-Einheiten um; dadurch verwenden Breitenprüfung und Ausgabe exakt
denselben Buchstabenabstand.

Absätze werden an expliziten Zeilenumbrüchen getrennt und zunächst
deterministisch wortweise gesetzt. Ist die letzte Zeile kürzer als 35 Prozent
der Satzbreite oder besteht sie nur aus einem Wort, optimiert der Renderer den
gesamten Absatz bei unveränderter Zeilenzahl. Bewertet werden der optische
Zeilenfall, Satz- und Teilsatzgrenzen sowie kleine deutsche Wortgruppen wie
Präposition und Nominalgruppe oder Determinator und Nomen. Sprachlich
ungünstige Trennstellen und sehr kurze Zeilen sind weiche Strafwerte: Ist eine
solche Trennung wegen der verfügbaren Breite unvermeidbar, bleibt der Text
weiterhin renderbar. Schriftstufe und Höhe des Inhaltsblocks ändern sich durch
diese Nachoptimierung nicht.

Alle 82 kanonischen Flavor-Texte passen in der festen Stufe 16/23 einzeilig in
ihre 518 Einheiten breite Satzfläche. Für spätere, längere Flavor-Entwürfe bleibt
zusätzlich ein strenger Zweizeilenpfad bestehen: Er verwirft Trennungen in
kleinen deutschen Wortgruppen vollständig, bevorzugt Satz- und
Teilsatzgrenzen und bewertet erst danach den optischen Zeilenfall. Eine neue
zweizeilige Fassung würde jedoch den Testvertrag brechen und benötigt deshalb
eine bewusste Layoutentscheidung.
Eine Wörterbuch- oder automatische Silbentrennung findet bewusst nicht statt.
Lange deutsche Komposita werden daher nicht eigenmächtig verändert.

### Druckuntergrenzen

Bei zehn Layout-Einheiten pro Millimeter und einer Noto-Versalhöhe von rund
71,4 Prozent ergeben 14 Einheiten ungefähr 1,0 mm Versalhöhe. Funktionale
Spielangaben in Noto Sans Regular liegen deshalb nicht unter 14 Einheiten.
Auch die kompakte Punkteangabe sowie Karten-ID und Seltenheit stehen nun bei
14 Einheiten. Die rechtliche
Marken-/Copyrightzeile ist bewusst als nachrangiges Footer-Mobiliar in 12/15
Noto Sans Regular gesetzt und benötigt deshalb einen physischen Andruck.
Review- und Proof-Texte bei 12 Einheiten sind technische Markierungen und keine
druckbare Karteninformation. Diese rechnerischen Untergrenzen ersetzen keinen
physischen Andruck der kleinen Schriftgrade.

Die Projektabschnitte besitzen getrennte, feste Rollen ohne Ausweichstufe:
`project_requirements` setzt die ausgeschriebenen Anforderungen in 23/32,
`project_goal` das nachgeordnete Projektziel in 20/28. Alle 16 Anforderungen
sind zweizeilig; die Ziele verteilen sich auf fünf Zwei-, vier Drei- und sieben
Vierzeiler. Die Fit-Höhen von 72 beziehungsweise 120 Einheiten lassen selbst
bei der jeweils maximalen Zeilenzahl acht Einheiten Reserve. Damit enthält der
kanonische Satz keine `prototype-emergency`-Stufe und das SVG- sowie
Manifestfeld `typography_exceptions` bleibt für alle 82 Karten leer. Passt eine
spätere Fassung nicht in ihre feste Rolle, bricht der Renderer ab; eine
verdeckte Notstufe wird nicht erzeugt.

Die Symbolbasis ist stattdessen `@phosphor-icons/core` 2.1.1 in Bold. Alle 22
benötigten Grundglyphen liegen lokal unter
`data/assets/icons/phosphor/2.1.1/bold/`; das Iconmanifest ordnet ihnen 22
Produktbegriffe zu. Projektfaktor, Boosterbanderole und Wildcard-Wahl besitzen
feste Komposit-SVGs unter `data/assets/icons/composites/`. Der Renderer prüft
ViewBox, Element- und Attribut-Whitelist sowie lokale Pfade und übernimmt die
Geometrie direkt in den Kartenmaster. SVG und PNG benötigen deshalb weder
Netzwerk noch externe Icondateien. Manifest- und Asset-Hashes stehen in den
SVG- und Build-Metadaten. Entscheidung und vollständige Zuordnung dokumentiert
ADR 0014.

## Informationshierarchie

### Strichstärkenskala

Die produktive Vorderseite verwendet genau drei Strichstärken mit jeweils
einem klaren Funktionssprung:

| Stärke | Funktion | Elemente |
|---:|---|---|
| 1,0 | trennt | neutrale Keylines aller fünf Platten, Konturen leerer Seltenheits-Pips |
| 1,5 | gliedert | Akzentregeln, Flavor- und Sektionstrenner sowie Anforderungs- und Punktekreise |
| 2,25 | betont | äußerer Trägerkreis des Identitätsstempels |

Damit ist der Identitätsstempel oben links das einzige Element in der
schwersten Stufe. Phosphor-Bold-Glyphen sind gefüllte Pfadgeometrie und führen
keine zusätzliche Strichstärke ein. Die
Platzhalter-Schraffur verwendet 3,0 Einheiten, gehört aber nur zur
internen Vorschau und nicht zur produktiven Kartenoberfläche. Auch Review- und
Proof-Markierungen führen keinen weiteren Wert ein, sondern verwenden 1,5.

Für die drei akzentfarbenen Strukturrollen Plattenakzent, Sektionstrenner und
Flavor-Trenner gilt dieselbe Stärke von 1,5 Einheiten und die gemeinsame
Horizontalspanne x 78 bis x 612. Plattenakzente und Sektionstrenner stehen bei
100 Prozent. Nur der Flavor-Trenner wird als bewusst leisere Strukturstufe mit
45 Prozent Deckkraft gesetzt. Die umlaufende Kontur des Bildblocks gehört
dagegen zur neutralen 1,0er-Plattenstufe und endet gemalt wie die übrigen
Platten bei x 70 und x 620. Hinzu kommt der ausdrücklich als Wasserzeichen
behandelte Faktor-Emblemkreis bei 28 Prozent; er ist keine weitere
Hierarchiestufe.

Die Titelleiste enthält links vom Kartennamen genau ein kreisförmig gefasstes
Kartentypzeichen: `FolderOpen` für Projekt, das feste Komposit aus
`FolderOpen` und `SlidersHorizontal` für Projektfaktor sowie `Lightning` für
Ereignis. Alle drei Kartentypen verwenden im Trägerkreis einheitlich den
warmen neutralen Papierton `background/paper` (`#E8E0CA`). Kontur und Glyphe
verwenden gemeinsam das neutrale `line/default`; Domänen-, Familien- und
Ereignisfarben werden an dieser Stelle nicht wiederholt. Die linke
Geometriekante des Trägerkreises liegt auf der gemeinsamen Innenflucht x 78;
der Titel beginnt bei x 126. Der
Ereignis-Identitätsstempel enthält ausschließlich `Lightning`; es gibt darin
weder ein Polaritätssymbol noch einen zusätzlichen Träger.
Alle Kartentitel verwenden die feste Stufe 26/36, damit die Titelhierarchie
über das gesamte Set konstant bleibt. Der aktuelle Titel mit der geringsten
horizontalen Reserve ist `KAT-R14`, „Automatisierter Editionsworkflow“; im 490
Einheiten breiten Titelfeld verbleiben 36,5 Einheiten. Die Baseline
wird aus den tatsächlichen Auf- und Unterlängen von Noto Serif Bold metrisch
zentriert, statt nur aus Schriftgröße und Zeilenbox geschätzt. Dadurch bleiben
die sichtbaren Glyphen aller 82 Titel mindestens rund 5,6 Einheiten von den
Kanten ihres Textfelds entfernt.

In der Typzeile steht der Kartentyp groß in der jeweiligen Akzentfarbe; der
kleinere Domänen-, Familien- oder Ereignistext verwendet dagegen einheitlich
das neutrale `text/primary`. Die Akzentfarbe bleibt an Symbolen und
Strukturelementen erhalten. Dadurch hängt insbesondere der klein gesetzte
Familienname `METHODE` nicht vom Kontrast des
Methoden-Goldtons ab. Projekte zeigen vor ihrem Familienlabel ein 20 Einheiten
großes, ungerahmtes Familiensymbol. Am rechten Rand folgen zwei bis vier
kreisförmig gefasste Anforderungen in Quelldatenreihenfolge: Jeder
sichtbare Träger ist eine 27 × 27 Einheiten große Ellipse mit Radius 13,5 und
1,5 Einheiten Kontur; darin steht ein 18 Einheiten großes Symbol. Der Träger
ist in einem unveränderten 28er-Slot um 0,5 Einheiten zentriert. Die Reihe
steht gegenüber der Typzeilenmitte um eine Einheit nach unten versetzt, ihr
Mittelpunkt liegt bei y 520,3644. Aufeinanderfolgende Slots haben bei 6
Einheiten nominalem Gap einen Mittelpunktabstand von 34 Einheiten; zwischen
den sichtbaren 27er-Kreisflächen bleiben dadurch 7 Einheiten. Wiederholungen
bleiben als einzelne Träger mit `data-count="1"` und fortlaufendem `data-slot`
erhalten. Nach 10 Einheiten Abstand zum letzten Anforderungsslot folgt der
Punkteslot; zwischen den sichtbaren Kreisflächen bleiben 11 Einheiten. Auch
sein Träger misst sichtbar 27 Einheiten und trägt die kompakte Punkteangabe
`NP` ohne Leerzeichen, beispielsweise `4P`, in 14/18. Seine Papierfüllung
bleibt bestehen; Kontur und Text verwenden bewusst das neutrale Schwarz
`line/default` (`#17212B`) statt der Domänenfarbe. Die Anforderungskreise
behalten dagegen ihre jeweilige Familienfarbe.
Anforderungstexte, Pills und rechteckige Module werden in der Typzeile nicht
ausgegeben.

Faktoren zeigen die Familie ebenfalls als Symbol; dadurch ist auch der Joker
mit `Asterisk` redundant über Icon, Farbe und Text markiert. Im Regelfeld
erhält jeder Projektfaktor genau ein großes Familienemblem: Die Gruppe
`factor-family-emblem` enthält einen ungefüllten 96 × 96 Einheiten großen
Kreis mit 1,5 Einheiten Kontur und 28 Prozent Deckkraft. Darin steht eine
zentrierte 63er-Glyphe mit 22 Prozent Deckkraft. Die schwache Deckkraft beider
Elemente erzeugt absichtlich eine Wasserzeichenwirkung, vor der der Regeltext
dominant bleibt. Auf die gemalte Unterkante des Kreises folgen exakt acht
Einheiten Abstand und anschließend die tatsächliche Regeltext-Zeilenbox. Der
Text steht horizontal zentriert in der 480 Einheiten breiten Satzfläche bei
x 105. Emblem, Abstand und Text bilden einen gemeinsamen Stack; seine
Vertikalposition hängt deshalb kontrolliert von der Zeilenzahl ab. 36
Projektfaktoren passen einzeilig; nur `KAT-U03` und `KAT-U25` benötigen zwei
Zeilen. Alle 38 verwenden ausschließlich die Standardstufe 27/38. Der
Zeilenboxabstand zum gemalten Emblem beträgt immer acht Einheiten, der kleinste
Abstand zur tatsächlichen ersten Tintenkante 14,25 Einheiten.

### Gemeinsamer senkrechter Inhaltsstack

Projekt, Projektfaktor und Ereignis verwenden dieselbe senkrechte Regel. Der
gemeinsame Frame beginnt bei `(x 78, y 552,1144)`, ist 534 Einheiten breit und
endet an der gemalten Oberkante des Flavor-Trenners. Bei den 82 aktuellen
einzeiligen Flavor-Texten liegt diese Unterkante bei y 802,3856; der Frame ist
damit 250,2712 Einheiten hoch. Der freie Raum um den semantischen Stack wird
immer im Verhältnis 45 Prozent oberhalb zu 55 Prozent unterhalb verteilt.
Gemessen werden deklarierte Zeilenboxen sowie beim Faktor die gemalte
Emblemfläche, nicht wechselnde Buchstabenkonturen.

Die drei Stacks unterscheiden sich nur semantisch:

- Ereignis: vollständige Regeltext-Zeilenbox;
- Projektfaktor: gemalter 96er-Träger, acht Einheiten Abstand und vollständige
  Regeltext-Zeilenbox;
- Projekt: `ANFORDERUNGEN` mit Trenner und ausgeschriebenem Anforderungstext,
  vier Einheiten Abschnittsabstand sowie `PROJEKTZIEL` mit Trenner und
  Zieltext.

Anforderungs- und Zieltext werden zunächst innerhalb ihrer Fitgrenzen von 72
beziehungsweise 120 Einheiten gesetzt; danach wird der tatsächlich benötigte
Gesamtstack positioniert. Der größte aktuelle Projektstack ist 227,5 Einheiten
hoch und lässt im gemeinsamen Frame 10,2470 Einheiten oberhalb sowie 12,5242
Einheiten unterhalb frei. Der Renderer klemmt keine negative Resthöhe auf null,
verschiebt keinen überlaufenden Stack und verkleinert Ereignis- oder
Faktorregeltext nicht. Bei Überlauf entsteht ein `RenderError`. Karten ohne
Flavor Text reservieren als ausdrücklich definierte Variante den Beginn der
Flavor-Zone als Frame-Unterkante und zeichnen keinen Flavor-Trenner. Diese
bewusste Entscheidung wird in der kanonischen CSV durch eine vorhandene, exakt
leere `flavor_text`-Zelle ausgedrückt; eine fehlende Spalte, eine verkürzte
Zeile oder reiner Leerraum gelten als Datenfehler. Auch ein exakt bis an beide
Framekanten gefüllter Stack wird abgelehnt, weil dann kein 45/55-Freiraum mehr
definiert ist.

Alle Ereignisse verwenden unabhängig von ihrer Polarität den gemeinsamen
Akzenttoken `event/base` (`#60457A`). Direkt fünf Einheiten nach `EREIGNIS`
folgt genau ein 18 Einheiten großes, violettes Effektsymbol vor dem in den
Spielregeln definierten E1–E8-Schlüsselwort. Eine Polaritätsmarke, ein dafür
reservierter Slot oder ein anderer Polaritätsträger werden nicht ausgegeben.
Schlüsselwort und gegebenenfalls Zielangabe bleiben neutral. Die Zuordnung ist
kanonisch:

| Vorlage | Iconrolle | Phosphor-Basis | Schlüsselwort |
|---|---|---|---|
| E1 | `inspect` | `Eye` | `SICHTEN` |
| E2 | `draw` | `CardsThree` | `NACHZIEHEN` |
| E3 | `retrieve` | `ArrowCounterClockwise` | `RÜCKHOLEN` |
| E4 | `redistribute` | `ArrowsLeftRight` | `UMVERTEILEN` |
| E5 | `joker` | `Asterisk` | `JOKER` |
| E6 | `extra_effort` | `HourglassMedium` | `MEHRAUFWAND` |
| E7 | `negative` | `TrendDown` | `RÜCKSCHLAG` |
| E8 | `safeguard` | `ShieldCheck` | `ABSICHERUNG` |

Damit besitzen alle 28 Ereignisse genau ein Effektsymbol; Zielangaben folgen
dem Schlüsselwort. Da Ereignisse keine rechten Bedienelemente besitzen, reicht
das einzeilige Sekundärtextfeld bewusst über die allgemeine Typzone bei x 478
hinaus bis zwölf Einheiten vor die rechte Kante der `type_surface`, also bis
x 608. Alle 28 Texte bleiben einzeilig. Der engste Fall `KAT-U17` mit
`RÜCKSCHLAG · ZIEL: DATEN + METHODE` behält rund 106,997 Einheiten bis zu
dieser Textgrenze. Projekte beginnen
mit `ANFORDERUNGEN` und setzen danach `PROJEKTZIEL`. Der Anforderungssatz bleibt
vollständig ausgeschrieben; lediglich das bereits durch das Label ausgedrückte
Quelldatenpräfix `Abschluss:` wird nicht mitgerendert. Die Trennlinien liegen
neun Einheiten unter dem Beginn der jeweiligen Inhaltszone; der Mengentext
beginnt elf Einheiten nach Zonenbeginn. Das Label selbst ist um
12,75 Einheiten nach oben versetzt. Projektfaktoren und Ereignisse beginnen
dagegen direkt mit dem Regeltext; das redundante Label `WIRKUNG` entfällt.
Polaritäten bleiben in den Kartendaten sowie als nicht sichtbares
`data-polarity` am SVG-Wurzelelement erhalten, steuern aber weder Farbe noch
ein sichtbares Wort, Zeichen, Banner oder Icon. Für Spielende sind negative
Ereignisse stattdessen eindeutig an den Schlüsselwörtern `MEHRAUFWAND` und
`RÜCKSCHLAG` erkennbar. Der Identitätsstempel in der Titelleiste enthält
ausschließlich `Lightning`. ADR 0015 dokumentiert den gemeinsamen
Ereignisakzent und den neutralen Sekundärtext; ADR 0018 löst dessen sichtbare
Polaritätscodierung sowie die freistehende Marke aus ADR 0016 ab.

Der eigentliche Ereignis-Regeltext verwendet setweit ausschließlich 25/35 und
den gemeinsamen senkrechten Inhaltsstack. Unter den 28 Karten entstehen drei
Zwei-, sieben Drei-, sechs Vier-, sechs Fünf- und sechs Sechszeiler. Selbst die
sechs dichtesten Karten behalten tatsächlichen Glyphenabstand zum Frame: oben
mindestens 23,622 und unten mindestens 26,1492 Einheiten. Ein Größenwechsel
innerhalb der Ereignisse findet nicht statt.

Label, Sektionstrenner und Text beider Abschnitte gehören zum gemeinsamen
Projektstack. Die Anforderungskreise stehen
rechtsbündig in der Typzeile; zwei
benötigte Betriebsfaktoren erscheinen daher als zwei getrennte `GearSix`-
Glyphen. Projektkarten leiten ihren Akzent aus ihrer primären Domäne ab. Die
vier Familienfarben bleiben für Symbole und Strukturrollen erhalten; alle
kleinen Familiennamen werden dagegen neutral gesetzt. Der Methoden-Goldton
wird deshalb nicht eigens abgedunkelt. Ereignisse leiten ihren Akzent stets
aus `event/base` statt aus ihrer Polarität ab. Über alle 16 Projekte beträgt
das tatsächliche Minimum zwischen der Unterkante der letzten sichtbaren
Anforderungs-Glyphe und der Oberkante von `PROJEKTZIEL` 16,5 Einheiten.
Zwischen dem letzten Projektzieltext und dem Flavor-Trenner bleiben mindestens
15,7742 Einheiten. Die sichtbaren Label-zu-Trenner-Abstände betragen 4,25
Einheiten für `PROJEKTZIEL` und 6,75 Einheiten für `ANFORDERUNGEN`; die
exhaustiven Tests sichern mindestens 4,0 Einheiten ab.
Faktoren verwenden ein offenes Regelfeld mit einem gemeinsam positionierten
Emblem-und-Text-Stack statt verschachtelter Kartenfelder. Der
kursiv gesetzte Flavor Text bleibt durch Linie und Schriftwechsel erkennbar;
er verwendet die feste Stufe 16/23 in Layout-Einheiten. Sein einzeiliger Block
liegt in allen drei Kartenlayouts in derselben Zone am Fuß der Inhaltsplatte:
Baseline 827,1356, Divider 803,1356. Zur Zonenunterkante bleiben zwei
Einheiten, die tatsächlichen Glyphen behalten dabei mindestens 5,2 Einheiten
Abstand. Das redundante Label `RANDNOTIZ` entfällt.

Titel-, Bild-, Typ-, Inhalts- und Footerplatte verwenden weder Drop Shadows
noch einen gerichteten Letterpress- oder Bevel-Effekt. Statt unterschiedlich
heller Kanten besitzen alle fünf Platten dieselbe geschlossene neutrale
Haarlinie aus `line/default`: 1,0 Einheiten breit, ohne Opazität und um 0,5
Einheiten nach innen gesetzt. Ihre gemalten Außenkanten liegen bei x 70 und
x 620. Die farbigen Linien von Typ- und Inhaltsplatte beginnen acht Einheiten
innerhalb der Platte und liegen 2,5 Einheiten unterhalb ihrer Oberkante. Sie
folgen wie Projekttrenner und Flavor-Trenner der gemeinsamen Innenflucht x 78
bis x 612. Dieselbe Innenflucht gilt für Identitätsstempel, Typzeile,
Projektlabels, Regeltext, Flavor und Fußzeile. Identitätsstempel und
Titelleiste bleiben bewusst farbneutral; die semantische Farbe beginnt erst
in der Typzeile. Der einheitliche, etwas dunklere Papierton hebt lediglich die
Stempelfläche vom Titelpapier ab. Auch der Footer bleibt farblich neutral.
Titelplatte, Bildpassepartout, Typusplatte und Inhaltsplatte verwenden
einheitlich das helle Papier `background/paper-raised` (`#F5EEDB`). Ihre
Hierarchie entsteht durch Fugen, Keylines, Akzentregeln und Typografie statt
durch unterschiedliche Papiertöne. Falls das Passepartout im Kontext heller
wirkt, ist das optischer Kontrast zur Illustration und keine Design- oder
Farbänderung: Es besitzt exakt denselben Token und Farbwert wie die drei
anderen hellen Hauptplatten und keine eigene Textur.

Vertikal folgt der Plattenstapel einem einheitlichen Rhythmus: Zwischen
Titelleiste, Bildblock, Typzeile, Inhaltsplatte und Footer liegen vier dunkle
Fugen von jeweils 4 Einheiten. Weil der 690 × 940 Einheiten große Layoutraum
horizontal und vertikal mit geringfügig verschiedenen Faktoren in den
822 × 1122-Master skaliert wird, werden die Außenränder erst nach dieser
Transformation verglichen. Der Stapel reicht im Layoutraum von y 69,8644 bis
y 870,1356. Damit misst der dunkle Abstand zum abgerundeten Kartenfeld im
Master links, rechts, oben und unten jeweils rund 14,3913 Einheiten
beziehungsweise 1,22 mm; nach der gleichmäßigen Verkleinerung der Kartenfläche
sind davon gedruckt rund 1,19 mm übrig. Für diese gemeinsame Rand- und Fugengeometrie ist die
Inhaltsplatte 293,2712 Einheiten hoch. Innerhalb der Inhaltsplatte reicht der
gemeinsame Frame von y 552,1144 bis zur gemalten Oberkante des
Flavor-Trenners. Ereignistext,
Faktoremblem samt Regeltext und der vollständige Projekt-Doppelabschnitt
folgen dort derselben 45/55-Freiraumverteilung.

Im Plattenstapel besitzen nur die beiden oberen Ecken der Titelleiste und die
beiden unteren Ecken des auf 3 mm reduzierten Footers einen Radius von rund
0,4 mm. Für beide Platten hat die gemeinsame Außenflucht mit Bildblock,
Typzeile und Inhaltsplatte Vorrang. Typ- und Inhaltsplatte bleiben eckig.
Weitere Rundungen sind auf echte Statusbadges, die Anforderungs- und
Punktekreise, den äußeren
Kartenkörper und die innere Bildkante beschränkt. Das anthrazitfarbene
Innenfeld verläuft
subtil von `#252A2F` oben über den Mittelton `#20252A` nach
`#1B2024` unten. Der Footer verwendet denselben unteren Anthrazitton, statt sich
mit dem helleren Mittelton als erhabene Platte vom Umfeld abzusetzen. Der
Bildblock besitzt keine eigene dunkle Rahmenfläche.

Der Renderer simuliert kein Papierkorn: SVG und PNG enthalten keine digitale
Papierstruktur, `feTurbulence` und andere SVG-Filter sind ausgeschlossen.

Die Illustration erhält zwei filterfreie Materialbehandlungen: Ein fünf
Einheiten tiefer warmbrauner Verlauf liegt an allen vier Bildrändern mit 4
Prozent Stärke im Mischmodus `multiply`. Zusätzlich fällt von der oberen
Bildkante ein sieben Einheiten tiefer schwarzer Verlauf mit maximal 3 Prozent
Deckkraft ein. Beide bleiben innerhalb der Bildmaske und verändern die
Illustrationsdatei nicht.

B4 beziehungsweise `light-mat` ist die einzige Bildbehandlung des
Renderers. Das Papierpassepartout reicht von x 70 bis x 620; das
534 × 356 Einheiten große und damit 3:2 proportionierte Bildfenster beginnt
rundum acht Einheiten weiter innen. Die neutrale Platten-Keyline aus
`line/default` liegt mit 1,0 Einheiten Stärke an der äußeren
Passepartout-Kante. Sie ist um 0,5 Einheiten nach innen gesetzt; ihre gemalten
Grenzen reichen von x 70 bis x 620 und fluchten mit den übrigen
Platten. Die Keyline bleibt rechtwinklig; nur die innere Bildmaske besitzt 4
Einheiten Radius. Die Grundfarbe ist exakt `background/paper-raised`
(`#F5EEDB`) und entspricht damit Titel-, Typus- und Inhaltsplatte; eine
digitale Körnungsauflage, zusätzliche farbige Kontur, ein schwarzes
Passepartout, ein Mikrospalt oder eine Guilloche entstehen nicht.
Auch die Platzhalter-Schraffur bleibt durch dieselbe Bildmaske innerhalb der
Bildkante.

`light-mat` wird in SVG- und Manifest-Metadaten festgehalten.

Finale Quelldateien und alle sichtbaren Bildfenster besitzen ein horizontales
Seitenverhältnis von 3:2. Das B4-Bildfenster verwendet `xMidYMid slice`; finale
3:2-Quellen werden dadurch ohne systematischen Beschnitt dargestellt.
Der Preview-Modus akzeptiert auch 4:3-Bilder; bei ihnen entfallen durch den mittigen Crop oben
und unten jeweils ein Achtzehntel beziehungsweise rund 5,56 Prozent der Höhe.
Der Print-Modus verlangt ausnahmslos 3:2.

Die Fußzeile enthält ausschließlich Karten-ID, die klassischen Stufen
`COMMON`, `UNCOMMON`, `RARE` oder `MYTHIC` samt einer festen Skala aus vier
Seltenheits-Pips und rechts `OTTERS OF THE COAST™ © 2026`. Common füllt einen,
Uncommon zwei, Rare drei und Mythic alle vier Pips; die jeweils übrigen
Positionen erscheinen als leere Kontur. So bleibt jede Stufe innerhalb
desselben Rasters vergleichbar. Der 29 Einheiten breite Viererblock ist
unabhängig von der Textbreite auf der horizontalen Kartenachse bei x 345
zentriert; seine sichtbaren Außenkanten reichen von x 330,5 bis x 359,5.
Karten-ID, Mittelpunkt und Seltenheitswort sind getrennte Textsegmente. Bei der
festen 14er-Stufe erhält die ID 0,84 Einheiten Laufweite, das Seltenheitswort
mit 1,40 Einheiten bewusst mehr Sperrung. Reproduktions- und
Reviewinformationen bleiben in den technischen Metadaten. Gefüllte und leere
Seltenheitsmarken verwenden den gleichen neutralen Footer-Ton; der Foil-Status
verändert ihre Farbe nicht. Die Marken-/Copyrightzeile ist kleiner als die
Kartenidentität und verwendet den gedämpften Ton `#A3A098`, damit sie gegenüber
Karten-ID und Seltenheit visuell zurücktritt.
Die verkleinerten Projektkreise und das Faktor-Wasserzeichen verändern diese
Seltenheitspips weder geometrisch noch farblich.

## Browser-Portierung für den Kartendesigner

`website/renderer.js` ist eine JavaScript-Portierung von `build_card_svg` und
allem, was es zeichnet; sie treibt den Kartendesigner der Website. Layout,
Profil, Konstanten, Wortlisten, Icongeometrie und Schriftmetriken exportiert
`website/prepare.py` aus diesem Renderer (`make website`), die Zeichenlogik
ist von Hand übertragen. Wer hier Zeichenlogik ändert, zieht sie in
`website/renderer.js` nach und prüft mit `make website-parity`: Der Test
rendert alle Karten mit beiden Renderern und verlangt identische Struktur,
Textzeilen und Geometrie; Positionen aus der Textmessung dürfen um höchstens
0,05 Einheiten abweichen. Die Browser-Fassung erzeugt keine Druckdateien und
hat keine Review- oder Print-Gates.

## Reproduzierbarkeit und Preflight

Der Build verwendet `resvg-py==0.5.0` und `Pillow==12.3.0`. Das eingebettete
sRGB-Profil besitzt einen normalisierten ICC-Header, damit zwei getrennte
Läufe byteidentische PNGs erzeugen. Der technische Preflight prüft pro Datei:

- exakt 1644 × 2244 Pixel
- PNG, 8-Bit-RGB und keinen Alphakanal
- gültiges eingebettetes sRGB-ICC-Profil
- 600 dpi auf beiden Achsen
- weniger als 32.000.000 Bytes
- lokale, eindeutige 3:2-PNG-Illustration im Print-Modus; 4:3 nur als
  Bestandsvorschau
- selbstenthaltenes SVG ohne externe Ressourcen
- lokales, vollständiges Iconmanifest sowie erlaubte 256er-SVGs mit
  reproduzierbaren SHA-256-Hashes
- unveränderte verbindliche PDF-Druckvorlage
- 1 mm zusätzlicher DHK-Sicherheitsabstand innerhalb des Lieferanten-Safe
- keine sichtbare Panelkante oder Schattenkante außerhalb des DHK-Safe
- gemeinsame x-Außenkanten für Titel, Bildblock, Typzeile, Inhalt und Footer
- gemeinsame x-Innenkanten für Typzeile, Inhaltslinien, Regel- und Flavortext
  sowie Footer
- vier vertikale Fugen von exakt 4 Einheiten sowie im 822×1122-Master gleiche
  dunkle Außenränder zwischen Plattenstapel und abgerundetem Kartenfeld
- eine neutrale 1,0-Einheiten-Haarlinie aus `line/default`, um 0,5 Einheiten
  nach innen gesetzt, an der äußeren Kante des 8-Einheiten-Papierpassepartouts
  sowie Radius 4 an dessen innerer Bildkante; keine zusätzliche farbige
  Rahmenlinie an der Illustration
- subtiler Anthrazitverlauf mit hellerem Kopf und dunklerem Fuß
- identische neutrale 1,0-Haarlinien an allen fünf Hauptplatten, jeweils gemalt
  von x 70 bis x 620
- alle familien- beziehungsweise ereignisfarbenen Strukturlinien 1,5
  Einheiten breit; innere Regeln von x 78 bis x 612 und ohne reduzierte
  Deckkraft, nur der Flavor-Trenner bei 45 Prozent
- sichtbare Strichstärken ausschließlich 1,0, 1,5 und 2,25; die
  3,0-Platzhalter-Schraffur nur in der internen Vorschau
- keine simulierte Papierstruktur vor dem physischen A/B-Andruck
- Passepartout, Titel-, Typus- und Inhaltsplatte exakt mit demselben
  `background/paper-raised` (`#F5EEDB`)
- warmbrauner 4-Prozent-Multiply-Rand innerhalb jeder Illustrationsmaske
- filterfreier 3-Prozent-Innenschatten an der oberen Illustrationskante
- keine linke Archivschiene oder anderer durchgehender Seitenbalken
- hellgraue Außenfläche außerhalb der Schnittlinie und tiefschwarzer Ring bis
  1,0 mm innerhalb des Lieferanten-Safe, damit die rote Sicherheitsmarke des
  Druckdienstes vollständig im schwarzen Rand liegt
- getrennt positionierte Proof-Beschriftungen ohne Überlappung
- Identitätsstempel auf der gemeinsamen Innenflucht x 78, Titelbeginn bei
  x 126 und Kartentitel einheitlich in 26/36 mit metrisch zentrierter Baseline
- Projekt-Typzeilen mit ungerahmtem 20er-Familiensymbol, zwei bis vier um eine
  Einheit abgesenkten, rechtsbündigen 27er-Anforderungskreisen in 28er-Slots
  mit 18er-Glyphen, 34 Einheiten Mittelpunktabstand und 6 Einheiten nominalem
  Slot-Gap sowie einem neutral-schwarzen 27er-Punktekreis nach 10 Einheiten
  Slot-Abstand
- ein gemeinsamer Inhaltsframe ab y 552,1144 bis zur gemalten Oberkante des
  Flavor-Trenners; der typabhängige Gesamtstack verteilt seinen freien Raum bei
  allen 82 Karten strikt zu 45 Prozent oben und 55 Prozent unten
- ausgeschriebene `ANFORDERUNGEN` zuerst und fest in 23/32, danach
  `PROJEKTZIEL` fest in 20/28; jeweils mindestens acht Einheiten Fit-Reserve
- über alle 16 Projekte mindestens 16,5 Einheiten tatsächlicher Glyphenabstand
  zwischen Anforderungen und `PROJEKTZIEL`, 15,7742 Einheiten vom Zieltext zum
  Flavor-Trenner sowie 6,75 beziehungsweise 4,25 Einheiten von den beiden
  Abschnittslabels zu ihren Trennlinien
- Projektfaktor-Stacks mit einem ungefüllten 96er-Wasserzeichenkreis bei 28
  Prozent, einer 63er-Glyphe bei 22 Prozent und Regeltext in 27/38; exakt acht
  Einheiten zwischen gemaltem Emblem und Zeilenbox sowie mindestens 14,25
  Einheiten bis zur tatsächlichen Tintenkante
- ausschließlich `Lightning` im Ereignis-Identitätsstempel, ohne dortiges
  Polaritätssymbol oder zusätzlichen Träger
- gemeinsamer Ereignisakzent `event/base` (`#60457A`) unabhängig von der
  Polarität sowie neutraler Sekundärtext bei allen Kartenarten
- keine sichtbare Polaritätsmarke oder dafür reservierter Slot; direkt fünf
  Einheiten nach `EREIGNIS` genau ein violettes 18er-Effektsymbol gemäß der
  kanonischen E1–E8-Zuordnung
- alle 28 Ereignis-Sekundärtexte einzeilig bis zur rechten Textgrenze x 608,
  ohne rechte Event-Controls; `KAT-U17` mit rund 106,997 Einheiten Rest
- alle 28 Ereignis-Regeltexte einheitlich in 25/35 mit zwei bis sechs Zeilen,
  ohne kleinere Ersatzstufe oder geometrischen Fallback
- kein sichtbarer CSV-Hash oder Preview-Modus in der Kartenfußzeile
- Rarität ausschließlich in der Kartenfußzeile

Die Tests liegen in `tests/test_render_cards.py`. Zusätzlich bleibt vor jedem
Commit `python3 scripts/validate_cards.py` verpflichtend.
