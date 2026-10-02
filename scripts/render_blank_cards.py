#!/usr/bin/env python3
"""Render the blank conference cards from the canonical front geometry.

Blank cards are the production answer to `docs/11-community-expansion.md`
section 5, variant B: participants fill one in at the stand and it is playable
in the running game immediately.  They are cut from the 50 reserve slots of
ADR 0002 and therefore belong to the standard print order, not to a second job.

The design is not authored a second time.  A blank is a regular front built by
``render_cards.build_card_svg`` from a synthetic row whose text fields are
empty, so frame, plates, type line, factor symbol and footer are the ones the
82 canonical motifs already use.  Only what a blank must not claim is removed
afterwards, by data-role, on the finished SVG:

*   the rarity word becomes ``BLANKO`` and every rarity pip becomes an empty
    outline, because a blank has no print quantity and therefore no rarity
    (ADR 0013 defines rarity as exactly that quantity),
*   the event keyword and the project requirement glyphs are dropped so their
    carriers stay as empty slots to write and tick into,
*   faint baselines are drawn into the title panel and the content panel.

The illustration window is filled with the flat paper tone rather than left
empty: participants draw their Bildidee into it, and a mat with no image is the
one part of the front the renderer would otherwise mark ``ILLUSTRATION FEHLT``.

Coated card stock takes ballpoint badly.  The writing fields are therefore as
large and as light as the layout allows, and the stand needs permanent fine
markers; this is an open item for the A/B proof.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import render_cards as rc  # noqa: E402

DEFAULT_OUTPUT = ROOT / "build" / "cards-blank"

#: One blank per thing a participant may decide.  The four factor variants
#: carry their family symbol pre-printed because the requirement match has to
#: be readable across the table, which a handwritten glyph is not.
BLANK_VARIANTS: tuple[dict[str, str], ...] = (
    {
        "blank_id": "KAT-B01",
        "card_type": "Projektfaktor",
        "factor_family": "team",
        "label": "Blanko Projektfaktor Team",
    },
    {
        "blank_id": "KAT-B02",
        "card_type": "Projektfaktor",
        "factor_family": "data",
        "label": "Blanko Projektfaktor Daten",
    },
    {
        "blank_id": "KAT-B03",
        "card_type": "Projektfaktor",
        "factor_family": "operations",
        "label": "Blanko Projektfaktor Betrieb",
    },
    {
        "blank_id": "KAT-B04",
        "card_type": "Projektfaktor",
        "factor_family": "methods",
        "label": "Blanko Projektfaktor Methode",
    },
    {
        "blank_id": "KAT-B05",
        "card_type": "Ereignis",
        "factor_family": "",
        "label": "Blanko Ereignis",
    },
    {
        "blank_id": "KAT-B06",
        "card_type": "Projekt",
        "factor_family": "",
        "label": "Blanko Projekt",
    },
)

BLANK_IDS = tuple(variant["blank_id"] for variant in BLANK_VARIANTS)

#: A blank project shows the full four requirement slots rather than the two to
#: four of a printed project, so any profile from `11-community-expansion.md`
#: section 2 can be ticked into it.
BLANK_PROJECT_REQUIREMENTS = "team+data+operations+methods"

RARITY_LABEL = "BLANKO"
WRITING_LINE_OPACITY = 0.28
WRITING_LINE_WIDTH = 0.6
TITLE_LINE_INSET = 12.0
CONTENT_LINE_INSET = 14.0
CONTENT_LINE_COUNT = 5


class BlankError(RuntimeError):
    """Raised when a blank cannot be built from the canonical geometry."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _by_role(root: ET.Element, role: str) -> list[ET.Element]:
    return [element for element in root.iter() if element.attrib.get("data-role") == role]


def _parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def _set_text(element: ET.Element, value: str) -> None:
    """Replace the rendered string of a text element, tspans included."""

    spans = [child for child in element if _local(child.tag) == "tspan"]
    if not spans:
        element.text = value
        return
    spans[0].text = value
    for span in spans[1:]:
        element.remove(span)


def _template_row(rows: Sequence[Mapping[str, str]], variant: Mapping[str, str]) -> dict[str, str]:
    """Pick the lowest-numbered canonical motif a blank inherits its layout from."""

    candidates = [
        row
        for row in rows
        if row["card_type"] == variant["card_type"]
        and (not variant["factor_family"] or row["factor_family"] == variant["factor_family"])
        and row["foil_only"].strip().lower() != "true"
    ]
    if not candidates:
        raise BlankError(
            f"{variant['blank_id']}: keine Vorlage für {variant['card_type']} "
            f"{variant['factor_family'] or '–'} in data/cards.csv"
        )
    return dict(sorted(candidates, key=lambda row: row["card_id"])[0])


