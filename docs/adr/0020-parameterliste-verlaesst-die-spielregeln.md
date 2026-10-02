# ADR 0020: Parameterliste verlässt die Spielregeln

- Status: angenommen
- Datum: 2026-09-28
- Ändert: ADR 0010 (Ort der Parameterliste), `docs/10-spielregeln.md`
  (§19 entfällt, §20 wird §19), `scripts/render_rulebook.py`
  (Schalter `--ohne-parameter` entfällt)

## Kontext

ADR 0010 hat §19 „Festgelegte Parameter dieser Version" zur Liste der Werte
gemacht, deren Änderung ein neues ADR braucht. Für Spielende hat das Kapitel
keinen Nutzen: Jeder Wert steht schon in dem Paragraphen, der ihn regelt.
Liste und ADR-Verweis sind Projektverwaltung.

Die Website ließ bereits mehrere solche Vermerke aus den Regeln weg, das
Regelheft konnte §19 per Schalter auslassen. Mit diesem ADR werden die Regeln
selbst bereinigt, damit Markdown, Website und Regelheft denselben Text zeigen.
Im selben Zug entfallen die übrigen Entwicklungsvermerke: der Hinweis zur
Datei und zur Simulation, der ADR-Vermerk unter §19, der Verweis auf die
Lizenzrecherche, der Satz zu Foil-Mythics außerhalb des Bühnensatzes, der
Freigabevermerk im Kopf, die Bezeichnung „Testfassung" in §15 und der Hinweis
auf die entfallene Polaritätsmarke.

## Entscheidung

1. §19 entfällt aus `docs/10-spielregeln.md`. „Herkunft und Lizenz" wird §19.
2. Die festgelegten Parameter stehen ab jetzt in diesem ADR. Änderungen an
   ihnen brauchen weiterhin ein neues ADR, wie in ADR 0010 festgelegt:
   - festes Handlimit von fünf Karten (§9)
   - höchstens ein neuer Projektstart pro Zug (§8.1)
   - Projektstart verpflichtend, solange kein eigenes Projekt aktiv ist (§8.1)
   - Besetzung zwei bis vier Personen (§1)
   - genau sechs vollständige Runden (§15)
   - Absicherungen als einzige Ereignisse außerhalb des eigenen Zuges (§12)
   - höchstens ein gemeinsamer Faktor pro Kooperation (§11)
   - Kooperationen können nicht freiwillig beendet werden; einzelne Projekte
     schließen aber unabhängig vom Partnerprojekt ab (§11)
   - höchstens ein Mehraufwand-Ereignis pro Projekt (§13, E6)
   - Minuspunkte pauschal 1 pro aktivem, unvollendetem Projekt, unabhängig
     von dessen Punktwert (§16)
3. Das Regelheft verliert den Schalter `--ohne-parameter`.

## Folgen

- Die Verweise auf den Pflicht-Credit in
  `docs/09-licensing-and-attribution.md` und `docs/inspiration/README.md`
  zeigen auf §19.
- `scripts/sim/rules.py` und `scripts/README.md` verweisen für die Parameter
  auf dieses ADR.
- ADR 0010 bleibt als Protokoll unverändert. Seine Verweise auf §19 meinen die
  damals gültige Fassung.
- Das Regelheft hat 40 statt 44 Seiten, einen Rückstichbogen weniger.
