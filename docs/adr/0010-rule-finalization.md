# ADR 0010: Regelfinalisierung ohne Papiertest-Kriterium

- Status: angenommen
- Datum: 2026-08-17
- Ändert: `docs/10-spielregeln.md` (Version 0.2 → 1.0), `docs/02-game-design.md`,
  `docs/06-open-questions.md`

## Kontext

`docs/10-spielregeln.md` (Fassung 0.2) markierte zentrale Parameter als
**Testregel** und band ihre Bestätigung an „mindestens zwei vollständige
Papierpartien" (§19). Diese Papierpartien haben nicht stattgefunden. Unter
Zeitdruck zur Produktionsfreigabe wurde entschieden, das Papiertest-Kriterium
zu streichen und stattdessen auf Basis der Monte-Carlo-Simulation
(`scripts/sim/`, siehe `scripts/README.md`) zu finalisieren.

Drei der bis dahin offenen Fragen hatten belastbare, simulationsgestützte
Antworten; sie wurden im Zuge dieser Finalisierung entschieden. Alle übrigen
Testregel-Werte (Handlimit 5, ein Projektstart pro Zug, Zwangsauslage,
sechs Runden, ein gemeinsamer Kooperationsfaktor, keine freiwillige
Kooperationsauflösung, eine Mehraufwand-Wendung pro Projekt, 2–4 Personen)
bleiben bei ihrem bisherigen Wert — nicht weil sie erneut geprüft wurden,
sondern weil ihre Wirkungslosigkeit oder Unkritikalität bereits durch
Simulation belegt ist (Handlimit: `scripts/README.md`, Abschnitt
„Handlimit-Sweep") oder weil sie außerhalb des heutigen Entscheidungsumfangs
lagen.

## Entscheidung

### 1. Minuspunkte (§16): pauschal statt punktwertabhängig

Ein aktives, unvollendetes Projekt zählt am Spielende **1 Minuspunkt**,
unabhängig von seinem Punktwert — statt bisher seinen vollen Punktwert.

Gemessen (3000 Partien, vier Personen, Selbstspiel, bestes offenes
Selbstspielprofil):

| Variante | Punkte | negative Endsummen | Horten-Vorsprung |
|---|---:|---:|---:|
| voller Wert (bisher) | 2,72 | 18,7 % | +0,28 |
| halbiert (aufgerundet) | 3,73 | 7,2 % | +0,22 |
| **pauschal −1 (gewählt)** | **4,35** | **7,1 %** | **+0,18** |

Pauschal −1 dominiert halbiert auf jeder gemessenen Achse und ist der
einfachere Regelsatz. Verworfen: „halbiert" (schwächer in den Zahlen, keine
zusätzliche Verständlichkeit) und „voller Wert" (18,7 % negative Endsummen,
größter Horten-Vorsprung).

### 2. Parallele Projekte: keine Regeländerung

Die Simulation zeigt, dass zwei gleichzeitig aktive Projekte unter jeder
getesteten Variante schlechter abschneiden als eines. Keine Regeländerung
vorgenommen. Begründung, DH-Fachexpertise (siehe Sitzungsverlauf):
Parallelität ist in der Projektrealität Zwang, keine freiwillige
Optimierungsentscheidung; ein Spiel, dessen optimale Linie „ein Projekt nach
dem anderen" lautet, trifft damit eine fachlich korrekte Aussage.

Geprüft und verworfen: eine Kombination aus zusätzlicher Ziehung je
Zusatzprojekt und Teilpunkten statt vollem Minus kippt die Rechnung zwar
leicht ins Plus (+0,16 für zwei Projekte bei n=3000), verlangt aber zwei neue,
spielweite Mechaniken und eine Teilpunkte-Regel, die weder in
`scripts/sim/rules.py` noch in den Spielregeln existiert. Der Aufwand steht in
keinem Verhältnis zum fachlich ohnehin gewünschten Verhalten.

### 3. Kooperation (§11): Einzelabschluss

Ein Projekt in einer Kooperation wird **sofort einzeln abgeschlossen**, sobald
seine Anforderungen erfüllt sind — auch wenn das Partnerprojekt noch offen
ist. Ein gemeinsamer Faktor bleibt liegen, bis auch das Partnerprojekt
abgeschlossen ist, und wird erst dann verbraucht.

Gemessen (3000 Partien):

| Variante | Punkte | Abschlussquote beider Projekte |
|---|---:|---:|
| bisher (gemeinsamer Abschluss) | 2,03 | 41,8 % |
| **Einzelabschluss (gewählt)** | **2,49** | **65,9 %** |

Ohne diese Änderung war Kooperation wirtschaftlich negativ (2,03 gegen 2,29
Punkte ohne jede Kooperation) — eine Regel, die am Tisch nie freiwillig
genutzt worden wäre.

### 4. Papiertest-Kriterium gestrichen

§19 fordert nicht mehr „mindestens zwei vollständige Papierpartien" als
Bedingung für Endgültigkeit. Änderungen an den in §19 gelisteten Werten
benötigen stattdessen ein neues ADR. `docs/10-spielregeln.md` wechselt von
Version 0.2 („vollständig spielbare Testfassung, noch nicht
produktionsfreigegeben") auf Version 1.0 („produktionsfreigegeben"); alle
**Testregel**-Markierungen sind entfernt.

## Folgen

- `docs/10-spielregeln.md`: Header, §1/§4 (Projektbeschreibung), §8.1, §8.5,
  §9, §11, §13, §15, §16, §18, §19 angepasst. Kartentexte in `data/cards.csv`
  sind von dieser Änderung nicht betroffen — kein Kartentext verweist auf den
  Punktwert eines eigenen unvollendeten Projekts.
- `docs/02-game-design.md`: Kooperationsabschnitt und Statuszeile müssen den
  Einzelabschluss und den Wegfall des Papiertest-Vorbehalts spiegeln.
- `docs/06-open-questions.md`: die Frage zur Kooperationshäufigkeit/-auflösung
  bleibt insofern offen, als sie nicht Gegenstand dieser Entscheidung war;
  klargestellt wird nur, dass der generelle Papiertest-Vorbehalt für die
  Regeln entfällt.
- `scripts/sim/rules.py` bleibt unverändert: `Rules()`-Standardwerte
  (`minus_mode="full"`, `coop_solo_close=False`) repräsentieren weiterhin den
  historischen Ist-Zustand für Vergleichszwecke. Die jetzt produktive
  Konfiguration entspricht `minus_mode="flat1"` kombiniert mit
  `cooperation=True, coop_solo_close=True`; es gibt dafür noch keinen
  gebündelten Eintrag in `RULE_VARIANTS`. Wer künftig simuliert, muss diese
  Kombination explizit setzen.
- Nicht angefasst: alle übrigen §19-Werte (Handlimit, Rundenzahl,
  Zwangsauslage, Mehraufwand-Limit, Kooperationsvoraussetzungen). Sie gelten
  ab sofort als endgültig, ohne dass sie in dieser Sitzung erneut geprüft
  wurden — ihre Bestätigung stützt sich auf frühere Simulationen
  (`docs/review/panel-16-projektkarten.md`, `scripts/README.md`).
