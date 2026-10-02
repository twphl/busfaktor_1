# ADR 0013: Seltenheit ist Druckmenge, nicht Spielstärke

- Status: angenommen
- Datum: 2026-08-29
- Ändert: `data/cards.csv` (Regeltexte KAT-M01, M02, M04, M05, M06, M08, M09),
  `scripts/sim/deck.py`, `scripts/sim/engine.py`, `docs/02-game-design.md`
- Beantwortet: P1-MYTHIC aus `../review/panel-review-karten-2026-08-28.md`

## Kontext

Seltenheit war im Projekt nie als Bedeutung festgelegt, nur als Druckmenge:
`03-print-plan.md` definiert Common, Uncommon, Rare und Mythic ausschließlich
über Kopien je Motiv. Die einzige inhaltliche Aussage steht in
`00-project-brief.md` — „sammelbar, ohne Pay-to-win-Logik" — und die einzige
mechanische Regel für Mythics in ADR 0003: „Mythics dürfen keine notwendigen
Basisfunktionen enthalten."

Diese Verbotsregel wurde umgesetzt, indem Mythics vorhandene Effekte mit einer
Einschränkung versehen bekamen. Das Spiel hat aber keine Kostendimension: Jedes
Ereignis kostet dasselbe, nämlich eine Handkarte und das eine Ereignis pro Zug
(§8.3), während Projektfaktoren unbegrenzt angelegt werden dürfen (§8.2). Bei
gleichem Preis ist eine engere Bedingungsmenge nicht „situativ anders", sondern
strikt schlechter. Die Regel, die Mythics entbehrlich machen sollte, hat sie
dominierbar gemacht.

Der Befund vor dieser Entscheidung: sieben der neun Mythics waren reine
Mengenvarianten anderer Karten, drei nach unten und vier nach oben.

| Karte | Verhältnis vorher |
|---|---|
| `M01` | Teilmenge von `M06` — dieselbe Absicherung, engere Reichweite |
| `M02` | Teilmenge von `U27` — Joker mit zwei statt vier Faktortypen |
| `M05` | Teilmenge von `U27` — dito |
| `M09` | Teilmenge von `U27` — zusätzlich an eine Projektlage gebunden |
| `M04` | Obermenge von `R15` — drei Verschiebungen statt einer |
| `M06` | Obermenge von `M01` — jede Reichweite statt einer |
| `M08` | Obermenge von `U22`/`R02` — zwei Faktoren statt einem |
| `M03` | eigenständig: einzige Karte, die Faktoren über Personengrenzen bewegt |
| `M07` | eigenständig: einzige Karte, die nicht verbraucht wird |

Foil-Mythics gehören nicht zum Bühnensatz (§2 der Spielregeln). Der Konflikt
tritt also nur in der frei zusammengestellten Partie auf — genau dort, wo
jemand eigene Boosterkarten mitbringt und wo Pay-to-win entstehen würde.

## Entscheidung

**1. Seltenheit bezeichnet Druckmenge und Sammelwert, nicht Spielstärke.**
Eine Karte ist nicht deshalb stärker oder schwächer, weil sie seltener
gedruckt wird. Das gilt in beide Richtungen: Mythics dürfen weder Rares
dominieren noch von Uncommons dominiert werden.

**2. Nicht-Dominanz-Test.** Für je zwei Karten mit demselben Effekt-Template
gilt: Die Menge der Situationen, in denen die eine nutzbar ist und etwas
bewirkt, darf keine Teilmenge der anderen sein, solange beide dasselbe kosten.
Wer eine Karte enger fasst, muss ihr an anderer Stelle etwas geben, das die
weitere Karte nicht kann — und umgekehrt.

**3. Mythics sind eigenständig, nicht stärker.** Die Eigenständigkeit entsteht
aus einer anderen Wirkungsachse, nicht aus einer größeren Zahl. Zulässige
Achsen sind Reichweite, Verbleib der Karte nach dem Abschluss, Kooperation und
Kosten. Unzulässig ist die bloße Erhöhung einer Anzahl.

**4. „Bis zu N" wird zu „genau N".** Wo eine Mythic dieselbe Handlung nur
öfter ausführt, wird die Zahl verbindlich. Damit kann die seltenere Karte das
Wenige nicht mehr, was die häufigere kann; sie ist die Karte für die große
Tischlage, nicht die bessere Variante.

## Umsetzung

Sieben Regeltexte in `data/cards.csv` geändert. Template, Polarität,
Faktortypen, Motive, Flavor Texts, Kopienzahlen und der Bühnensatz bleiben
unverändert.

