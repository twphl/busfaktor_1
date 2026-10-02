from __future__ import annotations

import random
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sim.deck import (  # noqa: E402
    REPEAT_POLICIES,
    Card,
    CardDef,
    build_stage_set,
    can_satisfy,
    load_cards,
    parse_event,
)
from scripts.sim.engine import ActiveProject, Game, play_game  # noqa: E402
from scripts.sim.rules import RULE_VARIANTS, Rules  # noqa: E402
from scripts.sim.strategies import STRATEGIES, make_strategy  # noqa: E402


def factor(family: str, uid: int = 0) -> Card:
    return Card(uid, CardDef(f"X{uid}", f"F{uid}", "Projektfaktor", "common", families=(family,)))


def wildcard(families: tuple[str, ...], uid: int = 0) -> Card:
    return Card(uid, CardDef(f"W{uid}", f"W{uid}", "Projektfaktor", "uncommon", families=families))


def zone_counts(game: Game) -> Counter[int]:
    """Jede Karte genau einmal — über alle Zonen nach §14 gezählt."""

    counts: Counter[int] = Counter()
    for card in game.project_deck + game.action_deck + game.discard + game.consumed:
        counts[card.uid] += 1
    seen_coops: set[int] = set()
    for player in game.players:
        for card in player.hand + player.completed:
            counts[card.uid] += 1
        for project in player.active:
            counts[project.card.uid] += 1
            for _, card in project.filled:
                counts[card.uid] += 1
            for _, card in project.surcharges:
                counts[card.uid] += 1
            coop = project.coop
            if coop is not None and coop.shared is not None and id(coop) not in seen_coops:
                seen_coops.add(id(coop))
                counts[coop.shared.uid] += 1
    return counts


class StageSetTests(unittest.TestCase):
    def test_stage_set_is_74_cards(self) -> None:
        stage = build_stage_set("commons")
        self.assertEqual(len(stage.projects), 16)
        self.assertEqual(len(stage.factors), 46)
        self.assertEqual(len(stage.events), 12)
        self.assertEqual(len(stage.projects) + len(stage.actions), 74)

    def test_every_repeat_policy_keeps_the_slot_count(self) -> None:
        for policy in REPEAT_POLICIES:
            stage = build_stage_set(policy)
            expected = 38 if policy == "none" else 46
            self.assertEqual(len(stage.factors), expected, policy)
            self.assertEqual(len(stage.repeated_ids), expected - 38, policy)

    def test_requirements_policy_follows_project_demand(self) -> None:
        stage = build_stage_set("requirements")
        families = stage.family_counts()
        demand = Counter(req for card in stage.projects for req in card.defn.requirements)
        # Team ist der meistgeforderte Faktortyp und muss die meisten Faktoren haben.
        self.assertEqual(max(demand, key=demand.get), "team")
        self.assertEqual(
            max(("team", "data", "operations", "methods"), key=lambda f: families[f]), "team"
        )

    def test_all_stage_events_are_supported(self) -> None:
        self.assertEqual(build_stage_set("commons").unsupported, ())

    def test_projects_score_their_requirement_count(self) -> None:
        for card in build_stage_set("commons").projects:
            self.assertEqual(card.defn.points, len(card.defn.requirements), card.card_id)

    def test_wildcards_expose_both_families(self) -> None:
        wildcards = [
            card.defn
            for card in build_stage_set("commons").factors
            if card.defn.is_wildcard
        ]
        self.assertEqual(len(wildcards), 2)
        for card in wildcards:
            self.assertEqual(len(card.families), 2)


