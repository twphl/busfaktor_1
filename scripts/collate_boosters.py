#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

# Damit `print_run` sowohl beim direkten Aufruf (python3 scripts/...) als auch
# beim Import als `scripts.collate_boosters` (Tests) gefunden wird.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import print_run  # noqa: E402
from print_run import (  # noqa: E402
    CARDS_PER_PACK,
    FUNCTIONAL_SLOTS,
    GROUND_FAMILIES,
    RARITY_SLOTS,
    PrintRun,
)

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards.csv"
BUILD = ROOT / "build"


def load_cards(run: PrintRun) -> dict[str, dict[str, str]]:
    """Motive aus der CSV, Kopienzahlen aus dem Auflagenprofil.

    `booster_copies` ist seit ADR 0019 keine Spalte mehr, sondern wird aus der
    Packstruktur abgeleitet (siehe `print_run`).  Sie wird hier ins Kartendict
    geschrieben, damit der Verteilalgorithmus unverändert damit arbeitet.
    Motive ohne Boosterkarte fallen aus dem Pool.
    """
    with CARDS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    cards = {row["card_id"]: row for row in sorted(rows, key=lambda row: row["card_id"])}
    copies = run.booster_copies(cards)
    for card_id, card in cards.items():
        card["booster_copies"] = str(copies[card_id])
    return {card_id: card for card_id, card in cards.items() if copies[card_id] > 0}


def domain_key(card: dict[str, str]) -> tuple[str, ...]:
    result = [card["domain_primary"]]
    if card["domain_secondary"]:
        result.append(card["domain_secondary"])
    return tuple(result)


def card_ids_for(
    cards: dict[str, dict[str, str]],
    *,
    rarity: str,
    card_type: str,
    factor_family: str | None = None,
) -> list[str]:
    return [
        card_id
        for card_id, card in cards.items()
        if card["rarity"] == rarity
        and card["card_type"] == card_type
        and (factor_family is None or card["factor_family"] == factor_family)
    ]


def deal_to_slots(
    *,
    group: str,
    card_ids: list[str],
    slots: list[int],
    cards: dict[str, dict[str, str]],
    packs: list[dict],
    rng: random.Random,
    candidate_allowed: Callable[[str, dict], bool] | None = None,
) -> None:
    base_pool = Counter(
        {
            card_id: int(cards[card_id]["booster_copies"])
            for card_id in card_ids
        }
    )
    if sum(base_pool.values()) != len(slots):
        raise RuntimeError(
            f"{group}: {sum(base_pool.values())} cards for {len(slots)} slots"
        )

    for _attempt in range(1_000):
        for pack in packs:
            pack["cards"] = [entry for entry in pack["cards"] if entry["group"] != group]

        remaining = base_pool.copy()
        shuffled_slots = slots.copy()
        rng.shuffle(shuffled_slots)
        failed = False

        for pack_index in shuffled_slots:
            pack = packs[pack_index]
            existing_ids = {entry["card_id"] for entry in pack["cards"]}
            domain_counts = Counter(
                domain
                for entry in pack["cards"]
                for domain in domain_key(cards[entry["card_id"]])
            )
            candidates = [
                card_id
                for card_id in sorted(remaining)
                if remaining[card_id] > 0
                and card_id not in existing_ids
                and (candidate_allowed is None or candidate_allowed(card_id, pack))
            ]
            if not candidates:
                failed = True
                break

            def score(card_id: str) -> tuple[int, int, float]:
                domain_penalty = sum(domain_counts[d] for d in domain_key(cards[card_id]))
                return (-remaining[card_id], domain_penalty, rng.random())

            selected = min(candidates, key=score)
            remaining[selected] -= 1
            card = cards[selected]
            pack["cards"].append(
                {
                    "card_id": selected,
                    "rarity": card["rarity"],
                    "card_type": card["card_type"],
                    "group": group,
                }
            )

        if not failed and not any(remaining.values()):
            return

    raise RuntimeError(f"Could not collate {group} after 1,000 attempts")


def deal_common_factors(
    cards: dict[str, dict[str, str]],
    packs: list[dict],
    rng: random.Random,
    run: PrintRun,
) -> None:
    # Every pack gets one common factor from every ground family. The fifth
    # slot rotates evenly across all packs; with 36 packs that is nine bonus
    # slots per family, with 13 it is four for the first family and three for
    # the rest.
    bonus_counts = {
        family: slots - len(packs) for family, slots in run.common_factor_slots().items()
    }
    bonus_families = [family for family, count in bonus_counts.items() for _ in range(count)]
    rng.shuffle(bonus_families)
    bonus_packs = {
        family: [index for index, assigned in enumerate(bonus_families) if assigned == family]
        for family in GROUND_FAMILIES
    }

    for family in GROUND_FAMILIES:
        slots = list(range(len(packs))) + bonus_packs[family]
        deal_to_slots(
            group=f"common-factor-{family}",
            card_ids=card_ids_for(
                cards,
                rarity="common",
                card_type="Projektfaktor",
                factor_family=family,
            ),
            slots=slots,
            cards=cards,
            packs=packs,
            rng=rng,
        )