def _blank_row(rows: Sequence[Mapping[str, str]], variant: Mapping[str, str], mode: str) -> dict[str, str]:
    row = _template_row(rows, variant)
    row.update(
        card_id=variant["blank_id"],
        name="",
        flavor_text="",
        project_goal="",
        notes="",
        test_notes="",
        editorial_tags="",
        motif_origin="",
        visual_motif="",
        mechanical_role="",
    )
    # A project factor's rule is fixed by its family — "Erfüllt eine
    # Team-Anforderung." and its three siblings — so the blank carries it
    # pre-printed and the participant supplies only title, flavor and image.
    # Every other type writes its own rule and starts empty.
    if variant["card_type"] != "Projektfaktor":
        row["rules_text"] = ""
    if variant["card_type"] == "Ereignis":
        # Keeps polarity, which the renderer requires but never draws (ADR 0018),
        # and drops the E1-E8 symbol so the slot stays open.
        row["effect_template"] = ""
    if variant["card_type"] == "Projekt":
        row["requirements"] = BLANK_PROJECT_REQUIREMENTS
        row["points"] = ""
    row["_render_mode"] = mode
    return row


def blank_artwork(path: Path, mapping: Mapping[str, Any], width: int = 1068) -> Path:
    """Write the flat paper field that stands in for the drawn illustration."""

    if width % 3:
        raise BlankError("Die Blankofläche braucht eine durch 3 teilbare Breite")
    colour = rc._color(mapping, "background/paper")
    rgb = tuple(int(colour.lstrip("#")[index : index + 2], 16) for index in (0, 2, 4))
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, width * 2 // 3), rgb).save(path)
    return path


def _neutralise_rarity(root: ET.Element, mapping: Mapping[str, Any]) -> None:
    """Say BLANKO instead of a rarity and leave every pip an empty outline."""

    for element in _by_role(root, "footer-rarity"):
        _set_text(element, RARITY_LABEL)
    marks = _by_role(root, "rarity-mark")
    empty = next((mark for mark in marks if mark.attrib.get("data-state") == "empty"), None)
    if empty is None:
        return
    stroke = empty.attrib.get("stroke", rc._color(mapping, "line/highlight"))
    stroke_width = empty.attrib.get("stroke-width", "1")
    inset = float(stroke_width) / 2
    for mark in marks:
        if mark.attrib.get("data-state") != "filled":
            continue
        mark.set("x", f"{float(mark.attrib['x']) + inset:g}")
        mark.set("y", f"{float(mark.attrib['y']) + inset:g}")
        mark.set("width", f"{float(mark.attrib['width']) - 2 * inset:g}")
        mark.set("height", f"{float(mark.attrib['height']) - 2 * inset:g}")
        mark.set("fill", "none")
        mark.set("stroke", stroke)
        mark.set("stroke-width", stroke_width)
        mark.set("data-state", "empty")
    for group in _by_role(root, "card-footer"):
        group.set("data-rarity-filled", "0")


def _open_slots(root: ET.Element, card_type: str) -> None:
    """Drop the values a participant supplies, keeping their carriers."""

    parents = _parent_map(root)
    if card_type == "Ereignis":
        for element in _by_role(root, "event-keyword"):
            _set_text(element, "")
    if card_type == "Projekt":
        # The domain of a project is thematic, not mechanical, so it stays the
        # participant's choice; the requirement slots stay empty circles.
        for role in ("project-requirement-symbol", "project-points-label", "project-family-symbol"):
            for element in _by_role(root, role):
                parent = parents.get(element)
                if parent is not None:
                    parent.remove(element)
        for role in ("project-requirements-text", "project-goal-text", "card-category"):
            for element in _by_role(root, role):
                _set_text(element, "")


