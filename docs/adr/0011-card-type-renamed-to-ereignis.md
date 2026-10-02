# ADR 0011: Kartenart „Wendung“ heißt „Ereignis“

- Status: angenommen
- Datum: 2026-08-28
- Ändert: Begriff aus ADR 0006; `data/cards.csv`, `docs/`, `scripts/`,
  `figma/`, `assets/community/`

## Kontext

ADR 0006 hat die dritte Kartenart als `Wendung` eingeführt. Bei der
Regelredaktion trug der Begriff die Kartenart nicht mehr:

- **Dauerwirkung statt Moment.** Die Templates E5 (Joker) und E6 (Mehraufwand)
  bleiben bis zum Projektabschluss angelegt (`10-spielregeln.md` §4, §13).
  „Wendung“ verspricht einen einmaligen Umschwung.
- **Zustände statt Umschwünge.** Alle neun Mythics beschreiben Bedingungen —
  `Unbefristete Stelle`, `Altsystem mit Handbuch`, `Lückenlose Provenienz` —
  keine Wendepunkte.
- **Registerbruch.** `Projekt` und `Projektfaktor` sind Verwaltungsvokabular,
  `Wendung` war Dramaturgievokabular.
- **Interne Kollision.** Das Redaktionsmuster in `02-game-design.md` benennt
  seinen mittleren Schritt „Drehung“ — ein Beinahe-Synonym mit anderer
  Bedeutung.

Geprüft und verworfen wurden `Vorgang` (bester Registertreffer, aber abstrakt
und mit dem Spielablauf verwechselbar), `Entwicklung` (heißt in einem
RSE-Kontext Softwareentwicklung) sowie `Vorfall` und `Zwischenfall` (nur
negativ; 15 der 28 Motive sind positiv).

## Entscheidung

Die Kartenart heißt `Ereignis` (Plural `Ereignisse`). Ausschlaggebend war die
Verständlichkeit ohne Regelblatt: der Begriff ist in Kartenspielen etabliert,
polaritätsneutral und auf einer Konferenz ohne Erklärung lesbar.

Umgesetzt wurde durchgehend:

- `card_type` in `data/cards.csv` und alle 28 Regeltexte samt Rückbezügen
  (`Sie erfüllt` → `Es erfüllt`, `Deren Effekt` → `Dessen Effekt`)
- Regelwerk, Spielregeln, Print-Plan, Art Direction, Roadmap und Briefs
- Codebezeichner `twist` → `event` in `scripts/`, `tests/` und
  `data/*.yaml`; CLI-Flag `--no-twists` → `--no-events`
- Figma-Plugin (`code.js`, `mapping.json`), Typzeile `WENDUNG` → `EREIGNIS`,
  Komponenten `Card / Twist / *` → `Card / Event / *`
- Community-Material (`assets/community/`)

In `04-art-direction.md` wurde die vorbestehende allgemeinsprachliche
Verwendung von „Ereignis“ auf „Szene“ und „Vorfall“ umgestellt, damit der
Begriff ausschließlich die Kartenart bezeichnet.

## Folgen

- Mechanik, Zahlen, Templates E1–E8 und Booster-Kollation bleiben unverändert.
  `scripts/validate_cards.py` und die 35 Tests laufen ohne Anpassung der
  erwarteten Mengen durch.
- ADR 0006, ADR 0007 und ADR 0010 behalten ihren Wortlaut als
  Entscheidungsprotokolle; ADR 0006 trägt einen Nachtrag.
- `docs/research/` und `__scrap/` bleiben unverändert. Beide sind Herkunfts-
  und Panelstand, kein normativer Text.
- Die Figma-Komponenten müssen in der Datei selbst nachbenannt werden; das
  Repository beschreibt den Zielzustand.