def deal_functional_groups(
    cards: dict[str, dict[str, str]],
    packs: list[dict],
    rng: random.Random,
    run: PrintRun,
) -> None:
    all_packs = list(range(len(packs)))
    normal_packs = [index for index, pack in enumerate(packs) if pack["pack_type"] == "normal"]
    special_packs = [index for index, pack in enumerate(packs) if pack["pack_type"] == "special"]

    deal_common_factors(cards, packs, rng, run)

    groups = (
        ("common-project", "common", "Projekt", all_packs, 1),
        ("common-event", "common", "Ereignis", all_packs, 1),
        ("uncommon-event", "uncommon", "Ereignis", all_packs, 1),
        ("rare-project", "rare", "Projekt", all_packs, 1),
        ("rare-event", "rare", "Ereignis", normal_packs, 1),
        ("mythic-event", "mythic", "Ereignis", special_packs, 1),
    )
    for group, rarity, card_type, pack_indices, slots_per_pack in groups:
        deal_to_slots(
            group=group,
            card_ids=card_ids_for(cards, rarity=rarity, card_type=card_type),
            slots=[index for index in pack_indices for _ in range(slots_per_pack)],
            cards=cards,
            packs=packs,
            rng=rng,
        )

    def uncommon_factor_allowed(card_id: str, pack: dict) -> bool:
        if cards[card_id]["factor_family"] != "wildcard":
            return True
        return not any(
            entry["rarity"] == "uncommon"
            and entry["card_type"] == "Projektfaktor"
            and cards[entry["card_id"]]["factor_family"] == "wildcard"
            for entry in pack["cards"]
        )

    deal_to_slots(
        group="uncommon-factor",
        card_ids=card_ids_for(cards, rarity="uncommon", card_type="Projektfaktor"),
        slots=[index for index in all_packs for _ in range(2)],
        cards=cards,
        packs=packs,
        rng=rng,
        candidate_allowed=uncommon_factor_allowed,
    )


def validate_collation(
    packs: list[dict], cards: dict[str, dict[str, str]], run: PrintRun
) -> None:
    if len(packs) != run.packs:
        raise RuntimeError(f"Expected {run.packs} packs, got {len(packs)}")
    expected_types = Counter({"normal": run.normal_packs, "special": run.special_packs})
    if Counter(pack["pack_type"] for pack in packs) != expected_types:
        raise RuntimeError(
            f"Pack-type count differs from {run.normal_packs} normal "
            f"and {run.special_packs} special"
        )

    actual_copies = Counter()
    for pack in packs:
        entries = pack["cards"]
        if len(entries) != CARDS_PER_PACK:
            raise RuntimeError(f"{pack['pack_id']} has {len(entries)} cards")
        ids = [entry["card_id"] for entry in entries]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{pack['pack_id']} contains a duplicate card ID")
        actual_copies.update(ids)

        rarity_counts = Counter(entry["rarity"] for entry in entries)
        if rarity_counts != Counter(RARITY_SLOTS[pack["pack_type"]]):
            raise RuntimeError(
                f"{pack['pack_id']} has invalid rarities: {dict(rarity_counts)}"
            )
        functional_counts = Counter(
            (entry["rarity"], entry["card_type"]) for entry in entries
        )
        if functional_counts != Counter(FUNCTIONAL_SLOTS[pack["pack_type"]]):
            raise RuntimeError(
                f"{pack['pack_id']} has invalid functional slots: {dict(functional_counts)}"
            )
        type_counts = Counter(entry["card_type"] for entry in entries)
        if type_counts != Counter({"Projekt": 2, "Projektfaktor": 7, "Ereignis": 3}):
            raise RuntimeError(f"{pack['pack_id']} has invalid type profile: {dict(type_counts)}")

        common_factors = [
            cards[entry["card_id"]]
            for entry in entries
            if entry["rarity"] == "common" and entry["card_type"] == "Projektfaktor"
        ]
        common_family_counts = Counter(card["factor_family"] for card in common_factors)
        if any(common_family_counts[family] < 1 for family in GROUND_FAMILIES):
            raise RuntimeError(
                f"{pack['pack_id']} lacks a common ground family: {dict(common_family_counts)}"
            )
        if set(common_family_counts) - set(GROUND_FAMILIES):
            raise RuntimeError(f"{pack['pack_id']} has an invalid common wildcard")

        uncommon_wildcards = sum(
            entry["rarity"] == "uncommon"
            and entry["card_type"] == "Projektfaktor"
            and cards[entry["card_id"]]["factor_family"] == "wildcard"
            for entry in entries
        )
        if uncommon_wildcards > 1:
            raise RuntimeError(f"{pack['pack_id']} contains two uncommon wildcards")

        mythics = [entry for entry in entries if entry["rarity"] == "mythic"]
        if any(cards[entry["card_id"]]["foil_only"] != "true" for entry in mythics):
            raise RuntimeError(f"{pack['pack_id']} contains a non-foil mythic")

    expected_copies = Counter(
        {
            card_id: int(card["booster_copies"])
            for card_id, card in cards.items()
        }
    )
    if actual_copies != expected_copies:
        missing = expected_copies - actual_copies
        extra = actual_copies - expected_copies
        raise RuntimeError(
            f"Card-copy totals differ; missing={dict(missing)}, extra={dict(extra)}"
        )