def _writing_lines(root: ET.Element, mapping: Mapping[str, Any]) -> None:
    """Draw the faint baselines the card is written on.

    The content panel gets them only where it is otherwise empty.  A factor
    card carries the family emblem across that field, and ruling over a
    watermark gives two competing grids instead of one writing surface, so
    those blanks keep the title rule and leave the panel to the emblem.
    """

    ink = rc._color(mapping, "line/default")

    def rule(parent: ET.Element, x1: float, y: float, x2: float, role: str) -> None:
        rc._element(
            parent,
            "line",
            x1=x1,
            y1=y,
            x2=x2,
            y2=y,
            stroke=ink,
            stroke_width=WRITING_LINE_WIDTH,
            opacity=WRITING_LINE_OPACITY,
            data_role=role,
        )

    titles = _by_role(root, "card-title")
    panels = _by_role(root, "content-panel")
    if not titles or not panels:
        raise BlankError("Titel- oder Inhaltsfläche fehlt im gerenderten Blanko")
    title = titles[0]
    panel = panels[0]
    panel_x = float(panel.attrib["x"])
    panel_y = float(panel.attrib["y"])
    panel_width = float(panel.attrib["width"])
    panel_height = float(panel.attrib["height"])

    parents = _parent_map(root)
    title_parent = parents.get(title, root)
    title_x = float(title.attrib["x"])
    title_y = float(title.attrib["y"])
    rule(title_parent, title_x, title_y + 4, panel_x + panel_width - TITLE_LINE_INSET, "blank-title-rule")

    if _by_role(root, "factor-family-emblem-symbol"):
        return

    panel_parent = parents.get(panel, root)
    step = panel_height / (CONTENT_LINE_COUNT + 1)
    for index in range(1, CONTENT_LINE_COUNT + 1):
        rule(
            panel_parent,
            panel_x + CONTENT_LINE_INSET,
            panel_y + index * step,
            panel_x + panel_width - CONTENT_LINE_INSET,
            f"blank-content-rule-{index}",
        )


def build_blank_svg(
    variant: Mapping[str, str],
    rows: Sequence[Mapping[str, str]],
    profile: Mapping[str, Any],
    mapping: Mapping[str, Any],
    artwork_path: Path,
    mode: str,
) -> bytes:
    """Build one blank front and open every field a participant fills in."""

    row = _blank_row(rows, variant, mode)
    svg_bytes = rc.build_card_svg(row, profile, artwork_path, proof=False)
    root = ET.fromstring(svg_bytes)
    _neutralise_rarity(root, mapping)
    _open_slots(root, variant["card_type"])
    _writing_lines(root, mapping)
    root.set("data-blank", variant["blank_id"])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def render_blanks(
    *,
    profile_path: str | Path = rc.DEFAULT_PROFILE,
    csv_path: str | Path = rc.DEFAULT_CARDS,
    output_dir: str | Path = DEFAULT_OUTPUT,
    variants: Sequence[Mapping[str, str]] = BLANK_VARIANTS,
    mode: str = "preview",
    keep_svg: bool = True,
) -> dict[str, Any]:
    """Render every blank variant as PNG and SVG plus a hash manifest."""

    if mode not in {"preview", "print"}:
        raise BlankError(f"Unbekannter Modus: {mode}")
    profile = rc.load_profile(profile_path)
    mapping = rc._load_layout()
    rows = rc.load_cards(csv_path)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    svg_dir = destination / "svg"
    if keep_svg:
        svg_dir.mkdir(parents=True, exist_ok=True)
    artwork_path = blank_artwork(destination / "blank-field.png", mapping)

    width = profile["upload_png"]["width"]
    height = profile["upload_png"]["height"]
    manifest: dict[str, Any] = {
        "schema": "dhk-blank-render-manifest/v1",
        "renderer_version": rc.RENDERER_VERSION,
        "mode": mode,
        "profile_sha256": profile["_sha256"],
        "layout_config_sha256": mapping["_sha256"],
        "cards": [],
    }
    for variant in variants:
        svg_bytes = build_blank_svg(variant, rows, profile, mapping, artwork_path, mode)
        png_bytes = rc.finalize_png(rc.rasterize_svg(svg_bytes, width, height), profile)
        png_path = destination / f"{variant['blank_id']}.png"
        png_path.write_bytes(png_bytes)
        if keep_svg:
            (svg_dir / f"{variant['blank_id']}.svg").write_bytes(svg_bytes)
        inspection = rc.inspect_png(png_bytes, profile)
        manifest["cards"].append(
            {
                "card_id": variant["blank_id"],
                "label": variant["label"],
                "card_type": variant["card_type"],
                "factor_family": variant["factor_family"],
                "png_sha256": inspection["sha256"],
                "png_bytes": inspection["bytes"],
            }
        )
    (destination / "manifest.json").write_bytes(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    )
    return manifest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Blanko-Karten für den Konferenzstand rendern")
    parser.add_argument("--profile", type=Path, default=rc.DEFAULT_PROFILE)
    parser.add_argument("--cards", type=Path, default=rc.DEFAULT_CARDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mode", choices=("preview", "print"), default="preview")
    parser.add_argument("--no-svg", action="store_true", help="Nur PNG und Manifest schreiben")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = render_blanks(
            profile_path=args.profile,
            csv_path=args.cards,
            output_dir=args.output,
            mode=args.mode,
            keep_svg=not args.no_svg,
        )
    except (BlankError, rc.RenderError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    for card in manifest["cards"]:
        print(f"{card['card_id']}  {card['label']}")
    print(f"{len(manifest['cards'])} Blanko-Varianten nach {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
