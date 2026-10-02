# ADR 0019: Reduzierter Druckauftrag mit 234 Standardkarten

- Status: angenommen
- Datum: 2026-09-10
- Überholt: ADR 0002
- Ändert: ADR 0003 (Umlaufmenge der Foils), ADR 0007 (zweiter Bühnensatz),
  `docs/03-print-plan.md`, `docs/11-community-expansion.md` (Produktionsvariante),
  `data/print_plan.yaml`, `data/booster_collation.yaml`,
  `data/cards.csv` (Spalte `booster_copies`), `scripts/collate_boosters.py`,
  `scripts/validate_cards.py`

## Kontext

Die Kostenschätzung für den in ADR 0002 festgelegten Auftrag über 612
Standardkarten liegt über dem Budget. Die Zahl 612 stammte aus der Annahme
eines maximal großen Standardauftrags, nicht aus einem Angebot; der
Druckanbieter war nie festgelegt und steht in `../06-open-questions.md` unter
„Produktion" bis heute offen. Verfügbar ist ein Auftrag über 234
Standardkarten.

Die 612 Karten trugen drei Posten: 36 Booster (414 Karten), zwei Bühnensätze
(148) und Reserve (50). Bei 234 Karten trägt nicht mehr alles gleichzeitig.

## Entscheidung

**1. Der Standardauftrag sinkt auf 234 Karten. Der Foilauftrag bleibt bei 18.**

**2. Die 234 Standardkarten werden so belegt:**

| Verwendung | Karten |
|---|---:|
| ein Bühnensatz | 74 |
| 8 Special-Booster à 11 Standardkarten | 88 |
| 5 normale Booster à 12 Karten | 60 |
| Blanko-Karten für die Community-Aktion | 12 |
| Reserve | 0 |
| **Gesamt** | **234** |

**3. Von den 18 Foils gehen 8 in den Umlauf, 10 werden zurückgelegt.** Je
Special-Booster liegt genau eine Mythic; die übrigen Kopien bleiben als
Belegexemplar und Ersatz im Haus.

Der Foilauftrag wird nicht auf 9 gesenkt, weil 18 die angenommene Mindestmenge
des separaten Holoauftrags ist (ADR 0002) — eine Halbierung spart daher
vermutlich nichts. Sie würde zusätzlich Standardkarten kosten: ein
Special-Booster mit nur einem Foil braucht 11 Standardkarten statt 10.