class EventParsingTests(unittest.TestCase):
    def test_stage_event_templates(self) -> None:
        specs = {
            card.card_id: card.defn.event for card in build_stage_set("commons").events
        }
        self.assertEqual(specs["KAT-C03"].template, "E6")
        self.assertEqual(specs["KAT-C03"].families, ("team",))
        self.assertEqual(specs["KAT-C08"].families, ("data",))
        self.assertEqual(specs["KAT-C17"].families, ("operations",))
        self.assertEqual(specs["KAT-C25"].look, 3)
        self.assertEqual(specs["KAT-C25"].take, 1)
        self.assertEqual(specs["KAT-U26"].take, 2)
        self.assertEqual(specs["KAT-U02"].chooser, "target")
        self.assertEqual(specs["KAT-R16"].scope, "all")
        self.assertEqual(specs["KAT-R06"].counters, "rueckschlag")

    def test_joker_without_named_family_allows_all_four(self) -> None:
        spec = parse_event("E5", "Es erfüllt eine Anforderung eines Faktortyps deiner Wahl.")
        self.assertEqual(len(spec.families), 4)

    def test_mythic_joker_keeps_its_two_families(self) -> None:
        spec = parse_event("E5", "Es erfüllt eine Team- oder Daten-Anforderung.")
        self.assertEqual(spec.families, ("team", "data"))

    def test_every_playable_event_parses(self) -> None:
        events = [card for card in load_cards() if card.is_event]
        self.assertEqual(len(events), 28)
        for card in events:
            self.assertIsNotNone(card.event)
            self.assertIn(card.event.template, {f"E{index}" for index in range(1, 9)})


class MatchingTests(unittest.TestCase):
    def test_two_identical_symbols_need_two_cards(self) -> None:
        need = Counter({"data": 2})
        self.assertFalse(can_satisfy(need, [factor("data", 1)]))
        self.assertTrue(can_satisfy(need, [factor("data", 1), factor("data", 2)]))

    def test_wildcard_fills_the_gap(self) -> None:
        need = Counter({"team": 1, "methods": 1})
        cards = [factor("team", 1), wildcard(("team", "methods"), 2)]
        self.assertTrue(can_satisfy(need, cards))

    def test_wildcard_backtracks_to_the_second_family(self) -> None:
        need = Counter({"data": 1, "methods": 1})
        cards = [wildcard(("data", "methods"), 1), wildcard(("data", "methods"), 2)]
        self.assertTrue(can_satisfy(need, cards))
        self.assertFalse(can_satisfy(Counter({"team": 2}), cards))


class ProjectMathTests(unittest.TestCase):
    def make_project(self, requirements: tuple[str, ...]) -> ActiveProject:
        card = Card(99, CardDef("P", "P", "Projekt", "rare", requirements=requirements,
                                points=len(requirements)))
        return ActiveProject(card, owner=0, started_turn=0)

    def test_double_symbol_needs_two_physical_factors(self) -> None:
        project = self.make_project(("data", "data"))
        project.filled.append(("data", factor("data", 1)))
        self.assertFalse(project.is_complete())
        project.filled.append(("data", factor("data", 2)))
        self.assertTrue(project.is_complete())

    def test_surcharge_adds_a_requirement(self) -> None:
        project = self.make_project(("team",))
        project.filled.append(("team", factor("team", 1)))
        self.assertTrue(project.is_complete())
        project.surcharges.append(("team", factor("team", 2)))
        self.assertFalse(project.is_complete())
        self.assertEqual(project.open_counts()["team"], 1)


class RulesTests(unittest.TestCase):
    def test_minus_modes(self) -> None:
        self.assertEqual([Rules().minus_points(p) for p in (2, 3, 4)], [2, 3, 4])
        half = Rules(minus_mode="half")
        self.assertEqual([half.minus_points(p) for p in (2, 3, 4)], [1, 2, 2])
        flat = Rules(minus_mode="flat1")
        self.assertEqual([flat.minus_points(p) for p in (2, 3, 4)], [1, 1, 1])

    def test_all_variants_build(self) -> None:
        for name, changes in RULE_VARIANTS.items():
            self.assertIsInstance(Rules().with_(**changes), Rules, name)


