# ADR 0014: Phosphor Icons als renderer-native Symbolbasis

- Status: angenommen
- Datum: 2026-08-29
- Berührt: Iconassets, Kartenlayout, Vorderseitenrenderer, Lizenzdokumentation
- Teilweise abgelöst durch: ADR 0015 hinsichtlich Ereignisakzent und neutralem
  Sekundärtext sowie ADR 0018 hinsichtlich des vollständigen Verzichts auf
  eine sichtbare Polaritätsmarke
- Geometrie-Fortschreibung: Layout `1.21.0` / Renderer `0.25.0` ersetzt die
  unten historisch dokumentierte feste Faktorposition durch den gemeinsamen
  45/55-Inhaltsstack; Iconquelle und semantische Zuordnung bleiben gültig

## Kontext

Das Symbolsystem für Faktortypen war noch offen. Der Vorderseitenrenderer
zeichnete Familien-, Kartenart- und Polaritätszeichen als kleine eigene
Grundformen. Für Karten, Marker und spätere Produktbestandteile wird dagegen
eine gemeinsame, reproduzierbare Bildsprache benötigt. Sie muss ohne
Netzwerkzugriff funktionieren, in den selbstenthaltenen SVG-Mastern aufgehen
und ihre Herkunft sowie Lizenz maschinenlesbar dokumentieren.

## Entscheidung

### Quelle und Einbettung

`@phosphor-icons/core` wird in Version 2.1.1 und ausschließlich im Gewicht
`bold` verwendet. Die 22 benötigten Grundglyphen liegen lokal unter
`data/assets/icons/phosphor/2.1.1/bold/`. `data/assets/icons/manifest.json`
ordnet ihnen 22 projektspezifische Bedeutungen zu. Der Renderer akzeptiert nur
lokale SVGs mit `viewBox="0 0 256 256"`, `currentColor` und einer kleinen
Allowlist aus Pfaden und Gruppen. Er übernimmt die Pfade inline; die erzeugten
Karten-SVGs besitzen keine externe Iconabhängigkeit.

SVG- und Build-Metadaten halten den Hash des Iconmanifests sowie Pfad und
SHA-256 der verwendeten beziehungsweise registrierten Dateien fest. Die
Phosphor-MIT-Lizenz bleibt unter
`data/assets/icons/phosphor/LICENSE.phosphor.txt` erhalten.

### Semantische Zuordnung

| Rolle | Phosphor-Basis |
|---|---|
| Team | `UsersThree` |
| Daten | `Database` |
| Betrieb | `GearSix` |
| Methode | `ListChecks` |
| Joker | `Asterisk` |
| Projekt | `FolderOpen` |
| Projektfaktor | `FolderOpen` + `SlidersHorizontal` |
| Ereignis | `Lightning` |
| Sichten (`inspect`) | `Eye` |
| Nachziehen (`draw`) | `CardsThree` |
| Rückholen (`retrieve`) | `ArrowCounterClockwise` |
| Umverteilen (`redistribute`) | `ArrowsLeftRight` |
| positiv | `TrendUp` |
| negativ | `TrendDown` |
| ambivalent | `Scales` |
| Seltenheitsmarke | `Seal` |
| Projektsiegel | `Stamp` |
| Boosterbanderole | `CardsThree` + `TagSimple` |
| Kooperation | `Handshake` |
| Mehraufwand | `HourglassMedium` |
| Absicherung | `ShieldCheck` |
| Wildcard-Wahl | `Asterisk` + `CheckCircle` |

Projektfaktor, Boosterbanderole und Wildcard-Wahl besitzen feste,
selbstenthaltene Komposit-SVGs unter `data/assets/icons/composites/`.

### Aktive Kartenflächen

Der Vorderseitenrenderer verwendet die neuen Glyphen für:

- die ungerahmte Projektfamilie sowie zwei bis vier rechtsbündige
  Anforderungssymbole in eigenen kreisförmigen Trägern in der
  Projekt-Typzeile;
- die Faktorfamilie einschließlich Joker in der Typzeile und als großes
  Emblem im Regelfeld von Faktoren;
- Projekt, Projektfaktor und Ereignis im Identitätsstempel;
- genau ein 18er-Effektsymbol vor jedem Ereignisschlüsselwort gemäß der
  kanonischen Zuordnung E1 `inspect`/`Eye`/`SICHTEN`, E2
  `draw`/`CardsThree`/`NACHZIEHEN`, E3
  `retrieve`/`ArrowCounterClockwise`/`RÜCKHOLEN`, E4
  `redistribute`/`ArrowsLeftRight`/`UMVERTEILEN`, E5
  `joker`/`Asterisk`/`JOKER`, E6
  `extra_effort`/`HourglassMedium`/`MEHRAUFWAND`, E7
  `negative`/`TrendDown`/`RÜCKSCHLAG` und E8
  `safeguard`/`ShieldCheck`/`ABSICHERUNG`.

Ereignisse besitzen keine rechten Bedienelemente. Ihr Sekundärtext nutzt daher
bewusst die breite `type_surface` bis x 608 statt nur die allgemeine Typzone
bis x 478. Alle 28 Ereignistexte bleiben einzeilig; selbst `KAT-U17` mit
`RÜCKSCHLAG · ZIEL: DATEN + METHODE` behält rund 106,997 Einheiten bis zur
rechten Textgrenze.

