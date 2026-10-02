#!/usr/bin/env python3
"""Auflagenprofile: was von `data/cards.csv` getrennt gehört.

`data/cards.csv` beschreibt **Motive** — Name, Seltenheitsklasse, Kartenart,
Regeltext, Bühnenzugehörigkeit.  Nichts davon hängt daran, wie groß der
Druckauftrag ist.  Die Kopienzahl je Motiv hängt sehr wohl daran, und sie stand
bis ADR 0019 als Spalte `booster_copies` in derselben Datei — 82-mal
ausgeschrieben, obwohl sie eine reine Funktion von `rarity` war (Common 9,
Uncommon 4, Rare 3, Mythic 2).

Seit ADR 0019 gibt es zwei Auflagen: `612-plus-18` nach ADR 0002 und
`234-plus-18` nach ADR 0019.  Beide bleiben ausführbar, weil die Kopienzahlen
hier aus der Packstruktur des Profils *abgeleitet* statt gespeichert werden.

Bei 612 Karten gingen die Zahlen glatt auf; bei 234 nicht mehr.  Wo eine Gruppe
nicht ohne Rest teilbar ist, erhalten die Motive mit der **niedrigsten
`card_id`** die Zusatzkopie — dieselbe Regel, mit der ADR 0009 die acht
doppelten Bühnenfaktoren auswählt, und aus demselben Grund: damit die Auswahl
nachvollziehbar und nicht willkürlich ist.  Reicht eine Gruppe nicht für alle
ihre Motive, fallen aus demselben Grund die *höchsten* `card_id` heraus; über
`omit_from_boosters` lässt sich das redaktionell überschreiben.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRINT_RUNS = ROOT / "data" / "print_runs"

GROUND_FAMILIES = ("team", "data", "operations", "methods")

# Slots je Pack.  Für beide Auflagen identisch: nur die Anzahl der Packs
# unterscheidet sie, nicht ihr Aufbau (docs/03-print-plan.md).
FUNCTIONAL_SLOTS = {
    "normal": {
        ("common", "Projekt"): 1,
        ("common", "Projektfaktor"): 5,
        ("common", "Ereignis"): 1,
        ("uncommon", "Projektfaktor"): 2,
        ("uncommon", "Ereignis"): 1,
        ("rare", "Projekt"): 1,
        ("rare", "Ereignis"): 1,
    },
    "special": {
        ("common", "Projekt"): 1,
        ("common", "Projektfaktor"): 5,
        ("common", "Ereignis"): 1,
        ("uncommon", "Projektfaktor"): 2,
        ("uncommon", "Ereignis"): 1,
        ("rare", "Projekt"): 1,
        ("mythic", "Ereignis"): 1,
    },
}
RARITY_SLOTS = {
    pack_type: {
        rarity: sum(count for (r, _), count in slots.items() if r == rarity)
        for rarity in ("common", "uncommon", "rare", "mythic")
    }
    for pack_type, slots in FUNCTIONAL_SLOTS.items()
}
CARDS_PER_PACK = 12


def _spread(total: int, buckets: list[str]) -> dict[str, int]:
    """Verteile `total` auf `buckets`; der Rest geht an die vorderen."""
    if not buckets:
        return {}
    base, extra = divmod(total, len(buckets))
    return {name: base + (1 if index < extra else 0) for index, name in enumerate(buckets)}


@dataclass(frozen=True)
class PrintRun:
    name: str
    adr: str
    standard_total: int
    foil_total: int
    foil_in_circulation: int
    stage_sets: int
    blank_cards: int
    reserve: int
    normal_packs: int
    special_packs: int
    omit_from_boosters: tuple[str, ...]

    @property
    def packs(self) -> int:
        return self.normal_packs + self.special_packs

    def pack_specs(self) -> list[str]:
        return (["normal"] * self.normal_packs) + (["special"] * self.special_packs)

    def standard_cards_in_boosters(self) -> int:
        """Foils belegen einen Packslot, zählen aber nicht gegen den Standardauftrag."""
        return self.packs * CARDS_PER_PACK - self.foil_in_circulation

    def slots_per_group(self) -> dict[tuple[str, str], int]:
        """Boosterslots je (Seltenheit, Kartenart) über alle Packs."""
        totals: Counter[tuple[str, str]] = Counter()
        for pack_type, count in (("normal", self.normal_packs), ("special", self.special_packs)):
            for group, per_pack in FUNCTIONAL_SLOTS[pack_type].items():
                totals[group] += per_pack * count
        return dict(totals)

    def common_factor_slots(self) -> dict[str, int]:
        """Common-Faktorslots je Faktortyp.

        Jedes Pack erhält je einen Team-, Daten-, Betriebs- und Methodenfaktor;
        der fünfte Slot rotiert gleichmäßig über alle Packs
        (docs/03-print-plan.md, Abschnitt Faktortypenverteilung).
        """
        bonus = _spread(self.packs, list(GROUND_FAMILIES))
        return {family: self.packs + bonus[family] for family in GROUND_FAMILIES}

    def booster_copies(self, cards: dict[str, dict[str, str]]) -> dict[str, int]:
        """Kopien je Motiv im Boosterpool, abgeleitet aus der Packstruktur."""
        copies: dict[str, int] = {card_id: 0 for card_id in cards}

        def assign(motifs: list[str], slots: int) -> None:
            motifs = sorted(motifs)
            keep = [m for m in motifs if m not in self.omit_from_boosters]
            # Reicht es nicht für alle, fallen die hoechsten card_id heraus.
            if slots < len(keep):
                keep = keep[:slots]
            base, extra = divmod(slots, len(keep)) if keep else (0, 0)
            for index, card_id in enumerate(keep):
                copies[card_id] = base + (1 if index < extra else 0)

        for (rarity, card_type), slots in self.slots_per_group().items():
            if (rarity, card_type) == ("common", "Projektfaktor"):
                continue  # nach Faktortyp getrennt, siehe unten
            assign(
                [
                    card_id
                    for card_id, card in cards.items()
                    if card["rarity"] == rarity and card["card_type"] == card_type
                ],
                slots,
            )

        for family, slots in self.common_factor_slots().items():
            assign(
                [
                    card_id
                    for card_id, card in cards.items()
                    if card["rarity"] == "common"
                    and card["card_type"] == "Projektfaktor"
                    and card["factor_family"] == family
                ],
                slots,
            )
        return copies


def load(name: str) -> PrintRun:
    path = PRINT_RUNS / f"{name}.json"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in PRINT_RUNS.glob("*.json")))
        raise SystemExit(f"unknown print run {name!r}; available: {available}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return PrintRun(
        name=data["name"],
        adr=data["adr"],
        standard_total=data["standard_total"],
        foil_total=data["foil_total"],
        foil_in_circulation=data["foil_in_circulation"],
        stage_sets=data["stage_sets"],
        blank_cards=data["blank_cards"],
        reserve=data["reserve"],
        normal_packs=data["packs"]["normal"],
        special_packs=data["packs"]["special"],
        omit_from_boosters=tuple(data.get("omit_from_boosters", ())),
    )


DEFAULT = "234-plus-18"