class GameTests(unittest.TestCase):
    def strategies(self, name: str = "open-2-safe", count: int = 4) -> list:
        return [make_strategy(name) for _ in range(count)]

    def test_cards_are_conserved(self) -> None:
        for seed in range(25):
            game = Game(Rules(), self.strategies(), random.Random(seed))
            total_before = zone_counts(game)
            game.play()
            counts = zone_counts(game)
            self.assertEqual(sum(total_before.values()), 74)
            self.assertEqual(sum(counts.values()), 74, f"seed {seed}")
            self.assertTrue(all(value == 1 for value in counts.values()), f"seed {seed}")

    def test_cards_are_conserved_with_cooperation(self) -> None:
        rules = Rules(cooperation=True)
        for seed in range(15):
            game = Game(rules, [make_strategy("coop") for _ in range(4)],
                        random.Random(seed))
            game.play()
            counts = zone_counts(game)
            self.assertEqual(sum(counts.values()), 74, f"seed {seed}")
            self.assertTrue(all(value == 1 for value in counts.values()), f"seed {seed}")

    def test_same_seed_gives_same_result(self) -> None:
        first = play_game(Rules(), self.strategies(), 4711)
        second = play_game(Rules(), self.strategies(), 4711)
        self.assertEqual(
            [player.score for player in first.players],
            [player.score for player in second.players],
        )

    def test_score_is_plus_minus_minus(self) -> None:
        result = play_game(Rules(), self.strategies(), 17)
        for player in result.players:
            self.assertEqual(player.score, player.plus - player.minus)
            self.assertEqual(player.plus, sum(player.completed))
            self.assertEqual(player.minus, sum(player.unfinished))

    def test_forced_start_puts_a_project_on_the_table_in_round_one(self) -> None:
        # §8.1: mit einem Projekt auf der Starthand ist der Start in Runde 1 Pflicht.
        for seed in range(10):
            result = play_game(Rules(forced_start=True), self.strategies(), seed)
            for player in result.players:
                self.assertEqual(player.first_start_round, 1, f"seed {seed}")

    def test_hoarding_delays_the_first_project_without_the_rule(self) -> None:
        rules = Rules(forced_start=False)
        rounds = []
        for seed in range(40):
            result = play_game(rules, [make_strategy("hoard") for _ in range(4)], seed)
            rounds += [player.first_start_round or 7 for player in result.players]
        self.assertGreater(sum(rounds) / len(rounds), 1.5)

    def test_hand_limit_is_enforced_at_end_of_turn(self) -> None:
        rules = Rules(hand_limit=3)
        for seed in range(10):
            game = Game(rules, self.strategies(), random.Random(seed))
            for player in game.players:
                game.take_turn(player)
                self.assertLessEqual(game.hand_size(player), rules.hand_limit, f"seed {seed}")

    def test_projects_outside_the_limit_are_not_counted(self) -> None:
        rules = Rules(projects_count_toward_limit=False, hand_limit=2)
        game = Game(rules, self.strategies(), random.Random(3))
        player = game.players[0]
        game.take_turn(player)
        non_projects = [card for card in player.hand if not card.defn.is_project]
        self.assertLessEqual(len(non_projects), 2)

    def test_no_events_variant_removes_them_from_the_deck(self) -> None:
        game = Game(Rules(events=False), self.strategies(), random.Random(1))
        cards = game.action_deck + [card for player in game.players for card in player.hand]
        self.assertTrue(all(not card.defn.is_event for card in cards))

    def test_every_strategy_plays_a_full_game(self) -> None:
        for name in STRATEGIES:
            result = play_game(Rules(cooperation=True), [make_strategy(name) for _ in range(4)], 5)
            self.assertEqual(len(result.players), 4)

    def test_winner_has_the_highest_score(self) -> None:
        result = play_game(Rules(), self.strategies(), 99)
        best = max(player.score for player in result.players)
        for index in result.winners:
            self.assertEqual(result.players[index].score, best)


if __name__ == "__main__":
    unittest.main()
