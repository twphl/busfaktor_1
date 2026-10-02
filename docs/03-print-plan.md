# Druck- und Kollationsplan

Maßgeblich ist ADR 0019. Der ursprüngliche Plan über 612 Standardkarten
(ADR 0002) bleibt als Auflagenprofil `612-plus-18` ausführbar, ist aber
überholt.

## Produktionsrahmen

| Auftrag | Karten | Material |
|---|---:|---|
| Standarddruck | 234 | normaler Spielkartenkarton |
| Foildruck | 18 | Holo/Foil, identische Rückseite |
| **Gesamt** | **252** |  |

Standard- und Foilkarten sollen nach Möglichkeit dasselbe Format, denselben
Grundkarton und Eckenradius verwenden. Blickdichte Sleeves sind für
Bühnenspiele sinnvoll.

## Standardkartenverwendung

| Verwendung | Karten |
|---|---:|
| ein Bühnensatz | 74 |
| 8 Special-Booster à 11 Standardkarten | 88 |
| 5 normale Booster à 12 Karten | 60 |
| Blanko-Karten für die Community-Aktion | 12 |
| Reserve | 0 |
| **Gesamt** | **234** |

Eine Reserve gibt es nicht; an ihrer Stelle stehen zwölf Blanko-Karten. Die
Begründung steht in ADR 0019.

## Foils

18 Karten werden gedruckt, **8 gehen in den Umlauf**. Je Special-Booster liegt
genau eine Mythic. Die übrigen 10 Foils sind Belegexemplar und Ersatz.

Das ist keine Sparmaßnahme — 18 ist die angenommene Mindestmenge des separaten
Holoauftrags. Entscheidend ist die Umlaufmenge: Bei 13 Boostern liegt je
Rare-Motiv 1,00 Karte im Pool; lägen 18 Foils im Umlauf, käme jedes
Mythic-Motiv auf 2,00 Kopien und wäre häufiger als eine Rare. ADR 0013 verlangt
das Gegenteil.

Acht Special-Booster stehen neun Mythic-Motiven gegenüber: `KAT-M09` liegt in
keinem Booster, ist aber zweimal gedruckt und vollständig im Rückhalt.

## Booster

13 Booster mit je 12 Karten ergeben 156 Karten, davon 148 Standard und 8 Foil.

### Seltenheiten

| Packtyp | Anzahl | Inhalt |
|---|---:|---|
| normal | 5 | 7 Common, 3 Uncommon, 2 Rare |
| Special | 8 | 7 Common, 3 Uncommon, 1 Rare, 1 Mythic Foil |

### Funktionsslots

| Slot | normal | Special |
|---|---:|---:|
| Common-Projekt | 1 | 1 |
| Common-Projektfaktor | 5 | 5 |
| Common-Ereignis | 1 | 1 |
| Uncommon-Projektfaktor | 2 | 2 |
| Uncommon-Ereignis | 1 | 1 |
| Rare-Projekt | 1 | 1 |
| Rare-Ereignis | 1 | – |
| Mythic-Ereignis als Foil | – | 1 |

Jedes Pack enthält damit garantiert 2 Projekte, 7 Projektfaktoren und 3
Ereignisse. Der Packaufbau ist in beiden Auflagen identisch; nur die Anzahl der
Packs unterscheidet sie.

## Motiv- und Kopienzahlen

Kopienzahlen stehen **nicht** in `data/cards.csv`. Sie hängen an der Auflage,
das Motiv nicht, und werden aus der Packstruktur abgeleitet
(`scripts/print_run.py`). Wo eine Gruppe nicht ohne Rest aufgeht, erhält das
Motiv mit der niedrigeren `card_id` die Zusatzkopie — dieselbe Regel wie in
ADR 0009.

| Gruppe | Motive | Karten | Kopien je Motiv |
|---|---:|---:|---|
| Common Projekt | 4 | 13 | 1× 4, 3× 3 |
| Common Projektfaktor | 20 | 65 | 5× 4, 15× 3 |
| Common Ereignis | 4 | 13 | 1× 4, 3× 3 |
| Uncommon Projektfaktor | 18 | 26 | 8× 2, 10× 1 |
| Uncommon Ereignis | 9 | 13 | 4× 2, 5× 1 |
| Rare Projekt | 12 | 13 | 1× 2, 11× 1 |
| Rare Ereignis | 6 | 5 | 5× 1, 1× 0 |
| Mythic Ereignis (Foil) | 9 | 8 | 8× 1, 1× 0 |
| **Gesamt** | **82** | **156** |  |

Nach Funktion: 26 Projekte, 91 Projektfaktoren, 39 Ereignisse (31 Standard,
8 Foil).

### Zwei Motive ohne Boosterkarte

Gedruckt wird jedes der 82 Motive. Die Nullen betreffen nur den Boosterpool:

