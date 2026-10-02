# Busfaktor: 1

**Ein Sammelkartenspiel über DH-, RDM- und RSE-Projekte**

Ein kleines, auf Konferenzen spiel- und verteilbares Kartenspiel über Digital
Humanities, Research Software Engineering, Forschungsdaten, Infrastruktur, KI
und institutionelle Katastrophen.

Der aktuelle Entwurf ist ein Phylo-inspiriertes Projekt- und
Set-Collection-Spiel. Projekte werden mit Faktoren aus Team, Daten, Betrieb
und Methode erfüllt; Ereignisse helfen, stören oder verändern laufende
Projekte.

## Aktueller Produktionsrahmen

Auflage `234-plus-18` nach ADR 0019. Der ursprüngliche Rahmen mit 612
Standardkarten war nicht finanzierbar; er bleibt als Auflagenprofil
`612-plus-18` ausführbar.

- 234 Standardkarten und 18 Foilkarten, von denen 8 in den Umlauf gehen
- 13 Booster à 12 Karten, davon 8 Special-Booster
- jedes Booster: 2 Projekte, 7 Projektfaktoren und 3 Ereignisse
- Mythics ausschließlich als Foil in Special-Boostern
- ein gemeinsamer Bühnensatz à 74 Karten
- 12 Blanko-Karten für Einreichungen am Stand
- keine Reserve
- manuelle Kollationierung und Verpackung

## Setstruktur

| Seltenheit | Motive | Booster-Kopien je Motiv | Karten im Boosterpool |
|---|---:|---|---:|
| Common | 28 | 3–4 | 91 |
| Uncommon | 27 | 1–2 | 39 |
| Rare | 18 | 0–2 | 18 |
| Mythic Foil | 9 | 0–1 | 8 |
| **Boosterpool** | **82** |  | **156** |

Die 82 Booster-Motive bestehen aus 16 Projekten, 38 Projektfaktoren und 28
Ereignisse. Die kanonische CSV enthält genau diese 82 Motive und nichts sonst.

Kopienzahlen stehen **nicht** in der CSV: Sie hängen an der Auflage, das Motiv
nicht, und werden aus der Packstruktur des Auflagenprofils abgeleitet.
`KAT-R16` und `KAT-M09` erhalten keine Boosterkarte — gedruckt werden beide,
das eine im Bühnensatz, das andere als Foil im Rückhalt (ADR 0019).

## Repository-Navigation

- [`CONTRIBUTING.md`](CONTRIBUTING.md): Regeln für Beiträge
- [`docs/README.md`](docs/README.md): Dokumentationsindex
- [`docs/10-spielregeln.md`](docs/10-spielregeln.md): vollständige Spielregeln
- [`docs/02-game-design.md`](docs/02-game-design.md): Designübersicht
- [`docs/03-print-plan.md`](docs/03-print-plan.md): Druck- und Boosterplan
- [`data/cards.csv`](data/cards.csv): kanonische Karten- und Motivliste
- [`data/render_profile.json`](data/render_profile.json): verbindliche Druck- und Exportgeometrie
- [`data/card_layout.json`](data/card_layout.json): eigenständige Layout-, Farb- und Symbolkonfiguration
- [`docs/12-card-renderer.md`](docs/12-card-renderer.md): renderer-nativer SVG-/PNG-Produktionspfad
- [`data/print_runs/`](data/print_runs/): Auflagenprofile, Quelle aller Mengen
- [`data/booster_collation.yaml`](data/booster_collation.yaml): Kollationsregeln
- [`scripts/collate_boosters.py`](scripts/collate_boosters.py): reproduzierbarer Booster-Generator
- [`website/`](website/): Projektwebsite mit Regeln, Kartensammlung,
  Kartendesigner und Partie im Browser
- [`keynote-neustart/`](keynote-neustart/): Präsentation zum Spiel
- [`server/`](server/): Signaling-Server für Online-Partien

## Schnellstart

```bash
python3 scripts/validate_cards.py
python3 scripts/collate_boosters.py --seed 20260804
uv sync
make cards-goldens
```

Die erzeugten Boosterlisten landen als `build/boosters-<Auflage>.csv` in
`build/`. Für den überholten Plan:

```bash
make collate DHK_PRINT_RUN=612-plus-18
```

## Lizenz

Alle eigenen Inhalte — Regeln, Kartendaten, Illustrationen, Gestaltung,
Dokumentation und Code — stehen unter
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Die
Spielmechanik folgt PHYLO Process of Science (CC BY-SA 4.0, Sydney Ang,
Genevieve Leduc-Robert, Lu Li, and Sam MacKinnon). Schriften, Icons, PeerJS
und drei PHYLO-Beispielkarten behalten ihre eigenen Lizenzen; Einzelheiten in
[`LICENSE`](LICENSE) und
[`docs/09-licensing-and-attribution.md`](docs/09-licensing-and-attribution.md).
