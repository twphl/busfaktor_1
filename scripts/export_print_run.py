#!/usr/bin/env python3
"""Lay the print run out as numbered upload files, one per physical card.

The renderer produces one PNG per *motif*; a printer wants one file per *card*.
This script closes that gap and fixes the order in which the 612 standard cards
are uploaded, because the stack usually comes back in exactly that order and is
then cut into piles by hand.  Collation is therefore designed into the sequence
rather than done afterwards against `build/boosters.csv`:

    1.  Buehnensatz 1                        74
    2.  Buehnensatz 2                        74
    3.  18 Normalbooster a 12               216
    4.  18 Specialbooster a 11 Standard     198
    5.  Blanko                     konfigurierbar
    6.  Puffer                              Rest
                                            ---
                                            612

The two booster blocks are not interleaved.  Every special pack is short one
card, because its mythic sits in the separate 18-card foil order (ADR 0003), and
keeping the packs that need an insert together means the foil order is a
straight one-to-one strip: foil position *k* belongs to special pack *k*.  Runs
of packs that need nothing inserted are cut off the stack first.

Both orders are written as their own folder, plus one manifest that names, for
every number, which card it is and which pile it belongs to.  Identical motifs
are hardlinked rather than copied, so a 612-file run stays the size of its 88
distinct images.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import print_run  # noqa: E402
import render_blank_cards as blanks  # noqa: E402
import render_cards as rc  # noqa: E402

DEFAULT_OUTPUT = ROOT / "build" / "print-run"

FOIL_SLOT = "12"


def boosters_path_for(run: print_run.PrintRun) -> Path:
    return ROOT / "build" / f"boosters-{run.name}.csv"


def blank_split(run: print_run.PrintRun) -> tuple[int, int, int]:
    """Split `blank_cards` over the six blank motifs, evenly.

    ADR 0019 prints each blank motif twice: eight factor blanks (four motifs),
    two event blanks and two project blanks.  The `612-plus-18` run predates
    the decision and carries none.  Override on the CLI to weight the split
    towards factors, which `docs/11-community-expansion.md` section 2 calls the
    standard case at the stand.
    """

    motifs = len(FACTOR_BLANKS) + 2
    per_motif, remainder = divmod(run.blank_cards, motifs)
    if remainder:
        raise ExportError(
            f"{run.blank_cards} Blankokarten lassen sich nicht gleichmäßig auf "
            f"{motifs} Blankomotive verteilen; --blank-* setzen"
        )
    return per_motif * len(FACTOR_BLANKS), per_motif, per_motif

FACTOR_BLANKS = tuple(
    variant["blank_id"] for variant in blanks.BLANK_VARIANTS if variant["card_type"] == "Projektfaktor"
)
EVENT_BLANK = "KAT-B05"
PROJECT_BLANK = "KAT-B06"

MANIFEST_COLUMNS = (
    "number",
    "order",
    "section",
    "pile",
    "pack_id",
    "pack_type",
    "slot",
    "card_id",
    "name",
    "card_type",
    "rarity",
    "file",
)


class ExportError(RuntimeError):
    """Raised when the run cannot be laid out as specified."""


def _is_true(value: str) -> bool:
    return value.strip().lower() == "true"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def stage_set(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Build one 74-card stage set: projects, factors with their repeats, events.

    The set is ordered by card type and then by ID so the pile is predictable
    when it is counted by hand; ADR 0009 fixes which eight factors lie twice.
    """

    order = {"Projekt": 0, "Projektfaktor": 1, "Ereignis": 2}
    selected = [row for row in rows if _is_true(row["stage_candidate"])]
    cards: list[dict[str, str]] = []
    for row in sorted(selected, key=lambda row: (order[row["card_type"]], row["card_id"])):
        copies = int(row["stage_copies"] or 1)
        cards.extend({"card_id": row["card_id"]} for _ in range(copies))
    return cards