- `KAT-R16` liegt einmal im Bühnensatz. Rare-Ereignisse kommen nur in normalen
  Packs vor, davon gibt es fünf für sechs Motive. Ausgelassen werden darf nur
  ein Bühnenkandidat (`KAT-R02`, `KAT-R06`, `KAT-R15`, `KAT-R16`);
  `KAT-R01` und `KAT-R05` stehen nicht im Bühnensatz und müssen einen
  Boosterslot behalten.
- `KAT-M09` ist zweimal foil gedruckt und liegt vollständig im Rückhalt.

Beide sind damit über Booster nicht erwerbbar — ein Sammelverlust, kein
Druckverlust.

## Faktortypenverteilung

Jedes Pack erhält unter den fünf Common-Faktoren mindestens je einen Team-,
Daten-, Betriebs- und Methodenfaktor. Beim fünften Faktor wechseln die
Faktortypen gleichmäßig über alle Packs; bei 13 Packs erhält ein Faktortyp vier
Zusatzslots, die übrigen drei je drei.

Die zwei Uncommon-Faktoren werden so verteilt, dass:

- höchstens eine Wildcard im Pack liegt
- nach Möglichkeit zwei verschiedene Faktortypen erscheinen
- dieselbe Karten-ID nie zweimal im Pack vorkommt

## Bühnensatz

Der 74er-Satz enthält:

- alle 16 Projekte einmal
- alle 38 Faktormotive einmal, acht davon zusätzlich ein zweites Mal
- 12 kuratierte Ereignisse
- keine Foil-Mythics

Die acht Zusatzkopien sind **nicht** gleichmäßig auf die vier Faktortypen
verteilt, sondern spiegeln die Anforderungsbilanz der 16 Projekte (Team 15,
Methode 13, Daten 12, Betrieb 11): 3× Team, 2× Daten, 1× Betrieb, 2× Methode.
Damit enthält der Satz 46 Projektfaktoren mit der Faktortypenbilanz Team 12,
Daten 11, Betrieb 10, Methode 11, Wildcard 2. Welche acht Motive konkret
doppelt liegen, steht in `data/cards.csv` (Spalte `stage_copies`) und in
ADR 0009 — dort auch die Begründung und die Simulationszahlen.

Die Zusammensetzung ist auflagenunabhängig: Sie beschreibt *einen* Satz, nicht
deren Anzahl.

Spielerhilfen als eigene Karten sind gestrichen. Zugfolge, Faktortypen, Ablagen,
Wertung und die acht Ereignistemplates erklärt das gedruckte Regelblatt.

## Blanko-Karten

Zwölf Karten, sechs Motive à zwei: vier Projektfaktoren (je Faktortyp), ein
Ereignis, ein Projekt. Sie tragen die reguläre Rückseite und denselben Karton,
gehören also zum Standardauftrag und nicht zu einem zweiten Druckjob.

Sie setzen Variante C aus `11-community-expansion.md` um: Formular *und* sofort
bespielbare Karte. Jede Blanko-Karte muss dieselbe Nummer tragen wie ihr
Formular, sonst ist die Zuordnung nach der Konferenz nicht herstellbar — ein
Nummernfeld im Blanko-Layout ist damit Anforderung, nicht Option.

## Auflagenprofile

`data/print_runs/*.json` trägt Packzahlen, Bühnensätze, Blanko-Karten und
Foilumlauf. Beide Auflagen bleiben ausführbar:

```bash
make collate                              # 234-plus-18
make collate DHK_PRINT_RUN=612-plus-18    # der alte Plan
```

## Kollation und Qualitätskontrolle

`scripts/collate_boosters.py` erzeugt `build/boosters-<Auflage>.csv` mit
typisierten Slots. Der Generator prüft:

- Packzahl und Packtypen gegen das Auflagenprofil
- pro Pack exakt 12 Karten, 2 Projekte, 7 Faktoren und 3 Ereignisse
- korrekte Seltenheiten
- keine doppelte ID im Pack
- alle vier Faktortypen in jedem Pack
- Rare-Ereignisse nur in normalen Packs
- Mythics ausschließlich als Foil in Special-Packs
- exakte Kopienzahl jeder ID
- reproduzierbare Ausgabe bei gleichem Seed

`scripts/validate_cards.py` prüft zusätzlich, dass die Boosterslots exakt
aufgehen, dass die Standardrechnung die Auftragsgröße trifft und dass jedes
Motiv wenigstens einmal gedruckt wird.

Die Kollation mit Seed `20260804` erfüllt diese automatischen Prüfungen. Die
tatsächlich sortierten Packs werden zusätzlich stichprobenartig physisch
geprüft.

Beim manuellen Verpacken werden Karten nach ID abgehakt, jedes Pack gezählt und
Special-Packs äußerlich ununterscheidbar gehalten. Foils lagern vor der
Kollation mindestens 24 Stunden flach.
