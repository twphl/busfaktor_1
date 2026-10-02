#!/usr/bin/env python3
"""Spielweisen für die Simulation.

Die Strategien entscheiden über Ziehquelle, Projektstart, Anlegen, Abwerfen und
das Ausspielen eines Ereignisses. Die Zielwahl eines Ereignisses trifft die Regelmaschine
(siehe `engine.Game._build_play`).

`hoard` bildet die Hortenlinie ab: ein Projekt wird erst ausgelegt, wenn es im selben Zug
abgeschlossen werden kann — oder wenn §8.1 es erzwingt.
"""

from __future__ import annotations

import random
from collections import Counter


class Strategy:
    name = "base"
    label = "Basis"
    coop = False
    max_active = 2  # harte Obergrenze gleichzeitig aktiver Projekte
    slack = 1  # ungedeckte Anforderungen, die ein Start kosten darf
    prefer = "cheap"  # cheap | rich
    hoard = False

    # ---------------------------------------------------------------- Planung

    def committed(self, player) -> int:
        """Noch offene Anforderungen aller aktiven Projekte."""

        return sum(sum(project.open_counts().values()) for project in player.active)

    def spare_factors(self, player) -> list:
        """Handfaktoren, die kein laufendes Projekt mehr braucht."""

        need: Counter[str] = Counter()
        for project in player.active:
            need += project.open_counts()
        spare = []
        for card in sorted(player.factors_in_hand(), key=lambda c: len(c.defn.families)):
            for family in card.defn.families:
                if need[family] > 0:
                    need[family] -= 1
                    break
            else:
                spare.append(card)
        return spare

    def missing_for(self, player, card) -> int:
        """Anforderungen eines Projekts, die die Hand gerade nicht deckt."""

        need = Counter(card.defn.requirements)
        for factor in self.spare_factors(player):
            for family in factor.defn.families:
                if need[family] > 0:
                    need[family] -= 1
                    break
        return sum(need.values())

    def start_slack(self, game) -> int:
        """Wie viele ungedeckte Anforderungen ein Start kosten darf."""

        remaining = game.rules.rounds - game.round_no
        return max(0, min(self.slack, remaining - 1))

    def rank_projects(self, game, player, projects):
        def key(card):
            completable = 0 if game.can_complete_now(player, card) else 1
            points = card.defn.points
            return (completable, points if self.prefer == "cheap" else -points, card.uid)

        return sorted(projects, key=key)

    def planned_project(self, game, player):
        projects = player.projects_in_hand()
        if not projects:
            return None
        return self.rank_projects(game, player, projects)[0]

    def wants_project_card(self, game, player) -> bool:
        hand_projects = len(player.projects_in_hand())
        pipeline = len(player.active) + hand_projects
        if self.hoard:
            return pipeline == 0
        if pipeline == 0:
            return True
        if hand_projects or game.round_no >= game.rules.rounds:
            return False
        if len(player.active) < self.max_active and len(self.spare_factors(player)) >= 2:
            return True
        # Nachschub holen, solange das laufende Projekt fast fertig ist.
        return all(sum(project.open_counts().values()) <= 1 for project in player.active)

    # ---------------------------------------------------------------- Phase 1

    def choose_source(self, game, player, sources) -> str:
        if "discard" in sources:
            top = game.discard[-1]
            if top.defn.is_factor:
                need = game.plan_needs(player)
                if any(need[family] > 0 for family in top.defn.families):
                    return "discard"
        if "project" in sources and self.wants_project_card(game, player):
            return "project"
        if "action" in sources:
            return "action"
        return sources[0]

    # ---------------------------------------------------------------- Phase 2

    def choose_forced_start(self, game, player):
        return self.rank_projects(game, player, player.projects_in_hand())[0]

    def choose_start(self, game, player):
        projects = player.projects_in_hand()
        if not projects:
            return None
        ranked = self.rank_projects(game, player, projects)
        finishable = [card for card in ranked if game.can_complete_now(player, card)]
        if finishable:
            return finishable[0]
        if self.hoard or game.round_no == game.rules.rounds:
            # Ein Start ohne Abschlussaussicht bringt nur Minuspunkte.
            return None
        if len(player.active) >= self.max_active:
            return None
        # Nur so viele Anforderungen aufreißen, wie die Hand plus Restrunden decken.
        slack = self.start_slack(game)
        for card in ranked:
            if self.missing_for(player, card) <= slack:
                return card
        return None

    def choose_attach(self, game, player, moves):
        def key(move):
            card, project, family = move
            open_after = sum(project.open_counts().values()) - 1
            return (
                0 if open_after == 0 else 1,
                open_after,
                -project.points,
                1 if card.defn.is_wildcard else 0,
                card.uid,
            )

        return min(moves, key=key)

    def choose_event(self, game, player, plays):
        best = max(plays, key=lambda play: play.value)
        return best if best.value >= 1.0 else None

    # ---------------------------------------------------------------- Phase 3

    def choose_discard(self, game, player):
        scored = [(game.card_value(player, card), card.uid, card) for card in player.hand]
        return min(scored)[2]