def collate(seed: int, run: PrintRun) -> tuple[list[dict], dict]:
    cards = load_cards(run)
    rng = random.Random(seed)
    pack_types = run.pack_specs()
    rng.shuffle(pack_types)
    packs = [
        {"pack_id": f"KAT-P{index + 1:02d}", "pack_type": pack_type, "cards": []}
        for index, pack_type in enumerate(pack_types)
    ]

    deal_functional_groups(cards, packs, rng, run)
    validate_collation(packs, cards, run)

    type_order = {"Projekt": 0, "Projektfaktor": 1, "Ereignis": 2}
    rarity_order = {"common": 0, "uncommon": 1, "rare": 2, "mythic": 3}
    for pack in packs:
        pack["cards"].sort(
            key=lambda entry: (
                type_order[entry["card_type"]],
                rarity_order[entry["rarity"]],
                entry["card_id"],
            )
        )

    entries = [entry for pack in packs for entry in pack["cards"]]
    summary = {
        "print_run": run.name,
        "adr": run.adr,
        "seed": seed,
        "packs": len(packs),
        "normal_packs": sum(pack["pack_type"] == "normal" for pack in packs),
        "special_packs": sum(pack["pack_type"] == "special" for pack in packs),
        "cards": len(entries),
        "rarities": dict(sorted(Counter(entry["rarity"] for entry in entries).items())),
        "card_types": dict(sorted(Counter(entry["card_type"] for entry in entries).items())),
        "factor_families": dict(
            sorted(
                Counter(
                    cards[entry["card_id"]]["factor_family"]
                    for entry in entries
                    if entry["card_type"] == "Projektfaktor"
                ).items()
            )
        ),
        "domains": dict(
            sorted(Counter(cards[entry["card_id"]]["domain_primary"] for entry in entries).items())
        ),
        "checks": {
            "functional_profile_per_pack": "2 projects / 7 project factors / 3 events",
            "all_ground_families_per_pack": True,
            "duplicate_ids_within_pack": False,
            "exact_card_copy_counts": True,
        },
    }
    return packs, summary


def write_output(packs: list[dict], summary: dict, run: PrintRun) -> None:
    cards = load_cards(run)
    BUILD.mkdir(exist_ok=True)
    with (BUILD / f"boosters-{run.name}.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "pack_id",
            "pack_type",
            "slot",
            "rarity",
            "foil",
            "card_type",
            "factor_family",
            "polarity",
            "effect_template",
            "card_id",
            "name",
            "domain_primary",
            "domain_secondary",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for pack in packs:
            for slot, entry in enumerate(pack["cards"], 1):
                card = cards[entry["card_id"]]
                writer.writerow(
                    {
                        "pack_id": pack["pack_id"],
                        "pack_type": pack["pack_type"],
                        "slot": slot,
                        "rarity": entry["rarity"],
                        "foil": card["foil_only"],
                        "card_type": card["card_type"],
                        "factor_family": card["factor_family"],
                        "polarity": card["polarity"],
                        "effect_template": card["effect_template"],
                        "card_id": entry["card_id"],
                        "name": card["name"],
                        "domain_primary": card["domain_primary"],
                        "domain_secondary": card["domain_secondary"],
                    }
                )
    (BUILD / f"booster-summary-{run.name}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Collate KAT-01 Phylo-style boosters")
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument(
        "--print-run",
        default=print_run.DEFAULT,
        help="Auflagenprofil aus data/print_runs (Standard: %(default)s)",
    )
    args = parser.parse_args()
    run = print_run.load(args.print_run)
    packs, summary = collate(args.seed, run)
    write_output(packs, summary, run)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
