# Skripte

| Skript | Zweck |
|---|---|
| `print_run.py` | Lädt die Auflagenprofile aus `data/print_runs/` und leitet die Kopienzahl je Motiv aus der Packstruktur ab (ADR 0019). |
| `validate_cards.py` | Prüft `data/cards.csv` gegen die Motivvorgaben und die Mengen des gewählten Auflagenprofils. Vor jedem Commit ausführen. |
| `collate_boosters.py` | Erzeugt die Booster-Kollation nach `data/booster_collation.yaml` und dem Auflagenprofil. |
| `generate_illustration_prompts.py` | Verknüpft den Masterprompt, Titel und Flavor Text mit allen 82 Kartenmotiven. |
| `render_cards.py` | Baut selbstenthaltene SVG-Master und druckportal-konforme 600-dpi-PNGs. |
| `render_card_back.py` | Baut die gemeinsame Kartenrückseite im selben Format: Bandsatz mit Siegel (ADR 0017). |
| `render_blank_cards.py` | Rendert die Blanko-Karten für Einreichungen am Stand. |
| `export_print_run.py` | Legt die Auflage als nummerierte Uploaddateien an, eine Datei je physischer Karte. |
| `render_print_and_play.py` | Setzt alle Kartenmotive einmal auf A4-Druckbogen. |
| `render_rulebook.py` | Setzt `docs/10-spielregeln.md` als Regelheft. |
| `simulate.py` | Monte-Carlo-Auswertungen des Bühnenspiels. |
| `sim/` | Regelmaschine, Kartenmodell und Spielweisen für `simulate.py`. |

## Illustrationsprompts

```bash
make prompts
```

Die Ausgabe liegt unter `build/illustration-prompts/`: eine Textdatei pro
Karten-ID sowie `manifest.csv` mit Kartenname, Seltenheit und Dateiname. Titel
und Flavor Text werden als semantischer Kontext eingefügt, verbunden mit der
ausdrücklichen Anweisung, sie nicht als Typografie im Bild darzustellen.
Jeder Produktionsprompt fordert eine horizontale 3:2-Quellillustration an und
hält eine umlaufende Crop-Safe-Zone für das mittige 3:2-Kartenfenster frei.
Alternative Eingabe- und Ausgabepfade lassen sich direkt angeben:

```bash
python3 scripts/generate_illustration_prompts.py \
   --cards data/cards.csv \
   --template prompts/illustration-template.md \
   --output build/illustration-prompts
```

## Kartenrenderer

Der Renderer ist der alleinige Produktionspfad aus ADR 0012. Die vier
Golden Cards decken alle vier Seltenheiten und alle drei Kartenarten ab:

```bash
uv sync
make cards-goldens
```

Der vollständige 82er-Vorschau-Satz entsteht mit `make cards`. Technische
Proofs mit eingezeichnetem Schnitt-, Lieferanten-Safe- und Text-Safe-Bereich
entstehen mit `make cards-proof`. Details zu Maßen, Schriften, Preview- und
Print-Gates stehen in [`docs/12-card-renderer.md`](../docs/12-card-renderer.md).

### Icons

Die 22 semantischen Iconrollen stehen in
`data/assets/icons/manifest.json`. Ihre Basis sind 22 lokal versionierte
Phosphor-Core-SVGs 2.1.1 in Bold; Projektfaktor, Boosterbanderole und
Wildcard-Wahl liegen als feste Komposite daneben. `render_cards.py` prüft die
Assets und bettet ihre Pfade direkt in jeden SVG-Master ein. Ein Kartenbuild
lädt keine Icons aus dem Netz. Die Ereignisrollen `inspect`, `draw`,
`retrieve` und `redistribute` ergänzen den Katalog; `CardsThree` und
`TrendDown` werden für mehrere semantische Rollen wiederverwendet.

`scripts/download_icons.sh` lädt bei einer bewusst angestoßenen
Neuinstallation ausschließlich das gepinnte Upstream-Paket und kopiert die
freigegebene Dateiliste. Komposite und Manifest sind projektspezifische
Quellen und werden dadurch nicht ersetzt. Lizenz und Attribution stehen in
`docs/09-licensing-and-attribution.md` und ADR 0014.

