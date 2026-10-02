#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
import sys

# Damit `print_run` sowohl beim direkten Aufruf (python3 scripts/...) als auch
# beim Import als `scripts.validate_cards` (Tests) gefunden wird.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import print_run  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards.csv"

EXPECTED_MOTIFS = {
    "common": 28,
    "uncommon": 27,
    "rare": 18,
    "mythic": 9,
}
# Kopienzahlen stehen seit ADR 0019 nicht mehr in der CSV: sie hängen an der
# Auflage, das Motiv nicht. Sie kommen aus `data/print_runs/` über `print_run`.
PLAYABLE_RARITIES = ("common", "uncommon", "rare", "mythic")
EXPECTED_TYPES = {"Projekt": 16, "Projektfaktor": 38, "Ereignis": 28}
EXPECTED_RARITY_TYPES = {
    ("common", "Projekt"): 4,
    ("common", "Projektfaktor"): 20,
    ("common", "Ereignis"): 4,
    ("uncommon", "Projektfaktor"): 18,
    ("uncommon", "Ereignis"): 9,
    ("rare", "Projekt"): 12,
    ("rare", "Ereignis"): 6,
    ("mythic", "Ereignis"): 9,
}
EXPECTED_FACTOR_FAMILIES = {
    "team": 9,
    "data": 9,
    "operations": 9,
    "methods": 9,
    "wildcard": 2,
}
EXPECTED_EVENT_POLARITIES = {"negative": 12, "positive": 15, "ambivalent": 1}
NEGATIVE_EVENT_TEMPLATES = {"E6", "E7"}
EXPECTED_EFFECT_TEMPLATES = {
    "E1": 1,
    "E2": 2,
    "E3": 3,
    "E4": 2,
    "E5": 5,
    "E6": 5,
    "E7": 7,
    "E8": 3,
}
# Nach der Balance-Korrektur an C11, C18, R09 und R12 (Doppelsymbole kosten
# Ziehaufwand, ohne bezahlt zu werden). Die Verteilung ist bewusst nicht mehr
# gleichmäßig; die acht Zusatzkopien im Bühnensatz müssen sie spiegeln.
EXPECTED_PROJECT_REQUIREMENTS = {
    "team": 15,
    "data": 12,
    "operations": 11,
    "methods": 13,
}
EXPECTED_STAGE_EVENTS = {
    "KAT-C03",
    "KAT-C08",
    "KAT-C17",
    "KAT-C25",
    "KAT-U02",
    "KAT-U22",
    "KAT-U26",
    "KAT-U27",
    "KAT-R02",
    "KAT-R06",
    "KAT-R15",
    "KAT-R16",
}
# ADR 0009: der Bühnensatz braucht 46 Projektfaktoren, es gibt nur 38 Motive.
# Die acht Zusatzkopien spiegeln EXPECTED_PROJECT_REQUIREMENTS statt einer
# gleichmäßigen Verteilung, siehe docs/adr/0009-stage-factor-repeats.md.
EXPECTED_STAGE_REPEATED_FACTORS = {
    "KAT-C01",
    "KAT-C04",
    "KAT-C05",
    "KAT-C09",
    "KAT-C10",
    "KAT-C15",
    "KAT-C21",
    "KAT-C23",
}
EXPECTED_STAGE_FACTOR_FAMILIES = {
    "team": 12,
    "data": 11,
    "operations": 10,
    "methods": 11,
    "wildcard": 2,
}
REQUIRED_COLUMNS = {
    "card_id",
    "name",
    "domain_primary",
    "editorial_tags",
    "rarity",
    "card_type",
    "factor_family",
    "target_family",
    "polarity",
    "effect_template",
    "requirements",
    "points",
    "project_goal",
    "foil_only",
    "stage_candidate",
    "stage_copies",
    "motif_origin",
    "visual_motif",
    "mechanical_role",
    "rules_text",
    "flavor_text",
    "test_notes",
}
VALID_DOMAINS = {"team", "data", "operations", "methods", "neutral"}
# Redaktionelle Sekundärtags, siehe docs/13-redaktionelle-tags.md. Sie sind
# kein fünfter Faktortyp und keine Spielressource: sie werden nicht gedruckt,
# nicht simuliert und nicht boostergewichtet. Die Reihenfolge ist verbindlich,
# damit Diffs stabil bleiben.
EDITORIAL_TAGS = (
    "rights",
    "access",
    "accessibility",
    "participation",
    "provenance",
    "care",
    "labor",
    "interpretation",
)
MAX_EDITORIAL_TAGS = 3
VALID_REQUIREMENTS = {"team", "data", "operations", "methods"}
FACTOR_DOMAINS = {
    "team": "team",
    "data": "data",
    "operations": "operations",
    "methods": "methods",
    "wildcard": "neutral",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_blank(row: dict[str, str], fields: tuple[str, ...]) -> None:
    populated = [field for field in fields if row[field]]
    if populated:
        fail(f"{row['card_id']}: fields must be blank for {row['card_type']}: {populated}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the canonical KAT-01 card data")
    parser.add_argument(
        "--print-run",
        default=print_run.DEFAULT,
        help="Auflagenprofil aus data/print_runs (Standard: %(default)s)",
    )
    run = print_run.load(parser.parse_args().print_run)

    with CARDS.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing_columns:
            fail(f"missing columns: {sorted(missing_columns)}")
        rows = list(reader)

    ids = [row["card_id"] for row in rows]
    duplicates = [card_id for card_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        fail(f"duplicate card IDs: {duplicates}")

    names = [row["name"] for row in rows]
    duplicate_names = [name for name, count in Counter(names).items() if count > 1]
    if duplicate_names:
        fail(f"duplicate card names: {duplicate_names}")

    rarity_counts = Counter(row["rarity"] for row in rows)
    if rarity_counts != Counter(EXPECTED_MOTIFS):
        fail(f"motif counts differ: expected {EXPECTED_MOTIFS}, got {dict(rarity_counts)}")

    playable = [row for row in rows if row["rarity"] in PLAYABLE_RARITIES]
    if len(playable) != len(rows):
        stray = sorted(row["card_id"] for row in rows if row not in playable)
        fail(f"every motif must be a booster motif since the player aids were dropped: {stray}")

    for row in rows:
        card_id = row["card_id"]
        flavor_text = row["flavor_text"]
        if flavor_text is None:
            fail(f"{card_id}: flavor_text field is missing from the row")
        if flavor_text and not flavor_text.strip():
            fail(f"{card_id}: flavor_text must be empty or contain visible text")
        for field in ("card_id", "name", "domain_primary", "rarity", "card_type"):
            if not row[field]:
                fail(f"{card_id or '<unknown>'}: required field {field} is blank")

        rarity = row["rarity"]

        if row["domain_primary"] not in VALID_DOMAINS:
            fail(f"{card_id}: invalid primary domain {row['domain_primary']}")
        if row["domain_secondary"] and row["domain_secondary"] not in VALID_DOMAINS - {"neutral"}:
            fail(f"{card_id}: invalid secondary domain {row['domain_secondary']}")
        tags = row["editorial_tags"].split("+") if row["editorial_tags"] else []
        unknown = [tag for tag in tags if tag not in EDITORIAL_TAGS]
        if unknown:
            fail(f"{card_id}: unknown editorial tags {unknown}")
        if len(set(tags)) != len(tags):
            fail(f"{card_id}: duplicate editorial tags {row['editorial_tags']}")
        if len(tags) > MAX_EDITORIAL_TAGS:
            fail(f"{card_id}: at most {MAX_EDITORIAL_TAGS} editorial tags per card")
        if tags != sorted(tags, key=EDITORIAL_TAGS.index):
            fail(f"{card_id}: editorial tags must follow the documented order {list(EDITORIAL_TAGS)}")
        if row["foil_only"] not in {"true", "false"}:
            fail(f"{card_id}: foil_only must be true or false")
        if row["stage_candidate"] not in {"true", "false"}:
            fail(f"{card_id}: stage_candidate must be true or false")
        wants_stage_copies = row["card_type"] == "Projektfaktor" and row["stage_candidate"] == "true"
        if wants_stage_copies:
            try:
                stage_copies = int(row["stage_copies"])
            except ValueError:
                fail(f"{card_id}: stage_copies must be an integer")
            if stage_copies < 1:
                fail(f"{card_id}: stage_copies must be at least 1")
        elif row["stage_copies"]:
            fail(f"{card_id}: stage_copies must be blank outside stage-candidate project factors")
        if rarity == "mythic" and row["foil_only"] != "true":
            fail(f"{card_id}: mythics must be foil-only")
        if rarity != "mythic" and row["foil_only"] == "true":
            fail(f"{card_id}: only mythics may be foil-only in KAT-01")

    for row in playable:
        card_id = row["card_id"]
        for field in ("motif_origin", "visual_motif", "mechanical_role", "rules_text", "test_notes"):
            if not row[field]:
                fail(f"{card_id}: playable card is missing {field}")

        if row["card_type"] == "Projekt":
            require_blank(row, ("factor_family", "target_family", "polarity", "effect_template"))
            if not row["project_goal"]:
                fail(f"{card_id}: project_goal is required for projects")
            requirements = row["requirements"].split("+") if row["requirements"] else []
            if not 2 <= len(requirements) <= 4:
                fail(f"{card_id}: projects need two to four requirements")
            invalid = set(requirements) - VALID_REQUIREMENTS
            if invalid:
                fail(f"{card_id}: invalid project requirements {sorted(invalid)}")
            try:
                points = int(row["points"])
            except ValueError:
                fail(f"{card_id}: project points must be an integer")
            if points != len(requirements):
                fail(f"{card_id}: points must equal the requirement count")
            if row["rarity"] not in {"common", "rare"}:
                fail(f"{card_id}: projects must be common or rare in KAT-01")
        elif row["card_type"] == "Projektfaktor":
            require_blank(row, ("target_family", "polarity", "effect_template", "requirements", "points", "project_goal"))
            family = row["factor_family"]
            if family not in EXPECTED_FACTOR_FAMILIES:
                fail(f"{card_id}: invalid factor family {family}")
            if row["domain_primary"] != FACTOR_DOMAINS[family]:
                fail(f"{card_id}: {family} factors must use domain {FACTOR_DOMAINS[family]}")
        elif row["card_type"] == "Ereignis":
            require_blank(row, ("factor_family", "requirements", "points", "project_goal"))
            if row["polarity"] not in EXPECTED_EVENT_POLARITIES:
                fail(f"{card_id}: invalid event polarity {row['polarity']}")
            if row["effect_template"] not in EXPECTED_EFFECT_TEMPLATES:
                fail(f"{card_id}: invalid effect template {row['effect_template']}")
            if (row["polarity"] == "negative") != (
                row["effect_template"] in NEGATIVE_EVENT_TEMPLATES
            ):
                fail(
                    f"{card_id}: negative polarity must match event template E6 or E7"
                )
            target_family = row["target_family"]
            if target_family and target_family != "any":
                parts = target_family.split("+")
                if len(parts) != len(set(parts)) or set(parts) - VALID_REQUIREMENTS:
                    fail(f"{card_id}: invalid target family {target_family}")
        else:
            fail(f"{card_id}: obsolete or invalid playable card type {row['card_type']}")

    type_counts = Counter(row["card_type"] for row in playable)
    if type_counts != Counter(EXPECTED_TYPES):
        fail(f"playable type counts differ: expected {EXPECTED_TYPES}, got {dict(type_counts)}")

    rarity_type_counts = Counter((row["rarity"], row["card_type"]) for row in playable)
    if rarity_type_counts != Counter(EXPECTED_RARITY_TYPES):
        fail(
            "rarity/type counts differ: "
            f"expected {EXPECTED_RARITY_TYPES}, got {dict(rarity_type_counts)}"
        )

    factors = [row for row in playable if row["card_type"] == "Projektfaktor"]
    factor_counts = Counter(row["factor_family"] for row in factors)
    if factor_counts != Counter(EXPECTED_FACTOR_FAMILIES):
        fail(f"factor type counts differ: expected {EXPECTED_FACTOR_FAMILIES}, got {dict(factor_counts)}")

    events = [row for row in playable if row["card_type"] == "Ereignis"]
    polarity_counts = Counter(row["polarity"] for row in events)
    if polarity_counts != Counter(EXPECTED_EVENT_POLARITIES):
        fail(
            f"event polarities differ: expected {EXPECTED_EVENT_POLARITIES}, "
            f"got {dict(polarity_counts)}"
        )
    template_counts = Counter(row["effect_template"] for row in events)
    if template_counts != Counter(EXPECTED_EFFECT_TEMPLATES):
        fail(
            f"effect templates differ: expected {EXPECTED_EFFECT_TEMPLATES}, "
            f"got {dict(template_counts)}"
        )

    projects = [row for row in playable if row["card_type"] == "Projekt"]
    requirement_counts = Counter(
        requirement
        for row in projects
        for requirement in row["requirements"].split("+")
    )
    if requirement_counts != Counter(EXPECTED_PROJECT_REQUIREMENTS):
        fail(
            f"project requirements differ: expected {EXPECTED_PROJECT_REQUIREMENTS}, "
            f"got {dict(requirement_counts)}"
        )
    requirement_signatures = [tuple(sorted(row["requirements"].split("+"))) for row in projects]
    if len(set(requirement_signatures)) != len(requirement_signatures):
        fail("project requirement signatures must be unique")

    stage_rows = [row for row in playable if row["stage_candidate"] == "true"]
    stage_types = Counter(row["card_type"] for row in stage_rows)
    expected_stage_types = {"Projekt": 16, "Projektfaktor": 38, "Ereignis": 12}
    if stage_types != Counter(expected_stage_types):
        fail(f"stage motif selection differs: expected {expected_stage_types}, got {dict(stage_types)}")
    stage_events = {row["card_id"] for row in stage_rows if row["card_type"] == "Ereignis"}
    if stage_events != EXPECTED_STAGE_EVENTS:
        fail(f"stage event selection differs: expected {sorted(EXPECTED_STAGE_EVENTS)}, got {sorted(stage_events)}")

    stage_factor_rows = [row for row in stage_rows if row["card_type"] == "Projektfaktor"]
    repeated_factors = {row["card_id"] for row in stage_factor_rows if int(row["stage_copies"]) > 1}
    if repeated_factors != EXPECTED_STAGE_REPEATED_FACTORS:
        fail(
            f"stage factor repeats differ: expected {sorted(EXPECTED_STAGE_REPEATED_FACTORS)}, "
            f"got {sorted(repeated_factors)}"
        )
    stage_factor_families = Counter()
    for row in stage_factor_rows:
        stage_factor_families[row["factor_family"]] += int(row["stage_copies"])
    if stage_factor_families != Counter(EXPECTED_STAGE_FACTOR_FAMILIES):
        fail(
            f"stage factor type totals differ: expected {EXPECTED_STAGE_FACTOR_FAMILIES}, "
            f"got {dict(stage_factor_families)}"
        )
    stage_factor_total = sum(stage_factor_families.values())
    if stage_factor_total != 46:
        fail(f"stage set must contain 46 project factors, got {stage_factor_total}")

    # --- Auflagenabhängige Prüfungen (ADR 0019) ---------------------------
    # Die Motivdaten oben gelten für jede Auflage. Ab hier wird gegen ein
    # Profil aus `data/print_runs/` geprüft: Gehen die Boosterslots exakt auf,
    # stimmt die Gesamtrechnung, und wird jedes Motiv wenigstens einmal
    # gedruckt?
    cards_by_id = {row["card_id"]: row for row in rows}
    copies = run.booster_copies(cards_by_id)

    for (rarity, card_type), slots in run.slots_per_group().items():
        if (rarity, card_type) == ("common", "Projektfaktor"):
            continue  # je Faktortyp geprüft, siehe unten
        got = sum(
            copies[card_id]
            for card_id, card in cards_by_id.items()
            if card["rarity"] == rarity and card["card_type"] == card_type
        )
        if got != slots:
            fail(f"{run.name}: {rarity} {card_type} fills {got} of {slots} booster slots")

    for family, slots in run.common_factor_slots().items():
        got = sum(
            copies[card_id]
            for card_id, card in cards_by_id.items()
            if card["rarity"] == "common"
            and card["card_type"] == "Projektfaktor"
            and card["factor_family"] == family
        )
        if got != slots:
            fail(f"{run.name}: common {family} factors fill {got} of {slots} booster slots")

    booster_standard = sum(
        count for card_id, count in copies.items() if cards_by_id[card_id]["foil_only"] != "true"
    )
    booster_foil = sum(
        count for card_id, count in copies.items() if cards_by_id[card_id]["foil_only"] == "true"
    )
    if booster_foil != run.foil_in_circulation:
        fail(
            f"{run.name}: {booster_foil} foils in boosters, profile says "
            f"{run.foil_in_circulation}"
        )
    if run.foil_in_circulation > run.foil_total:
        fail(f"{run.name}: {run.foil_in_circulation} foils in circulation exceed {run.foil_total} printed")

    stage_set_size = sum(
        int(row["stage_copies"]) if row["stage_copies"] else 1
        for row in rows
        if row["stage_candidate"] == "true"
    )
    standard_used = (
        run.stage_sets * stage_set_size + booster_standard + run.blank_cards + run.reserve
    )
    if standard_used != run.standard_total:
        fail(
            f"{run.name}: standard cards do not add up — "
            f"{run.stage_sets}x{stage_set_size} stage + {booster_standard} booster + "
            f"{run.blank_cards} blank + {run.reserve} reserve = {standard_used}, "
            f"profile says {run.standard_total}"
        )

    # Jedes Motiv muss physisch existieren. Ein Motiv ohne Boosterkarte ist
    # zulässig, solange es im Bühnensatz liegt (ADR 0019); Foil-Mythics hängen
    # am Foilauftrag, nicht am Boosterumlauf.
    mythic_motifs = sum(1 for row in rows if row["foil_only"] == "true")
    for row in rows:
        card_id = row["card_id"]
        if row["foil_only"] == "true":
            if run.foil_total < mythic_motifs:
                fail(f"{card_id}: foil order of {run.foil_total} cannot cover {mythic_motifs} mythics")
            continue
        in_stage = run.stage_sets > 0 and row["stage_candidate"] == "true"
        if copies[card_id] == 0 and not in_stage:
            fail(f"{card_id} {row['name']}: not printed at all in run {run.name}")

    tag_counts = Counter(
        tag for row in rows for tag in (row["editorial_tags"].split("+") if row["editorial_tags"] else [])
    )
    unused = [tag for tag in EDITORIAL_TAGS if not tag_counts[tag]]
    if unused:
        fail(f"editorial tags without a single card: {unused}")

    physical_types = Counter()
    for row in playable:
        physical_types[row["card_type"]] += copies[row["card_id"]]
    omitted = sorted(card_id for card_id, count in copies.items() if count == 0)

    print("OK")
    print(f"  motifs: {len(rows)} booster motifs")
    print("  playable types: 16 projects, 38 project factors, 28 events")
    print(f"  print run: {run.name} (ADR {run.adr})")
    print(
        f"  booster cards: {booster_standard + booster_foil} in {run.packs} packs "
        f"({booster_standard} standard, {booster_foil} foil)"
    )
    print(
        "  booster profile: "
        + ", ".join(f"{count} {name}" for name, count in sorted(physical_types.items()))
    )
    print(
        f"  standard order: {run.stage_sets}x{stage_set_size} stage + {booster_standard} booster "
        f"+ {run.blank_cards} blank + {run.reserve} reserve = {run.standard_total}"
    )
    if omitted:
        print(f"  motifs without a booster card: {', '.join(omitted)}")
    print("  stage base: 66 unique motifs plus 8 repeated factor slots (3T/2D/1O/2M, ADR 0009)")
    untagged = sum(1 for row in rows if not row["editorial_tags"])
    print(
        "  editorial tags: "
        + ", ".join(f"{tag} {tag_counts[tag]}" for tag in EDITORIAL_TAGS)
        + f" ({untagged} motifs without a tag)"
    )


if __name__ == "__main__":
    main()