Der Ereignis-Identitätsstempel enthält ausschließlich `Lightning`. Positive,
negative und ambivalente Ereignisse erhalten dort weder ein zusätzliches
Polaritätssymbol noch eine Trägerfläche. `TrendUp` und `Scales` bleiben als
semantische Polaritätsrollen im Iconkatalog registriert, werden aber auf der
aktuellen Kartenfront nicht eingesetzt. `TrendDown` wird unabhängig davon als
Basis der Ereignisrolle E7 `negative` wiederverwendet.

Die sichtbaren Anforderungsträger sind einheitliche 27er-Kreise mit Radius
13,5, 1,5 Einheiten Kontur und 18er-Glyphen. Sie sind um 0,5 Einheiten in
unveränderten 28er-Slots zentriert; bei 6 Einheiten nominalem Slot-Gap bleibt
der Mittelpunkt-Pitch 34 und der sichtbare Kreisabstand beträgt 7 Einheiten.
Die Reihe steht eine Einheit unterhalb der Typzeilenmitte bei y 520,3644. Der
nachfolgende Punkteträger ist ebenfalls ein sichtbarer 27er-Kreis in einem
28er-Slot. Er folgt nach 10 Einheiten Slot-Abstand, also 11 Einheiten zwischen
den sichtbaren Kreisflächen, und trägt die kompakte Angabe `NP` ohne
Leerzeichen. Anders als die weiterhin familienfarbigen
Anforderungskreise verwendet er für Kontur und Text das neutrale Schwarz
`line/default`; nur seine Papierfüllung bleibt hell. Die
Metadaten `data-family`, `data-slot` und `data-count="1"` liegen am jeweiligen
Anforderungsträger; Reihenfolge und Wiederholungen aus den Quelldaten bleiben
dadurch explizit erhalten.

Die Papierfüllung ist exakt `background/paper-raised` (`#F5EEDB`). Derselbe
Token liegt ohne eigene Textur auf Passepartout, Titel-, Typus- und
Inhaltsplatte. Ein im Kontext heller wirkendes Passepartout ist optischer
Kontrast zur Illustration und keine zusätzliche Farbe oder Designänderung.

Das Projektfaktor-Regelfeld zeigt die Faktorfamilie genau einmal als großes
Emblem: ein ungefüllter 92er-Kreis bei x 299 und y 570,3644 mit 1,5 Einheiten
Kontur bei 28 Prozent Deckkraft und eine 60er-Glyphe bei x 315 und y 586,3644
mit 22 Prozent. Diese bewusst
schwache Deckkraft macht das Emblem zum Wasserzeichen und hält den Regeltext
in der Vordergrundhierarchie; der Text wird nach dem Emblem gezeichnet. Er
folgt in der horizontal und vertikal
zentrierten Zone `(105, 644,8644, 480, 121)`. 36 Faktoren bleiben bei 27/38
einzeilig; nur `KAT-U03` und `KAT-U25` werden bei derselben Standardstufe
zweizeilig gesetzt. Bei ihnen bleiben mindestens 4,25 Einheiten zur ersten
Zeilenbox und 10,50 Einheiten zur tatsächlichen Tintenkante.

Die bewährte Seltenheitsskala aus vier gefüllten beziehungsweise leeren Pips
bleibt auf den Karten unverändert. `Seal` ist im Katalog registriert, ersetzt
diese Skala aber nicht. Weder die neutralisierte Punkteanzeige noch das
Faktor-Wasserzeichen verändern Geometrie oder Farbe der Pips.

Die konkrete Faktor-Geometrie dieses ADR-Standes ist historisch. Seit Layout
`1.21.0` misst der Träger 96, die Glyphe 63 Einheiten; gemaltes Emblem, acht
Einheiten Abstand und Regeltext bilden einen gemeinsamen 45/55-Inhaltsstack.
Der aktuelle normative Vertrag steht in `docs/12-card-renderer.md`.

Projektsiegel, Boosterbanderole, Kooperation und Wildcard-Wahl sind im Katalog
verfügbar, erhalten jedoch erst mit einem eigenen Produkt- oder Markerrenderer
eine konkrete Fläche. Ihre Position oder physische Ausführung wird mit dieser
Entscheidung nicht vorweggenommen. Die Otter-Illustration der Kartenrückseite
bleibt ebenfalls unverändert.

## Folgen

- Kartenaufbau und Iconassets bleiben vollständig renderer- und
  repository-basiert.
- Ein Austausch oder Versionssprung der Iconbibliothek ist eine sichtbare
  Designänderung und benötigt aktualisierte Assets, Hashes, Tests und
  Dokumentation.
- Die eigene Gestaltung entsteht aus deutscher Terminologie, semantischer
  Zuordnung, Komposition, Farbe, Trägerformen und dem übrigen Trade Dress; die
  Basisglyphen werden korrekt als Phosphor Icons attribuiert.
- Diese Entscheidung ändert keine Produktionszahlen, Seltenheitsverteilungen
  oder Spielregeln.