Die kanonische Bildbehandlung `light-mat` verwendet das B4-Passepartout. Das
8 Einheiten breite Passepartout besitzt denselben hellen Papierton wie Titel-,
Typus- und Inhaltsplatte. Eine digitale Papierkörnung wird vor dem physischen
A/B-Andruck nicht simuliert. Die farbige Bild-Keyline entfällt. Stattdessen
markiert eine neutrale 1,0er-Haarlinie aus `line/default`, um 0,5 Einheiten
nach innen gesetzt, die äußere Passepartout-Kante; ihre gemalten Grenzen
fluchten unverändert bei x 70 und x 620 mit den anderen Platten. Die Keyline
bleibt eckig, die innere Bildkante besitzt Radius 4. Der Renderer bietet keine
alternative Bildbehandlung an.

### Rückseite

`render_card_back.py` teilt sich Geometrie, Farben und den PNG-Vertrag mit
`render_cards.py` (Import statt Kopie). Die Rückseite besteht aus vier
Ebenen: hellgraue Außenfläche, schwarzer Kartenkörper (`#090B0D`, dasselbe
Schwarz wie der Rahmenring — anders als vorne trägt das Innenfeld kein
Anthrazit), darin ein eine Stufe helleres Feld und darauf die Begriffszeilen.
Sämtliche Inhaltsplatten der Vorderseite fehlen bewusst.

Die Haarlinie ist 1,5 Einheiten (rund 0,13 mm) stark, verwendet den Token
`line/highlight` und liegt zusätzlich `FRAME_HAIRLINE_INSET` (10 Einheiten)
innerhalb des DHK-Safe. Ihre Ecken sind gefast, nicht gerundet: Jenseits des
Eckenmittelpunkts des Kartenkörpers wäre ein dazu konzentrischer Radius
rechnerisch negativ, die Konzentrizitätsregel der Vorderseite trägt dort also
nicht mehr. Auf jeder Fase sitzt eine Raute (`FRAME_CHAMFER`,
`FRAME_CORNER_GAP`); der Rahmen bricht dafür auf und läuft in ihre Spitzen.
Gezeichnet werden nur die beiden oberen Ecken — die unteren sind die
gedrehten Kopien.

Die Fläche innerhalb des Rahmens ist mit `background/shell-raised-bottom`
(`#1B2024`) vom umgebenden Schwarz abgehoben (`FRAME_FIELD_TOKEN`). Damit hat
auch die Rückseite eine Innen-Außen-Ordnung, und die Zeilen laufen sichtbar
aus dem Feld heraus über den dunklen Rand.

**Die Rückseite ist punktsymmetrisch — das ist eine Spielregel, keine
Gestaltungsfrage.** Eine Karte im verdeckten Stapel darf nicht verraten, wie
herum sie liegt. Deshalb wird nur die obere
Hälfte des Motivs gezeichnet; die untere ist dieselbe Gruppe, um 180 Grad um
die Kartenmitte gedreht. Symmetrie ist damit eine Eigenschaft des
Zeichencodes, keine Zahl, die verrutschen kann. `_card_centre` prüft
zusätzlich, dass Anschnitt, Schnitt und Innenfeld dieselbe Mitte haben —
sonst gäbe es nichts, worum sich sinnvoll drehen ließe.

Acht Diagonalen in vier eng gesetzten Paaren tragen das Vokabular des Fachs
in Noto Serif Bold: `TEI`, `IIIF`, `FAIR`, `LOD`, `OAI-PMH`, `CIDOC-CRM`,
`SHACL`, `RO-CRATE`, `XML` und weitere, durchgehend in Versalien, damit die
Textur einheitlich bleibt. `TEI` und `XML` sind zwei Begriffe und stehen im
Zyklus weit auseinander, damit sie nirgends als `TEI XML` zusammenlaufen —
ein Test prüft das einschließlich des Zyklusumbruchs. Die übrigen
Bindestrichnamen sind je ein Name und bleiben zusammen. Jede Zeile beginnt an einer anderen Stelle des Zyklus,
sodass kein Begriff über seiner eigenen Wiederholung steht.

