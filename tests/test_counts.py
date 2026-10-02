from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import print_run  # noqa: E402
from scripts.collate_boosters import collate, load_cards  # noqa: E402
from scripts.validate_cards import (  # noqa: E402
    EDITORIAL_TAGS,
    MAX_EDITORIAL_TAGS,
    NEGATIVE_EVENT_TEMPLATES,
)

# Seit ADR 0019 gibt es zwei Auflagen. Die Motivtests gelten für beide, die
# Kollationstests laufen gegen jede einzeln.
PRINT_RUNS = ("612-plus-18", "234-plus-18")


class CardCountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with (ROOT / "data" / "cards.csv").open(encoding="utf-8", newline="") as handle:
            cls.rows = list(csv.DictReader(handle))

    def test_motif_counts(self) -> None:
        counts = Counter(row["rarity"] for row in self.rows)
        self.assertEqual(counts["common"], 28)
        self.assertEqual(counts["uncommon"], 27)
        self.assertEqual(counts["rare"], 18)
        self.assertEqual(counts["mythic"], 9)
        self.assertEqual(len(self.rows), 82)

    def test_booster_copies_fill_every_pack_slot(self) -> None:
        # `booster_copies` ist seit ADR 0019 keine Spalte mehr, sondern wird
        # aus der Packstruktur des Auflagenprofils abgeleitet. Die Ableitung
        # muss die Slots exakt füllen — keine Karte zu viel, keine zu wenig.
        cards = {row["card_id"]: row for row in self.rows}
        for name in PRINT_RUNS:
            with self.subTest(print_run=name):
                run = print_run.load(name)
                copies = run.booster_copies(cards)
                self.assertEqual(sum(copies.values()), run.packs * print_run.CARDS_PER_PACK)
                foil = sum(c for cid, c in copies.items() if cards[cid]["foil_only"] == "true")
                self.assertEqual(foil, run.foil_in_circulation)

    def test_612_derivation_matches_the_historic_column(self) -> None:
        # Regression: Vor ADR 0019 stand die Kopienzahl in der CSV, konstant je
        # Seltenheit. Die Ableitung muss diesen Stand exakt reproduzieren,
        # sonst ist der alte Druckplan nicht mehr derselbe.
        historic = {"common": 9, "uncommon": 4, "rare": 3, "mythic": 2}
        cards = {row["card_id"]: row for row in self.rows}
        copies = print_run.load("612-plus-18").booster_copies(cards)
        for card_id, card in cards.items():
            self.assertEqual(copies[card_id], historic[card["rarity"]], card_id)

    def test_all_mythics_are_foil_only(self) -> None:
        for row in self.rows:
            if row["rarity"] == "mythic":
                self.assertEqual(row["foil_only"], "true")

    def test_phylo_card_type_counts(self) -> None:
        self.assertEqual(
            Counter(row["card_type"] for row in self.rows),
            Counter({"Projekt": 16, "Projektfaktor": 38, "Ereignis": 28}),
        )

    def test_negative_events_have_visible_negative_templates(self) -> None:
        events = [row for row in self.rows if row["card_type"] == "Ereignis"]
        for row in events:
            self.assertEqual(
                row["polarity"] == "negative",
                row["effect_template"] in NEGATIVE_EVENT_TEMPLATES,
                row["card_id"],
            )

    def test_booster_functional_profiles(self) -> None:
        # Das Funktionsprofil 2/7/3 je Pack gilt in jeder Auflage; nur die
        # Anzahl der Packs unterscheidet sie.
        for name in PRINT_RUNS:
            with self.subTest(print_run=name):
                run = print_run.load(name)
                cards = load_cards(run)
                packs, summary = collate(20260804, run)
                self.assertEqual(summary["cards"], run.packs * print_run.CARDS_PER_PACK)
                self.assertEqual(summary["print_run"], name)
                self.assertEqual(
                    sum(summary["card_types"].values()),
                    run.packs * print_run.CARDS_PER_PACK,
                )
                self.assertEqual(
                    summary["card_types"],
                    {
                        "Projekt": run.packs * 2,
                        "Projektfaktor": run.packs * 7,
                        "Ereignis": run.packs * 3,
                    },
                )

                for pack in packs:
                    entries = pack["cards"]
                    self.assertEqual(len(entries), 12)
                    self.assertEqual(len({entry["card_id"] for entry in entries}), 12)
                    self.assertEqual(
                        Counter(entry["card_type"] for entry in entries),
                        Counter({"Projekt": 2, "Projektfaktor": 7, "Ereignis": 3}),
                    )
                    common_families = {
                        cards[entry["card_id"]]["factor_family"]
                        for entry in entries
                        if entry["rarity"] == "common"
                        and entry["card_type"] == "Projektfaktor"
                    }
                    self.assertTrue(
                        {"team", "data", "operations", "methods"} <= common_families
                    )

    def test_editorial_tags_follow_the_documented_vocabulary(self) -> None:
        used = set()
        for row in self.rows:
            tags = row["editorial_tags"].split("+") if row["editorial_tags"] else []
            self.assertLessEqual(len(tags), MAX_EDITORIAL_TAGS, row["card_id"])
            self.assertEqual(len(set(tags)), len(tags), row["card_id"])
            self.assertLessEqual(set(tags), set(EDITORIAL_TAGS), row["card_id"])
            self.assertEqual(tags, sorted(tags, key=EDITORIAL_TAGS.index), row["card_id"])
            used.update(tags)
        self.assertEqual(used, set(EDITORIAL_TAGS))

    def test_editorial_tags_are_not_a_game_resource(self) -> None:
        # Sie dürfen weder in die Boosterkollation noch in gerenderte Felder
        # gelangen, siehe docs/13-redaktionelle-tags.md.
        run = print_run.load(print_run.DEFAULT)
        _, summary = collate(20260804, run)
        self.assertNotIn("editorial_tags", summary)
        boosters = ROOT / "build" / f"boosters-{run.name}.csv"
        with boosters.open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
        self.assertNotIn("editorial_tags", header)

    def test_collation_is_reproducible_for_same_seed(self) -> None:
        for name in PRINT_RUNS:
            with self.subTest(print_run=name):
                run = print_run.load(name)
                first, _ = collate(17, run)
                second, _ = collate(17, run)
                self.assertEqual(first, second)

    def test_every_motif_is_printed_in_every_run(self) -> None:
        # Ein Motiv darf aus dem Boosterpool fallen (ADR 0019), aber nicht aus
        # dem Druck: dann muss es im Bühnensatz liegen oder ein Foil-Mythic
        # sein, der am Foilauftrag hängt.
        cards = {row["card_id"]: row for row in self.rows}
        for name in PRINT_RUNS:
            with self.subTest(print_run=name):
                run = print_run.load(name)
                copies = run.booster_copies(cards)
                for card_id, card in cards.items():
                    if card["foil_only"] == "true":
                        continue
                    in_stage = run.stage_sets > 0 and card["stage_candidate"] == "true"
                    self.assertTrue(copies[card_id] > 0 or in_stage, card_id)


if __name__ == "__main__":
    unittest.main()