| Karte | Neu | Nicht dominiert, weil |
|---|---|---|
| `M01` Altsystem mit Handbuch | sichert gegen **Mehraufwand** ab | `R06` sichert gegen Rückschlag ab; beide Reichweiten sind disjunkt |
| `M06` Die Live-Demo funktioniert | sichert gegen **jedes** negative Ereignis ab, **kostet eine Handkarte** | `M01` und `R06` bleiben kostenlos |
| `M02` Lückenlose Provenienz | Joker Team/Daten, **kehrt beim Abschluss offen auf die Ablage zurück** | enger als `U27` im Faktortyp, bleibt dafür im Umlauf |
| `M05` Reproduzierbare KI-Pipeline | Joker Daten/Methode, darf **zweiter gemeinsamer Faktor** einer Kooperation sein (§11) | enger als `U27` im Faktortyp, kann dafür etwas, das §11 sonst verbietet |
| `M09` Projekt pünktlich abgeschlossen | Joker für die letzte offene Anforderung, **beendet eine Kooperation** mit dem Abschluss | enger als `U27` in der Projektlage, greift dafür in die Kooperation ein |
| `M04` Migration ohne Datenverlust | verschiebt **genau drei** Faktoren | `R15` bleibt die flexible Einzelverschiebung |
| `M08` Nachnutzung möglich | nimmt **zwei** Faktoren aus der offenen Ablage | `U22` und `R02` greifen auch, wenn nur ein Faktor dort liegt |

`M03` und `M07` bleiben unverändert. Beide erfüllen den Test bereits: `M03` ist
die einzige Karte, die Faktoren zwischen Projekten verschiedener Personen
bewegt, `M07` die einzige, die nach dem Projektabschluss auf die Hand
zurückkehrt. `M07` bleibt damit die bewusste Ausnahme der Regel „jede Karte
wirkt einmal"; sie ist auf Team-Anforderungen beschränkt und verbraucht bei
jeder Nutzung erneut das Ereignislimit des Zuges. Der Panelverdacht, `M07`
könne ein Ausreißer sein, bleibt eine Playtesthypothese und ist ohne Spieltest
nicht zu belegen (Entscheidung vom 2026-08-29, siehe P1-FACTOR).

### Neue Karteninteraktionen

Alle sieben Texte bleiben im vorhandenen Regelvokabular; §13 der Spielregeln
wird nicht geändert und Version 1.0 bleibt gültig (ADR 0010).

- `M01` reagiert auf ein „Ereignis mit Mehraufwand". Das Schlüsselwort ist
  bereits in Gebrauch; `R06` reagiert seit jeher auf ein „Ereignis mit
  Rückschlag".
- `M02` legt sich beim Projektabschluss offen auf die Ablage statt auf den
  Verbrauchsstapel. `M07` weicht auf dieselbe Weise ab, nur zur Hand hin.
- `M05` und `M09` überschreiben je eine Kooperationsregel aus §11. Genau das
  sieht §11 vor: „Kartentext kann diese Regel ausdrücklich überschreiben."
- `M06` verlangt das Ablegen einer Handkarte. Das Ablegen auf die offene
  Ablage ist in §9 definiert; neu ist nur, dass eine Karte es als Kosten
  verlangt.

## Verworfene Alternativen

- **Mythics stärker machen und den freien Modus als unbalanciert erklären.**
  Billiger umzusetzen, widerspricht aber „sammelbar, ohne Pay-to-win-Logik"
  aus `00-project-brief.md`. Ein Konferenzobjekt, dessen Foils den Tisch
  entscheiden, verkauft genau die Logik, die das Projekt ablehnt.
- **Mythics zu reinen Sammelkarten erklären.** Keine Kartenarbeit, aber
  18 gedruckte Karten mit Regeltext, den niemand spielen soll. §2 erlaubt
  ihren Einsatz ausdrücklich; diese Erlaubnis wieder zu streichen, nimmt dem
  Special-Booster seinen einzigen Spielwert.
- **`U27` einschränken.** Die naheliegendste Einzeländerung, aber `U27` liegt
  im Bühnensatz. Die tatsächlich gespielte Partie zu ändern, um Karten zu
  schonen, die in ihr nicht vorkommen, wäre die falsche Richtung.

## Folgen

- Der Bühnensatz, die Kollation und die Simulationsergebnisse bleiben
  unverändert: Keine der sieben Karten ist Bühnenkandidat.
- Die Prüfsummen in `scripts/validate_cards.py` bleiben gültig. Templates
  (E1–E8), Polaritäten und Faktortypen wurden nicht angefasst.
- `scripts/sim/` kennt zwei Reichweiten mehr: Die Absicherungsreichweite
  `mehraufwand` wird jetzt erkannt, und der Joker-Sonderfall „genau eine offene
  Anforderung" wird nicht mehr als freier Joker gelesen. Beides betraf nur
  Mythics und blieb deshalb bisher unbemerkt — ein Beleg für P1-SIM: Die
  Simulation liest Mechanik aus deutschen Textfragmenten.
- Offen bleibt aus P1-SIM, dass `M03` aus „zwei kooperierende Projekte" die
  Zahl 2 als Verschiebungsanzahl liest. Die Karte nennt keine Obergrenze.
- Jede neue oder geänderte Karte muss den Nicht-Dominanz-Test bestehen. Für
  Community-Karten (`11-community-expansion.md`) gilt er ebenfalls.
- Ohne Spieltest bleibt der Test analytisch. Er schließt strikte Dominanz aus,
  nicht jede Fehlbalance.