Die Serife ist eine Entscheidung, keine Voreinstellung. Vorne spricht Noto
Serif — Titel, Regeltext, Flavor —, während Noto Sans den Etikettendienst
versieht: Typzeile, Fußzeile und Abschnittslabels. Die Rückseite ist
Ausstattung, kein Etikett, und gehört damit in die Serifenstimme. Der fette
Schnitt und nicht der reguläre, weil helle Schrift auf Schwarz Substanz
braucht: Noto Serif Regular deckt nur 6,2 Prozent der Fläche gegenüber 8,2
beim fetten Schnitt und läuft im Druck Gefahr, an den dünnen Stellen
wegzubrechen. `PATTERN_FONT_ROLE` schaltet zwischen den Schnitten um,
`PATTERN_FONT_FACES` hält die zugehörige Familie und Strichstärke.

Verteilt werden die Paare **senkrecht zu den Zeilen**, nicht über die
Kartenhöhe: Ein gedrehtes Rechteck ist entlang seiner eigenen Normalen
ausgedehnter als es hoch ist. Wer das verwechselt, lässt die Ecken leer.
`PATTERN_BAND_COMPRESSION` zieht die Paare anschließend von den Kanten weg;
`PATTERN_PAIR_GAP_RATIO` bestimmt den engen Abstand innerhalb eines Paares.

Rhythmus und Anzahl sind zwei getrennte Knöpfe: `PATTERN_PAIR_SLOTS_PER_HALF`
teilt das halbe Band in gleich große Rasterplätze, `PATTERN_PAIRS_PER_HALF`
besetzt davon die inneren. Ein Paar wegzunehmen lässt die übrigen deshalb
stehen, wo sie sind, statt alles neu zu verteilen. Aktuell: drei Plätze, die
beiden inneren besetzt — die äußersten bleiben frei.

Die Läufe sind so lang wie die Schnittdiagonale und werden an der
Schnittlinie beschnitten — derselben Grenze, an der auch die Vorderseite ihr
Design beschneidet. Der Clip sitzt dabei auf einer eigenen, ungedrehten
Gruppe: Läge er auf der gedrehten, würde er in deren Koordinatensystem
ausgewertet und die Zeilen an einem schräg stehenden Rechteck abschneiden,
statt an der Schnittlinie.

**Der Rahmen weicht der Schrift, nicht umgekehrt.** Wo eine Zeile die
Haarlinie kreuzt, öffnet eine Luminanzmaske eine Lücke von 40 Einheiten
(rund 3,4 mm): Versalhöhe plus `PATTERN_FRAME_GAP_PADDING` auf beiden
Seiten. Die Korridore der Maske entstehen durch denselben
Halb-plus-Drehung-Mechanismus wie die Zeilen selbst, können also weder gegen
sie verrutschen noch die Symmetrie brechen.

Oben und unten mittig sitzt ein Zierzeichen auf der Haarlinie und
unterbricht sie. `FLOURISH_MOTIF` wählt zwischen `"otter-art"` (Vorgabe),
`"otter"` (gezeichnete Silhouette), `"diamond"` und `"none"`. Auch das
Zeichen wird nur einmal gezeichnet — das untere ist die gedrehte Kopie und
steht daher auf dem Kopf, wie es die Punktsymmetrie verlangt.

`otter-art` bettet `data/assets/images/otter_head.png` ein, 96 Einheiten (8,1 mm)
breit. Drei Dinge passieren dabei automatisch:

- **Verkleinert statt eingebettet.** Die Quelle ist 1308 px breit; eingebettet
  wird auf die doppelte Uploadgröße heruntergerechnet (384 px). Sonst lägen
  Megabytes Base64 in einer sonst vektoriellen Karte. Die Skalierung ist
  deterministisch, zwei Läufe bleiben byteidentisch. Quell- und
  Einbettungs-Hash stehen im SVG.
- **Am Lieferanten-Safe verankert.** `FLOURISH_ART_RISE` begrenzt auf 12
  Einheiten über der Rahmenlinie — genau bis zum Lieferanten-Safe. Mittig auf
  der Linie zentriert würde ein Medaillon dieser Größe über die Schnittlinie
  ragen und beim Beschnitt Kopf verlieren. Der Renderer bricht ab, wenn der
  Wert erhöht wird.
