#!/usr/bin/env python3
"""Regelmaschine für eine Partie nach `docs/10-spielregeln.md` (Fassung 0.2).

Abgebildet sind Aufbau (§5), Zugablauf (§6–§9), Projektabschluss (§10),
Kooperation (§11), Ereignisse samt Reaktionsfenster (§12–§13), die beiden
Ablagen (§14) sowie Spielende und Wertung (§15–§16).

Bewusste Vereinfachungen sind in `scripts/README.md` aufgeführt; die
wichtigste: Zielwahl und Effektnutzung von Ereignisse entscheidet die Maschine
heuristisch, die Strategie entscheidet nur, ob ein Ereignis gespielt wird.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .deck import Card, StageSet, build_stage_set, can_satisfy
from .rules import Rules


@dataclass
class ActiveProject:
    card: Card
    owner: int
    started_turn: int
    filled: list[tuple[str, Card]] = field(default_factory=list)
    surcharges: list[tuple[str, Card]] = field(default_factory=list)
    coop: "Cooperation | None" = None

    @property
    def points(self) -> int:
        return self.card.defn.points

    def requirement_counts(self) -> Counter[str]:
        counts = Counter(self.card.defn.requirements)
        for family, _ in self.surcharges:
            counts[family] += 1
        return counts

    def filled_counts(self) -> Counter[str]:
        counts = Counter(family for family, _ in self.filled)
        if self.coop is not None and self.coop.shared_family is not None:
            counts[self.coop.shared_family] += 1
        return counts

    def open_counts(self) -> Counter[str]:
        return self.requirement_counts() - self.filled_counts()

    def is_complete(self) -> bool:
        return not self.open_counts()

    def factor_count(self) -> int:
        return len(self.filled)


@dataclass
class Cooperation:
    projects: tuple[ActiveProject, ActiveProject]
    shared: Card | None = None
    shared_family: str | None = None
    closed: list[ActiveProject] = field(default_factory=list)

    def partner(self, project: ActiveProject) -> ActiveProject:
        first, second = self.projects
        return second if project is first else first


@dataclass
class PlayerState:
    index: int
    strategy: Any
    hand: list[Card] = field(default_factory=list)
    active: list[ActiveProject] = field(default_factory=list)
    completed: list[Card] = field(default_factory=list)

    # Kennzahlen
    first_start_round: int | None = None
    forced_discards: int = 0
    painful_discards: int = 0
    steals: int = 0
    self_recovers: int = 0
    options: list[int] = field(default_factory=list)
    coops: int = 0
    coops_closed: int = 0
    events_played: int = 0

    def projects_in_hand(self) -> list[Card]:
        return [card for card in self.hand if card.defn.is_project]

    def factors_in_hand(self) -> list[Card]:
        return [card for card in self.hand if card.defn.is_factor]


@dataclass
class PlayerResult:
    index: int
    strategy: str
    score: int
    plus: int
    minus: int
    completed: tuple[int, ...]
    unfinished: tuple[int, ...]
    first_start_round: int | None
    forced_discards: int
    painful_discards: int
    steals: int
    self_recovers: int
    mean_options: float
    coops: int
    coops_closed: int


@dataclass
class GameResult:
    players: tuple[PlayerResult, ...]
    reshuffles: int
    projects_seen: int
    started_projects: tuple[str, ...]
    completed_projects: tuple[str, ...]

    @property
    def winners(self) -> tuple[int, ...]:
        best = max(result.score for result in self.players)
        top = [result for result in self.players if result.score == best]
        if len(top) > 1:  # §16 Gleichstand
            most = max(len(result.completed) for result in top)
            top = [result for result in top if len(result.completed) == most]
        if len(top) > 1:
            least = min(result.minus for result in top)
            top = [result for result in top if result.minus == least]
        return tuple(result.index for result in top)


@dataclass
class EventPlay:
    card: Card
    template: str
    value: float
    payload: dict = field(default_factory=dict)


class Game:
    def __init__(self, rules: Rules, strategies: list[Any], rng: random.Random) -> None:
        if len(strategies) != rules.players:
            raise ValueError("one strategy per player required")
        self.rules = rules
        self.rng = rng
        stage: StageSet = build_stage_set(rules.repeats)

        self.project_deck = list(stage.projects)
        actions = [card for card in stage.actions if rules.events or not card.defn.is_event]
        self.action_deck = list(actions)
        rng.shuffle(self.project_deck)
        rng.shuffle(self.action_deck)

        self.discard: list[Card] = []  # offene Ablage, letzte Karte liegt oben
        self.consumed: list[Card] = []  # verdeckter Verbrauchsstapel
        self.discarded_by: dict[int, int] = {}
        self.controller: dict[int, int] = {}
        self.reshuffles = 0
        self.round_no = 1
        self.turn_index = 0
        self.started_projects: list[str] = []
        self.completed_projects: list[str] = []

        self.players = [PlayerState(index, strategy) for index, strategy in enumerate(strategies)]
        for player in self.players:
            for _ in range(rules.start_projects):
                if self.project_deck:
                    player.hand.append(self.project_deck.pop())
            for _ in range(rules.start_actions):
                card = self._draw_action()
                if card is not None:
                    player.hand.append(card)

    # ------------------------------------------------------------------ Stapel

    def _draw_action(self) -> Card | None:
        if not self.action_deck:
            if not self.consumed:
                return None
            self.action_deck = self.consumed  # §7 leerer Aktionsstapel
            self.consumed = []
            self.rng.shuffle(self.action_deck)
            self.reshuffles += 1
        return self.action_deck.pop()

    def available_sources(self) -> list[str]:
        sources = []
        if self.project_deck:
            sources.append("project")
        if self.action_deck or self.consumed:
            sources.append("action")
        if self.rules.draw_from_discard and self.discard:
            sources.append("discard")
        return sources

    def _draw(self, player: PlayerState, source: str) -> Card | None:
        card: Card | None
        if source == "project" and self.project_deck:
            card = self.project_deck.pop()
        elif source == "discard" and self.discard:
            card = self.discard.pop()
            owner = self.discarded_by.pop(card.uid, None)
            if owner is None or owner == player.index:
                player.self_recovers += 1
            else:
                self.players[owner].steals += 1
        else:
            card = self._draw_action()
        if card is not None:
            player.hand.append(card)
        return card

    def to_discard(self, player: PlayerState | None, card: Card) -> None:
        self.discard.append(card)
        if player is not None:
            self.discarded_by[card.uid] = player.index

    # ------------------------------------------------------------------ Partie

    def play(self) -> GameResult:
        for self.round_no in range(1, self.rules.rounds + 1):
            for player in self.players:
                self.take_turn(player)
                self.turn_index += 1
        return self._result()

    def take_turn(self, player: PlayerState) -> None:
        self.draw_phase(player)
        self.action_phase(player)
        self.cleanup_phase(player)

    def draw_phase(self, player: PlayerState) -> None:  # §7
        for _ in range(self.rules.draws_per_turn):
            sources = self.available_sources()
            if not sources:
                return
            source = player.strategy.choose_source(self, player, sources)
            self._draw(player, source)

    def action_phase(self, player: PlayerState) -> None:  # §8
        player.options.append(self.count_options(player))
        starts_left = self.rules.max_starts_per_turn

        if self.rules.forced_start and not player.active and player.projects_in_hand():
            card = player.strategy.choose_forced_start(self, player)
            self.start_project(player, card)
            starts_left -= 1
        if starts_left > 0:
            card = player.strategy.choose_start(self, player)
            if card is not None:
                self.start_project(player, card)
                starts_left -= 1

        self.attach_all(player)
        if self.rules.events:
            self.play_one_event(player)
            self.attach_all(player)
        if self.rules.cooperation:
            self.offer_cooperation(player)
            self.attach_all(player)

    def cleanup_phase(self, player: PlayerState) -> None:  # §9
        while self.hand_size(player) > self.hand_limit(player):
            card = player.strategy.choose_discard(self, player)
            player.hand.remove(card)
            player.forced_discards += 1
            if self.is_needed_now(player, card):
                player.painful_discards += 1
            self.to_discard(player, card)

    def hand_limit(self, player: PlayerState) -> int:
        penalty = self.rules.hand_limit_penalty_per_project * len(player.projects_in_hand())
        return max(0, self.rules.hand_limit - penalty)

    def hand_size(self, player: PlayerState) -> int:
        if self.rules.projects_count_toward_limit:
            return len(player.hand)
        return len([card for card in player.hand if not card.defn.is_project])

    # ------------------------------------------------------------------ Aktionen

    def start_project(self, player: PlayerState, card: Card | None) -> None:  # §8.1
        if card is None:
            return
        player.hand.remove(card)
        player.active.append(ActiveProject(card, player.index, self.turn_index))
        self.started_projects.append(card.card_id)
        if player.first_start_round is None:
            player.first_start_round = self.round_no

    def legal_attachments(self, player: PlayerState) -> list[tuple[Card, ActiveProject, str]]:
        moves = []
        for project in player.active:
            if self.rules.no_attach_on_start_turn and project.started_turn == self.turn_index:
                continue
            open_counts = project.open_counts()
            if not open_counts:
                continue
            for card in player.hand:
                if not card.defn.is_factor:
                    continue
                for family in card.defn.families:
                    if open_counts[family] > 0:
                        moves.append((card, project, family))
        return moves

    def attach_all(self, player: PlayerState) -> None:  # §8.2
        while True:
            moves = self.legal_attachments(player)
            if not moves:
                break
            move = player.strategy.choose_attach(self, player, moves)
            if move is None:
                break
            self.attach(player, *move)
            self.resolve_completions(player)

    def attach(self, player: PlayerState, card: Card, project: ActiveProject, family: str) -> None:
        player.hand.remove(card)
        self.controller[card.uid] = player.index
        coop = project.coop
        if (
            coop is not None
            and coop.shared is None
            and coop.partner(project).open_counts()[family] > 0
        ):
            coop.shared = card  # §11 gemeinsamer Faktor
            coop.shared_family = family
        else:
            project.filled.append((family, card))

    def resolve_completions(self, player: PlayerState) -> None:  # §10
        while True:
            ready = [project for project in player.active if project.is_complete()]
            closable = []
            for project in ready:
                coop = project.coop
                if coop is None or self.rules.coop_solo_close:
                    closable.append(project)
                elif coop.partner(project).is_complete():
                    closable.append(project)
            if not closable:
                return
            for project in closable:
                self.close_project(project)

    def close_project(self, project: ActiveProject) -> None:
        owner = self.players[project.owner]
        owner.active.remove(project)
        owner.completed.append(project.card)
        self.completed_projects.append(project.card.card_id)
        for _, card in project.filled:
            self.consumed.append(card)
        for _, card in project.surcharges:
            self.consumed.append(card)
        coop = project.coop
        if coop is not None:
            coop.closed.append(project)
            owner.coops_closed += 1
            if coop.shared is not None and len(coop.closed) == 2:
                self.consumed.append(coop.shared)
                coop.shared = None
                coop.shared_family = None

    # ------------------------------------------------------------------ Ereignisse

    def play_one_event(self, player: PlayerState) -> None:  # §8.3
        plays = self.legal_events(player)
        if not plays:
            return
        play = player.strategy.choose_event(self, player, plays)
        if play is None:
            return
        player.hand.remove(play.card)
        player.events_played += 1
        self.apply_event(player, play)

    def legal_events(self, player: PlayerState) -> list[EventPlay]:
        plays: list[EventPlay] = []
        for card in player.hand:
            spec = card.defn.event
            if spec is None or spec.template == "E8":
                continue  # Absicherungen bleiben für das Reaktionsfenster
            play = self._build_play(player, card, spec)
            if play is not None:
                plays.append(play)
        return plays

    def _build_play(self, player: PlayerState, card: Card, spec) -> EventPlay | None:
        template = spec.template
        if template == "E1":
            if not (self.action_deck or self.consumed):
                return None
            return EventPlay(card, template, 1.0)
        if template == "E2":
            if not (self.action_deck or self.consumed):
                return None
            return EventPlay(card, template, 1.5)
        if template == "E3":
            need = self.plan_needs(player)
            recovered: Card | None = None
            for candidate in reversed(self.discard):
                if not candidate.defn.is_factor:
                    continue
                if any(need[family] > 0 for family in candidate.defn.families):
                    recovered = candidate
                    break
                recovered = recovered or candidate
            if recovered is None:
                return None
            useful = any(need[family] > 0 for family in recovered.defn.families)
            return EventPlay(card, template, 2.0 if useful else 0.5, {"card": recovered})
        if template == "E4":
            move = self._best_redistribution(player)
            if move is None:
                return None
            return EventPlay(card, template, move.pop("value"), move)
        if template == "E5":
            joker: tuple[float, ActiveProject, str] | None = None
            for project in player.active:
                open_counts = project.open_counts()
                for family in spec.families:
                    if open_counts[family] <= 0:
                        continue
                    completes = sum(open_counts.values()) == 1
                    if spec.only_if_completes and not completes:
                        continue
                    value = 3.0 if completes else 1.2
                    if joker is None or value > joker[0]:
                        joker = (value, project, family)
            if joker is None:
                return None
            return EventPlay(card, template, joker[0], {"project": joker[1], "family": joker[2]})
        if template == "E6":
            burden: tuple[float, ActiveProject, PlayerState] | None = None
            for other in self.players:
                if other is player:
                    continue
                for project in other.active:
                    if project.surcharges:  # Testregel §13 E6
                        continue
                    value = 1.0 + project.factor_count() / max(1, project.points)
                    if burden is None or value > burden[0]:
                        burden = (value, project, other)
            if burden is None:
                return None
            value, project, victim = burden
            if spec.chooser == "target":
                family = self._victim_choice(victim, project, spec.families)
            else:
                family = spec.families[0]
            return EventPlay(card, template, value, {"project": project, "family": family})
        if template == "E7":
            if spec.scope == "all":
                if not any(p.filled for other in self.players for p in other.active):
                    return None
                return EventPlay(card, template, 1.5, {"scope": "all"})
            setback: tuple[float, ActiveProject, Card, str] | None = None
            for other in self.players:
                if other is player:
                    continue
                for project in other.active:
                    for family, attached in project.filled:
                        if family not in spec.families:
                            continue
                        value = 1.0 + project.points / 4 + project.factor_count() / 4
                        if setback is None or value > setback[0]:
                            setback = (value, project, attached, family)
            if setback is None:
                return None
            value, project, attached, family = setback
            return EventPlay(
                card, template, value, {"project": project, "card": attached, "family": family}
            )
        return None

    def _victim_choice(self, victim: PlayerState, project: ActiveProject, families) -> str:
        """§13 E6/U02: Die betroffene Person wählt den zusätzlichen Faktortyp selbst."""

        supply: Counter[str] = Counter()
        for card in victim.hand:
            if card.defn.is_factor:
                for family in card.defn.families:
                    supply[family] += 1
        return max(families, key=lambda family: (supply[family], family))

    def _best_redistribution(self, player: PlayerState) -> dict | None:
        for source in player.active:
            for family, card in source.filled:
                for target in player.active:
                    if target is source:
                        continue
                    open_counts = target.open_counts()
                    for option in card.defn.families:
                        if open_counts[option] <= 0:
                            continue
                        completes = sum(open_counts.values()) == 1
                        if not completes:
                            continue
                        return {
                            "value": 3.0,
                            "card": card,
                            "source": source,
                            "target": target,
                            "family": option,
                            "old_family": family,
                        }
        return None

    def apply_event(self, player: PlayerState, play: EventPlay) -> None:  # §13
        spec = play.card.defn.event
        assert spec is not None
        template = play.template
        polarity = play.card.defn.polarity

        if polarity == "negative":
            victim = self._event_victim(play)
            if self.try_counter(player, victim, play):
                self.consumed.append(play.card)
                return

        if template == "E1":  # Sichten
            seen = [card for card in (self._draw_action() for _ in range(spec.look)) if card]
            for _ in range(min(spec.take, len(seen))):
                best = max(seen, key=lambda card: self.card_value(player, card))
                seen.remove(best)
                player.hand.append(best)
            self.action_deck = seen + self.action_deck  # zurück unter den Stapel
            self.consumed.append(play.card)
            return
        if template == "E2":  # Nachziehen
            found = 0
            guard = 0
            aside: list[Card] = []
            while found < spec.take and guard < 60:
                guard += 1
                card = self._draw_action()
                if card is None:
                    break
                if card.defn.is_factor:
                    player.hand.append(card)
                    found += 1
                else:
                    # §13 E2: beiseitegelegte Ereignisse werden beim Erneuern des
                    # Aktionsstapels nicht mitgemischt, erst danach verbraucht.
                    aside.append(card)
            self.consumed.extend(aside)
            self.consumed.append(play.card)
            return
        if template == "E3":  # Rückholen
            target = play.payload["card"]
            if target in self.discard:
                self.discard.remove(target)
                self.discarded_by.pop(target.uid, None)
                player.hand.append(target)
            self.consumed.append(play.card)
            return
        if template == "E4":  # Umverteilen
            source: ActiveProject = play.payload["source"]
            destination: ActiveProject = play.payload["target"]
            entry = (play.payload["old_family"], play.payload["card"])
            if entry in source.filled:
                source.filled.remove(entry)
                destination.filled.append((play.payload["family"], play.payload["card"]))
            self.consumed.append(play.card)
            self.resolve_completions(player)
            return
        if template == "E5":  # Joker
            project: ActiveProject = play.payload["project"]
            self.controller[play.card.uid] = player.index
            project.filled.append((play.payload["family"], play.card))
            self.resolve_completions(player)
            return
        if template == "E6":  # Mehraufwand
            project = play.payload["project"]
            project.surcharges.append((play.payload["family"], play.card))
            return
        if template == "E7":  # Rückschlag
            if play.payload.get("scope") == "all":
                for other in self.players:
                    self._return_worst_factor(other)
            else:
                self._return_factor(play.payload["project"], play.payload["card"])
            self.consumed.append(play.card)
            return
        self.consumed.append(play.card)

    def _event_victim(self, play: EventPlay) -> PlayerState | None:
        project = play.payload.get("project")
        if isinstance(project, ActiveProject):
            return self.players[project.owner]
        return None

    def try_counter(self, actor: PlayerState, victim: PlayerState | None, play: EventPlay) -> bool:
        """§12 Reaktionsfenster: nur Absicherungen können ein Ereignis stoppen.

        Bei einem einzelnen Ziel reagiert hier ausschließlich die betroffene
        Person (Vereinfachung); bei einem Ereignis gegen alle beginnt das
        Reaktionsrecht links von der aktiven Person.
        """

        if victim is not None:
            order = [victim]
        else:
            order = [
                self.players[(actor.index + offset) % len(self.players)]
                for offset in range(1, len(self.players))
            ]
        for player in order:
            if player is actor:
                continue
            for card in player.hand:
                spec = card.defn.event
                if spec is None or spec.template != "E8":
                    continue
                if not self._counter_matches(spec.counters, play):
                    continue
                player.hand.remove(card)
                self.consumed.append(card)
                return True
        return False

    @staticmethod
    def _counter_matches(counters: str, play: EventPlay) -> bool:
        if counters == "rueckschlag":
            return play.template == "E7"
        if counters == "mehraufwand":
            return play.template == "E6"
        if counters == "single":
            return play.payload.get("scope") != "all"
        return True

    def _return_factor(self, project: ActiveProject, card: Card) -> None:
        for entry in list(project.filled):
            if entry[1] is card:
                project.filled.remove(entry)
                owner = self.controller.get(card.uid, project.owner)
                self.players[owner].hand.append(card)
                return
        coop = project.coop
        if coop is not None and coop.shared is card:
            owner = self.controller.get(card.uid, project.owner)
            self.players[owner].hand.append(card)
            coop.shared = None
            coop.shared_family = None

    def _return_worst_factor(self, player: PlayerState) -> None:
        candidates = [
            (project, entry)
            for project in player.active
            for entry in project.filled
        ]
        if not candidates:
            return
        project, entry = min(candidates, key=lambda item: item[0].points)
        self._return_factor(project, entry[1])

    # ------------------------------------------------------------------ Kooperation

    def offer_cooperation(self, player: PlayerState) -> None:  # §11
        if not getattr(player.strategy, "coop", False):
            return
        mine = [
            project
            for project in player.active
            if project.coop is None and project.factor_count() <= 1
        ]
        if not mine:
            return
        partners = [other for other in self.players if other is not player]
        self.rng.shuffle(partners)
        for other in partners:
            if not getattr(other.strategy, "coop", False):
                continue
            if any(
                project.coop is not None and other.index in {p.owner for p in project.coop.projects}
                for project in player.active
            ):
                continue  # §11: je Personenpaar nur eine Kooperation
            for own in mine:
                for their in other.active:
                    if their.coop is not None or their.factor_count() > 1:
                        continue
                    shared = set(own.open_counts()) & set(their.open_counts())
                    if not shared:
                        continue
                    coop = Cooperation((own, their))
                    own.coop = coop
                    their.coop = coop
                    player.coops += 1
                    other.coops += 1
                    return

    # ------------------------------------------------------------------ Bewertung

    def plan_needs(self, player: PlayerState) -> Counter[str]:
        """Offene Anforderungen aller aktiven plus des geplanten Projekts."""

        need: Counter[str] = Counter()
        for project in player.active:
            need += project.open_counts()
        planned = player.strategy.planned_project(self, player)
        if planned is not None:
            need += Counter(planned.defn.requirements)
        return need

    def active_needs(self, player: PlayerState) -> Counter[str]:
        need: Counter[str] = Counter()
        for project in player.active:
            need += project.open_counts()
        return need

    def is_needed_now(self, player: PlayerState, card: Card) -> bool:
        """Schmerzhafter Abwurf: die Karte fehlt dem eigenen Plan.

        Auf aktive Projekte allein kann sich das nicht stützen — ein passender
        Faktor wird in Phase 2 immer angelegt und liegt beim Aufräumen gar nicht
        mehr auf der Hand. Gezählt wird deshalb gegen die offenen Anforderungen
        der aktiven Projekte plus des Projekts, das die Person als nächstes
        beginnen will.
        """

        if not card.defn.is_factor:
            return False
        need = self.plan_needs(player)
        covered: Counter[str] = Counter()
        for other in player.factors_in_hand():
            if other is card:
                continue
            for family in other.defn.families:
                if need[family] - covered[family] > 0:
                    covered[family] += 1
                    break
        return any(need[family] - covered[family] > 0 for family in card.defn.families)

    def card_value(self, player: PlayerState, card: Card) -> float:
        need = self.plan_needs(player)
        if card.defn.is_factor:
            hit = max((need[family] for family in card.defn.families), default=0)
            base = 10.0 if hit > 0 else 3.0
            return base + (0.5 if card.defn.is_wildcard else 0.0)
        if card.defn.is_project:
            # Das geplante Projekt steht über einem gebrauchten Faktor: ohne
            # Projekt sind die gesammelten Faktoren am Spielende wertlos.
            planned = player.strategy.planned_project(self, player)
            return 10.5 if planned is not None and planned is card else 2.0
        spec = card.defn.event
        return 6.0 if spec is not None and spec.template == "E8" else 5.0

    def count_options(self, player: PlayerState) -> int:
        options = len(self.legal_attachments(player))
        options += len(player.projects_in_hand()) if len(player.active) == 0 else 0
        options += len(self.legal_events(player))
        return options

    def can_complete_now(self, player: PlayerState, project_card: Card) -> bool:
        """Reicht die Hand, um dieses Projekt sofort abzuschließen?"""

        return can_satisfy(
            Counter(project_card.defn.requirements), player.factors_in_hand()
        )

    def _result(self) -> GameResult:
        results = []
        for player in self.players:
            plus = sum(card.defn.points for card in player.completed)
            minus = sum(self.rules.minus_points(project.points) for project in player.active)
            results.append(
                PlayerResult(
                    index=player.index,
                    strategy=player.strategy.name,
                    score=plus - minus,
                    plus=plus,
                    minus=minus,
                    completed=tuple(card.defn.points for card in player.completed),
                    unfinished=tuple(project.points for project in player.active),
                    first_start_round=player.first_start_round,
                    forced_discards=player.forced_discards,
                    painful_discards=player.painful_discards,
                    steals=player.steals,
                    self_recovers=player.self_recovers,
                    mean_options=(sum(player.options) / len(player.options))
                    if player.options
                    else 0.0,
                    coops=player.coops,
                    coops_closed=player.coops_closed,
                )
            )
        return GameResult(
            players=tuple(results),
            reshuffles=self.reshuffles,
            projects_seen=len(set(self.started_projects)),
            started_projects=tuple(self.started_projects),
            completed_projects=tuple(self.completed_projects),
        )


def play_game(rules: Rules, strategies: list[Any], seed: int) -> GameResult:
    return Game(rules, strategies, random.Random(seed)).play()
