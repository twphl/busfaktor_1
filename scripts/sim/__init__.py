"""Monte-Carlo-Simulation des Bühnenspiels KAT-01.

Modelliert die Testfassung aus ``docs/10-spielregeln.md`` gegen die kanonischen
Kartendaten in ``data/cards.csv``. Einstiegspunkt für Auswertungen ist
``scripts/simulate.py``.
"""

from .deck import (
    FAMILIES,
    Card,
    CardDef,
    StageSet,
    build_stage_set,
    can_satisfy,
    load_cards,
)
from .engine import Game, GameResult, PlayerResult, play_game
from .rules import RULE_VARIANTS, Rules
from .strategies import STRATEGIES, make_strategy

__all__ = [
    "FAMILIES",
    "Card",
    "CardDef",
    "StageSet",
    "build_stage_set",
    "can_satisfy",
    "load_cards",
    "Game",
    "GameResult",
    "PlayerResult",
    "play_game",
    "RULE_VARIANTS",
    "Rules",
    "STRATEGIES",
    "make_strategy",
]