- **Die Lücke folgt der Silhouette.** Auf Höhe der Rahmenlinie ist der Kopf
  schmaler als an seiner breitesten Stelle. Die Lücke wird deshalb aus dem
  Alphakanal genau dieser Bildzeile gemessen (38,9 statt 48 Einheiten
  Halbbreite), sonst klaffte links und rechts Luft.

Die Grenze der Illustration ist ihre Strichstärke: Der mittlere Strich der
Vorlage ist 9 px auf 1284 px Kopfbreite. Bei 96 Einheiten sind das 0,057 mm.
Die kräftigen Konturen und die Silhouette tragen, das feine Fellwerk und die
Schnurrhaare liegen unter der zuverlässig druckbaren Grenze von etwa 0,1 mm.
Für volle Detailtreue bräuchte der Kopf rund 14 mm Breite — ein Fünftel der
Karte. Die eigengezeichnete Silhouette unter `"otter"` hat dieses Problem
nicht, dafür weniger Charakter.

Die Haarlinie liegt nicht willkürlich: Ihr Radius ist so gewählt, dass ihre
Eckenmittelpunkte mit denen des Kartenkörpers zusammenfallen — sie ist damit
aus `INNER_CARD_FIELD_RADIUS` abgeleitet, nach derselben Konzentrizitätsregel,
die vorne für Titel- und Footerecken gilt. Ihr Abstand kommt dagegen aus dem
DHK-Safe, nicht aus `INNER_CARD_FIELD_INSET`: Farbe muss innerhalb der
Sicherheitszone bleiben, und das ist eine Druckvorgabe, keine
Gestaltungsentscheidung. `tests/test_render_card_back.py` prüft beides.

```bash
make cards-back        # build/card-back/
make cards-back-proof  # build/card-back-proof/
make cards-test        # Vorder- und Rückseite, Testzahl siehe Runner-Ausgabe
```

Die Ausgabe ist `card-back.png`, `svg/card-back.svg` und `manifest.json`.
`--proof` blendet dieselben Schnitt- und Safe-Guides ein wie beim
Vorderseitenrenderer, `--no-svg` schreibt nur PNG und Manifest.

Direkter Aufruf für eine Karte:

```bash
uv run python scripts/render_cards.py \
  --card KAT-R12 \
  --output build/cards-preview
```

Jeder Build schreibt `<ID>.png`, optional `svg/<ID>.svg` und ein
`manifest.json` mit SHA-256-Hashes. Preview-Modus und CSV-Hash stehen im
Manifest und in den SVG-Metadaten, werden jedoch nicht sichtbar in die
Kartenfußzeile gesetzt. Das strengere Freigabegate für Produktionsdateien
bleibt über `--mode print` aktiv.

## Simulation

Die Simulation spielt vollständige Partien nach `docs/10-spielregeln.md`
(Fassung 0.2) mit dem Bühnensatz aus `data/cards.csv`. Sie ersetzt keinen
Papiertest, beantwortet aber die Fragen, für die 6 000 Partien nötig sind:
Lohnt sich Horten? Wo liegt der Handlimit-Korridor? Ist eine Projektkarte für
ihre Punktzahl zu teuer?

```bash
python3 scripts/simulate.py set                       # Zusammensetzung des Satzes
python3 scripts/simulate.py tournament --games 2000    # Strategien an einem Tisch
python3 scripts/simulate.py variants   --games 3000    # Regelvarianten gegen das Horten
python3 scripts/simulate.py handlimit  --games 3000    # Handlimit 2–6
python3 scripts/simulate.py projects   --games 3000    # Schwierigkeit je Projektkarte
python3 scripts/simulate.py repeats    --games 3000    # die acht doppelten Faktormotive
python3 scripts/simulate.py coop       --games 3000    # Kooperation nach §11
```

Gemeinsame Optionen: `--players`, `--rounds`, `--hand-limit`, `--repeats`,
`--no-events`, `--seed`, `--jobs` (Prozesse) und `--json PFAD`. Die Ausgabe ist
Markdown. Gleicher Seed ergibt gleiche Zahlen. Die Zahlen hängen an
`data/cards.csv`; nach jeder Änderung an Anforderungen, Punktwerten oder der
Bühnenauswahl neu laufen lassen.

Tests: `uv run python -m unittest discover -s tests`.

