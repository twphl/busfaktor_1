# Mitwirken

Beiträge sind willkommen: neue Karten, Regelvorschläge, Korrekturen am Renderer
oder an der Website. Für alle Änderungen gelten die folgenden Regeln.

## Grundsätze

1. `data/cards.csv` ist die kanonische Quelle für Kartenmotive und
   Seltenheiten. Druckmengen gehören nicht hinein: Sie hängen an der Auflage
   und stehen in `data/print_runs/` (ADR 0019).
2. Änderungen an Kartenanzahlen, Boosterstruktur oder Auflagenmengen brauchen
   ein ADR unter `docs/adr/`. Vorher die Gesamtmathematik prüfen; die festen
   Zahlen der aktiven Auflage stehen im [README](README.md) und in
   [`docs/03-print-plan.md`](docs/03-print-plan.md).
3. Dokumentation und Kartentexte sind auf Deutsch; Code, Variablennamen und
   Kommentare dürfen Englisch sein.
4. Das Spiel darf von bekannten TCG-Strukturen inspiriert sein, verwendet aber
   eigene Terminologie, eigene Regeltexte, eine eigene semantische
   Iconzuordnung und eigenes Trade Dress. Offen lizenzierte Basisglyphen sind
   mit dokumentierter Herkunft zulässig.
5. Keine geschützten Logos, Figuren, Fraktionszeichen oder erkennbar kopierten
   Layouts aus bestehenden Franchises.
6. Der Humor richtet sich gegen Strukturen, Prozesse und institutionelle
   Absurditäten, nicht gegen marginalisierte Gruppen, Berufsanfänger:innen
   oder konkrete Personen.
7. Figuren sind über das Set hinweg vielfältig: Alter, Hauttöne,
   Genderpräsentation, Körperformen, Rollen und Hierarchiestufen variieren.
   Keine stereotype Rollenzuweisung.
8. Generative Bilder liefern nur Illustrationen. Titel, Regeltext, Icons,
   Rahmen, Seltenheit, Kartennummern und Formulare setzt der versionierte
   Renderer. Illustrationen enthalten keine lesbare Typografie.
9. Keine Illustrationen ohne dokumentierte Rechte und Credits einchecken.

## Neue Karten und Mechaniken

- Neue Karten zunächst als Zeile in `data/cards.csv` ergänzen. Mechaniken erst
  in Datenfeldern oder Markdown erproben, bevor Layout entsteht.
- Mechanikänderungen mit kurzem Beispiel und erwarteter Auswirkung
  beschreiben.
- Kartennamen bleiben kurz und auf Kartenformat lesbar.
- Karten von Teilnehmenden laufen als eigenes Pack im Bereich `KAT-X`, siehe
  [`docs/11-community-expansion.md`](docs/11-community-expansion.md).

Eine Karte ist spielbereit, wenn sie Folgendes besitzt:

- eindeutige ID (`card_id`) und kurzen Namen (`name`)
- Domäne (`domain_primary`), Kartenart (`card_type`) und Seltenheit (`rarity`)
- vollständigen Regeltext (`rules_text`), bei Projekten zusätzlich
  Anforderungen, Punkte und Projektziel
- Flavor Text oder die bewusste Entscheidung ohne Flavor Text
- mechanische Rolle (`mechanical_role`) und visuelles Briefing
  (`visual_motif`)
- Testnotizen (`test_notes`)
- redaktionelle Sekundärtags oder ein bewusst leeres Tagfeld
  ([`docs/13-redaktionelle-tags.md`](docs/13-redaktionelle-tags.md))

Welche Felder je Kartenart Pflicht sind, prüft `scripts/validate_cards.py`.

## Prüfen

Vor jedem Commit:

```bash
python3 scripts/validate_cards.py
uv run python -m unittest discover -s tests
python3 scripts/collate_boosters.py --seed 20260804
```

Änderungen an der Website zusätzlich mit `make website-game` prüfen, Änderungen
am Renderer mit `make website-parity`.