Entscheidend ist die Umlaufmenge, nicht die Druckmenge. Bei 13 Boostern liegt
je Rare-Motiv 1,00 Karte im Pool. Mit 18 Foils im Umlauf läge jedes
Mythic-Motiv bei 2,00 Kopien — Mythics wären häufiger als Rares und ADR 0013
(„Seltenheit ist Druckmenge") wäre verletzt. Mit 8 Foils im Umlauf gilt
M 0,89 < R 1,00 < U 1,44 < C 3,25.

**4. Der zweite Bühnensatz entfällt.** ADR 0007 begründet ihn mit „Proben,
Ersatz oder einem zweiten Tisch". Diese Redundanz kostet 74 Karten und damit
sechs Booster; bei halbiertem Budget ist sie die erste Streichung, nicht das
Konferenzobjekt.

**5. Die Reserve entfällt vollständig zugunsten von 12 Blanko-Karten.**
`../11-community-expansion.md` beschreibt in Abschnitt 5 drei
Produktionsvarianten; hiermit ist **Variante C** entschieden — Formular *und*
sofort bespielbare Blanko-Karte. Die sechs Blanko-Motive aus
`scripts/render_blank_cards.py` (`KAT-B01` bis `KAT-B06`: vier Projektfaktoren
je Faktortyp, ein Ereignis, ein Projekt) werden je zweimal gedruckt.

Die Reserve war laut `../06-open-questions.md` inhaltlich nie bestimmt und ein
reiner Rest aus der Subtraktion. Sie gegen etwas Bestimmtes einzutauschen ist
die bessere Verwendung, solange die Menge ohnehin klein ist: Eine Reserve von
einer Karte hätte keinen Schadensfall abgedeckt.

## Folgen

### Kopienzahlen je Motiv im Boosterpool

| Gruppe | Motive | Karten | Verteilung |
|---|---:|---:|---|
| Common Projekt | 4 | 13 | 1 Motiv à 4, 3 Motive à 3 |
| Common Projektfaktor | 20 | 65 | 5 Motive à 4, 15 Motive à 3 |
| Common Ereignis | 4 | 13 | 1 Motiv à 4, 3 Motive à 3 |
| Uncommon Projektfaktor | 18 | 26 | 8 Motive à 2, 10 Motive à 1 |
| Uncommon Ereignis | 9 | 13 | 4 Motive à 2, 5 Motive à 1 |
| Rare Projekt | 12 | 13 | 1 Motiv à 2, 11 Motive à 1 |
| Rare Ereignis | 6 | 5 | 5 Motive à 1, 1 Motiv à 0 (siehe unten) |
| Mythic Ereignis (Foil) | 9 | 8 | 8 Motive à 1, 1 Motiv à 0 (siehe unten) |

### Zwei Motive ohne Boosterkarte

**Kein Motiv entfällt aus dem Druck.** Alle 73 Standardmotive und alle 9
Mythic-Motive werden gedruckt. Die Nullen in der Tabelle betreffen
ausschließlich den Boosterpool.

**Rare-Ereignis.** Rare-Ereignisse liegen nur in normalen Packs; fünf Slots
stehen sechs Motiven gegenüber. Ausgelassen werden darf deshalb ausschließlich
eines der vier Bühnenkandidaten `KAT-R02`, `KAT-R06`, `KAT-R15`, `KAT-R16`
(`EXPECTED_STAGE_EVENTS`) — diese liegen je einmal im Bühnensatz und sind damit
gedruckt, spielbar und am Tisch sichtbar. `KAT-R01` und `KAT-R05` stehen nicht
im Bühnensatz und kämen sonst tatsächlich nicht vor; sie müssen zwingend einen
Boosterslot erhalten. `scripts/validate_cards.py` muss das prüfen.

**Mythic.** Acht Special-Booster stehen neun Mythic-Motiven gegenüber. Ein
Motiv liegt in keinem Booster, ist aber wie alle anderen zweimal foil gedruckt
und liegt vollständig im Rückhalt. Es kann gezielt vergeben werden — als Preis,
Belegexemplar oder Tauschanreiz. Welches Motiv das ist, ist eine redaktionelle
Wahl und in `data/cards.csv` über `booster_copies` festzuschreiben.

Der reale Verlust ist damit in beiden Fällen kein Druckverlust, sondern ein
Sammelverlust: zwei Motive sind über Booster nicht erwerbbar. Das gilt ohnehin
schon für die 12 kuratierten Bühnenereignisse und die acht doppelten
Faktormotive — die Sammlung war auch bei 612 Karten nie aus Boostern allein
vollständig.

### Blanko-Karten

Zwölf Karten, sechs Motive à zwei Kopien. Sie tragen die reguläre Rückseite und
denselben Karton, gehören also zum Standardauftrag und nicht zu einem zweiten
Druckjob. Der Renderer existiert bereits (`make cards-blank`), die Motive sind
gerendert und die ID `KAT-B..` ist im Schema-Pattern
`^KAT-[CUMRBX][0-9]{2}$` vorgesehen.

Nach `../11-community-expansion.md` Abschnitt 5 muss bei Variante C jede
Blanko-Karte dieselbe Nummer tragen wie das zugehörige Formular, sonst ist die
Zuordnung nach der Konferenz nicht herstellbar. Das Nummernfeld ist damit eine
Anforderung an das Blanko-Layout, keine Option.

Zwölf Karten decken die Aktion nicht ab, sie zeigen sie: Sie reichen für
Musterkarten am Tisch und für die ersten Einreichungen, die sofort mitgespielt
werden sollen. Der Regelfall bleibt Variante A, das Formular.

Nebeneffekt: Bei einer beschädigten Standardkarte ist eine handschriftlich
ausgefüllte Blanko-Karte der einzig verbliebene Notbehelf. Das ersetzt keine
Reserve, ist aber besser als nichts.

### Weitere Folgen

- Das Konferenzobjekt schrumpft von 36 auf 13 Booster.
- Es gibt keine Reserve mehr. Beschädigte Standardkarten sind nicht
  ersetzbar; für Mythics gibt es dagegen erstmals Ersatz durch die 10
  zurückgelegten Foils. Die offene Frage nach dem Zweck der Reserve in
  `../06-open-questions.md` ist damit erledigt: Es gibt keine.
- Die Produktionsvariante aus `../11-community-expansion.md` Abschnitt 9 ist
  entschieden (C). Offen bleiben dort Lizenz der Community-Kartendaten,
  Druck oder Digitalveröffentlichung des Packs und die Kuration.
- Der Bühnensatz bleibt unverändert: 16 Projekte, 46 Projektfaktoren, 12
  Ereignisse nach ADR 0007 und ADR 0009. Die Regeln (Version 1.0) sind nicht
  betroffen, da eine Partie ohnehin nur einen Satz benötigt (§2).
- Kollation und Prüfsummen werden auflagenabhängig, `data/cards.csv` bleibt es
  nicht. Die Datei beschreibt Motive, nicht Auflagen: Von ihren 25 Spalten ist
  einzig `booster_copies` auflagenspezifisch — und dort redundant, weil sie
  eine reine Funktion von `rarity` ist (Common 9, Uncommon 4, Rare 3,
  Mythic 2). Auch `stage_candidate` und `stage_copies` bleiben gültig: Sie
  beschreiben die Zusammensetzung *eines* Bühnensatzes, nicht deren Anzahl.
  `booster_copies` wandert deshalb in ein Auflagenprofil unter
  `data/print_runs/`, das Packzahlen, Bühnensätze, Blanko-Karten und
  Foilumlauf trägt. Beide Auflagen bleiben damit ausführbar: `612-plus-18`
  nach ADR 0002 und `234-plus-18` nach diesem ADR.
  `scripts/collate_boosters.py` wählt das Profil über einen Parameter
  (`PACK_SPECS` und die Pack-Anzahl-Prüfung kommen von dort),
  `scripts/validate_cards.py` prüft die Motivdaten auflagenunabhängig und die
  Mengen (`EXPECTED_COPIES`, `EXPECTED_PHYSICAL_RARITIES`) gegen das gewählte
  Profil.
- Bei 612 Karten gingen die Kopienzahlen glatt auf, bei 234 nicht mehr
  (Commons liegen bei 3 bis 4 Kopien). Welche Motive die Zusatzkopie erhalten,
  folgt derselben Regel wie ADR 0009 für die Bühnenfaktoren: niedrigste
  `card_id` je Gruppe zuerst, damit die Auswahl nachvollziehbar und nicht
  willkürlich ist. Für die beiden Motive ohne Boosterkarte gilt die Auflage
  oben.

## Verworfene Alternativen

- **Nur ein Motiv-Komplettset (73 Standard plus 9 Foil).** Nicht spielbar: §2
  verlangt 46 Projektfaktoren, es gibt aber nur 38 Faktormotive; die 12
  kuratierten Ereignisse wären durch alle 28 ersetzt. Nicht verteilbar: ein
  einzelnes Exemplar streicht die Konferenzfunktion aus
  `../00-project-brief.md` vollständig. Und 161 der 234 bezahlten Karten
  blieben ungenutzt.
- **Statt eines Special- einen normalen Booster streichen** (9 Special,
  4 normal). Hielte alle neun Mythics im Umlauf, kostet aber einen
  Rare-Ereignis-Slot: dann lägen zwei statt einem Rare-Ereignis in keinem
  Booster. Zugleich fiele der Boosterpool auf 0,94 Rare-Karten je Motiv gegen
  1,00 Mythic-Karten — Mythics wären wieder häufiger als Rares und ADR 0013
  verletzt. Der Special-Booster ist die günstigere Streichung, weil das
  ausgelassene Mythic-Motiv gedruckt bleibt und gezielt vergeben werden kann.
- **14 Booster ohne Blanko-Karten.** Der ursprüngliche Beschluss dieses ADR.
  Lässt eine einzige Karte Reserve übrig, die keinen Schadensfall abdeckt, und
  verschiebt die Community-Aktion auf Variante A (nur Formular).
- **Zwei Bühnensätze behalten, dafür nur 7 Booster.** Erhält den zweiten Tisch,
  lässt aber nur 7 Booster und 7 Foils im Umlauf. Die Seltenheitsordnung bricht
  dabei deutlich (R 0,39 gegen M 0,78 Kopien je Motiv).
- **Kein Bühnensatz, dafür 21 Booster.** Maximiert das Konferenzobjekt und
  nutzt alle 234 Karten aus, streicht aber das Bühnenspiel — eine der beiden
  im Brief als gleich wichtig bezeichneten Funktionen. Ein einzelnes Booster
  ist laut Brief ausdrücklich kein vollständiges Spiel.
- **Foilauftrag auf 9 senken.** Siehe Entscheidung 3: spart vermutlich nichts
  und kostet zusätzliche Standardkarten.