### Was abgebildet ist

- Aufbau §5, Zugablauf §6–§9, Abschluss §10, Kooperation §11,
  Ereignisse §12–§13,
  beide Ablagen §14, Spielende und Wertung §15–§16 samt Gleichstandsregel.
- Alle acht Ereignis-Templates. Die zwölf Bühnen-Ereignisse sind vollständig
  implementiert, einschließlich Reaktionsfenster für Absicherungen (E8) und der
  Regel, dass bei `KAT-U02` die betroffene Person den zusätzlichen Faktortyp wählt.
- Doppelte Anforderungssymbole verlangen zwei physische Faktoren; Wildcards
  werden mit Backtracking zugeteilt (`deck.can_satisfy`).
- Regelvarianten als Datenfeld statt als Codezweig: `sim/rules.py` enthält jeden
  festgelegten Regelparameter (ADR 0020) als Parameter, `RULE_VARIANTS` die diskutierten Alternativen.

### Bewusste Vereinfachungen

- **Zielwahl der Ereignisse** trifft die Maschine heuristisch (stärkstes Ziel,
  bestes Joker-Feld); die Strategie entscheidet nur, *ob* gespielt wird.
- **Absicherungen** spielt bei einem einzelnen Ziel nur die betroffene Person;
  bei einem Ereignis gegen alle reagiert die erste Person links der aktiven.
  Dritte halten ihre Absicherung sonst zurück.
- **Kooperation** ist eine Option (`--variants kooperation`), kein Standard.
  Angeboten wird sie nur von der Strategie `coop`.
- **Keine Verhandlung, kein Bluff, keine Sitzordnungspolitik.** Für die Frage,
  ob eine Regel eine dominante Linie erzeugt, reicht das; für die Frage, wie
  sich der Tisch anfühlt, nicht.

### Die acht doppelten Faktormotive

Der Bühnensatz enthält 46 Projektfaktoren, `data/cards.csv` aber nur 38
Faktormotive. Welche acht doppelt liegen, legt ADR 0009 fest; die Auswahl steht
in `data/cards.csv`, Spalte `stage_copies`: 3× Team, 2× Daten, 1× Betrieb, 2× Methode (KAT-C01/C04/C05,
KAT-C09/C10, KAT-C15, KAT-C21/C23), an der Anforderungsbilanz der 16 Projekte
ausgerichtet statt gleichmäßig verteilt. `scripts/validate_cards.py` prüft das.

Der Simulator liest diese Auswahl nicht automatisch — `--repeats` bleibt ein
eigener, unabhängiger Parameter für Vergleiche:

- `commons` (Standard): zwei Commons je Faktortyp, Bilanz 11/11/11/11
- `requirements`: automatisch proportional zur Anforderungsbilanz berechnet, 13/10/10/11
- `none`: ohne Zusatzkopien, 38 Faktoren

Der gedruckte Satz (3T/2D/1O/2M, Bilanz 12/11/10/11) liegt zwischen
`commons` und `requirements` und wurde als eigener Testlauf bestätigt (siehe
ADR 0009): +0,13 Punkte und weniger negative Endsummen gegenüber `commons`,
von `requirements` bei dieser Stichprobengröße nicht unterscheidbar. Wer die
tatsächlich gedruckte Verteilung simulieren will, muss sie von Hand nachbauen
(siehe ADR 0009 für den Ansatz); `--repeats` liest `stage_copies` nicht.

### Strategien

| Name | Verhalten |
|---|---|
| `open-1-safe` / `open-1-bold` | ein Projekt zugleich, Start mit 1 bzw. 3 ungedeckten Anforderungen |
| `open-2-safe` / `open-2-bold` | bis zu zwei Projekte zugleich |
| `hoard` | legt ein Projekt nur aus, wenn es sofort abschließbar ist — oder wenn §8.1 zwingt |
| `coop` | offenes Spiel, bietet Kooperationen an |
| `random` | zufällige legale Züge, Referenzlinie für den Können-Vorsprung |

„offen" ist in den Auswertungen jeweils das beste der vier offenen Profile im
Selbstspiel. Ein Profil mit *null* ungedeckten
Anforderungen beim Start wäre bereits die Hortenlinie; offene Profile beginnen
deshalb bei 1.
