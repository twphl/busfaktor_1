#!/usr/bin/env python3
"""Render the shared DHK card back from the same geometry as the front.

The back is a field of horizontally set DH, RSE, and RDM vocabulary carrying a
central seal.  It keeps the outer bleed, the black card body, whose rounded
inner field carries the same deep black as the surrounding frame instead of the
front's anthracite gradient, a thin light hairline just inside the internal DHK
safe area, and a lozenge riding each corner chamfer.

Three decisions carry the design:

*   **The lines are held inside the anthracite.**  They are clipped by the
    chamfered field the frame encloses, never by the trim, so the black border
    stays a border instead of becoming a bleed.
*   **No line begins or ends in view.**  Each run is built longer than the field
    and started left of it by a per-line phase, so the clip is the only thing
    that ever cuts a term and the text reads as endless rather than as a wrapped
    paragraph.
*   **The rhythm is solved from the field, not imposed on it.**  ``y`` is a
    baseline, so it is the outermost line's cap top — not its baseline — that has
    to clear the frame.  Spacing on a fixed pitch and hoping leaves that
    clearance to chance; at some sizes the outer line lands a fraction of a unit
    inside the frame and gets shaved.  The outermost baseline is therefore placed
    at the clearance it needs, the line count is rounded off the target pitch, and
    the pitch is solved to hit that position exactly.

Nothing on the back is larger than the front's footer type or lighter than its
``text/on-dark-muted``, which is the front's own answer to how loud text on
anthracite may be.

The motif is authored as one half and drawn again rotated 180 degrees, so the
back is point-symmetric by construction: a card in a face-down pile cannot
betray its orientation.  The seal follows the same rule — one otter head and one
half of its microtext ring are authored, the half turn supplies the rest, which
is the oldest solution in the deck-of-cards trade for putting a readable figure
on a face that has no upright.

Every content plate of the front renderer (title, type line, artwork, rules,
flavor, footer) is left out.

Geometry, colours, and the PNG contract are imported from ``render_cards`` so
front and back cannot drift apart.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image

from render_cards import (
    DEFAULT_PROFILE,
    INNER_CARD_FIELD_INSET,
    INNER_CARD_FIELD_RADIUS,
    ROOT,
    RenderError,
    _attr_number,
    _color,
    _element,
    _ellipse,
    _font,
    _json_bytes,
    _load_layout,
    _rect,
    _resolve_fonts,
    _sha256_file,
    _sha256_bytes,
    _tool_versions,
    _tracking_for_text,
    _typography_steps,
    finalize_png,
    inspect_png,
    load_profile,
    rasterize_svg,
)


DEFAULT_OUTPUT = ROOT / "build" / "card-back"
BACK_VERSION = "0.13.0"
BACK_ID = "card-back"
FRAME_HAIRLINE_STROKE_WIDTH = 1.5  # master px = about 0.13 mm
FRAME_HAIRLINE_COLOR_TOKEN = "line/highlight"
# Extra inset beyond the internal DHK safe.  Past the card body's corner
# centre a concentric radius would be negative, so the frame trades its
# rounding for a chamfer — which is what the corner ornament then sits on.
FRAME_HAIRLINE_INSET = 10.0
FRAME_CHAMFER = 30.0  # length the chamfer cuts off each axis at a corner
FRAME_CORNER_GAP = 11.0  # half-length of the break, matched to the lozenge tips
# The field the frame encloses is lifted one step off the surrounding black,
# so the back gains the same inside/outside order the front has.
FRAME_FIELD_TOKEN = "background/shell-raised-bottom"
FIELD_CLIP_ID = "back-field-clip"

# The vocabulary of the field the game is about, set as a running texture.
# All-caps throughout so the pattern keeps one texture; RO-Crate and BagIt are
# therefore set as RO-CRATE and BAGIT.
PATTERN_TERMS = (
    "TEI",
    "IIIF",
    "FAIR",
    "LOD",
    "RDF",
    "OAI-PMH",
    "DOI",
    "SPARQL",
    "METS",
    "ORCID",
    "CIDOC-CRM",
    "MODS",
    "JSON-LD",
    "EAD",
    "SKOS",
    "XML",
    "ALTO",
    "SHACL",
    "GND",
    "XSLT",
    "RO-CRATE",
    "OCR",
    "OAIS",
    "HTR",
    "BAGIT",
    "NER",
    "DMP",
    "UTF-8",
    "PID",
)
PATTERN_SEPARATOR = "   "  # the gap between two terms, measured as real glyphs
PATTERN_TRACKING_REFERENCE = "ABC"  # any all-caps token: tracking is a ratio of the size
# Uppercase tracking is applied whichever family is chosen: the reason for it —
# caps set too tight — does not depend on whether the face has serifs.
PATTERN_FONT_ROLE = "sans_bold"  # "sans_bold", "sans_regular", "bold", "regular", "italic"
PATTERN_FONT_FACES = {
    "sans_bold": ("Noto Sans", "700", "normal"),
    "sans_regular": ("Noto Sans", "400", "normal"),
    "bold": ("Noto Serif", "700", "normal"),
    "regular": ("Noto Serif", "400", "normal"),
    "italic": ("Noto Serif", "400", "italic"),
}
# The front's footer sets its brand line at 14.3 and its card identity at 16.7
# master units.  16 lands between them, so the back's loudest type is the front's
# quietest — a register the printed proof has already been through.
PATTERN_SIZE = 16.0
PATTERN_COLOR_TOKEN = "text/on-dark-muted"
PATTERN_PITCH_RATIO = 2.3  # target line pitch as a multiple of the type size
PATTERN_EDGE_CLEARANCE_RATIO = 0.85  # clear space above the outer cap, in cap heights
# How far inside the frame the text field ends, in cap heights.  Without it the
# clip sits on the hairline and every line is cut exactly on the drawn frame.
# The lines are meant to be cut — that is what makes them endless — but the cut
# needs air, the same way the outer line needs air above its caps.
PATTERN_FIELD_PADDING_RATIO = 0.85
# Phase and overhang are ratios of the field width.  The overhang has to cover
# the largest phase plus a whole term on each side, or a line end could wander
# into view at the very edge of the clip.
PATTERN_PHASE_PITCH_RATIO = 0.55
PATTERN_OVERHANG_RATIO = 0.25
# An irrational step keeps the phases from repeating down the block, so the
# lines never settle into visible columns.
PATTERN_PHASE_STEP = 0.618034

# The seal.  Radii are ratios of SEAL_RADIUS so the whole mark scales as one.
SEAL_RADIUS = 130.0
# The halo the seal clears out of the running lines, as a multiple of the field
# padding.  Tying it to the same measure keeps the two margins in step when the
# type size changes.  It sits below 1 because the seal is a filled mark rather
# than an edge: the rim already separates it from the text, so it needs less air
# than the frame does.
SEAL_KNOCKOUT_PADDING_RATIO = 0.68
SEAL_RING_TEXT_RADIUS_RATIO = 0.80
# One type size on the whole back, and it is the front's footer register.  The
# seal is not allowed a louder voice than the field it sits in.
SEAL_RING_TEXT_SIZE = PATTERN_SIZE
# What the ring says has to be something the field cannot say.  Drawing it from
# PATTERN_TERMS made the seal repeat the vocabulary already running behind it,
# which is a seal saying nothing.  An inscription names the issuing body — here
# the game and its imprint — so this is deliberately its own list.
#
# It is also a hard character budget: the ring is authored over 180 degrees and
# repeated by the half turn, so the inscription must be complete within half the
# circumference.  At this size that is about 37 characters.  Spelling the three
# domains out costs 80 and would need either 0.6 mm type or a seal wider than the
# card, which is why they stay abbreviated elsewhere and absent here.
SEAL_RING_TERMS = ("BUSFAKTOR: 1", "DH", "RSE", "RDM")
SEAL_RING_TRACKING_BAND = (0.92, 1.35)  # tolerated stretch of the fitted advance
SEAL_INNER_RADIUS_RATIO = 0.66
SEAL_INNER_KEYLINE_INSET = 5.0
SEAL_DIVISION_RULE_RATIO = 0.78  # half-width of the rule the two heads meet at
SEAL_RING_SEPARATOR = " · "
SEAL_RING_OPACITY = 0.9
SEAL_ART_PATH = ROOT / "data" / "assets" / "images" / "otter_head.png"
SEAL_ART_ID = "seal-otter-art"
SEAL_ART_WIDTH = 86.0  # master px across one head
SEAL_ART_OVERSAMPLE = 2  # embedded pixels per upload pixel
SEAL_ART_OFFSET_RATIO = 0.44  # head centre, as a share of the inner radius
# Inside the seal the artwork sits on paper, so it takes the front's paper and
# ink rather than the cream and black it wears on a dark ground.
SEAL_ART_LIGHT_TOKEN = "background/paper-raised"
SEAL_ART_DARK_TOKEN = "text/primary"
# The ramp is anchored on the two dominant tones, not on the extremes or on
# percentiles: the artwork is essentially two-tone, so the most common dark
# value and the most common light value *are* its ink and its paper.  Anchoring
# anywhere else leaves the head a shade off the card's own paper, because a few
# near-white eye highlights sit above the paper tone.
SEAL_ART_TONE_SPLIT = 128


def _back_renderer_sha256() -> str:
    return _sha256_file(Path(__file__).resolve())


def _draw_frame(
    root: ET.Element,
    profile: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> dict[str, float]:
    """Draw the three frame layers the back shares with every front."""

    view_box = profile["master_svg"]["view_box"]
    rectangles = profile["master_svg"]["rectangles"]
    trim_box = rectangles["trim"]
    vendor_safe_box = rectangles["vendor_safe"]

    _rect(
        root,
        0,
        0,
        view_box[2],
        view_box[3],
        fill=_color(mapping, "background/outer-bleed"),
        role="full-bleed-background",
    )
    _rect(
        root,
        trim_box["x"],
        trim_box["y"],
        trim_box["width"],
        trim_box["height"],
        fill=_color(mapping, "background/shell"),
        role="trim-background",
    )
    inner_card_box = {
        "x": vendor_safe_box["x"] + INNER_CARD_FIELD_INSET,
        "y": vendor_safe_box["y"] + INNER_CARD_FIELD_INSET,
        "width": vendor_safe_box["width"] - 2 * INNER_CARD_FIELD_INSET,
        "height": vendor_safe_box["height"] - 2 * INNER_CARD_FIELD_INSET,
    }
    _rect(
        root,
        inner_card_box["x"],
        inner_card_box["y"],
        inner_card_box["width"],
        inner_card_box["height"],
        fill=_color(mapping, "background/shell"),
        radius=INNER_CARD_FIELD_RADIUS,
        role="inner-card-field",
    ).set("data-fill-mode", "flat-shell-black")
    _draw_inner_hairline(root, profile, mapping, inner_card_box)
    return inner_card_box


def _frame_box(safe_box: Mapping[str, float]) -> dict[str, float]:
    """Centre-line rectangle of the frame, inset inside the internal DHK safe."""

    inset = FRAME_HAIRLINE_INSET + FRAME_HAIRLINE_STROKE_WIDTH / 2
    return {
        "left": safe_box["x"] + inset,
        "top": safe_box["y"] + inset,
        "right": safe_box["x"] + safe_box["width"] - inset,
        "bottom": safe_box["y"] + safe_box["height"] - inset,
    }


def _corner_chamfers(box: Mapping[str, float]) -> list[dict[str, Any]]:
    """The four cut corners, each as its two endpoints and its midpoint."""

    chamfer = FRAME_CHAMFER
    corners = (
        ("top-left", box["left"] + chamfer, box["top"], box["left"], box["top"] + chamfer),
        ("top-right", box["right"] - chamfer, box["top"], box["right"], box["top"] + chamfer),
        (
            "bottom-right",
            box["right"],
            box["bottom"] - chamfer,
            box["right"] - chamfer,
            box["bottom"],
        ),
        ("bottom-left", box["left"], box["bottom"] - chamfer, box["left"] + chamfer, box["bottom"]),
    )
    result = []
    for name, x1, y1, x2, y2 in corners:
        length = math.hypot(x2 - x1, y2 - y1)
        result.append(
            {
                "name": name,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "mid_x": (x1 + x2) / 2,
                "mid_y": (y1 + y2) / 2,
                "angle": math.degrees(math.atan2(y2 - y1, x2 - x1)),
                "unit_x": (x2 - x1) / length,
                "unit_y": (y2 - y1) / length,
            }
        )
    return result


def _inset_field(box: Mapping[str, float], inset: float) -> tuple[dict[str, float], float]:
    """Offset the chamfered outline inwards by a uniform distance.

    Keeping the chamfer length while pulling the sides in would move the diagonal
    edge by ``inset * sqrt(2)`` instead of ``inset``, so the offset outline would
    not stay parallel to the frame at the corners.  The chamfer therefore shrinks
    by ``inset * (2 - sqrt(2))``, which is what a true uniform offset costs it.
    """

    chamfer = FRAME_CHAMFER - inset * (2 - math.sqrt(2))
    if chamfer <= 0:
        raise RenderError(
            f"Feldabstand {inset} frisst die Fase von {FRAME_CHAMFER} Einheiten auf"
        )
    inner = {
        "left": box["left"] + inset,
        "top": box["top"] + inset,
        "right": box["right"] - inset,
        "bottom": box["bottom"] - inset,
    }
    if inner["left"] >= inner["right"] or inner["top"] >= inner["bottom"]:
        raise RenderError(f"Feldabstand {inset} lässt kein Textfeld übrig")
    return inner, chamfer


def _frame_field_path(box: Mapping[str, float], chamfer: float = FRAME_CHAMFER) -> str:
    """The closed chamfered outline, used to fill the field the frame encloses."""

    return (
        f"M {_attr_number(box['left'] + chamfer)} {_attr_number(box['top'])} "
        f"H {_attr_number(box['right'] - chamfer)} "
        f"L {_attr_number(box['right'])} {_attr_number(box['top'] + chamfer)} "
        f"V {_attr_number(box['bottom'] - chamfer)} "
        f"L {_attr_number(box['right'] - chamfer)} {_attr_number(box['bottom'])} "
        f"H {_attr_number(box['left'] + chamfer)} "
        f"L {_attr_number(box['left'])} {_attr_number(box['bottom'] - chamfer)} "
        f"V {_attr_number(box['top'] + chamfer)} Z"
    )


def _frame_path(box: Mapping[str, float], chamfers: Sequence[Mapping[str, Any]]) -> str:
    """Draw the frame as open runs, leaving a break at every corner ornament."""

    chamfer = FRAME_CHAMFER
    segments = [
        f"M {_attr_number(box['left'] + chamfer)} {_attr_number(box['top'])} "
        f"H {_attr_number(box['right'] - chamfer)}",
        f"M {_attr_number(box['right'])} {_attr_number(box['top'] + chamfer)} "
        f"V {_attr_number(box['bottom'] - chamfer)}",
        f"M {_attr_number(box['right'] - chamfer)} {_attr_number(box['bottom'])} "
        f"H {_attr_number(box['left'] + chamfer)}",
        f"M {_attr_number(box['left'])} {_attr_number(box['bottom'] - chamfer)} "
        f"V {_attr_number(box['top'] + chamfer)}",
    ]
    for corner in chamfers:
        for start_x, start_y, sign in (
            (corner["x1"], corner["y1"], 1),
            (corner["x2"], corner["y2"], -1),
        ):
            stop_x = corner["mid_x"] - sign * corner["unit_x"] * FRAME_CORNER_GAP
            stop_y = corner["mid_y"] - sign * corner["unit_y"] * FRAME_CORNER_GAP
            segments.append(
                f"M {_attr_number(start_x)} {_attr_number(start_y)} "
                f"L {_attr_number(stop_x)} {_attr_number(stop_y)}"
            )
    return " ".join(segments)


def _draw_inner_hairline(
    root: ET.Element,
    profile: Mapping[str, Any],
    mapping: Mapping[str, Any],
    inner_card_box: Mapping[str, float],
) -> None:
    """Draw the frame line, chamfered at the corners and broken for the ornaments.

    Everything stays inside the internal DHK safe by ``FRAME_HAIRLINE_INSET``.
    The line is otherwise continuous: the running text is held inside the field
    it encloses, so nothing crosses it and it needs no gaps of its own.
    """

    del inner_card_box
    safe_box = profile["master_svg"]["rectangles"]["internal_text_safe"]
    box = _frame_box(safe_box)
    _element(
        root,
        "path",
        d=_frame_field_path(box),
        fill=_color(mapping, FRAME_FIELD_TOKEN),
        data_role="frame-field",
        data_color_token=FRAME_FIELD_TOKEN,
    )
    _element(
        root,
        "path",
        d=_frame_path(box, _corner_chamfers(box)),
        fill="none",
        stroke=_color(mapping, FRAME_HAIRLINE_COLOR_TOKEN),
        stroke_width=FRAME_HAIRLINE_STROKE_WIDTH,
        stroke_linecap="butt",
        data_role="inner-frame-hairline",
        data_color_token=FRAME_HAIRLINE_COLOR_TOKEN,
        data_bounded_by="internal_text_safe",
        data_inset=FRAME_HAIRLINE_INSET,
        data_box_left=box["left"],
        data_box_top=box["top"],
        data_box_right=box["right"],
        data_box_bottom=box["bottom"],
    )


def _draw_corner_ornament(parent: ET.Element, corner: Mapping[str, Any], ink: str) -> None:
    """A lozenge riding the chamfer, in the same weight as the frame itself."""

    group = _element(
        parent,
        "g",
        transform=(
            f"translate({_attr_number(corner['mid_x'])} {_attr_number(corner['mid_y'])}) "
            f"rotate({_attr_number(round(corner['angle'], 4))})"
        ),
        data_role="frame-corner-ornament",
        data_corner=corner["name"],
    )
    _element(
        group,
        "path",
        d="M -11 0 L 0 -6.5 L 11 0 L 0 6.5 Z",
        fill="none",
        stroke=ink,
        stroke_width=FRAME_HAIRLINE_STROKE_WIDTH,
        stroke_linejoin="miter",
        data_role="corner-lozenge",
    )
    _element(group, "path", d="M -3.4 0 L 0 -2 L 3.4 0 L 0 2 Z", fill=ink, data_role="corner-pip")


def _card_centre(
    view_box: Sequence[float], inner_card_box: Mapping[str, float]
) -> tuple[float, float]:
    """Return the centre the back is point-symmetric about, and prove it is one.

    Bleed, trim, and the inner card field all have to share a centre; if they
    ever stop doing so, a motif built as half plus its rotated copy would no
    longer be symmetric about anything meaningful.
    """

    centre = (view_box[2] / 2, view_box[3] / 2)
    inner_centre = (
        inner_card_box["x"] + inner_card_box["width"] / 2,
        inner_card_box["y"] + inner_card_box["height"] / 2,
    )
    if max(abs(a - b) for a, b in zip(centre, inner_centre)) > 0.01:
        raise RenderError(
            f"Innenfeld-Mitte {inner_centre} weicht von der Kartenmitte {centre} ab; "
            "eine punktsymmetrische Rückseite ist so nicht konstruierbar"
        )
    return centre


def _cap_metrics(fonts: Mapping[str, Path], role: str, size: float) -> tuple[float, float]:
    """Return how far the caps rise above the baseline, and their height.

    Measured from an all-caps reference rather than from any one term, so the
    clearance the frame is given does not change when the vocabulary changes.
    """

    font = _font(fonts, role, size)
    _, top, _, bottom = (value / 4 for value in font.getbbox(PATTERN_TRACKING_REFERENCE))
    if bottom <= top:
        raise RenderError("Musterschrift lässt sich nicht vermessen")
    ascent = font.getmetrics()[0] / 4
    return ascent - top, bottom - top


def _band_geometry(
    fonts: Mapping[str, Path],
    view_box: Sequence[float],
    inner_card_box: Mapping[str, float],
    safe_box: Mapping[str, float],
) -> dict[str, Any]:
    """Solve the line rhythm, the run length, and the phase of every line.

    Only the upper half is authored; the lower half is that same group rotated
    180 degrees about the card centre, which is what makes the back
    point-symmetric by construction instead of by arithmetic.
    """

    if PATTERN_SIZE <= 0:
        raise RenderError(f"PATTERN_SIZE muss positiv sein, ist aber {PATTERN_SIZE}")
    centre_x, centre_y = _card_centre(view_box, inner_card_box)
    box = _frame_box(safe_box)
    cap_rise, cap_height = _cap_metrics(fonts, PATTERN_FONT_ROLE, PATTERN_SIZE)
    tracking = _tracking_for_text(PATTERN_TRACKING_REFERENCE, PATTERN_SIZE, "Noto Sans")

    # The clip, not the frame, is the boundary of the text field.  Solving the
    # rhythm against the frame while clipping inside it would shave the outer
    # line by exactly the padding.
    padding = cap_rise * PATTERN_FIELD_PADDING_RATIO
    clip_box, clip_chamfer = _inset_field(box, padding)

    clearance = cap_rise * PATTERN_EDGE_CLEARANCE_RATIO
    outermost_baseline = clip_box["top"] + clearance + cap_rise
    reach = centre_y - outermost_baseline
    if reach <= 0:
        raise RenderError(
            f"Schriftgrad {PATTERN_SIZE} lässt zwischen Rahmen und Kartenmitte keine Zeile zu"
        )
    half_lines = max(1, round(reach / (PATTERN_SIZE * PATTERN_PITCH_RATIO) + 0.5))
    pitch = reach / (half_lines - 0.5) if half_lines > 1 else reach * 2
    if pitch <= cap_height:
        raise RenderError(
            f"Zeilenabstand {pitch:.1f} ist nicht größer als die Versalhöhe "
            f"{cap_height:.1f} — die Zeilen berühren sich"
        )
    baselines = [centre_y - pitch * (step + 0.5) for step in range(half_lines)]

    extent = clip_box["right"] - clip_box["left"]
    phase_pitch = extent * PATTERN_PHASE_PITCH_RATIO
    overhang = phase_pitch + extent * PATTERN_OVERHANG_RATIO
    span = extent + 2 * overhang
    stride = max(1, len(PATTERN_TERMS) // 3)
    runs = [
        _build_run(fonts, tracking, span, index * stride) for index in range(half_lines)
    ]
    phases = [
        (index * phase_pitch * PATTERN_PHASE_STEP) % phase_pitch for index in range(half_lines)
    ]
    return {
        "baselines": baselines,
        "box": box,
        "cap_height": cap_height,
        "cap_rise": cap_rise,
        "centre_x": centre_x,
        "centre_y": centre_y,
        "clearance": clearance,
        "clip_box": clip_box,
        "clip_chamfer": clip_chamfer,
        "padding": padding,
        "extent": extent,
        "half_lines": half_lines,
        "overhang": overhang,
        "phases": phases,
        "pitch": pitch,
        "runs": runs,
        "span": span,
        "tracking": tracking,
    }


def _build_run(
    fonts: Mapping[str, Path],
    tracking: float,
    span: float,
    start_index: int,
) -> tuple[str, float]:
    """Cycle through the vocabulary until the line overruns the field on both sides.

    Each line starts at a different point in the cycle, so no term ever sits
    directly above its own repetition and the texture reads as running prose
    rather than as a grid.
    """

    font = _font(fonts, PATTERN_FONT_ROLE, PATTERN_SIZE)
    terms: list[str] = []
    width = 0.0
    index = start_index
    while width < span:
        terms.append(PATTERN_TERMS[index % len(PATTERN_TERMS)])
        index += 1
        run = PATTERN_SEPARATOR.join(terms)
        width = font.getlength(run) / 4 + len(run) * tracking
        if len(terms) > 400:
            raise RenderError("Musterzeile wird nicht lang genug — Term zu schmal?")
    return PATTERN_SEPARATOR.join(terms), width


def _draw_both_halves(
    parent: ET.Element,
    geometry: Mapping[str, Any],
    build: Any,
    *,
    role: str,
) -> None:
    """Emit ``build`` twice: as authored, and rotated 180 degrees about the centre.

    Point symmetry is thereby a property of the drawing code, not a number that
    could drift.  Anything drawn through this helper is symmetric or nothing is.
    """

    half_turn = (
        f"rotate(180 {_attr_number(geometry['centre_x'])} "
        f"{_attr_number(geometry['centre_y'])})"
    )
    for half, transform in (("authored", None), ("half-turn", half_turn)):
        group = _element(
            parent,
            "g",
            transform=transform,
            data_role=role,
            data_symmetry_half=half,
        )
        build(group)


def _define_field_clip(defs: ET.Element, geometry: Mapping[str, Any]) -> None:
    """The chamfered field is what cuts the lines — never the trim.

    It runs parallel to the frame, one padding inside it, so the cut never lands
    on the drawn hairline.
    """

    clip = _element(
        defs,
        "clipPath",
        id=FIELD_CLIP_ID,
        data_role="field-clip",
        data_padding=round(geometry["padding"], 3),
    )
    _element(
        clip,
        "path",
        d=_frame_field_path(geometry["clip_box"], geometry["clip_chamfer"]),
    )


def _draw_bands(
    root: ET.Element,
    mapping: Mapping[str, Any],
    geometry: Mapping[str, Any],
) -> dict[str, Any]:
    """Set the vocabulary as horizontal runs that overrun the field on both sides."""

    field = _element(
        root,
        "g",
        clip_path=f"url(#{FIELD_CLIP_ID})",
        data_role="back-band-field",
    )

    def build(group: ET.Element) -> None:
        # The clip must sit on the untransformed host above.  On the rotated
        # group it would be read in that group's coordinate system and cut the
        # field along a rotated outline, which is not the frame.
        lines = _element(
            group,
            "g",
            fill=_color(mapping, PATTERN_COLOR_TOKEN),
            font_family=PATTERN_FONT_FACES[PATTERN_FONT_ROLE][0],
            font_size=PATTERN_SIZE,
            font_weight=PATTERN_FONT_FACES[PATTERN_FONT_ROLE][1],
            font_style=PATTERN_FONT_FACES[PATTERN_FONT_ROLE][2],
            letter_spacing=geometry["tracking"] or None,
        )
        for index, baseline in enumerate(geometry["baselines"]):
            run, run_width = geometry["runs"][index]
            start = (
                geometry["clip_box"]["left"] - geometry["overhang"] + geometry["phases"][index]
            )
            _element(
                lines,
                "text",
                x=start,
                y=baseline,
                data_role="band-run",
                data_line=index,
                data_term_count=run.count(PATTERN_SEPARATOR) + 1,
                data_run_width=round(run_width, 3),
            ).text = run

    _draw_both_halves(field, geometry, build, role="back-band-half")

    return {
        "clipped_to": "frame-field inset by the field padding",
        "color_token": PATTERN_COLOR_TOKEN,
        "edge_clearance": round(geometry["clearance"], 3),
        "field_padding": round(geometry["padding"], 3),
        "line_count": 2 * geometry["half_lines"],
        "line_pitch": round(geometry["pitch"], 3),
        "outermost_baseline": round(geometry["baselines"][-1], 3),
        "overhang": round(geometry["overhang"], 3),
        "rotation_degrees": 0.0,
        "symmetry": "point (180 deg about the card centre)",
        "terms": list(PATTERN_TERMS),
        "terms_per_line": [run.count(PATTERN_SEPARATOR) + 1 for run, _ in geometry["runs"]],
        "type_size": PATTERN_SIZE,
    }


def _recolour_to_tokens(artwork: Image.Image, light: str, dark: str) -> Image.Image:
    """Map the artwork's own two tones onto the card's palette.

    A per-luminance lookup keeps every antialiased edge intact while forcing both
    ends of the ramp onto the tokens, so no second white creeps onto the card.
    """

    alpha = artwork.getchannel("A")
    luminance = artwork.convert("L")
    histogram = luminance.histogram(mask=alpha.point(lambda value: value > 200))
    total = sum(histogram)
    if not total:
        raise RenderError("Zierbild hat keine deckenden Pixel")

    split = SEAL_ART_TONE_SPLIT
    low = max(range(split), key=lambda value: histogram[value])
    high = split + max(range(256 - split), key=lambda value: histogram[split + value])
    if high <= low:
        raise RenderError("Zierbild hat keinen Tonwertumfang")
    light_rgb = tuple(int(light[index : index + 2], 16) for index in (1, 3, 5))
    dark_rgb = tuple(int(dark[index : index + 2], 16) for index in (1, 3, 5))
    channels = []
    for index in range(3):
        table = []
        for value in range(256):
            ratio = min(1.0, max(0.0, (value - low) / (high - low)))
            table.append(round(dark_rgb[index] + ratio * (light_rgb[index] - dark_rgb[index])))
        channels.append(luminance.point(table))
    return Image.merge("RGBA", (*channels, alpha))


def _seal_artwork(defs: ET.Element, mapping: Mapping[str, Any]) -> float:
    """Embed the otter head once, trimmed and resampled to the size it is used at.

    The source is far larger than the mark needs; embedding it whole would put
    megabytes of base64 into a card that is otherwise vector.  Downscaling is
    deterministic, so two runs still produce identical bytes.  The symbol is
    centred on its own origin, so both heads are one ``use`` and a rotation.
    """

    if not SEAL_ART_PATH.is_file():
        raise RenderError(f"Zierbild fehlt: {SEAL_ART_PATH}")
    with Image.open(SEAL_ART_PATH) as source:
        source.load()
        artwork = source.convert("RGBA")
        box = artwork.getchannel("A").getbbox()
        if box is None:
            raise RenderError(f"Zierbild ist vollständig transparent: {SEAL_ART_PATH}")
        artwork = artwork.crop(box)
        aspect = artwork.height / artwork.width
        # 2 upload px per master px, times the oversample factor.
        target_width = round(SEAL_ART_WIDTH * 2 * SEAL_ART_OVERSAMPLE)
        artwork = artwork.resize((target_width, round(target_width * aspect)), Image.LANCZOS)
        artwork = _recolour_to_tokens(
            artwork,
            _color(mapping, SEAL_ART_LIGHT_TOKEN),
            _color(mapping, SEAL_ART_DARK_TOKEN),
        )
    buffer = io.BytesIO()
    artwork.save(buffer, format="PNG", compress_level=9, optimize=False)
    payload = buffer.getvalue()
    height = SEAL_ART_WIDTH * aspect
    group = _element(
        defs,
        "g",
        id=SEAL_ART_ID,
        data_role="seal-artwork",
        data_source=SEAL_ART_PATH.name,
        data_source_sha256=_sha256_file(SEAL_ART_PATH),
        data_embedded_sha256=_sha256_bytes(payload),
    )
    _element(
        group,
        "image",
        x=-SEAL_ART_WIDTH / 2,
        y=-height / 2,
        width=SEAL_ART_WIDTH,
        height=height,
        preserveAspectRatio="xMidYMid meet",
        href="data:image/png;base64," + base64.b64encode(payload).decode("ascii"),
    )
    return height


def _seal_ring_run(fonts: Mapping[str, Path], radius: float, size: float) -> tuple[str, float]:
    """Set the inscription once, fitted to exactly half the ring.

    Half a turn is authored and repeated by rotation, so the run has to close on
    itself at 180 degrees.  Rather than leave a ragged join, the per-character
    advance is scaled by whatever it takes to land the run exactly on the
    half-circumference.

    That scale is also the design's own check: it is how much the inscription had
    to be stretched or squeezed to fit.  Far from 1 means the wrong text is in the
    wrong ring, and no amount of tracking will hide it — so it raises instead of
    silently setting an unreadable or gap-toothed ring.
    """

    font = _font(fonts, PATTERN_FONT_ROLE, size)
    limit = math.pi * radius
    run = SEAL_RING_SEPARATOR.join(SEAL_RING_TERMS) + SEAL_RING_SEPARATOR
    natural = font.getlength(run) / 4
    if natural <= 0:
        raise RenderError("Siegelumschrift lässt sich nicht vermessen")
    scale = limit / natural
    low, high = SEAL_RING_TRACKING_BAND
    if not low <= scale <= high:
        raise RenderError(
            f"Siegelumschrift passt nicht in den halben Ring: Sperrung {scale:.2f} "
            f"liegt außerhalb von {low}–{high}. {len(run)} Zeichen bei Grad {size} "
            f"brauchen {natural:.0f} Einheiten, verfügbar sind {limit:.0f}. "
            "Entweder die Umschrift kürzen oder den Siegelradius ändern."
        )
    return run, scale


def _draw_seal(
    root: ET.Element,
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    geometry: Mapping[str, Any],
    art_height: float,
) -> dict[str, Any]:
    """Draw the central seal: a microtext ring around two heads that meet at a rule.

    Everything that has an upright — the heads, the ring lettering — is authored
    once above the centre and repeated by the half turn.  The concentric shapes
    are point-symmetric on their own and are drawn once.
    """

    centre_x, centre_y = geometry["centre_x"], geometry["centre_y"]
    ink = _color(mapping, FRAME_HAIRLINE_COLOR_TOKEN)
    paper = _color(mapping, SEAL_ART_LIGHT_TOKEN)
    dark = _color(mapping, SEAL_ART_DARK_TOKEN)
    shell = _color(mapping, "background/shell")

    ring_text_radius = SEAL_RADIUS * SEAL_RING_TEXT_RADIUS_RATIO
    ring_text_size = SEAL_RING_TEXT_SIZE
    inner_radius = SEAL_RADIUS * SEAL_INNER_RADIUS_RATIO
    offset = inner_radius * SEAL_ART_OFFSET_RATIO
    if offset + art_height / 2 > inner_radius:
        raise RenderError(
            f"Siegelkopf ragt über das Innenfeld hinaus: {offset + art_height / 2:.1f} "
            f"gegen {inner_radius:.1f}"
        )

    seal = _element(root, "g", data_role="back-seal")
    knockout = SEAL_RADIUS + geometry["padding"] * SEAL_KNOCKOUT_PADDING_RATIO
    _ellipse(
        seal,
        centre_x - knockout,
        centre_y - knockout,
        2 * knockout,
        2 * knockout,
        fill=_color(mapping, FRAME_FIELD_TOKEN),
    ).set("data-role", "seal-knockout")
    _ellipse(
        seal,
        centre_x - SEAL_RADIUS,
        centre_y - SEAL_RADIUS,
        2 * SEAL_RADIUS,
        2 * SEAL_RADIUS,
        fill=shell,
        stroke=ink,
        stroke_width=FRAME_HAIRLINE_STROKE_WIDTH,
    ).set("data-role", "seal-rim")

    run, scale = _seal_ring_run(fonts, ring_text_radius, ring_text_size)
    font = _font(fonts, PATTERN_FONT_ROLE, ring_text_size)
    # Centre the first term on twelve o'clock, the way a legend is centred on a
    # coin.  Starting the run there instead would put the tail of the other half
    # at the top, so the eye would meet the inscription mid-phrase and read the
    # order wrong.
    lead = font.getlength(SEAL_RING_TERMS[0]) / 4 * scale
    ring_offset = -lead / 2

    def build_ring(group: ET.Element) -> None:
        lettering = _element(
            group,
            "g",
            fill=ink,
            font_family=PATTERN_FONT_FACES[PATTERN_FONT_ROLE][0],
            font_size=ring_text_size,
            font_weight=PATTERN_FONT_FACES[PATTERN_FONT_ROLE][1],
            text_anchor="middle",
            opacity=SEAL_RING_OPACITY,
            data_role="seal-ring-lettering",
        )
        cursor = ring_offset
        for character in run:
            advance = font.getlength(character) / 4 * scale
            if character != " ":
                theta = math.degrees((cursor + advance / 2) / ring_text_radius) - 90
                radians = math.radians(theta)
                _element(
                    lettering,
                    "text",
                    x=0,
                    y=0,
                    transform=(
                        f"translate("
                        f"{_attr_number(centre_x + ring_text_radius * math.cos(radians))} "
                        f"{_attr_number(centre_y + ring_text_radius * math.sin(radians))}) "
                        f"rotate({_attr_number(round(theta + 90, 4))})"
                    ),
                ).text = character
            cursor += advance

    _draw_both_halves(seal, geometry, build_ring, role="seal-ring-half")

    _ellipse(
        seal,
        centre_x - inner_radius,
        centre_y - inner_radius,
        2 * inner_radius,
        2 * inner_radius,
        fill=paper,
        stroke=ink,
        stroke_width=FRAME_HAIRLINE_STROKE_WIDTH,
    ).set("data-role", "seal-field")
    keyline = inner_radius - SEAL_INNER_KEYLINE_INSET
    _ellipse(
        seal,
        centre_x - keyline,
        centre_y - keyline,
        2 * keyline,
        2 * keyline,
        fill="none",
        stroke=dark,
        stroke_width=1.0,
        opacity=0.55,
    ).set("data-role", "seal-keyline")

    def build_head(group: ET.Element) -> None:
        _element(
            group,
            "use",
            href=f"#{SEAL_ART_ID}",
            transform=(
                f"translate({_attr_number(centre_x)} {_attr_number(centre_y - offset)})"
            ),
            data_role="seal-head",
        )

    _draw_both_halves(seal, geometry, build_head, role="seal-head-half")

    rule = inner_radius * SEAL_DIVISION_RULE_RATIO
    _element(
        seal,
        "line",
        x1=centre_x - rule,
        y1=centre_y,
        x2=centre_x + rule,
        y2=centre_y,
        stroke=dark,
        stroke_width=1.0,
        opacity=0.35,
        data_role="seal-division-rule",
    )

    return {
        "art_light_token": SEAL_ART_LIGHT_TOKEN,
        "art_source": SEAL_ART_PATH.name,
        "heads": 2,
        "inner_radius": inner_radius,
        "knockout_radius": knockout,
        "placement": "card centre",
        "radius": SEAL_RADIUS,
        "ring_inscription": list(SEAL_RING_TERMS),
        "ring_text_radius": ring_text_radius,
        "ring_text_size": ring_text_size,
        "ring_tracking_scale": round(scale, 4),
        "symmetry": "point (180 deg about the card centre)",
    }


def _draw_proof_guides(
    root: ET.Element, profile: Mapping[str, Any], mapping: Mapping[str, Any]
) -> None:
    proof_group = _element(root, "g", id="proof-guides", pointer_events="none")
    proof_size = _typography_steps(mapping, "proof_label")[0][0]
    guide_specs = (
        ("trim", "#00AEEF", "SCHNITT", 16, "start"),
        ("vendor_safe", "#E5007D", "LIEFERANTEN-SAFE", 16, "end"),
        ("internal_text_safe", "#F4B400", "DHK-SAFE +1 MM", 34, "start"),
    )
    for key, color, label, y_offset, anchor in guide_specs:
        box = profile["master_svg"]["rectangles"][key]
        _rect(
            proof_group,
            box["x"],
            box["y"],
            box["width"],
            box["height"],
            stroke=color,
            stroke_width=2,
            opacity=0.95,
            role=f"proof-{key}",
        )
        _element(
            proof_group,
            "text",
            x=box["x"] + 6 if anchor == "start" else box["x"] + box["width"] - 6,
            y=box["y"] + y_offset,
            fill=color,
            font_family="Noto Sans",
            font_size=proof_size,
            font_weight=700,
            letter_spacing=_tracking_for_text(label, proof_size, "Noto Sans"),
            text_anchor=anchor,
            data_role=f"proof-label-{key}",
        ).text = label


def build_back_svg(profile: Mapping[str, Any], proof: bool = False) -> bytes:
    """Create the self-contained SVG master of the card back."""

    mapping = _load_layout()
    fonts = _resolve_fonts()
    view_box = profile["master_svg"]["view_box"]

    root = ET.Element(
        _q_svg("svg"),
        {
            "version": "1.1",
            "width": "69.6mm",
            "height": "95mm",
            "viewBox": " ".join(str(value) for value in view_box),
            "data-renderer": f"dhk-card-back-renderer/{BACK_VERSION}",
            "data-card-id": BACK_ID,
            "data-face": "back",
        },
    )
    title = _element(root, "title")
    title.text = "DHK Kartenrückseite · Bandsatz mit Siegel"
    metadata = _element(root, "metadata")
    defs = _element(root, "defs")
    rectangles = profile["master_svg"]["rectangles"]
    vendor_safe_box = rectangles["vendor_safe"]
    inner_card_box = {
        "x": vendor_safe_box["x"] + INNER_CARD_FIELD_INSET,
        "y": vendor_safe_box["y"] + INNER_CARD_FIELD_INSET,
        "width": vendor_safe_box["width"] - 2 * INNER_CARD_FIELD_INSET,
        "height": vendor_safe_box["height"] - 2 * INNER_CARD_FIELD_INSET,
    }
    geometry = _band_geometry(
        fonts,
        view_box,
        inner_card_box,
        rectangles["internal_text_safe"],
    )
    _define_field_clip(defs, geometry)
    art_height = _seal_artwork(defs, mapping)

    inner_card_box = _draw_frame(root, profile, mapping)
    bands = _draw_bands(root, mapping, geometry)

    frame_corners = _corner_chamfers(_frame_box(rectangles["internal_text_safe"]))
    authored_corners = [
        corner for corner in frame_corners if corner["name"] in ("top-left", "top-right")
    ]
    ornament_ink = _color(mapping, FRAME_HAIRLINE_COLOR_TOKEN)

    def build_corners(group: ET.Element) -> None:
        for corner in authored_corners:
            _draw_corner_ornament(group, corner, ornament_ink)

    _draw_both_halves(root, geometry, build_corners, role="frame-corner-half")
    seal = _draw_seal(root, mapping, fonts, geometry, art_height)

    metadata.text = json.dumps(
        {
            "card_id": BACK_ID,
            "face": "back",
            "inner_card_field": {key: float(value) for key, value in inner_card_box.items()},
            "inner_frame_hairline": {
                "bounded_by": "internal_text_safe",
                "color_token": FRAME_HAIRLINE_COLOR_TOKEN,
                "continuous_except": "corner ornaments",
                "stroke_width": FRAME_HAIRLINE_STROKE_WIDTH,
            },
            "frame": {
                "corner_ornament": "lozenge on chamfer",
                "frame_chamfer": FRAME_CHAMFER,
                "frame_field_token": FRAME_FIELD_TOKEN,
                "frame_inset_beyond_dhk_safe": FRAME_HAIRLINE_INSET,
            },
            "seal": seal,
            "band_lines": dict(
                bands,
                font_role=PATTERN_FONT_ROLE,
                family=PATTERN_FONT_FACES[PATTERN_FONT_ROLE][0],
            ),
            "layout_config_sha256": mapping["_sha256"],
            "profile_sha256": profile.get("_sha256", ""),
            "renderer": BACK_VERSION,
            "renderer_sha256": _back_renderer_sha256(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    if proof:
        _draw_proof_guides(root, profile, mapping)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _q_svg(name: str) -> str:
    return "{http://www.w3.org/2000/svg}" + name


def render_back(
    *,
    profile_path: str | Path = DEFAULT_PROFILE,
    output_dir: str | Path = DEFAULT_OUTPUT,
    proof: bool = False,
    keep_svg: bool = True,
) -> dict[str, Any]:
    """Write the back PNG, its SVG master, and a hash manifest."""

    profile = load_profile(profile_path)
    mapping = _load_layout()
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    svg_bytes = build_back_svg(profile, proof=proof)
    width = profile["upload_png"]["width"]
    height = profile["upload_png"]["height"]
    png_bytes = finalize_png(rasterize_svg(svg_bytes, width, height), profile)
    png_path = destination / f"{BACK_ID}.png"
    png_path.write_bytes(png_bytes)
    if keep_svg:
        svg_dir = destination / "svg"
        svg_dir.mkdir(parents=True, exist_ok=True)
        (svg_dir / f"{BACK_ID}.svg").write_bytes(svg_bytes)

    inspection = inspect_png(png_bytes, profile)
    manifest = {
        "schema": "dhk-card-back-render-manifest/v1",
        "renderer_version": BACK_VERSION,
        "renderer_sha256": _back_renderer_sha256(),
        "proof": proof,
        "profile_sha256": profile["_sha256"],
        "source_template_sha256": profile["source_template"]["sha256"],
        "layout_config_sha256": mapping["_sha256"],
        "tools": _tool_versions(),
        "back": {
            "card_id": BACK_ID,
            "svg_sha256": _sha256_bytes(svg_bytes),
            "png_sha256": inspection["sha256"],
            "png_bytes": inspection["bytes"],
        },
    }
    (destination / "manifest.json").write_bytes(_json_bytes(manifest))
    return manifest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Erzeugt die DHK-Kartenrückseite: Bandsatz im Anthrazitfeld mit Siegel."
    )
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--proof", action="store_true", help="Schnitt- und Safe-Guides einblenden")
    parser.add_argument("--no-svg", action="store_true", help="Nur PNG und Manifest schreiben")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = render_back(
            profile_path=args.profile,
            output_dir=args.output,
            proof=args.proof,
            keep_svg=not args.no_svg,
        )
    except RenderError as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        return 1
    print(
        f"OK: Rückseite in {args.output} "
        f"(SVG-Master → {manifest['back']['png_bytes']} Bytes PNG, 1644×2244, 600 dpi, RGB/sRGB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
