#!/usr/bin/env python3
"""Generate one complete illustration prompt per booster motif."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CARDS = ROOT / "data" / "cards.csv"
DEFAULT_TEMPLATE = ROOT / "prompts" / "illustration-template.md"
DEFAULT_OUTPUT = ROOT / "build" / "illustration-prompts"
MASTERPROMPT_PATTERN = re.compile(
    r"^## Masterprompt\s+.*?^```text\s*\n(?P<prompt>.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)


def extract_masterprompt(template_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    match = MASTERPROMPT_PATTERN.search(template)
    if not match:
        raise ValueError(f"Kein text-Block unter '## Masterprompt' in {template_path}")
    return match.group("prompt").strip()


def load_cards(cards_path: Path) -> list[dict[str, str]]:
    with cards_path.open(encoding="utf-8", newline="") as handle:
        cards = [
            row
            for row in csv.DictReader(handle)
            if row["rarity"] in {"common", "uncommon", "rare", "mythic"}
        ]

    card_ids = [card["card_id"] for card in cards]
    if len(card_ids) != len(set(card_ids)):
        raise ValueError(f"Doppelte card_id in {cards_path}")
    missing_motifs = [
        card_id
        for card_id, card in zip(card_ids, cards)
        if not card["visual_motif"].strip()
    ]
    if missing_motifs:
        raise ValueError(f"Leeres visual_motif: {', '.join(missing_motifs)}")
    return cards


def build_prompt(
    masterprompt: str,
    name: str,
    flavor_text: str,
    visual_motif: str,
) -> str:
    semantic_context = (
        "Semantic context for image selection only. Do not depict or reproduce "
        "any of the following words as typography, labels, captions, signage, "
        "or interface text.\n"
        f'Card title: "{name.strip()}"\n'
        f'Flavor text: "{flavor_text.strip()}"\n'
        "Make the relationship between title and flavor text visually clear "
        "through physical objects, action, and consequence."
    )
    return f"{masterprompt}\n\n{semantic_context}\n\n{visual_motif.strip()}\n"


def generate_prompts(cards_path: Path, template_path: Path, output_dir: Path) -> int:
    masterprompt = extract_masterprompt(template_path)
    cards = load_cards(cards_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_prompt in output_dir.glob("KAT-*.txt"):
        stale_prompt.unlink()

    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["card_id", "name", "rarity", "filename"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for card in cards:
            filename = f"{card['card_id']}.txt"
            (output_dir / filename).write_text(
                build_prompt(
                    masterprompt,
                    card["name"],
                    card["flavor_text"],
                    card["visual_motif"],
                ),
                encoding="utf-8",
            )
            writer.writerow(
                {
                    "card_id": card["card_id"],
                    "name": card["name"],
                    "rarity": card["rarity"],
                    "filename": filename,
                }
            )
    return len(cards)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Erzeugt vollständige Bildprompts aus Masterprompt, semantischem "
            "Kartenkontext und visual_motif."
        )
    )
    parser.add_argument("--cards", type=Path, default=DEFAULT_CARDS)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = generate_prompts(args.cards, args.template, args.output)
    print(f"OK: {count} Illustrationsprompts in {args.output}")


if __name__ == "__main__":
    main()
