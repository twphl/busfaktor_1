# ADR 0009: Verteilung der acht doppelten Faktormotive im Bühnensatz

- Status: angenommen
- Datum: 2026-08-17
- Ändert: `data/cards.csv`, `scripts/validate_cards.py`, `docs/03-print-plan.md`

## Kontext

Ein 74-Karten-Bühnensatz (ADR 0007) enthält 46 Projektfaktoren, `data/cards.csv`
aber nur 38 Faktormotive. Acht Motive müssen also doppelt gedruckt werden.
Welche das sind, war bisher nicht festgelegt: `docs/03-print-plan.md` nannte
nur „je zwei zusätzliche Faktoren pro Faktortyp" — eine unbegründete
Annahme, die in `data/` nirgends nachvollziehbar war (Befund 19 in
`../review/panel-16-projektkarten.md`). Der Bühnensatz war damit nicht
reproduzierbar herstellbar.

Die Anforderungen der 16 Projekte sind nicht gleichmäßig verteilt:

| Faktortyp | Anforderungen |
|---|---:|
| Team | 15 |
| Methode | 13 |
| Daten | 12 |
| Betrieb | 11 |

Diese Schieflage ist selbst eine Entscheidung, kein Versehen: Die
Balance-Korrektur an KAT-C11, KAT-C18, KAT-R09 und KAT-R12 (siehe
`../review/panel-16-projektkarten.md`, Abschnitt 3/5) hat gezielt doppelte
Anforderungssymbole aufgelöst, weil sie unverhältnismäßig viele Ziehkarten
kosten. Vor dieser Korrektur lag die Verteilung bei 13/13/13/12 (Team/Daten/
Betrieb/Methode), nahezu gleichmäßig. Die Verschiebung auf 15/12/11/13 ist der
akzeptierte Nebeneffekt dieser Korrektur, nicht neu zu verhandeln.

Simulation (`scripts/sim/`, 3000 Partien je Variante, vier Personen,
Selbstspiel) vergleicht drei Verteilungen der acht Zusatzkopien:

| Verteilung | T/D/O/M im Satz | Punkte | negative Endsummen |
|---|---|---:|---:|
| gleichmäßig (2/2/2/2) | 11/11/11/11 | 2,70 | 19,3 % |
| anforderungsgewichtet (3T/2D/1O/2M) | 12/11/10/11 | 2,83 | 18,5 % |

Eine automatisch proportional berechnete Alternative (4T/1D/1O/2M) lag
statistisch nicht unterscheidbar auf demselben Niveau (2,83) — die genaue
Aufteilung ist also unkritisch, solange sie in Richtung Team gewichtet.

## Entscheidung

Die acht Zusatzkopien folgen der Anforderungsbilanz statt einer
Gleichverteilung: **3× Team, 2× Daten, 1× Betrieb, 2× Methode.** Verdoppelt
werden die folgenden acht Common-Faktormotive (niedrigste `card_id` je
Faktortyp, damit die Auswahl nachvollziehbar und nicht willkürlich ist):

| Faktortyp | Kopien | Motive |
|---|---:|---|
| Team | 3 | KAT-C01, KAT-C04, KAT-C05 |
| Daten | 2 | KAT-C09, KAT-C10 |
| Betrieb | 1 | KAT-C15 |
| Methode | 2 | KAT-C21, KAT-C23 |

Festgeschrieben über die neue Spalte `stage_copies` in `data/cards.csv`
(Wert `2` für die acht genannten Motive, `1` für die übrigen 30
bühnenkandidierten Faktormotive, leer für alles andere).
`scripts/validate_cards.py` prüft die Auswahl exakt, analog zu
`EXPECTED_STAGE_EVENTS`.

## Folgen

- Faktortypenbilanz im Bühnensatz: Team 12, Daten 11, Betrieb 10, Methode 11,
  Wildcard 2 — Summe 46, wie in ADR 0007 festgelegt.
- Der Bühnensatz ist ab sofort aus `data/cards.csv` allein reproduzierbar
  herstellbar; `docs/03-print-plan.md` verweist auf diese Entscheidung statt
  eine eigene, unbelegte Verteilung zu behaupten.
- `scripts/sim/` kann diese Verteilung als kanonischen Fall führen; die
  bisherigen Policies `commons` (gleichmäßig) und `requirements` (automatisch
  proportional) bleiben als Vergleichsvarianten für künftige Kartenänderungen
  nützlich und werden nicht entfernt.
- Ändert sich künftig ein Anforderungsprofil und damit `EXPECTED_PROJECT_REQUIREMENTS`,
  muss diese Verteilung neu geprüft werden.