class OpenStrategy(Strategy):
    """Offenes Spiel: Projekte auslegen, bevor die Hand sie vollständig deckt.

    `max_active` begrenzt die gleichzeitig laufenden Projekte, `slack` die Zahl
    der beim Start noch ungedeckten Anforderungen. `slack = 0` wäre bereits die
    Hortenlinie, offene Profile beginnen deshalb bei 1.
    """

    def __init__(self, max_active: int, slack: int, prefer: str = "cheap") -> None:
        self.max_active = max_active
        self.slack = slack
        self.prefer = prefer
        self.name = f"open-{max_active}-{'safe' if slack <= 1 else 'bold'}"
        self.label = (
            f"offen, bis zu {max_active} Projekt{'e' if max_active > 1 else ''} zugleich, "
            f"Start mit bis zu {slack} offenen Anforderungen"
        )


class HoardStrategy(Strategy):
    """Horten: Projekt und Faktoren erst sammeln, dann in einem Zug abschließen."""

    name = "hoard"
    label = "Horten"
    hoard = True
    max_active = 1


class CoopStrategy(OpenStrategy):
    """Offenes Spiel, das Kooperationen aktiv anbietet und annimmt."""

    def __init__(self, max_active: int = 2, slack: int = 1) -> None:
        super().__init__(max_active, slack)
        self.coop = True
        self.name = "coop"
        self.label = "offen mit Kooperation"


class RandomStrategy(Strategy):
    """Zufällige legale Züge — Referenzlinie für den Können-Vorsprung."""

    name = "random"
    label = "zufällig"

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random(0)

    def choose_source(self, game, player, sources):
        return self.rng.choice(sources)

    def choose_forced_start(self, game, player):
        return self.rng.choice(player.projects_in_hand())

    def choose_start(self, game, player):
        projects = player.projects_in_hand()
        if not projects or self.rng.random() < 0.5:
            return None
        return self.rng.choice(projects)

    def choose_attach(self, game, player, moves):
        return self.rng.choice(moves)

    def choose_event(self, game, player, plays):
        return self.rng.choice(plays) if self.rng.random() < 0.7 else None

    def choose_discard(self, game, player):
        return self.rng.choice(player.hand)


# Die vier offenen Profile spannen Pipeline-Breite gegen Startrisiko auf.
# „offen" in den Auswertungen ist jeweils das beste dieser vier.
OPEN_VARIANTS = (
    ("open-1-safe", lambda: OpenStrategy(1, 1, "cheap")),
    ("open-1-bold", lambda: OpenStrategy(1, 3, "rich")),
    ("open-2-safe", lambda: OpenStrategy(2, 1, "cheap")),
    ("open-2-bold", lambda: OpenStrategy(2, 3, "rich")),
)

STRATEGIES: dict[str, object] = dict(OPEN_VARIANTS)
STRATEGIES.update(
    {
        "hoard": HoardStrategy,
        "random": RandomStrategy,
        "coop": CoopStrategy,
    }
)

OPEN_NAMES = tuple(name for name, _ in OPEN_VARIANTS)


def make_strategy(name: str):
    try:
        factory = STRATEGIES[name]
    except KeyError:  # pragma: no cover - CLI-Fehlerpfad
        raise SystemExit(f"unknown strategy: {name} (known: {', '.join(sorted(STRATEGIES))})")
    return factory()