def booster_blocks(pack_rows: Sequence[Mapping[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split the collated packs into the standard sequence and the foil strip."""

    packs: dict[str, list[Mapping[str, str]]] = {}
    for row in pack_rows:
        packs.setdefault(row["pack_id"], []).append(row)
    for pack_id, slots in packs.items():
        if len(slots) != 12:
            raise ExportError(f"{pack_id}: {len(slots)} statt 12 Slots")

    normal = sorted(pack_id for pack_id, slots in packs.items() if slots[0]["pack_type"] == "normal")
    special = sorted(pack_id for pack_id, slots in packs.items() if slots[0]["pack_type"] == "special")

    standard: list[dict[str, Any]] = []
    foil: list[dict[str, Any]] = []
    for section, pack_ids in (("booster-normal", normal), ("booster-special", special)):
        for index, pack_id in enumerate(pack_ids, start=1):
            for row in sorted(packs[pack_id], key=lambda row: int(row["slot"])):
                entry = {
                    "section": section,
                    "pile": f"{pack_id} ({index:02d}/{len(pack_ids):02d})",
                    "pack_id": pack_id,
                    "pack_type": row["pack_type"],
                    "slot": row["slot"],
                    "card_id": row["card_id"],
                }
                if _is_true(row["foil"]):
                    if row["slot"] != FOIL_SLOT:
                        raise ExportError(f"{pack_id}: Foil liegt in Slot {row['slot']} statt {FOIL_SLOT}")
                    foil.append(entry)
                else:
                    standard.append(entry)
    return standard, foil


def blank_sequence(factors: int, events: int, projects: int) -> list[dict[str, Any]]:
    """Deal the factor blanks round-robin over the four families, then the rest."""

    if min(factors, events, projects) < 0:
        raise ExportError("Blankozahlen dürfen nicht negativ sein")
    cards = [
        {"section": "blanko", "pile": "Blanko", "card_id": FACTOR_BLANKS[index % len(FACTOR_BLANKS)]}
        for index in range(factors)
    ]
    cards.sort(key=lambda card: card["card_id"])
    cards.extend({"section": "blanko", "pile": "Blanko", "card_id": EVENT_BLANK} for _ in range(events))
    cards.extend({"section": "blanko", "pile": "Blanko", "card_id": PROJECT_BLANK} for _ in range(projects))
    return cards


def stage_gap(rows: Sequence[Mapping[str, str]]) -> list[str]:
    """Name the standard motifs no stage set contains.

    ``stage_candidate`` selects 66 of the 73 standard motifs; the seven it
    leaves out are all events, and printing each of them once per set is what
    turns two 74-card sets into two complete ones.
    """

    return [
        row["card_id"]
        for row in sorted(rows, key=lambda row: row["card_id"])
        if not _is_true(row["foil_only"]) and not _is_true(row["stage_candidate"])
    ]


def buffer_sequence(
    rows: Sequence[Mapping[str, str]],
    count: int,
    mode: str,
    run: print_run.PrintRun,
) -> list[dict[str, Any]]:
    """Fill the remaining reserve slots.

    ``stage-gap`` spends them on the motifs the stage sets lack, one copy per
    set, which is the only filling that answers a question the set actually
    asks.  ``reference`` falls back to distinct motifs in canonical order and
    ``blanko`` to further blanks; both leave the reserve undetermined.
    """

    if count < 0:
        raise ExportError(
            f"Die Blankozahl überschreitet die {run.standard_total} Standardkarten um {-count}"
        )
    if mode == "blanko":
        return [
            {"section": "puffer", "pile": "Puffer", "card_id": FACTOR_BLANKS[index % len(FACTOR_BLANKS)]}
            for index in range(count)
        ]

    cards: list[dict[str, Any]] = []
    if mode == "stage-gap":
        missing = stage_gap(rows)
        for set_number in range(1, run.stage_sets + 1):
            cards.extend(
                {
                    "section": "puffer",
                    "pile": f"Ergänzung Bühnensatz {set_number}",
                    "card_id": card_id,
                }
                for card_id in missing
            )
        cards = cards[:count]

    if len(cards) < count:
        # Top the run up so the standard order still reaches the profile total.
        taken = Counter(card["card_id"] for card in cards)
        pool = [
            row["card_id"]
            for row in sorted(rows, key=lambda row: row["card_id"])
            if not _is_true(row["foil_only"]) and row["card_id"] not in taken
        ]
        if count - len(cards) > len(pool):
            raise ExportError(f"Puffer {count} übersteigt die verfügbaren Standardmotive")
        cards.extend(
            {"section": "puffer", "pile": "Puffer", "card_id": card_id}
            for card_id in pool[: count - len(cards)]
        )
    return cards


def foil_backstock(
    rows: Sequence[Mapping[str, str]],
    in_boosters: Sequence[Mapping[str, Any]],
    run: print_run.PrintRun,
) -> list[dict[str, Any]]:
    """Foils that are printed but not collated (ADR 0019).

    The foil order is a fixed minimum of 18 cards, but the booster pool takes
    only `foil_in_circulation` of them — eight in the 234-card run.  The rest
    is printed all the same and held back as proof copies and replacements, so
    the print file must carry every copy.
    """

    mythics = sorted(row["card_id"] for row in rows if _is_true(row["foil_only"]))
    if not mythics:
        return []
    per_motif, extra = divmod(run.foil_total, len(mythics))
    target = {
        card_id: per_motif + (1 if index < extra else 0)
        for index, card_id in enumerate(mythics)
    }
    used = Counter(entry["card_id"] for entry in in_boosters)
    cards: list[dict[str, Any]] = []
    for card_id in mythics:
        held = target[card_id] - used[card_id]
        if held < 0:
            raise ExportError(
                f"{card_id}: {used[card_id]} Foils kollationiert, aber nur "
                f"{target[card_id]} gedruckt"
            )
        cards.extend(
            {"section": "foil-rueckhalt", "pile": "Foil-Rückhalt", "card_id": card_id}
            for _ in range(held)
        )
    return cards


def build_sequence(
    rows: Sequence[Mapping[str, str]],
    pack_rows: Sequence[Mapping[str, str]],
    *,
    blank_factors: int,
    blank_events: int,
    blank_projects: int,
    buffer_mode: str,
    run: print_run.PrintRun,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Lay out both orders in the sequence the piles are cut from."""

    standard: list[dict[str, Any]] = []
    single_set = stage_set(rows)
    if len(single_set) != 74:
        raise ExportError(f"Bühnensatz umfasst {len(single_set)} statt 74 Karten")
    for number in range(1, run.stage_sets + 1):
        standard.extend(
            {"section": f"buehne-{number}", "pile": f"Bühnensatz {number}", "card_id": card["card_id"]}
            for card in single_set
        )

    booster_standard, foil = booster_blocks(pack_rows)
    standard.extend(booster_standard)

    standard.extend(blank_sequence(blank_factors, blank_events, blank_projects))
    used = len(standard)
    standard.extend(buffer_sequence(rows, run.standard_total - used, buffer_mode, run))

    foil = foil + foil_backstock(rows, foil, run)

    if len(standard) != run.standard_total:
        raise ExportError(
            f"Standardreihe umfasst {len(standard)} statt {run.standard_total} Karten"
        )
    if len(foil) != run.foil_total:
        raise ExportError(f"Foilreihe umfasst {len(foil)} statt {run.foil_total} Karten")
    return standard, foil


def gate_report(card_ids: Iterable[str]) -> list[str]:
    """Name every review gate that stands between this run and a print upload."""

    mapping = rc._load_layout()
    gates = mapping.get("review_gates", {})
    wanted = set(card_ids)
    problems = []
    for label, key in (("Content-Review offen", "content_blocked_card_ids"), ("Bildreview offen", "artwork_blocked_card_ids")):
        blocked = sorted(wanted.intersection(gates.get(key, [])))
        if blocked:
            problems.append(f"{label}: {', '.join(blocked)}")
    if mapping.get("status") != "final":
        problems.append(f"Layoutstatus {mapping.get('status', 'leer')} statt final")
    return problems


def render_motifs(
    card_ids: Sequence[str],
    destination: Path,
    *,
    mode: str,
    profile_path: Path,
    csv_path: Path,
    artwork_dir: Path,
) -> dict[str, Path]:
    """Render every distinct motif once and return the lookup by card ID."""

    canonical = sorted(card_id for card_id in card_ids if card_id not in blanks.BLANK_IDS)
    used_blanks = sorted(set(card_ids).intersection(blanks.BLANK_IDS))
    cards_dir = destination / "cards"
    blank_dir = destination / "blank"

    rc.render_selected(
        profile_path=profile_path,
        csv_path=csv_path,
        artwork_dir=artwork_dir,
        output_dir=cards_dir,
        card_ids=canonical,
        proof=False,
        mode=mode,
        keep_svg=False,
    )
    sources = {card_id: cards_dir / f"{card_id}.png" for card_id in canonical}

    if used_blanks:
        variants = [variant for variant in blanks.BLANK_VARIANTS if variant["blank_id"] in used_blanks]
        blanks.render_blanks(
            profile_path=profile_path,
            csv_path=csv_path,
            output_dir=blank_dir,
            variants=variants,
            mode=mode,
            keep_svg=False,
        )
        sources.update({card_id: blank_dir / f"{card_id}.png" for card_id in used_blanks})
    return sources


def materialise(source: Path, target: Path, method: str) -> None:
    if target.exists():
        target.unlink()
    if method == "hard":
        try:
            os.link(source, target)
            return
        except OSError:
            pass
    elif method == "symlink":
        target.symlink_to(os.path.relpath(source, target.parent))
        return
    shutil.copy2(source, target)


def write_run(
    entries: Sequence[Mapping[str, Any]],
    sources: Mapping[str, Path],
    destination: Path,
    *,
    prefix: str,
    order: str,
    method: str,
    rows_by_id: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    """Write one numbered upload folder and return its manifest rows."""

    destination.mkdir(parents=True, exist_ok=True)
    for stale in destination.glob("*.png"):
        stale.unlink()
    width = max(len(str(len(entries))), 2)
    manifest = []
    for number, entry in enumerate(entries, start=1):
        card_id = entry["card_id"]
        source = sources.get(card_id)
        if source is None or not source.is_file():
            raise ExportError(f"{card_id}: gerendertes Motiv fehlt")
        filename = f"{prefix}{number:0{width}d}_{card_id}.png"
        materialise(source, destination / filename, method)
        row = rows_by_id.get(card_id, {})
        manifest.append(
            {
                "number": number,
                "order": order,
                "section": entry["section"],
                "pile": entry.get("pile", ""),
                "pack_id": entry.get("pack_id", ""),
                "pack_type": entry.get("pack_type", ""),
                "slot": entry.get("slot", ""),
                "card_id": card_id,
                "name": row.get("name", ""),
                "card_type": row.get("card_type", ""),
                "rarity": row.get("rarity", "blanko"),
                "file": filename,
            }
        )
    return manifest


def export(
    *,
    profile_path: Path = rc.DEFAULT_PROFILE,
    csv_path: Path = rc.DEFAULT_CARDS,
    artwork_dir: Path = rc.DEFAULT_ARTWORK_DIR,
    boosters_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT,
    mode: str = "print",
    blank_factors: int | None = None,
    blank_events: int | None = None,
    blank_projects: int | None = None,
    buffer_mode: str = "stage-gap",
    method: str = "hard",
    render: bool = True,
    run: print_run.PrintRun | None = None,
) -> dict[str, Any]:
    """Render, number and lay out both print orders."""

    run = run or print_run.load(print_run.DEFAULT)
    default_factors, default_events, default_projects = blank_split(run)
    blank_factors = default_factors if blank_factors is None else blank_factors
    blank_events = default_events if blank_events is None else blank_events
    blank_projects = default_projects if blank_projects is None else blank_projects

    rows = load_rows(Path(csv_path))
    rows_by_id = {row["card_id"]: row for row in rows}
    pack_rows = load_rows(Path(boosters_path or boosters_path_for(run)))

    standard, foil = build_sequence(
        rows,
        pack_rows,
        blank_factors=blank_factors,
        blank_events=blank_events,
        blank_projects=blank_projects,
        buffer_mode=buffer_mode,
        run=run,
    )
    card_ids = sorted({entry["card_id"] for entry in [*standard, *foil]})
    problems = gate_report(card_ids)
    if problems and mode == "print":
        raise ExportError(
            "Print-Gate: " + "; ".join(problems) + ". Für einen Entwurfslauf --draft verwenden."
        )

    destination = Path(output_dir)
    motifs = destination / "motifs"
    if render:
        sources = render_motifs(
            card_ids,
            motifs,
            mode=mode,
            profile_path=Path(profile_path),
            csv_path=Path(csv_path),
            artwork_dir=Path(artwork_dir),
        )
    else:
        sources = {}
        for card_id in card_ids:
            folder = "blank" if card_id in blanks.BLANK_IDS else "cards"
            sources[card_id] = motifs / folder / f"{card_id}.png"

    manifest_rows = write_run(
        standard,
        sources,
        destination / "standard",
        prefix="",
        order="standard",
        method=method,
        rows_by_id=rows_by_id,
    )
    manifest_rows += write_run(
        foil,
        sources,
        destination / "foil",
        prefix="F",
        order="foil",
        method=method,
        rows_by_id=rows_by_id,
    )

    with (destination / "print-run.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(manifest_rows)

    sections = Counter(entry["section"] for entry in standard)
    stage_missing = stage_gap(rows)
    printed = Counter(entry["card_id"] for entry in standard if entry["section"] == "puffer")
    stage_covered = all(printed[card_id] >= run.stage_sets for card_id in stage_missing)
    summary = {
        "schema": "dhk-print-run/v1",
        "mode": mode,
        "draft": bool(problems),
        "open_gates": problems,
        "standard_cards": len(standard),
        "foil_cards": len(foil),
        "distinct_motifs": len(card_ids),
        "sections": dict(sections),
        "blanks": {"factors": blank_factors, "events": blank_events, "projects": blank_projects},
        "buffer_mode": buffer_mode,
        "stage_gap": stage_missing,
        "stage_gap_covered": stage_covered,
        "copies_per_card_id": dict(Counter(entry["card_id"] for entry in standard)),
    }
    (destination / "print-run.json").write_bytes(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nummerierte Druckreihe für den Upload erzeugen")
    parser.add_argument("--profile", type=Path, default=rc.DEFAULT_PROFILE)
    parser.add_argument("--cards", type=Path, default=rc.DEFAULT_CARDS)
    parser.add_argument("--artwork-dir", type=Path, default=rc.DEFAULT_ARTWORK_DIR)
    parser.add_argument(
        "--print-run",
        default=print_run.DEFAULT,
        help="Auflagenprofil aus data/print_runs (Standard: %(default)s)",
    )
    parser.add_argument(
        "--boosters",
        type=Path,
        default=None,
        help="Kollation; Standard ist build/boosters-<Auflage>.csv",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Entwurfslauf trotz offener Reviews; blockierte Motive tragen den Platzhalter",
    )
    parser.add_argument("--blank-factors", type=int, default=None)
    parser.add_argument("--blank-events", type=int, default=None)
    parser.add_argument("--blank-projects", type=int, default=None)
    parser.add_argument(
        "--buffer-mode",
        choices=("stage-gap", "reference", "blanko"),
        default="stage-gap",
        help="stage-gap druckt die in den Bühnensätzen fehlenden Motive je Satz einmal",
    )
    parser.add_argument("--materialise", choices=("hard", "copy", "symlink"), default="hard")
    parser.add_argument("--no-render", action="store_true", help="Vorhandene Motivrenders weiterverwenden")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = export(
            profile_path=args.profile,
            csv_path=args.cards,
            artwork_dir=args.artwork_dir,
            boosters_path=args.boosters,
            output_dir=args.output,
            mode="preview" if args.draft else "print",
            blank_factors=args.blank_factors,
            blank_events=args.blank_events,
            blank_projects=args.blank_projects,
            buffer_mode=args.buffer_mode,
            method=args.materialise,
            render=not args.no_render,
            run=print_run.load(args.print_run),
        )
    except (ExportError, blanks.BlankError, rc.RenderError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    for section, count in summary["sections"].items():
        print(f"{section:18} {count:>4}")
    print(f"{'Standard':18} {summary['standard_cards']:>4}")
    print(f"{'Foil':18} {summary['foil_cards']:>4}")
    print(f"{summary['distinct_motifs']} verschiedene Motive nach {args.output}")
    if summary["open_gates"]:
        print("Entwurfslauf, nicht druckreif: " + "; ".join(summary["open_gates"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
