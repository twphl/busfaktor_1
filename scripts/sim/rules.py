#!/usr/bin/env python3
"""Regelparameter der Testfassung 0.2 und ihre dokumentierten Varianten.

Jeder Wert entspricht einem festgelegten Regelparameter (Liste in ADR 0020). Die
Varianten unten bilden diskutierte Alternativen ab, damit sie reproduzierbar
gemessen werden können.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil


@dataclass(frozen=True)
class Rules:
    players: int = 4
    rounds: int = 6  # §15
    hand_limit: int = 5  # §9
    start_projects: int = 1  # §5.5
    start_actions: int = 2  # §5.5
    draws_per_turn: int = 2  # §7

    # §8.1 Zwangsauslage: ohne aktives Projekt muss eines begonnen werden.
    forced_start: bool = True
    max_starts_per_turn: int = 1
    # Weichere Alternative aus §8.2 der Panel-Empfehlung.
    no_attach_on_start_turn: bool = False

    # §9-Varianten
    projects_count_toward_limit: bool = True
    hand_limit_penalty_per_project: int = 0

    # §16: voller Punktwert | halber Wert (aufgerundet) | pauschal 1 | keine
    minus_mode: str = "full"

    # §7: oberste Karte der offenen Ablage als Ziehquelle
    draw_from_discard: bool = True

    # §11
    cooperation: bool = False
    coop_solo_close: bool = False  # Paket B: Einzelabschluss erlauben

    events: bool = True  # Aktionsstapel ohne Ereignisse simulieren
    repeats: str = "commons"  # Auswahl der acht doppelten Faktormotive

    def minus_points(self, points: int) -> int:
        if self.minus_mode == "full":
            return points
        if self.minus_mode == "half":
            return ceil(points / 2)
        if self.minus_mode == "flat1":
            return 1
        if self.minus_mode == "none":
            return 0
        raise ValueError(f"unknown minus mode: {self.minus_mode}")

    def with_(self, **changes) -> "Rules":
        return replace(self, **changes)


# Benannte Varianten für die Vergleichstabellen in scripts/simulate.py.
RULE_VARIANTS: dict[str, dict] = {
    "basis": {},
    "hl6": {"hand_limit": 6},
    "hl4": {"hand_limit": 4},
    "hl3": {"hand_limit": 3},
    "hl2": {"hand_limit": 2},
    "ohne-zwangsauslage": {"forced_start": False},
    "projekte-limitfrei": {"projects_count_toward_limit": False},
    "projekt-in-hand-minus1": {"hand_limit_penalty_per_project": 1},
    "minus-halb": {"minus_mode": "half"},
    "minus-pauschal1": {"minus_mode": "flat1"},
    "kein-anlegen-im-startzug": {"no_attach_on_start_turn": True},
    "ohne-ereignisse": {"events": False},
    "kooperation": {"cooperation": True},
    "kooperation-einzelabschluss": {"cooperation": True, "coop_solo_close": True},
}
