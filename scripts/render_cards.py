#!/usr/bin/env python3
"""Render reproducible DHK card previews from the canonical CSV.

The SVG is the layout master.  The upload PNG is rasterised directly from that
master at 1644 x 2244 px, then normalised to opaque 8-bit sRGB with 600 dpi
metadata.
"""

from __future__ import annotations

import argparse
import base64
import copy
import csv
import hashlib
import io
import json
import re
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageCms, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "data" / "render_profile.json"
DEFAULT_CARDS = ROOT / "data" / "cards.csv"
DEFAULT_ARTWORK_DIR = ROOT / "data" / "cards"
DEFAULT_OUTPUT = ROOT / "build" / "cards-preview"
LAYOUT_PATH = ROOT / "data" / "card_layout.json"
ICON_ROOT = ROOT / "data" / "assets" / "icons"
ICON_MANIFEST_PATH = ICON_ROOT / "manifest.json"
ICON_KEYS = frozenset(
    {
        "team",
        "data",
        "operations",
        "methods",
        "joker",
        "project",
        "project_factor",
        "event",
        "inspect",
        "draw",
        "retrieve",
        "redistribute",
        "positive",
        "negative",
        "ambivalent",
        "rarity",
        "project_seal",
        "booster_band",
        "cooperation",
        "extra_effort",
        "safeguard",
        "wildcard_choice",
    }
)
RENDERER_VERSION = "0.30.0"

STROKE_HAIRLINE = 1.0
STROKE_LINE = 1.5
STROKE_EMPHASIS = 2.25
PRODUCTION_STROKE_SCALE = (STROKE_HAIRLINE, STROKE_LINE, STROKE_EMPHASIS)
INTERNAL_PLACEHOLDER_HATCH_STROKE = 3.0

INNER_CARD_FIELD_INSET = 3  # master px = about 0.25 mm inside the vendor safe
INNER_CARD_FIELD_RADIUS = 16  # master px = about 1.35 mm
# The vendor prints its red safety mark on the safe rectangle, so a face ending
# 0.25 mm inside it puts that mark on the anthracite edge and leaves the black
# border nothing to give once the cut drifts.  The whole face -- the field and
# everything on it -- is therefore scaled down about the centre of the cut until
# it clears the mark by the same 1 mm the internal DHK safe already keeps.  One
# uniform factor preserves every proportion and every internal margin ratio; the
# long axis simply ends up with a little more black than the narrow one.
CARD_FACE_SAFE_CLEARANCE = 12  # master px = 1.0 mm inside the vendor safe
TITLE_FOOTER_CORNER_RADIUS = 4
ART_EDGE_WARMTH_DEPTH = 5
ART_EDGE_WARMTH_OPACITY = 0.04
ACCENT_RULE_STROKE_WIDTH = STROKE_LINE
ACCENT_RULE_X_START = 78
ACCENT_RULE_X_END = 612
FLAVOR_RULE_OPACITY = 0.45
ART_TREATMENT = "light-mat"
MAIN_BOX_KEYLINE_STROKE_WIDTH = STROKE_HAIRLINE
ART_TOP_INNER_SHADOW_DEPTH = 7
ART_TOP_INNER_SHADOW_OPACITY = 0.03
PLATE_ACCENT_TOP_OFFSET = 2.5
PLATE_ACCENT_HEIGHT = ACCENT_RULE_STROKE_WIDTH
LAST_LINE_MIN_MEASURE = 0.35
PROSE_PROTECTED_SPLIT_PENALTY = 0.75
PROSE_SENTENCE_BREAK_BONUS = 0.20
PROSE_STRONG_CLAUSE_BREAK_BONUS = 0.10
PROSE_CLAUSE_BREAK_BONUS = 0.03
PROSE_SHORT_LINE_PENALTY = 0.25
PROSE_SINGLE_WORD_PENALTY = 0.25
FLAVOR_TOP_CLEARANCE = 6
FLAVOR_BOTTOM_INSET = 2
FLAVOR_DIVIDER_GAP = 8
SECTION_DIVIDER_OFFSET = 9
SECTION_BODY_TOP_OFFSET = 11
SECTION_LABEL_Y_OFFSET = -12.75
PROJECT_FAMILY_ICON_SIZE = 20
PROJECT_TYPE_SLOT_SIZE = 28
PROJECT_TYPE_CIRCLE_SIZE = 27
PROJECT_TYPE_CIRCLE_Y_OFFSET = 1
PROJECT_REQUIREMENT_ICON_SIZE = 18
PROJECT_REQUIREMENT_ICON_GAP = 6
PROJECT_REQUIREMENT_TO_POINTS_GAP = 10
FACTOR_EMBLEM_CARRIER_OPACITY = 0.28
FACTOR_EMBLEM_ICON_OPACITY = 0.22
RARITY_PIP_COUNT = 4
RARITY_PIP_SIZE = 5
RARITY_PIP_STEP = 8
RARITY_PIP_RADIUS = 1
RARITY_PIP_OUTLINE_WIDTH = STROKE_HAIRLINE
RARITY_PIP_TRACK_WIDTH = RARITY_PIP_SIZE + (RARITY_PIP_COUNT - 1) * RARITY_PIP_STEP
FOOTER_IDENTITY_GAP = 9
RARITY_TRACKING_LABELS = frozenset({"COMMON", "UNCOMMON", "RARE", "MYTHIC"})
FLAVOR_MIN_LINE_MEASURE = 0.29
FLAVOR_SENTENCE_BREAK_BONUS = 0.15
FLAVOR_CLAUSE_BREAK_BONUS = 0.04
FLAVOR_PHRASE_BREAK_BONUS = 0.25

GERMAN_PREPOSITIONS = frozenset(
    {
        "als",
        "am",
        "an",
        "ans",
        "auf",
        "aufs",
        "aus",
        "bei",
        "beim",
        "bis",
        "durch",
        "durchs",
        "für",
        "fürs",
        "gegen",
        "in",
        "im",
        "ins",
        "innerhalb",
        "mit",
        "nach",
        "ohne",
        "seit",
        "über",
        "um",
        "ums",
        "unter",
        "von",
        "vom",
        "vor",
        "zu",
        "zum",
        "zur",
        "zwischen",
    }
)
GERMAN_DETERMINERS = frozenset(
    {
        "alle",
        "das",
        "dem",
        "den",
        "der",
        "deren",
        "des",
        "dessen",
        "die",
        "diesem",
        "diesen",
        "dieser",
        "dieses",
        "ein",
        "eine",
        "einem",
        "einen",
        "einer",
        "eines",
        "ihrem",
        "ihren",
        "ihrer",
        "ihres",
        "jedem",
        "jeden",
        "jeder",
        "jedes",
        "kein",
        "keine",
        "keinem",
        "keinen",
        "keiner",
        "keines",
        "meinem",
        "meinen",
        "meiner",
        "meines",
        "sein",
        "seine",
        "seinem",
        "seinen",
        "seiner",
        "seines",
        "unser",
        "unsere",
        "unserem",
        "unseren",
        "unserer",
        "unseres",
    }
)
GERMAN_NUMBER_WORDS = frozenset(
    {
        "null",
        "eins",
        "zwei",
        "drei",
        "vier",
        "fünf",
        "sechs",
        "sieben",
        "acht",
        "neun",
        "zehn",
        "elf",
        "zwölf",
    }
)

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

FONT_CANDIDATES = {
    "regular": (
        ROOT / "data" / "assets" / "fonts" / "NotoSerif-Regular.ttf",
        Path("/usr/share/fonts/noto/NotoSerif-Regular.ttf"),
    ),
    "bold": (
        ROOT / "data" / "assets" / "fonts" / "NotoSerif-Bold.ttf",
        Path("/usr/share/fonts/noto/NotoSerif-Bold.ttf"),
    ),
    "italic": (
        ROOT / "data" / "assets" / "fonts" / "NotoSerif-Italic.ttf",
        Path("/usr/share/fonts/noto/NotoSerif-Italic.ttf"),
    ),
    "sans_bold": (
        ROOT / "data" / "assets" / "fonts" / "NotoSans-Bold.ttf",
        Path("/usr/share/fonts/noto/NotoSans-Bold.ttf"),
    ),
    "sans_regular": (
        ROOT / "data" / "assets" / "fonts" / "NotoSans-Regular.ttf",
        Path("/usr/share/fonts/noto/NotoSans-Regular.ttf"),
    ),
}


class RenderError(RuntimeError):
    """A card cannot be rendered or does not pass preflight."""


TextFit = tuple[float, float, list[str], float, str]


@dataclass(frozen=True)
class FlavorPlan:
    fit: TextFit | None
    divider_y: float | None
    content_frame_bottom: float


def _q(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _renderer_sha256() -> str:
    return _sha256_file(Path(__file__).resolve())


def _tool_versions() -> dict[str, str]:
    versions = {"python": sys.version.split()[0], "pillow": Image.__version__}
    try:
        import resvg_py  # type: ignore[import-not-found]
    except ImportError:
        versions["rasterizer"] = "rsvg-convert fallback"
    else:
        versions["resvg_py"] = str(getattr(resvg_py, "__version__", "unknown"))
        versions["rasterizer"] = "resvg_py"
    return versions


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def load_profile(path: str | Path = DEFAULT_PROFILE) -> dict[str, Any]:
    """Load and validate the immutable physical/export contract."""

    profile_path = Path(path)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    try:
        view_box = profile["master_svg"]["view_box"]
        output = profile["upload_png"]
        scale = output["scale_from_master"]
        master_rectangles = profile["master_svg"]["rectangles"]
        output_rectangles = output["rectangles"]
    except (KeyError, TypeError) as error:
        raise RenderError(f"Unvollständiges Renderprofil {profile_path}: {error}") from error

    if view_box != [0, 0, 822, 1122]:
        raise RenderError(f"SVG-viewBox muss [0, 0, 822, 1122] sein, ist aber {view_box}")
    if (output["width"], output["height"], output["dpi"], scale) != (1644, 2244, 600, 2):
        raise RenderError("Uploadprofil muss 1644×2244 px, 600 dpi und Maßstab 2 verwenden")
    for rectangle_name in ("trim", "vendor_safe", "internal_text_safe"):
        for key in ("x", "y", "width", "height"):
            if (
                output_rectangles[rectangle_name][key]
                != master_rectangles[rectangle_name][key] * scale
            ):
                raise RenderError(
                    f"{rectangle_name}-Rechteck ist für {key} keine exakte 2×-Ableitung"
                )
    vendor_safe = master_rectangles["vendor_safe"]
    internal_safe = master_rectangles["internal_text_safe"]
    safe_insets = (
        internal_safe["x"] - vendor_safe["x"],
        internal_safe["y"] - vendor_safe["y"],
        vendor_safe["x"] + vendor_safe["width"]
        - internal_safe["x"]
        - internal_safe["width"],
        vendor_safe["y"] + vendor_safe["height"]
        - internal_safe["y"]
        - internal_safe["height"],
    )
    if min(safe_insets) < 12:
        raise RenderError(
            "Internes DHK-Safe muss rundum mindestens 1 mm innerhalb "
            "des Lieferanten-Safe liegen"
        )
    if output["color"] != {"pixel_model": "RGB", "color_space": "sRGB", "alpha": False}:
        raise RenderError("Uploadprofil muss opakes RGB/sRGB festlegen")
    template = profile.get("source_template", {})
    template_path = ROOT / str(template.get("path", ""))
    if not template_path.is_file():
        raise RenderError(f"Verbindliche Druckvorlage fehlt: {template_path}")
    if _sha256_file(template_path) != template.get("sha256"):
        raise RenderError(f"SHA-256 der Druckvorlage stimmt nicht: {template_path}")
    profile["_path"] = str(profile_path)
    profile["_sha256"] = _sha256_file(profile_path)
    return profile


def load_cards(path: str | Path = DEFAULT_CARDS) -> list[dict[str, str]]:
    """Load the canonical card rows without changing their text."""

    cards_path = Path(path)
    raw = cards_path.read_bytes()
    required_columns = {
        "card_id",
        "name",
        "rarity",
        "card_type",
        "rules_text",
        "flavor_text",
    }
    with io.StringIO(raw.decode("utf-8"), newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = required_columns - set(reader.fieldnames or ())
        if missing_columns:
            raise RenderError(
                f"Fehlende Spalten in {cards_path}: {', '.join(sorted(missing_columns))}"
            )
        cards = [
            dict(row)
            for row in reader
            if row.get("rarity") in {"common", "uncommon", "rare", "mythic"}
        ]
    ids = [card.get("card_id", "") for card in cards]
    if not cards:
        raise RenderError(f"Keine Karten in {cards_path}")
    if len(ids) != len(set(ids)):
        raise RenderError(f"Doppelte card_id in {cards_path}")
    required_values = required_columns - {"flavor_text"}
    for card in cards:
        flavor_text = card.get("flavor_text")
        if flavor_text is None:
            raise RenderError(
                f"{card.get('card_id', '<ohne ID>')}: flavor_text fehlt in der Zeile"
            )
        if flavor_text and not flavor_text.strip():
            raise RenderError(
                f"{card.get('card_id', '<ohne ID>')}: flavor_text enthält nur Leerraum"
            )
        missing = sorted(
            key
            for key in required_values
            if not str(card.get(key) or "").strip()
        )
        if missing:
            raise RenderError(
                f"{card.get('card_id', '<ohne ID>')}: leere Felder {', '.join(missing)}"
            )
        card["_source_csv_sha256"] = _sha256_bytes(raw)
        card["_source_csv_name"] = cards_path.name
    return cards


def resolve_artwork(
    card_id: str,
    artwork_dir: str | Path = DEFAULT_ARTWORK_DIR,
    *,
    mode: str = "preview",
) -> Path:
    """Resolve one PNG illustration against the preview or print ratio contract."""

    if mode not in {"preview", "print"}:
        raise RenderError(f"Unbekannter Modus: {mode}")

    directory = Path(artwork_dir)
    path = directory / f"{card_id}.png"
    if not path.is_file():
        raise RenderError(f"{card_id}: Illustration fehlt: {path}")
    ambiguous = [item for item in directory.iterdir() if item.stem.casefold() == card_id.casefold()]
    if ambiguous != [path]:
        names = ", ".join(sorted(item.name for item in ambiguous))
        raise RenderError(f"{card_id}: Illustration ist nicht eindeutig ({names})")
    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            image_format = image.format
    except OSError as error:
        raise RenderError(f"{card_id}: Illustration ist nicht lesbar: {error}") from error
    if image_format != "PNG":
        raise RenderError(f"{card_id}: Illustration muss PNG sein, ist aber {image_format}")
    is_final_ratio = width * 2 == height * 3
    is_legacy_preview_ratio = width * 3 == height * 4
    if not is_final_ratio and not (mode == "preview" and is_legacy_preview_ratio):
        expected = "3:2" if mode == "print" else "3:2 oder als Bestandsvorschau 4:3"
        raise RenderError(
            f"{card_id}: Illustration muss exakt {expected} sein, ist aber {width}×{height}"
        )
    return path


def _load_layout() -> dict[str, Any]:
    if not LAYOUT_PATH.is_file():
        raise RenderError(f"Layoutkonfiguration fehlt: {LAYOUT_PATH}")
    raw = LAYOUT_PATH.read_bytes()
    layout = json.loads(raw.decode("utf-8"))
    if layout.get("schema") != "dhk-card-layout/v1":
        raise RenderError(f"Unbekanntes Layoutschema in {LAYOUT_PATH}")
    layout["_sha256"] = _sha256_bytes(raw)
    return layout


def _load_icon_manifest() -> dict[str, Any]:
    """Load the pinned semantic icon registry and validate every local path."""

    if not ICON_MANIFEST_PATH.is_file():
        raise RenderError(f"Iconmanifest fehlt: {ICON_MANIFEST_PATH}")
    raw = ICON_MANIFEST_PATH.read_bytes()
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RenderError(f"Iconmanifest ist ungültig: {error}") from error
    if manifest.get("schema") != "dhk-icon-manifest/v1":
        raise RenderError(f"Unbekanntes Iconschema in {ICON_MANIFEST_PATH}")
    library = manifest.get("library")
    icons = manifest.get("icons")
    if not isinstance(library, dict) or not isinstance(icons, dict):
        raise RenderError("Iconmanifest benötigt library und icons")
    if set(icons) != ICON_KEYS:
        missing = sorted(ICON_KEYS - set(icons))
        extra = sorted(set(icons) - ICON_KEYS)
        raise RenderError(
            f"Iconmanifest enthält nicht exakt die {len(ICON_KEYS)} Rollen "
            f"(fehlt: {', '.join(missing) or '–'}; zusätzlich: {', '.join(extra) or '–'})"
        )
    for field, expected in (
        ("name", "Phosphor Icons"),
        ("version", "2.1.1"),
        ("weight", "bold"),
        ("license", "MIT"),
    ):
        if library.get(field) != expected:
            raise RenderError(f"Iconbibliothek: {field} muss {expected!r} sein")
    license_path = _icon_local_path(str(library.get("license_file", "")))
    if not license_path.is_file():
        raise RenderError(f"Phosphor-Lizenz fehlt: {license_path}")
    for icon_key, specification in icons.items():
        if not isinstance(specification, dict):
            raise RenderError(f"Iconrolle {icon_key} ist keine Konfiguration")
        if not str(specification.get("label", "")).strip():
            raise RenderError(f"Iconrolle {icon_key} hat kein Label")
        path = _icon_local_path(str(specification.get("file", "")))
        if path.suffix.casefold() != ".svg" or not path.is_file():
            raise RenderError(f"Icondatei fehlt oder ist kein SVG: {path}")
    manifest["_sha256"] = _sha256_bytes(raw)
    return manifest


def _icon_local_path(relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise RenderError(f"Iconpfad muss relativ sein: {relative_path!r}")
    root = ICON_ROOT.resolve()
    candidate = (ICON_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise RenderError(f"Iconpfad verlässt data/assets/icons: {relative_path}") from error
    return candidate


def _load_icon_asset(icon_key: str) -> tuple[list[ET.Element], dict[str, str]]:
    """Return allowlisted SVG geometry plus reproducibility metadata."""

    manifest = _load_icon_manifest()
    try:
        specification = manifest["icons"][icon_key]
    except KeyError as error:
        raise RenderError(f"Unbekannte Iconrolle: {icon_key}") from error
    path = _icon_local_path(str(specification["file"]))
    raw = path.read_bytes()
    lowered = raw.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise RenderError(f"DTD oder Entity im Icon verboten: {path}")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise RenderError(f"Icon-SVG ist ungültig ({path}): {error}") from error
    if root.tag != _q("svg"):
        raise RenderError(f"Iconwurzel muss svg sein: {path}")
    if root.attrib.get("viewBox") != "0 0 256 256":
        raise RenderError(f"Icon-viewBox muss 0 0 256 256 sein: {path}")
    if root.attrib.get("fill") != "currentColor":
        raise RenderError(f"Icon muss currentColor verwenden: {path}")
    if set(root.attrib) - {"viewBox", "fill"}:
        raise RenderError(f"Unerlaubte Attribute an Iconwurzel: {path}")

    path_count = 0
    allowed_attributes = {
        "g": {"transform"},
        "path": {"d", "fill", "fill-rule", "clip-rule", "transform"},
    }
    for element in root.iter():
        if element is root:
            continue
        local_name = element.tag.rsplit("}", 1)[-1]
        if local_name not in allowed_attributes:
            raise RenderError(f"Unerlaubtes SVG-Element {local_name} in {path}")
        unexpected = set(element.attrib) - allowed_attributes[local_name]
        if unexpected:
            raise RenderError(
                f"Unerlaubte Attribute {', '.join(sorted(unexpected))} in {path}"
            )
        if any(
            token in value.casefold()
            for value in element.attrib.values()
            for token in ("url(", "href", "javascript:")
        ):
            raise RenderError(f"Externe Referenz im Icon verboten: {path}")
        if local_name == "path":
            path_count += 1
            if not element.attrib.get("d", "").strip():
                raise RenderError(f"Leerer Iconpfad: {path}")
    if not path_count:
        raise RenderError(f"Icon enthält keinen Pfad: {path}")

    library = manifest["library"]
    metadata = {
        "icon": icon_key,
        "label": str(specification["label"]),
        "source": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256_bytes(raw),
        "library": str(library["name"]),
        "version": str(library["version"]),
        "weight": str(library["weight"]),
    }
    return [copy.deepcopy(child) for child in root], metadata


def _icon_manifest_metadata() -> dict[str, Any]:
    manifest = _load_icon_manifest()
    assets = {}
    for icon_key in sorted(manifest["icons"]):
        _, metadata = _load_icon_asset(icon_key)
        assets[icon_key] = {
            "file": metadata["source"],
            "sha256": metadata["sha256"],
        }
    return {
        "manifest_sha256": manifest["_sha256"],
        "library": manifest["library"]["name"],
        "version": manifest["library"]["version"],
        "weight": manifest["library"]["weight"],
        "license": manifest["library"]["license"],
        "assets": assets,
    }


def _resolve_fonts() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for role, candidates in FONT_CANDIDATES.items():
        result[role] = next((path for path in candidates if path.is_file()), Path())
        if not result[role].is_file():
            raise RenderError(
                f"Freie Schrift für Rolle {role} fehlt. Erwartet wurde eine Noto-Datei unter "
                "data/assets/fonts/ oder /usr/share/fonts/noto/."
            )
    forbidden = {"beleren", "jacebeleren", "mplantin"}
    for path in result.values():
        if any(name in path.name.casefold() for name in forbidden):
            raise RenderError(f"Gesperrte Legacy-Schrift im Renderer: {path}")
    return result


def _attr_number(value: float | int) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _element(parent: ET.Element, name: str, **attrs: Any) -> ET.Element:
    clean = {
        key.replace("_", "-"): _attr_number(value)
        if isinstance(value, (int, float))
        else str(value)
        for key, value in attrs.items()
        if value is not None
    }
    return ET.SubElement(parent, _q(name), clean)


def _draw_icon(
    parent: ET.Element,
    icon_key: str,
    x: float,
    y: float,
    size: float,
    color: str,
    *,
    role: str,
    opacity: float | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> ET.Element:
    """Inline one pinned icon so the resulting SVG has no asset dependency."""

    children, metadata = _load_icon_asset(icon_key)
    scale = size / 256
    group = _element(
        parent,
        "g",
        transform=(
            f"translate({_attr_number(x)} {_attr_number(y)}) "
            f"scale({_attr_number(scale)})"
        ),
        fill=color,
        opacity=opacity,
        data_role=role,
        data_icon=metadata["icon"],
        data_icon_label=metadata["label"],
        data_icon_source=metadata["source"],
        data_icon_sha256=metadata["sha256"],
        data_icon_library=metadata["library"],
        data_icon_version=metadata["version"],
        data_icon_weight=metadata["weight"],
        data_icon_size=size,
    )
    for key, value in (attributes or {}).items():
        rendered = _attr_number(value) if isinstance(value, (int, float)) else str(value)
        group.set(key.replace("_", "-"), rendered)
    for child in children:
        group.append(child)
    return group


def _rect(
    parent: ET.Element,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str = "none",
    stroke: str | None = None,
    stroke_width: float | None = None,
    radius: float = 0,
    opacity: float | None = None,
    role: str | None = None,
) -> ET.Element:
    return _element(
        parent,
        "rect",
        x=x,
        y=y,
        width=width,
        height=height,
        rx=radius or None,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        opacity=opacity,
        data_role=role,
    )


def _ellipse(
    parent: ET.Element,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str = "none",
    stroke: str | None = None,
    stroke_width: float | None = None,
    opacity: float | None = None,
) -> ET.Element:
    return _element(
        parent,
        "ellipse",
        cx=x + width / 2,
        cy=y + height / 2,
        rx=width / 2,
        ry=height / 2,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        opacity=opacity,
    )


def _font(fonts: Mapping[str, Path], role: str, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(
        str(fonts[role]), round(size * 4), layout_engine=ImageFont.Layout.RAQM
    )


def _typography_steps(
    mapping: Mapping[str, Any], typography_role: str
) -> tuple[tuple[float, float, str], ...]:
    try:
        raw_steps = mapping["typography"][typography_role]["steps"]
    except (KeyError, TypeError) as error:
        raise RenderError(f"Unbekannte Typografierolle: {typography_role}") from error
    steps = tuple(
        (
            float(step["size"]),
            float(step["line_height"]),
            str(step.get("status", "standard")),
        )
        for step in raw_steps
    )
    if not steps or any(size <= 0 or line_height <= 0 for size, line_height, _ in steps):
        raise RenderError(f"Ungültige Typografiestufen für {typography_role}")
    if [size for size, _, _ in steps] != sorted(
        (size for size, _, _ in steps), reverse=True
    ):
        raise RenderError(f"Typografiestufen für {typography_role} sind nicht absteigend")
    return steps


def _tracking_for_text(text: str, size: float, family: str) -> float:
    """Return deterministic optical tracking in absolute SVG layout units."""

    if family == "Noto Serif" and size >= 36:
        return round(size * -0.0075, 2)
    if family != "Noto Sans" or not text.isupper():
        return 0
    if text in RARITY_TRACKING_LABELS:
        ratio = 0.10
    elif size > 20:
        ratio = 0.015
    elif size > 14:
        ratio = 0.04
    elif size >= 12:
        ratio = 0.06
    else:
        ratio = 0.08
    return round(size * ratio, 2)


def _text_width(
    text: str,
    font: ImageFont.FreeTypeFont,
    letter_spacing: float = 0,
) -> float:
    return font.getlength(text) / 4 + max(len(text) - 1, 0) * letter_spacing


def _balance_paragraph_lines(
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    width: float,
    letter_spacing: float,
) -> list[str]:
    """Reflow a paragraph with a short last line without changing line count."""

    if len(lines) < 2:
        return lines
    right_words = lines[-1].split()
    right_width = _text_width(lines[-1], font, letter_spacing)
    if right_width >= width * LAST_LINE_MIN_MEASURE and len(right_words) > 1:
        return lines

    words = " ".join(lines).split()
    line_count = len(lines)
    greedy_breaks: list[int] = []
    consumed_words = 0
    for line in lines[:-1]:
        consumed_words += len(line.split())
        greedy_breaks.append(consumed_words)

    protected_splits = _protected_german_splits(words)
    width_cache: dict[tuple[int, int], float] = {}

    def measured_width(start: int, end: int) -> float:
        key = (start, end)
        if key not in width_cache:
            width_cache[key] = _text_width(
                " ".join(words[start:end]), font, letter_spacing
            )
        return width_cache[key]

    # Each state stores score, distance from the greedy breaks and the exact
    # break tuple.  Keeping the latter in the comparison makes ties stable.
    states: dict[int, tuple[float, int, tuple[int, ...]]] = {0: (0.0, 0, ())}
    for line_index in range(line_count):
        next_states: dict[int, tuple[float, int, tuple[int, ...]]] = {}
        remaining_lines = line_count - line_index - 1
        for start, (base_score, base_distance, breaks) in states.items():
            last_possible_end = len(words) - remaining_lines
            for end in range(start + 1, last_possible_end + 1):
                line_width = measured_width(start, end)
                if line_width > width:
                    continue
                is_last_line = line_index == line_count - 1
                if is_last_line != (end == len(words)):
                    continue

                fill_ratio = line_width / width
                score = base_score + (1 - fill_ratio) ** 2
                if fill_ratio < LAST_LINE_MIN_MEASURE:
                    shortfall = (
                        LAST_LINE_MIN_MEASURE - fill_ratio
                    ) / LAST_LINE_MIN_MEASURE
                    score += PROSE_SHORT_LINE_PENALTY * shortfall**2
                if end - start == 1:
                    score += PROSE_SINGLE_WORD_PENALTY

                distance = base_distance
                candidate_breaks = breaks
                if not is_last_line:
                    if end in protected_splits:
                        score += PROSE_PROTECTED_SPLIT_PENALTY
                    if _is_sentence_break(words[end - 1]):
                        score -= PROSE_SENTENCE_BREAK_BONUS
                    elif _is_strong_clause_break(words[end - 1]):
                        score -= PROSE_STRONG_CLAUSE_BREAK_BONUS
                    elif _is_clause_break(words[end - 1]):
                        score -= PROSE_CLAUSE_BREAK_BONUS
                    distance += abs(end - greedy_breaks[line_index])
                    candidate_breaks = (*breaks, end)

                candidate = (score, distance, candidate_breaks)
                previous = next_states.get(end)
                if previous is None or candidate < previous:
                    next_states[end] = candidate
        states = next_states

    fitted = states.get(len(words))
    if fitted is None:
        return lines
    cuts = (0, *fitted[2], len(words))
    return [
        " ".join(words[cuts[index] : cuts[index + 1]])
        for index in range(line_count)
    ]


def _lexical_token(token: str) -> str:
    return re.sub(r"^\W+|\W+$", "", token, flags=re.UNICODE)


def _is_sentence_break(token: str) -> bool:
    lexical = _lexical_token(token)
    return len(lexical) > 1 and token.rstrip("”’›»)]}").endswith((".", "!", "?"))


def _is_clause_break(token: str) -> bool:
    return token.rstrip("”’›»)]}").endswith((",", ";", ":"))


def _is_strong_clause_break(token: str) -> bool:
    return token.rstrip("”’›»)]}").endswith((";", ":"))


def _starts_upper(token: str) -> bool:
    lexical = _lexical_token(token)
    return bool(lexical) and lexical[0].isupper()


def _protected_german_splits(words: Sequence[str]) -> set[int]:
    """Return whitespace positions that would split a small German phrase."""

    protected: set[int] = set()
    group_starters = (
        GERMAN_PREPOSITIONS
        | GERMAN_DETERMINERS
        | GERMAN_NUMBER_WORDS
    )
    for start, token in enumerate(words[:-1]):
        lexical = _lexical_token(token)
        normalized = lexical.casefold()
        if (
            normalized in group_starters
            and not _is_clause_break(token)
            and not _is_sentence_break(token)
        ):
            head: int | None = None
            for candidate in range(start + 1, len(words)):
                if (
                    _starts_upper(words[candidate])
                    or _is_clause_break(words[candidate])
                    or _is_sentence_break(words[candidate])
                    or candidate == len(words) - 1
                ):
                    head = candidate
                    break
            if head is not None:
                protected.update(range(start + 1, head + 1))

        next_lexical = _lexical_token(words[start + 1])
        looks_like_attributive_modifier = (
            bool(lexical)
            and lexical[:1].islower()
            and normalized.endswith(("e", "en", "er", "es", "em"))
            and bool(next_lexical)
            and next_lexical[0].isupper()
        )
        number_before_noun = (
            any(character.isdigit() for character in lexical)
            and not _is_clause_break(token)
            and not _is_sentence_break(token)
            and bool(next_lexical)
            and next_lexical[0].isupper()
        )
        if looks_like_attributive_modifier or number_before_noun:
            protected.add(start + 1)
    return protected


def _balance_flavor_two_lines(
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    width: float,
    letter_spacing: float,
) -> list[str]:
    """Choose a syntactically plausible two-line rag for German flavor text."""

    if len(lines) != 2:
        return lines
    words = " ".join(lines).split()
    greedy_split = len(lines[0].split())
    protected_splits = _protected_german_splits(words)
    candidates: list[tuple[float, int, int, str, str]] = []
    for split in range(1, len(words)):
        if split in protected_splits:
            continue
        left = " ".join(words[:split])
        right = " ".join(words[split:])
        left_width = _text_width(left, font, letter_spacing)
        right_width = _text_width(right, font, letter_spacing)
        if left_width > width or right_width > width:
            continue
        if min(left_width, right_width) < width * FLAVOR_MIN_LINE_MEASURE:
            continue

        score = abs(left_width - right_width) / width
        if _is_sentence_break(words[split - 1]):
            score -= FLAVOR_SENTENCE_BREAK_BONUS
        elif _is_clause_break(words[split - 1]):
            score -= FLAVOR_CLAUSE_BREAK_BONUS
        if _lexical_token(words[split]).casefold() in GERMAN_PREPOSITIONS:
            score -= FLAVOR_PHRASE_BREAK_BONUS
        candidates.append(
            (score, abs(split - greedy_split), -split, left, right)
        )
    if not candidates:
        return lines
    _, _, _, left, right = min(candidates)
    return [left, right]


def _wrap_words(
    text: str,
    font: ImageFont.FreeTypeFont,
    width: float,
    letter_spacing: float = 0,
    *,
    balance_last_line: bool = True,
    flavor_aware: bool = False,
) -> list[str]:
    paragraphs = text.replace("\r", "").split("\n")
    lines: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        paragraph_lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if _text_width(candidate, font, letter_spacing) <= width:
                current = candidate
            else:
                paragraph_lines.append(current)
                current = word
        paragraph_lines.append(current)
        if flavor_aware:
            paragraph_lines = _balance_flavor_two_lines(
                paragraph_lines,
                font,
                width,
                letter_spacing,
            )
        elif balance_last_line:
            paragraph_lines = _balance_paragraph_lines(
                paragraph_lines,
                font,
                width,
                letter_spacing,
            )
        lines.extend(paragraph_lines)
    return lines


def _fit_text(
    text: str,
    fonts: Mapping[str, Path],
    role: str,
    steps: Sequence[tuple[float, float, str]],
    width: float,
    height: float,
    *,
    family: str,
    single_line: bool = False,
    balance_last_line: bool = True,
    flavor_aware: bool = False,
) -> TextFit:
    for size, line_height, status in steps:
        font = _font(fonts, role, size)
        letter_spacing = _tracking_for_text(text, size, family)
        lines = (
            [text]
            if single_line
            else _wrap_words(
                text,
                font,
                width,
                letter_spacing,
                balance_last_line=balance_last_line,
                flavor_aware=flavor_aware,
            )
        )
        fitted_height = len(lines) * line_height
        fitted_width = max(
            (_text_width(line, font, letter_spacing) for line in lines), default=0
        )
        if fitted_width <= width + 0.1 and fitted_height <= height + 0.1:
            return size, line_height, lines, letter_spacing, status
    raise RenderError(
        f"Text passt nicht in {width:.0f}×{height:.0f}: {text[:72]}"
        + ("…" if len(text) > 72 else "")
    )


def _draw_text(
    parent: ET.Element,
    text: str,
    fonts: Mapping[str, Path],
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    steps: Sequence[tuple[float, float, str]],
    role: str = "regular",
    fill: str = "#17212B",
    family: str = "Noto Serif",
    anchor: str = "start",
    vertical: str = "top",
    single_line: bool = False,
    balance_last_line: bool = True,
    flavor_aware: bool = False,
    data_role: str | None = None,
    fitted: TextFit | None = None,
) -> tuple[float, list[str]]:
    if fitted is None:
        fitted = _fit_text(
            text,
            fonts,
            role,
            steps,
            width,
            height,
            family=family,
            single_line=single_line,
            balance_last_line=balance_last_line,
            flavor_aware=flavor_aware,
        )
    fitted_size, fitted_line_height, lines, letter_spacing, step_status = fitted
    if anchor == "middle":
        text_x = x + width / 2
    elif anchor == "end":
        text_x = x + width
    else:
        text_x = x
    block_height = len(lines) * fitted_line_height
    if vertical == "font-metrics-middle":
        if len(lines) != 1:
            raise RenderError("Metrische Vertikalzentrierung ist nur einzeilig möglich")
        ascent, descent = _font(fonts, role, fitted_size).getmetrics()
        baseline = y + (height - (ascent + descent) / 4) / 2 + ascent / 4
    else:
        if vertical == "middle":
            top = y + (height - block_height) / 2
        elif vertical == "bottom":
            top = y + height - block_height
        else:
            top = y
        baseline = top + fitted_size
    element = _element(
        parent,
        "text",
        x=text_x,
        y=baseline,
        fill=fill,
        font_family=family,
        font_size=fitted_size,
        font_weight="700" if role in {"bold", "sans_bold"} else "400",
        font_style="italic" if role == "italic" else "normal",
        text_anchor=anchor,
        letter_spacing=letter_spacing or None,
        font_feature_settings="'tnum' 1, 'lnum' 1"
        if any(character.isdigit() for character in text)
        else None,
        data_role=data_role,
        data_font_role=role,
        data_type_size_step=fitted_size,
        data_line_height=fitted_line_height,
        data_type_step_status=step_status,
    )
    for index, line in enumerate(lines):
        tspan = _element(
            element,
            "tspan",
            x=text_x,
            dy=0 if index == 0 else fitted_line_height,
        )
        tspan.text = line
    return fitted_size, lines


def _draw_title(
    parent: ET.Element,
    text: str,
    zone: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
) -> float:
    """Draw every card title at the single set-wide optical size."""

    fitted_size, _ = _draw_text(
        parent,
        text,
        fonts,
        x=zone["x"],
        y=zone["y"],
        width=zone["width"],
        height=zone["height"],
        steps=_typography_steps(mapping, "title"),
        role="bold",
        fill=_color(mapping, "text/primary"),
        vertical="font-metrics-middle",
        single_line=True,
        data_role="card-title",
    )
    return fitted_size


def _family_key(card: Mapping[str, str], layout_key: str) -> str:
    if layout_key == "factor":
        return card.get("factor_family", "wildcard") or "wildcard"
    return "wildcard"


def _appearance(
    card: Mapping[str, str], mapping: Mapping[str, Any], layout_key: str
) -> dict[str, str]:
    if layout_key == "factor":
        family_key = _family_key(card, layout_key)
        family = mapping["families"][family_key]
        return {
            "accent_token": family["color_token"],
            "label": family["label"],
        }
    if layout_key == "event":
        event_type = mapping["card_types"]["Ereignis"]
        return {"accent_token": event_type["color_token"]}
    domain_key = card.get("domain_primary", "wildcard") or "wildcard"
    domain = mapping["families"].get(domain_key, mapping["families"]["wildcard"])
    return {"accent_token": domain["color_token"], "label": domain["label"]}


def _layout_key(card: Mapping[str, str]) -> str:
    try:
        return {"Projekt": "project", "Projektfaktor": "factor", "Ereignis": "event"}[
            card["card_type"]
        ]
    except KeyError as error:
        raise RenderError(f"{card.get('card_id', '<ohne ID>')}: unbekannte Kartenart") from error


def _color(mapping: Mapping[str, Any], token: str) -> str:
    try:
        return str(mapping["colors"][token]["hex"])
    except KeyError as error:
        raise RenderError(f"Unbekannter Farbtoken: {token}") from error


def _define_art_edge_gradients(defs: ET.Element, mapping: Mapping[str, Any]) -> None:
    """Define four filter-free gradients for the illustration's warm edge wash."""

    warm = _color(mapping, "material/art-warm")
    specifications = (
        ("art-warm-left", "left", "0%", "0%", "100%", "0%", False),
        ("art-warm-right", "right", "0%", "0%", "100%", "0%", True),
        ("art-warm-top", "top", "0%", "0%", "0%", "100%", False),
        ("art-warm-bottom", "bottom", "0%", "0%", "0%", "100%", True),
    )
    for gradient_id, edge, x1, y1, x2, y2, reverse in specifications:
        gradient = _element(
            defs,
            "linearGradient",
            id=gradient_id,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            data_role="art-edge-warmth-gradient",
            data_edge=edge,
        )
        first, second = ((0, ART_EDGE_WARMTH_OPACITY) if reverse else (ART_EDGE_WARMTH_OPACITY, 0))
        _element(
            gradient,
            "stop",
            offset="0%",
            stop_color=warm,
            stop_opacity=first,
        )
        _element(
            gradient,
            "stop",
            offset="100%",
            stop_color=warm,
            stop_opacity=second,
        )


def _define_material_defs(defs: ET.Element, mapping: Mapping[str, Any]) -> None:
    """Define deterministic, filter-free material treatments once per SVG."""

    _define_art_edge_gradients(defs, mapping)

    inner_gradient = _element(
        defs,
        "linearGradient",
        id="inner-card-field-gradient",
        x1="0%",
        y1="0%",
        x2="0%",
        y2="100%",
        data_role="inner-card-field-gradient",
    )
    for offset, color_token in (
        ("0%", "background/shell-raised-top"),
        ("50%", "background/shell-raised"),
        ("100%", "background/shell-raised-bottom"),
    ):
        _element(
            inner_gradient,
            "stop",
            offset=offset,
            stop_color=_color(mapping, color_token),
            data_color_token=color_token,
        )

    art_shadow = _element(
        defs,
        "linearGradient",
        id="art-top-inner-shadow",
        x1="0%",
        y1="0%",
        x2="0%",
        y2="100%",
        data_role="artwork-top-inner-shadow-gradient",
    )
    for offset, opacity in (("0%", ART_TOP_INNER_SHADOW_OPACITY), ("35%", 0.018), ("100%", 0)):
        _element(
            art_shadow,
            "stop",
            offset=offset,
            stop_color="#000000",
            stop_opacity=opacity,
        )

def _selective_rounded_rect(
    parent: ET.Element,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    radius: float,
    corners: str,
    fill: str,
    stroke: str | None = None,
    stroke_width: float | None = None,
    role: str | None = None,
) -> ET.Element:
    right = x + width
    bottom = y + height
    if corners == "top":
        path = (
            f"M {x + radius} {y} H {right - radius} "
            f"A {radius} {radius} 0 0 1 {right} {y + radius} "
            f"V {bottom} H {x} V {y + radius} "
            f"A {radius} {radius} 0 0 1 {x + radius} {y} Z"
        )
    elif corners == "bottom":
        path = (
            f"M {x} {y} H {right} V {bottom - radius} "
            f"A {radius} {radius} 0 0 1 {right - radius} {bottom} "
            f"H {x + radius} A {radius} {radius} 0 0 1 {x} {bottom - radius} "
            f"V {y} Z"
        )
    else:
        raise RenderError(f"Unbekannter Eckenmodus: {corners}")
    return _element(
        parent,
        "path",
        d=path,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        data_role=role,
        data_box_x=x,
        data_box_y=y,
        data_box_width=width,
        data_box_height=height,
        data_corner_mode=corners,
        data_corner_radius=radius,
    )


def _plate_shape(
    parent: ET.Element,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    corners: str,
    radius: float,
    fill: str,
    role: str,
    stroke: str | None = None,
    stroke_width: float | None = None,
) -> ET.Element:
    if corners == "none":
        return _rect(
            parent,
            x,
            y,
            width,
            height,
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            role=role,
        )
    return _selective_rounded_rect(
        parent,
        x,
        y,
        width,
        height,
        radius=radius,
        corners=corners,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        role=role,
    )


def _draw_plate_keyline(
    parent: ET.Element,
    x: float,
    y: float,
    width: float,
    height: float,
    mapping: Mapping[str, Any],
    *,
    plate_role: str,
    corners: str,
    radius: float,
) -> None:
    """Draw one neutral inset outline on a plate's declared outer bounds."""

    stroke_width = MAIN_BOX_KEYLINE_STROKE_WIDTH
    inset = stroke_width / 2
    keyline = _plate_shape(
        parent,
        x + inset,
        y + inset,
        width - 2 * inset,
        height - 2 * inset,
        corners=corners,
        radius=max(0.0, radius - inset),
        fill="none",
        stroke=_color(mapping, "line/default"),
        stroke_width=stroke_width,
        role="plate-keyline",
    )
    keyline.set("data-plate-role", plate_role)
    keyline.set("data-relief", "flat")
    keyline.set("data-color-token", "line/default")
    keyline.set("data-inset", _attr_number(inset))
    keyline.set("data-stroke-width", _attr_number(stroke_width))
    keyline.set("data-box-x", _attr_number(x + inset))
    keyline.set("data-box-y", _attr_number(y + inset))
    keyline.set("data-box-width", _attr_number(width - 2 * inset))
    keyline.set("data-box-height", _attr_number(height - 2 * inset))


def _flat_plate(
    parent: ET.Element,
    zone: Mapping[str, float],
    mapping: Mapping[str, Any],
    accent: str,
    *,
    fill_token: str,
    role: str,
    corners: str = "none",
    radius: float = 0,
    show_accent: bool = True,
) -> None:
    x, y, width, height = (zone[key] for key in ("x", "y", "width", "height"))
    _plate_shape(
        parent,
        x,
        y,
        width,
        height,
        corners=corners,
        radius=radius,
        fill=_color(mapping, fill_token),
        role=role,
    )

    if show_accent:
        accent_role = f"{role}-accent"
        _rect(
            parent,
            ACCENT_RULE_X_START,
            y + PLATE_ACCENT_TOP_OFFSET,
            ACCENT_RULE_X_END - ACCENT_RULE_X_START,
            PLATE_ACCENT_HEIGHT,
            fill=accent,
            role=accent_role,
        ).set("data-accent-mode", "inset-rule")

    _draw_plate_keyline(
        parent,
        x,
        y,
        width,
        height,
        mapping,
        plate_role=role,
        corners=corners,
        radius=radius,
    )


def _draw_type_symbol(
    parent: ET.Element,
    layout_key: str,
    color: str,
) -> None:
    type_icons = {"project": "project", "factor": "project_factor", "event": "event"}
    try:
        type_icon = type_icons[layout_key]
    except KeyError as error:
        raise RenderError(f"Unbekanntes Typzeichen: {layout_key}") from error
    icon_size = 24 if layout_key == "factor" else 22
    icon_offset = (40 - icon_size) / 2
    _draw_icon(
        parent,
        type_icon,
        icon_offset,
        icon_offset,
        icon_size,
        color,
        role="card-type-symbol",
    )


def _draw_identity_stamp(
    parent: ET.Element,
    zones: Mapping[str, Any],
    mapping: Mapping[str, Any],
    layout_key: str,
) -> None:
    carrier_inset = 2
    x = zones["type"]["x"] - carrier_inset
    y = zones["title_surface"]["y"] + 5
    group = _element(
        parent,
        "g",
        transform=f"translate({_attr_number(x)} {_attr_number(y)})",
        data_role="card-type-badge",
        data_card_type=layout_key,
    )
    fill_token = "background/paper"
    carrier = _ellipse(
        group,
        carrier_inset,
        carrier_inset,
        36,
        36,
        fill=_color(mapping, fill_token),
        stroke=_color(mapping, "line/default"),
        stroke_width=STROKE_EMPHASIS,
    )
    carrier.set("data-role", "card-type-carrier")
    carrier.set("data-fill-mode", "neutral-paper")
    carrier.set("data-fill-token", fill_token)
    _draw_type_symbol(group, layout_key, _color(mapping, "line/default"))


def _draw_project_requirement_icons(
    parent: ET.Element,
    card: Mapping[str, str],
    type_surface: Mapping[str, Any],
    mapping: Mapping[str, Any],
    *,
    points_x: float,
) -> float:
    requirements = [
        key for key in card.get("requirements", "").split("+") if key
    ]
    if not requirements:
        raise RenderError(f"{card['card_id']}: Projektanforderungen fehlen")

    total_width = (
        len(requirements) * PROJECT_TYPE_SLOT_SIZE
        + (len(requirements) - 1) * PROJECT_REQUIREMENT_ICON_GAP
    )
    right = points_x - PROJECT_REQUIREMENT_TO_POINTS_GAP
    left = right - total_width
    surface_left = float(type_surface["x"])
    if left < surface_left:
        raise RenderError(f"{card['card_id']}: Anforderungsicons sind zu breit")

    center_y = float(type_surface["y"]) + float(type_surface["height"]) / 2
    top = (
        center_y
        - PROJECT_TYPE_CIRCLE_SIZE / 2
        + PROJECT_TYPE_CIRCLE_Y_OFFSET
    )
    carrier_inset = (PROJECT_TYPE_SLOT_SIZE - PROJECT_TYPE_CIRCLE_SIZE) / 2
    icon_inset = (PROJECT_TYPE_SLOT_SIZE - PROJECT_REQUIREMENT_ICON_SIZE) / 2
    group = _element(
        parent,
        "g",
        data_role="project-requirements",
        data_count=len(requirements),
        data_left=left,
        data_right=right,
    )
    for index, requirement in enumerate(requirements):
        try:
            family = mapping["families"][requirement]
        except KeyError as error:
            raise RenderError(
                f"{card['card_id']}: Unbekannte Projektanforderung {requirement!r}"
            ) from error
        slot_x = left + index * (
            PROJECT_TYPE_SLOT_SIZE + PROJECT_REQUIREMENT_ICON_GAP
        )
        carrier_x = slot_x + carrier_inset
        color = _color(mapping, family["color_token"])
        carrier = _ellipse(
            group,
            carrier_x,
            top,
            PROJECT_TYPE_CIRCLE_SIZE,
            PROJECT_TYPE_CIRCLE_SIZE,
            fill=_color(mapping, "background/paper-raised"),
            stroke=color,
            stroke_width=STROKE_LINE,
        )
        carrier.set("data-role", "project-requirement-carrier")
        carrier.set("data-family", requirement)
        carrier.set("data-slot", str(index + 1))
        carrier.set("data-count", "1")
        _draw_icon(
            group,
            family["icon"],
            slot_x + icon_inset,
            top + (PROJECT_TYPE_CIRCLE_SIZE - PROJECT_REQUIREMENT_ICON_SIZE) / 2,
            PROJECT_REQUIREMENT_ICON_SIZE,
            color,
            role="project-requirement-symbol",
            attributes={
                "data_family": requirement,
                "data_slot": index + 1,
                "data_count": 1,
            },
        )
    return left


def _draw_type_line(
    parent: ET.Element,
    card: Mapping[str, str],
    zones: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    accent: str,
    appearance: Mapping[str, str],
    layout_key: str,
) -> None:
    if layout_key == "project":
        primary = "PROJEKT"
        family_key = card.get("domain_primary", "")
        try:
            family = mapping["families"][family_key]
        except KeyError as error:
            raise RenderError(
                f"{card['card_id']}: Unbekannte Projektfamilie {family_key!r}"
            ) from error
        secondary = family["label"]
        secondary_icon = family["icon"]
    elif layout_key == "factor":
        primary = "PROJEKTFAKTOR"
        secondary = appearance["label"]
        family_key = _family_key(card, layout_key)
        secondary_icon = mapping["families"][family_key]["icon"]
    else:
        primary = "EREIGNIS"
        effect_label = mapping["effect_templates"].get(card.get("effect_template", ""), "")
        target_keys = [key for key in card.get("target_family", "").split("+") if key]
        target_label = " + ".join(mapping["families"][key]["label"] for key in target_keys)
        secondary = effect_label + (f" · ZIEL: {target_label}" if target_label else "")
        secondary_icon = mapping.get("effect_icons", {}).get(
            card.get("effect_template", ""), ""
        )

    zone = zones["type"]
    primary_steps = _typography_steps(mapping, "type_primary")
    primary_size = primary_steps[0][0]
    primary_width = _text_width(
        primary,
        _font(fonts, "sans_bold", primary_size),
        _tracking_for_text(primary, primary_size, "Noto Sans"),
    )
    _draw_text(
        parent,
        primary,
        fonts,
        x=zone["x"],
        y=zone["y"],
        width=primary_width + 2,
        height=zone["height"],
        steps=primary_steps,
        role="sans_bold",
        fill=accent,
        family="Noto Sans",
        vertical="middle",
        single_line=True,
        data_role="card-type",
    )
    secondary_right = zone["x"] + primary_width
    secondary_x = zone["x"] + primary_width + 5
    if secondary:
        if secondary_icon:
            icon_size = (
                PROJECT_FAMILY_ICON_SIZE if layout_key == "project" else 18
            )
            _draw_icon(
                parent,
                secondary_icon,
                secondary_x,
                zone["y"] + (zone["height"] - icon_size) / 2,
                icon_size,
                accent,
                role=(
                    "event-effect-symbol"
                    if layout_key == "event"
                    else (
                        "project-family-symbol"
                        if layout_key == "project"
                        else "factor-family-symbol"
                    )
                ),
            )
            secondary_x += icon_size + 5
        secondary_steps = _typography_steps(mapping, "type_secondary")
        secondary_size = secondary_steps[0][0]
        secondary_width = _text_width(
            secondary,
            _font(fonts, "sans_regular", secondary_size),
            _tracking_for_text(secondary, secondary_size, "Noto Sans"),
        )
        if layout_key == "project":
            secondary_box_width = secondary_width + 2
        elif layout_key == "event":
            surface = zones["type_surface"]
            secondary_box_width = max(
                80,
                surface["x"] + surface["width"] - 12 - secondary_x,
            )
        else:
            secondary_box_width = max(
                80,
                zone["x"] + zone["width"] - secondary_x,
            )
        _draw_text(
            parent,
            secondary,
            fonts,
            x=secondary_x,
            y=zone["y"] + 1,
            width=secondary_box_width,
            height=zone["height"],
            steps=secondary_steps,
            role="sans_regular",
            fill=_color(mapping, "text/primary"),
            family="Noto Sans",
            vertical="middle",
            single_line=True,
            data_role="event-keyword" if layout_key == "event" else "card-category",
        )
        secondary_right = secondary_x + secondary_width
    if layout_key == "project":
        points_text = f"{card.get('points', '')}P"
        surface = zones["type_surface"]
        points_color = _color(mapping, "line/default")
        badge_slot_x = (
            surface["x"] + surface["width"] - PROJECT_TYPE_SLOT_SIZE - 12
        )
        badge_x = badge_slot_x + (
            PROJECT_TYPE_SLOT_SIZE - PROJECT_TYPE_CIRCLE_SIZE
        ) / 2
        badge_y = (
            surface["y"]
            + (surface["height"] - PROJECT_TYPE_CIRCLE_SIZE) / 2
            + PROJECT_TYPE_CIRCLE_Y_OFFSET
        )
        requirements_left = _draw_project_requirement_icons(
            parent,
            card,
            surface,
            mapping,
            points_x=badge_slot_x,
        )
        if requirements_left - secondary_right < 12:
            raise RenderError(
                f"{card['card_id']}: Projektfamilie und Anforderungen kollidieren"
            )
        points_circle = _ellipse(
            parent,
            badge_x,
            badge_y,
            PROJECT_TYPE_CIRCLE_SIZE,
            PROJECT_TYPE_CIRCLE_SIZE,
            fill=_color(mapping, "background/paper-raised"),
            stroke=points_color,
            stroke_width=STROKE_LINE,
        )
        points_circle.set("data-role", "project-points")
        points_circle.set("data-shape", "circle")
        _draw_text(
            parent,
            points_text,
            fonts,
            x=badge_x + 1,
            y=badge_y,
            width=PROJECT_TYPE_CIRCLE_SIZE - 2,
            height=PROJECT_TYPE_CIRCLE_SIZE,
            steps=_typography_steps(mapping, "points"),
            role="sans_bold",
            fill=points_color,
            family="Noto Sans",
            anchor="middle",
            vertical="middle",
            single_line=True,
            data_role="project-points-label",
        )


def _draw_footer(
    parent: ET.Element,
    card: Mapping[str, str],
    zone: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    accent: str,
) -> None:
    group = _element(parent, "g", data_role="card-footer")
    rarity = mapping["rarities"][card["rarity"]]
    filled_marks = int(rarity["marks"])
    if not 1 <= filled_marks <= RARITY_PIP_COUNT:
        raise RenderError(
            f"{card['card_id']}: Seltenheitsstufe {filled_marks} liegt außerhalb "
            f"der {RARITY_PIP_COUNT} Pips"
        )
    group.set("data-rarity-filled", str(filled_marks))
    group.set("data-rarity-total", str(RARITY_PIP_COUNT))
    identity_steps = _typography_steps(mapping, "footer_identity")
    identity_size = identity_steps[0][0]
    identity_font = _font(fonts, "sans_bold", identity_size)
    identity_group = _element(group, "g", data_role="footer-identity-rarity")
    identity_x = float(zone["x"])
    identity_segments = (
        (card["card_id"], "footer-card-id"),
        ("·", "footer-identity-separator"),
        (rarity["label"], "footer-rarity"),
    )
    for index, (text, data_role) in enumerate(identity_segments):
        tracking = _tracking_for_text(text, identity_size, "Noto Sans")
        segment_width = _text_width(text, identity_font, tracking)
        _draw_text(
            identity_group,
            text,
            fonts,
            x=identity_x,
            y=zone["y"],
            width=segment_width + 2,
            height=zone["height"],
            steps=identity_steps,
            role="sans_bold",
            fill=_color(mapping, "text/on-dark"),
            family="Noto Sans",
            vertical="middle",
            single_line=True,
            data_role=data_role,
        )
        identity_x += segment_width
        if index < len(identity_segments) - 1:
            identity_x += FOOTER_IDENTITY_GAP

    mark_color = _color(mapping, "line/highlight")
    pip_track_x = float(zone["x"]) + (
        float(zone["width"]) - RARITY_PIP_TRACK_WIDTH
    ) / 2
    for index in range(RARITY_PIP_COUNT):
        is_filled = index < filled_marks
        outline_inset = 0 if is_filled else RARITY_PIP_OUTLINE_WIDTH / 2
        pip = _rect(
            group,
            pip_track_x + index * RARITY_PIP_STEP + outline_inset,
            zone["y"] + 8 + outline_inset,
            RARITY_PIP_SIZE - 2 * outline_inset,
            RARITY_PIP_SIZE - 2 * outline_inset,
            fill=mark_color if is_filled else "none",
            stroke=None if is_filled else mark_color,
            stroke_width=None if is_filled else RARITY_PIP_OUTLINE_WIDTH,
            radius=RARITY_PIP_RADIUS - outline_inset,
            role="rarity-mark",
        )
        pip.set("data-index", str(index + 1))
        pip.set("data-state", "filled" if is_filled else "empty")
    _draw_text(
        group,
        "OTTERS OF THE COAST™  © 2026",
        fonts,
        x=zone["x"] + 215,
        y=zone["y"],
        width=zone["width"] - 215,
        height=zone["height"],
        steps=_typography_steps(mapping, "footer_brand"),
        role="sans_regular",
        fill=_color(mapping, "text/on-dark-muted"),
        family="Noto Sans",
        anchor="end",
        vertical="middle",
        single_line=True,
        data_role="footer-brand",
    )


def _draw_artwork(
    parent: ET.Element,
    defs: ET.Element,
    card: Mapping[str, str],
    zone: Mapping[str, Any],
    artwork_path: Path | None,
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    review_blocked: bool,
    *,
    corner_radius: float = 2,
) -> str:
    x, y, width, height = (zone[key] for key in ("x", "y", "width", "height"))
    card_id = card["card_id"]
    clip_id = f"art-clip-{card_id}"
    clip = _element(defs, "clipPath", id=clip_id)
    _rect(clip, x, y, width, height, radius=corner_radius)
    if artwork_path is not None and not review_blocked:
        raw = artwork_path.read_bytes()
        data_uri = f"data:image/png;base64,{base64.b64encode(raw).decode('ascii')}"
        _element(
            parent,
            "image",
            x=x,
            y=y,
            width=width,
            height=height,
            preserveAspectRatio="xMidYMid slice",
            clip_path=f"url(#{clip_id})",
            href=data_uri,
            data_role="artwork",
        )
        warm_rim = _element(
            parent,
            "g",
            clip_path=f"url(#{clip_id})",
            data_role="artwork-warm-rim",
            data_depth=ART_EDGE_WARMTH_DEPTH,
            data_strength=ART_EDGE_WARMTH_OPACITY,
        )
        warm_edges = (
            ("left", x, y, ART_EDGE_WARMTH_DEPTH, height, "art-warm-left"),
            (
                "right",
                x + width - ART_EDGE_WARMTH_DEPTH,
                y,
                ART_EDGE_WARMTH_DEPTH,
                height,
                "art-warm-right",
            ),
            ("top", x, y, width, ART_EDGE_WARMTH_DEPTH, "art-warm-top"),
            (
                "bottom",
                x,
                y + height - ART_EDGE_WARMTH_DEPTH,
                width,
                ART_EDGE_WARMTH_DEPTH,
                "art-warm-bottom",
            ),
        )
        for edge, edge_x, edge_y, edge_width, edge_height, gradient_id in warm_edges:
            edge_element = _rect(
                warm_rim,
                edge_x,
                edge_y,
                edge_width,
                edge_height,
                fill=f"url(#{gradient_id})",
                role="artwork-warm-edge",
            )
            edge_element.set("data-edge", edge)
            edge_element.set("style", "mix-blend-mode:multiply")
        inner_shadow = _rect(
            parent,
            x,
            y,
            width,
            ART_TOP_INNER_SHADOW_DEPTH,
            fill="url(#art-top-inner-shadow)",
            role="artwork-top-inner-shadow",
        )
        inner_shadow.set("clip-path", f"url(#{clip_id})")
        inner_shadow.set("data-edge", "top")
        inner_shadow.set("data-depth", _attr_number(ART_TOP_INNER_SHADOW_DEPTH))
        inner_shadow.set("data-max-opacity", _attr_number(ART_TOP_INNER_SHADOW_OPACITY))
        return _sha256_bytes(raw)
    placeholder_group = _element(
        parent,
        "g",
        clip_path=f"url(#{clip_id})",
        data_role="artwork-placeholder-group",
    )
    _rect(
        placeholder_group,
        x,
        y,
        width,
        height,
        fill=_color(mapping, "background/placeholder"),
        radius=corner_radius,
        role="artwork-placeholder",
    )
    for offset in range(-int(height), int(width), 30):
        _element(
            placeholder_group,
            "line",
            x1=x + max(offset, 0),
            y1=y + max(-offset, 0),
            x2=x + min(offset + height, width),
            y2=y + min(height, height + offset),
            stroke=_color(mapping, "line/recessed"),
            stroke_width=INTERNAL_PLACEHOLDER_HATCH_STROKE,
            opacity=0.22,
            data_role="artwork-placeholder-hatch",
        )
    label = "BILDREVIEW OFFEN" if review_blocked else "ILLUSTRATION FEHLT"
    _draw_text(
        placeholder_group,
        label,
        fonts,
        x=x + 20,
        y=y + height / 2 - 18,
        width=width - 40,
        height=36,
        steps=_typography_steps(mapping, "artwork_placeholder"),
        role="sans_bold",
        fill=_color(mapping, "text/secondary"),
        family="Noto Sans",
        anchor="middle",
        vertical="middle",
        single_line=True,
    )
    return ""


def _draw_labeled_section(
    parent: ET.Element,
    label: str,
    text: str,
    zone: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    accent: str,
    typography_role: str,
    data_role: str,
    fitted: TextFit,
) -> None:
    x, y, width, height = (zone[key] for key in ("x", "y", "width", "height"))
    _element(
        parent,
        "line",
        x1=x,
        y1=y + SECTION_DIVIDER_OFFSET,
        x2=x + width,
        y2=y + SECTION_DIVIDER_OFFSET,
        stroke=accent,
        stroke_width=ACCENT_RULE_STROKE_WIDTH,
        data_role="section-divider",
        data_section=label.casefold(),
    )
    _draw_text(
        parent,
        label,
        fonts,
        x=x,
        y=y + SECTION_LABEL_Y_OFFSET,
        width=160,
        height=21,
        steps=_typography_steps(mapping, "section_label"),
        role="sans_bold",
        fill=accent,
        family="Noto Sans",
        single_line=True,
        data_role="section-label",
    )
    _draw_text(
        parent,
        text,
        fonts,
        x=x,
        y=y + SECTION_BODY_TOP_OFFSET,
        width=width,
        height=height - 14,
        steps=_typography_steps(mapping, typography_role),
        role="regular",
        fill=_color(mapping, "text/primary"),
        data_role=data_role,
        fitted=fitted,
    )


def _plan_flavor(
    card_id: str,
    text: str,
    zone: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
) -> FlavorPlan:
    _, y, width, height = (float(zone[key]) for key in ("x", "y", "width", "height"))
    if not text.strip():
        return FlavorPlan(fit=None, divider_y=None, content_frame_bottom=y)
    flavor_steps = _typography_steps(mapping, "flavor")
    try:
        fit = _fit_text(
            text,
            fonts,
            "italic",
            flavor_steps,
            width,
            height - FLAVOR_TOP_CLEARANCE - FLAVOR_BOTTOM_INSET,
            family="Noto Serif",
            flavor_aware=True,
        )
    except RenderError as error:
        raise RenderError(f"{card_id}: Flavor-Text passt nicht") from error
    _, line_height, lines, _, _ = fit
    block_top = y + height - FLAVOR_BOTTOM_INSET - len(lines) * line_height
    divider_y = block_top - FLAVOR_DIVIDER_GAP
    if divider_y < y:
        raise RenderError(
            f"{card_id}: Flavor-Trenner passt nicht ohne Fallback "
            f"({divider_y:.4f} < {y:.4f})"
        )
    return FlavorPlan(
        fit=fit,
        divider_y=divider_y,
        content_frame_bottom=divider_y - ACCENT_RULE_STROKE_WIDTH / 2,
    )


def _content_stack_frame(
    card_id: str,
    mapping: Mapping[str, Any],
    flavor_plan: FlavorPlan,
) -> tuple[float, float, float, float, float]:
    try:
        frame = mapping["geometry"]["content_stack_frame"]
        x = float(frame["x"])
        top = float(frame["y"])
        width = float(frame["width"])
        free_above_ratio = float(frame["free_above_ratio"])
        free_below_ratio = float(frame["free_below_ratio"])
    except (KeyError, TypeError, ValueError) as error:
        raise RenderError("Ungültiger gemeinsamer Inhaltsframe") from error
    if width <= 0 or top >= flavor_plan.content_frame_bottom:
        raise RenderError(f"{card_id}: Ungültiger gemeinsamer Inhaltsframe")
    if (
        free_above_ratio < 0
        or free_below_ratio < 0
        or abs(free_above_ratio + free_below_ratio - 1) > 1e-9
    ):
        raise RenderError("Inhaltsframe benötigt komplementäre Freiraumanteile")
    return x, top, width, free_above_ratio, free_below_ratio


def _balanced_stack_top(
    card_id: str,
    *,
    frame_top: float,
    frame_bottom: float,
    stack_height: float,
    free_above_ratio: float,
) -> float:
    frame_height = frame_bottom - frame_top
    if (
        frame_height <= 0
        or stack_height <= 0
        or not 0 <= free_above_ratio <= 1
    ):
        raise RenderError(f"{card_id}: Ungültige Inhaltsblockgeometrie")
    free_height = frame_height - stack_height
    if free_height <= 0:
        raise RenderError(
            f"{card_id}: Inhaltsblock lässt keinen freien Raum für 45/55 "
            f"und passt nicht ohne Fallback "
            f"({stack_height:.4f} >= {frame_height:.4f})"
        )
    return frame_top + free_height * free_above_ratio


def _content_stack_group(
    parent: ET.Element,
    card_id: str,
    layout_key: str,
    mapping: Mapping[str, Any],
    *,
    flavor_plan: FlavorPlan,
    stack_height: float,
) -> tuple[ET.Element, float, float, float]:
    _, frame_top, _, free_above_ratio, free_below_ratio = _content_stack_frame(
        card_id, mapping, flavor_plan
    )
    frame_bottom = flavor_plan.content_frame_bottom
    stack_top = _balanced_stack_top(
        card_id,
        frame_top=frame_top,
        frame_bottom=frame_bottom,
        stack_height=stack_height,
        free_above_ratio=free_above_ratio,
    )
    free_height = frame_bottom - frame_top - stack_height
    group = _element(
        parent,
        "g",
        data_role="content-stack",
        data_layout=layout_key,
        data_frame_top=frame_top,
        data_frame_bottom=frame_bottom,
        data_stack_top=stack_top,
        data_stack_bottom=stack_top + stack_height,
        data_stack_height=stack_height,
        data_free_above=free_height * free_above_ratio,
        data_free_below=free_height * free_below_ratio,
        data_free_above_ratio=free_above_ratio,
        data_free_below_ratio=free_below_ratio,
    )
    return group, stack_top, frame_top, frame_bottom


def _draw_project_stack(
    parent: ET.Element,
    card: Mapping[str, str],
    requirements_text: str,
    zones: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    accent: str,
    flavor_plan: FlavorPlan,
) -> None:
    card_id = card["card_id"]
    frame_x, _, frame_width, _, _ = _content_stack_frame(
        card_id, mapping, flavor_plan
    )
    try:
        spec = zones["content_stack"]
        requirements_fit_height = float(spec["requirements_fit_height"])
        goal_fit_height = float(spec["goal_fit_height"])
        section_gap = float(spec["section_gap"])
    except (KeyError, TypeError, ValueError) as error:
        raise RenderError(f"{card_id}: Ungültige Projekt-Stackgeometrie") from error
    if goal_fit_height <= 0 or requirements_fit_height <= 0 or section_gap < 0:
        raise RenderError(f"{card_id}: Ungültige Projekt-Stackgeometrie")
    try:
        requirements_fit = _fit_text(
            requirements_text,
            fonts,
            "regular",
            _typography_steps(mapping, "project_requirements"),
            frame_width,
            requirements_fit_height,
            family="Noto Serif",
        )
        goal_fit = _fit_text(
            card.get("project_goal", ""),
            fonts,
            "regular",
            _typography_steps(mapping, "project_goal"),
            frame_width,
            goal_fit_height,
            family="Noto Serif",
        )
    except RenderError as error:
        raise RenderError(f"{card_id}: Projekttext passt nicht") from error
    requirements_height = len(requirements_fit[2]) * requirements_fit[1]
    goal_height = len(goal_fit[2]) * goal_fit[1]
    header_span = SECTION_BODY_TOP_OFFSET - SECTION_LABEL_Y_OFFSET
    stack_height = (
        2 * header_span + requirements_height + section_gap + goal_height
    )
    group, stack_top, _, _ = _content_stack_group(
        parent,
        card_id,
        "project",
        mapping,
        flavor_plan=flavor_plan,
        stack_height=stack_height,
    )
    group.set("data-section-gap", _attr_number(section_gap))
    group.set("data-section-order", "anforderungen,projektziel")
    requirements_zone = {
        "x": frame_x,
        "y": stack_top - SECTION_LABEL_Y_OFFSET,
        "width": frame_width,
        "height": requirements_height + 14,
    }
    goal_label_top = stack_top + header_span + requirements_height + section_gap
    goal_zone = {
        "x": frame_x,
        "y": goal_label_top - SECTION_LABEL_Y_OFFSET,
        "width": frame_width,
        "height": goal_height + 14,
    }
    _draw_labeled_section(
        group,
        "ANFORDERUNGEN",
        requirements_text,
        requirements_zone,
        mapping,
        fonts,
        accent,
        "project_requirements",
        "project-requirements-text",
        requirements_fit,
    )
    _draw_labeled_section(
        group,
        "PROJEKTZIEL",
        card.get("project_goal", ""),
        goal_zone,
        mapping,
        fonts,
        accent,
        "project_goal",
        "project-goal-text",
        goal_fit,
    )


def _draw_factor_stack(
    parent: ET.Element,
    card: Mapping[str, str],
    zones: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    flavor_plan: FlavorPlan,
) -> None:
    card_id = card["card_id"]
    family_key = _family_key(card, "factor")
    try:
        family = mapping["families"][family_key]
    except KeyError as error:
        raise RenderError(
            f"{card_id}: Unbekannte Faktorfamilie {family_key!r}"
        ) from error

    frame_x, _, frame_width, _, _ = _content_stack_frame(
        card_id, mapping, flavor_plan
    )
    try:
        spec = zones["content_stack"]
        side_inset = float(spec["text_side_inset"])
        carrier_size = float(spec["carrier_size"])
        icon_size = float(spec["icon_size"])
        painted_gap = float(spec["painted_emblem_to_text_gap"])
        max_text_lines = int(spec["max_text_lines"])
    except (KeyError, TypeError, ValueError) as error:
        raise RenderError(f"{card_id}: Ungültige Faktor-Stackgeometrie") from error
    text_width = frame_width - 2 * side_inset
    if (
        side_inset < 0
        or text_width <= 0
        or carrier_size <= 0
        or icon_size <= 0
        or icon_size > carrier_size
        or painted_gap < 0
        or max_text_lines <= 0
    ):
        raise RenderError(f"{card_id}: Ungültige Faktor-Stackgeometrie")
    factor_steps = _typography_steps(mapping, "factor_rules")
    try:
        text_fit = _fit_text(
            card["rules_text"],
            fonts,
            "regular",
            factor_steps,
            text_width,
            max_text_lines * max(step[1] for step in factor_steps),
            family="Noto Serif",
        )
    except RenderError as error:
        raise RenderError(f"{card_id}: Faktor-Regeltext passt nicht") from error
    if len(text_fit[2]) > max_text_lines:
        raise RenderError(
            f"{card_id}: Faktor-Regeltext überschreitet {max_text_lines} Zeilen"
        )
    text_height = len(text_fit[2]) * text_fit[1]
    painted_carrier_height = carrier_size + STROKE_LINE
    stack_height = painted_carrier_height + painted_gap + text_height
    stack_group, painted_stack_top, _, _ = _content_stack_group(
        parent,
        card_id,
        "factor",
        mapping,
        flavor_plan=flavor_plan,
        stack_height=stack_height,
    )
    stack_group.set("data-emblem-to-text-gap", _attr_number(painted_gap))
    color = _color(mapping, family["color_token"])
    circle_x = frame_x + (frame_width - carrier_size) / 2
    circle_y = painted_stack_top + STROKE_LINE / 2
    icon_inset = (carrier_size - icon_size) / 2
    group = _element(
        stack_group,
        "g",
        data_role="factor-family-emblem",
        data_family=family_key,
    )
    carrier = _ellipse(
        group,
        circle_x,
        circle_y,
        carrier_size,
        carrier_size,
        fill="none",
        stroke=color,
        stroke_width=STROKE_LINE,
        opacity=FACTOR_EMBLEM_CARRIER_OPACITY,
    )
    carrier.set("data-role", "factor-family-emblem-carrier")
    carrier.set("data-family", family_key)
    _draw_icon(
        group,
        family["icon"],
        circle_x + icon_inset,
        circle_y + icon_inset,
        icon_size,
        color,
        role="factor-family-emblem-symbol",
        opacity=FACTOR_EMBLEM_ICON_OPACITY,
        attributes={"data_family": family_key},
    )

    text_y = painted_stack_top + painted_carrier_height + painted_gap
    _draw_text(
        stack_group,
        card["rules_text"],
        fonts,
        x=frame_x + side_inset,
        y=text_y,
        width=text_width,
        height=text_height,
        steps=factor_steps,
        role="regular",
        fill=_color(mapping, "text/primary"),
        anchor="middle",
        data_role="rules-text",
        fitted=text_fit,
    )


def _draw_event_stack(
    parent: ET.Element,
    card: Mapping[str, str],
    zones: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    flavor_plan: FlavorPlan,
) -> None:
    card_id = card["card_id"]
    frame_x, _, frame_width, _, _ = _content_stack_frame(
        card_id, mapping, flavor_plan
    )
    try:
        max_text_lines = int(zones["content_stack"]["max_text_lines"])
    except (KeyError, TypeError, ValueError) as error:
        raise RenderError(f"{card_id}: Ungültige Ereignis-Stackgeometrie") from error
    if max_text_lines <= 0:
        raise RenderError(f"{card_id}: Ungültige Ereignis-Stackgeometrie")
    event_steps = _typography_steps(mapping, "event_rules")
    try:
        fit = _fit_text(
            card["rules_text"],
            fonts,
            "regular",
            event_steps,
            frame_width,
            max_text_lines * max(step[1] for step in event_steps),
            family="Noto Serif",
        )
    except RenderError as error:
        raise RenderError(f"{card_id}: Ereignis-Regeltext passt nicht") from error
    if len(fit[2]) > max_text_lines:
        raise RenderError(
            f"{card_id}: Ereignis-Regeltext überschreitet {max_text_lines} Zeilen"
        )
    stack_height = len(fit[2]) * fit[1]
    group, stack_top, _, _ = _content_stack_group(
        parent,
        card_id,
        "event",
        mapping,
        flavor_plan=flavor_plan,
        stack_height=stack_height,
    )
    _draw_text(
        group,
        card["rules_text"],
        fonts,
        x=frame_x,
        y=stack_top,
        width=frame_width,
        height=stack_height,
        steps=event_steps,
        role="regular",
        fill=_color(mapping, "text/primary"),
        data_role="rules-text",
        fitted=fit,
    )


def _draw_flavor(
    parent: ET.Element,
    text: str,
    zone: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fonts: Mapping[str, Path],
    accent: str,
    plan: FlavorPlan,
) -> None:
    if plan.fit is None or plan.divider_y is None:
        return
    x, y, width, height = (zone[key] for key in ("x", "y", "width", "height"))
    flavor_steps = _typography_steps(mapping, "flavor")
    _draw_text(
        parent,
        text,
        fonts,
        x=x,
        y=y + FLAVOR_TOP_CLEARANCE,
        width=width,
        height=height - FLAVOR_TOP_CLEARANCE - FLAVOR_BOTTOM_INSET,
        steps=flavor_steps,
        role="italic",
        fill=_color(mapping, "text/secondary"),
        vertical="bottom",
        flavor_aware=True,
        data_role="flavor-text",
        fitted=plan.fit,
    )
    _element(
        parent,
        "line",
        x1=x,
        y1=plan.divider_y,
        x2=x + width,
        y2=plan.divider_y,
        stroke=accent,
        stroke_width=ACCENT_RULE_STROKE_WIDTH,
        opacity=FLAVOR_RULE_OPACITY,
        data_role="flavor-divider",
    )


def _review_flags(card_id: str, mapping: Mapping[str, Any]) -> tuple[bool, bool]:
    gates = mapping.get("review_gates", {})
    return (
        card_id in gates.get("content_blocked_card_ids", []),
        card_id in gates.get("artwork_blocked_card_ids", []),
    )


def _art_treatment_spec(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        spec = mapping["art_treatment"]
        configured_id = str(spec["id"])
    except (KeyError, TypeError) as error:
        raise RenderError("Bildbehandlung fehlt im Layout") from error

    if configured_id != ART_TREATMENT:
        raise RenderError(
            "Layout und Renderer verwenden unterschiedliche Bildbehandlungen: "
            f"{configured_id} != {ART_TREATMENT}"
        )
    return spec


def _resolve_art_treatment(
    mapping: Mapping[str, Any],
    zones: Mapping[str, Any],
) -> tuple[
    str,
    Mapping[str, Any],
    Mapping[str, Any],
    str,
    float,
    float,
]:
    """Resolve the one configured art treatment."""

    spec = _art_treatment_spec(mapping)
    treatment = str(spec["id"])
    try:
        art_surface = zones["art_surface"]
        art = zones["art"]
        art_radius = float(spec["art_radius"])
        mat_color_token = str(spec["mat_color_token"])
        clear_mat = float(spec["clear_mat"])
        mat_radius = float(spec["outer_radius"])
    except (KeyError, TypeError, ValueError) as error:
        raise RenderError(
            f"Unvollständige Bildbehandlung im Layout: {treatment}"
        ) from error
    if abs(float(art["width"]) * 2 - float(art["height"]) * 3) > 1e-6:
        raise RenderError(f"{treatment}: Bildfenster ist nicht exakt 3:2")
    if mat_radius < 0 or art_radius <= 0:
        raise RenderError(
            f"{treatment}: ungültige Eckenradien ({mat_radius:g}/{art_radius:g})"
        )
    clear_mats = (
        float(art["x"]) - float(art_surface["x"]),
        float(art["y"]) - float(art_surface["y"]),
        float(art_surface["x"])
        + float(art_surface["width"])
        - (float(art["x"]) + float(art["width"])),
        float(art_surface["y"])
        + float(art_surface["height"])
        - (float(art["y"]) + float(art["height"])),
    )
    if any(abs(value - clear_mat) > 1e-6 for value in clear_mats):
        raise RenderError(
            f"{treatment}: helles Passepartout ist nicht rundum {clear_mat:g} E"
        )
    return (
        treatment,
        art_surface,
        art,
        mat_color_token,
        mat_radius,
        art_radius,
    )


def _card_face_scale(profile: Mapping[str, Any]) -> float:
    """Uniform shrink that keeps the card face off the vendor safety mark."""

    vendor_safe = profile["master_svg"]["rectangles"]["vendor_safe"]
    half_width = vendor_safe["width"] / 2
    return (half_width - CARD_FACE_SAFE_CLEARANCE) / (half_width - INNER_CARD_FIELD_INSET)


def _card_face_transform(profile: Mapping[str, Any]) -> str:
    """Scale the face about the centre of the cut, the one point that cannot move."""

    trim = profile["master_svg"]["rectangles"]["trim"]
    centre_x = trim["x"] + trim["width"] / 2
    centre_y = trim["y"] + trim["height"] / 2
    return (
        f"translate({_attr_number(centre_x)} {_attr_number(centre_y)}) "
        f"scale({_card_face_scale(profile):.12f}) "
        f"translate({_attr_number(-centre_x)} {_attr_number(-centre_y)})"
    )


def build_card_svg(
    card: Mapping[str, str],
    profile: Mapping[str, Any],
    artwork_path: str | Path | None,
    proof: bool = False,
) -> bytes:
    """Create one self-contained SVG master in the profile coordinate system."""

    mapping = _load_layout()
    icon_manifest = _load_icon_manifest()
    fonts = _resolve_fonts()
    view_box = profile["master_svg"]["view_box"]
    layout_key = _layout_key(card)
    zones = mapping["geometry"]["layouts"][layout_key]
    polarity_key = ""
    if layout_key == "event":
        polarity_key = card.get("polarity", "")
        if not polarity_key:
            raise RenderError(f"{card['card_id']}: Polarität fehlt")
        if polarity_key not in mapping["polarities"]:
            raise RenderError(
                f"{card['card_id']}: Unbekannte Polarität {polarity_key!r}"
            )
    (
        art_treatment,
        art_surface,
        art,
        art_mat_token,
        art_mat_radius,
        art_corner_radius,
    ) = _resolve_art_treatment(mapping, zones)
    appearance = _appearance(card, mapping, layout_key)
    accent = _color(mapping, appearance["accent_token"])
    try:
        flavor_text = card["flavor_text"]
    except KeyError as error:
        raise RenderError(
            f"{card.get('card_id', '<ohne ID>')}: flavor_text fehlt"
        ) from error
    if not isinstance(flavor_text, str):
        raise RenderError(
            f"{card.get('card_id', '<ohne ID>')}: flavor_text muss Text sein"
        )
    if flavor_text and not flavor_text.strip():
        raise RenderError(
            f"{card.get('card_id', '<ohne ID>')}: flavor_text enthält nur Leerraum"
        )
    flavor_plan = _plan_flavor(
        card["card_id"], flavor_text, zones["flavor"], mapping, fonts
    )
    content_blocked, artwork_blocked = _review_flags(card["card_id"], mapping)
    render_mode = card.get("_render_mode", "preview")
    if render_mode == "print" and (content_blocked or artwork_blocked):
        raise RenderError(f"{card['card_id']}: Review-Sperre verhindert Print")

    root_attributes = {
        "version": "1.1",
        "width": "69.6mm",
        "height": "95mm",
        "viewBox": " ".join(str(value) for value in view_box),
        "data-renderer": f"dhk-card-renderer/{RENDERER_VERSION}",
        "data-card-id": card["card_id"],
        "data-mode": render_mode,
        "data-art-treatment": art_treatment,
        "data-icon-manifest-sha256": icon_manifest["_sha256"],
    }
    if polarity_key:
        root_attributes["data-polarity"] = polarity_key
    root = ET.Element(_q("svg"), root_attributes)
    title = _element(root, "title")
    title.text = f"{card['card_id']} · {card['name']}"
    metadata = _element(root, "metadata")
    metadata.text = json.dumps(
        {
            "artwork_blocked": artwork_blocked,
            "art_treatment": art_treatment,
            "card_id": card["card_id"],
            "content_blocked": content_blocked,
            "layout_config_sha256": mapping["_sha256"],
            "icon_manifest_sha256": icon_manifest["_sha256"],
            "profile_sha256": profile.get("_sha256", ""),
            "renderer": RENDERER_VERSION,
            "renderer_sha256": _renderer_sha256(),
            "source_csv_sha256": card.get("_source_csv_sha256", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    defs = _element(root, "defs")
    _define_material_defs(defs, mapping)
    trim_box = profile["master_svg"]["rectangles"]["trim"]
    trim_clip_id = f"trim-clip-{card['card_id']}"
    trim_clip = _element(defs, "clipPath", id=trim_clip_id)
    _rect(
        trim_clip,
        trim_box["x"],
        trim_box["y"],
        trim_box["width"],
        trim_box["height"],
    )
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
    vendor_safe_box = profile["master_svg"]["rectangles"]["vendor_safe"]
    inner_card_box = {
        "x": vendor_safe_box["x"] + INNER_CARD_FIELD_INSET,
        "y": vendor_safe_box["y"] + INNER_CARD_FIELD_INSET,
        "width": vendor_safe_box["width"] - 2 * INNER_CARD_FIELD_INSET,
        "height": vendor_safe_box["height"] - 2 * INNER_CARD_FIELD_INSET,
    }
    design_clip = _element(
        root,
        "g",
        id="card-design-clip",
        clip_path=f"url(#{trim_clip_id})",
    )
    face = _element(
        design_clip,
        "g",
        id="card-face",
        transform=_card_face_transform(profile),
    )
    _rect(
        face,
        inner_card_box["x"],
        inner_card_box["y"],
        inner_card_box["width"],
        inner_card_box["height"],
        fill="url(#inner-card-field-gradient)",
        radius=INNER_CARD_FIELD_RADIUS,
        role="inner-card-field",
    )

    old_width = mapping["geometry"]["document"]["width"]
    old_height = mapping["geometry"]["document"]["height"]
    scale_x = view_box[2] / old_width
    scale_y = view_box[3] / old_height
    design = _element(
        face,
        "g",
        id="card-design",
        transform=f"scale({scale_x:.12f} {scale_y:.12f})",
    )
    _flat_plate(
        design,
        zones["title_surface"],
        mapping,
        accent,
        fill_token="background/paper-raised",
        role="title-panel",
        corners="top",
        radius=TITLE_FOOTER_CORNER_RADIUS,
        show_accent=False,
    )
    _flat_plate(
        design,
        zones["type_surface"],
        mapping,
        accent,
        fill_token="background/paper-raised",
        role="type-panel",
    )
    _flat_plate(
        design,
        zones["content_surface"],
        mapping,
        accent,
        fill_token="background/paper-raised",
        role="content-panel",
    )
    _flat_plate(
        design,
        zones["footer_surface"],
        mapping,
        accent,
        fill_token="background/shell-raised-bottom",
        role="footer-panel",
        corners="bottom",
        radius=TITLE_FOOTER_CORNER_RADIUS,
        show_accent=False,
    )

    _rect(
        design,
        art_surface["x"],
        art_surface["y"],
        art_surface["width"],
        art_surface["height"],
        fill=_color(mapping, art_mat_token),
        radius=art_mat_radius,
        role="art-mat",
    )
    title_zone = zones["title"]
    _draw_title(design, card["name"], title_zone, mapping, fonts)
    _draw_identity_stamp(design, zones, mapping, layout_key)

    art_path = Path(artwork_path) if artwork_path else None
    if art_path is not None and not art_path.is_file():
        art_path = None
    artwork_sha = _draw_artwork(
        design,
        defs,
        card,
        art,
        art_path,
        mapping,
        fonts,
        artwork_blocked,
        corner_radius=art_corner_radius,
    )
    _draw_plate_keyline(
        design,
        art_surface["x"],
        art_surface["y"],
        art_surface["width"],
        art_surface["height"],
        mapping,
        plate_role="art-mat",
        corners="none",
        radius=art_mat_radius,
    )

    _draw_type_line(design, card, zones, mapping, fonts, accent, appearance, layout_key)

    if layout_key == "project":
        requirements_text = card["rules_text"]
        if requirements_text.casefold().startswith("abschluss:"):
            requirements_text = requirements_text[len("Abschluss:") :].lstrip()
        _draw_project_stack(
            design,
            card,
            requirements_text,
            zones,
            mapping,
            fonts,
            accent,
            flavor_plan,
        )
    elif layout_key == "factor":
        _draw_factor_stack(design, card, zones, mapping, fonts, flavor_plan)
    else:
        _draw_event_stack(design, card, zones, mapping, fonts, flavor_plan)
    _draw_flavor(
        design,
        flavor_text,
        zones["flavor"],
        mapping,
        fonts,
        accent,
        flavor_plan,
    )

    _draw_footer(design, card, zones["footer"], mapping, fonts, accent)

    if content_blocked or artwork_blocked:
        labels = []
        if content_blocked:
            labels.append("INHALT")
        if artwork_blocked:
            labels.append("BILD")
        badge_text = "REVIEW · " + "+".join(labels)
        badge_width = 170
        badge_inset = 7
        badge_x = art["x"] + art["width"] - badge_width - badge_inset
        badge_y = art["y"] + badge_inset
        _rect(
            design,
            badge_x,
            badge_y,
            badge_width,
            30,
            fill="#F5EEDB",
            stroke=accent,
            stroke_width=STROKE_LINE,
            radius=3,
            opacity=0.95,
            role="review-badge",
        )
        _draw_text(
            design,
            badge_text,
            fonts,
            x=badge_x + 6,
            y=badge_y + 4,
            width=158,
            height=22,
            steps=_typography_steps(mapping, "review_badge"),
            role="sans_bold",
            fill=accent,
            family="Noto Sans",
            anchor="middle",
            vertical="middle",
            single_line=True,
            data_role="review-badge-label",
        )

    typography_exceptions = [
        {
            "role": element.attrib.get("data-role", ""),
            "size": float(element.attrib["data-type-size-step"]),
            "line_height": float(element.attrib["data-line-height"]),
            "status": element.attrib["data-type-step-status"],
        }
        for element in design.iter()
        if element.attrib.get("data-type-step-status") == "prototype-emergency"
    ]
    if render_mode == "print" and typography_exceptions:
        roles = ", ".join(
            f"{item['role']} {item['size']:g}/{item['line_height']:g}"
            for item in typography_exceptions
        )
        raise RenderError(
            f"{card['card_id']}: Prototyp-Typografiestufe verhindert Print ({roles})"
        )

    used_icons: dict[str, dict[str, str]] = {}
    for element in design.iter():
        icon_key = element.attrib.get("data-icon")
        if not icon_key:
            continue
        used_icons[icon_key] = {
            "file": element.attrib["data-icon-source"],
            "sha256": element.attrib["data-icon-sha256"],
        }

    metadata.text = json.dumps(
        {
            "artwork_blocked": artwork_blocked,
            "artwork_sha256": artwork_sha,
            "art_treatment": art_treatment,
            "card_id": card["card_id"],
            "content_blocked": content_blocked,
            "layout": layout_key,
            "layout_config_sha256": mapping["_sha256"],
            "icon_manifest_sha256": icon_manifest["_sha256"],
            "icons": {key: used_icons[key] for key in sorted(used_icons)},
            "profile_sha256": profile.get("_sha256", ""),
            "renderer": RENDERER_VERSION,
            "renderer_sha256": _renderer_sha256(),
            "source_csv_sha256": card.get("_source_csv_sha256", ""),
            "typography_exceptions": typography_exceptions,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    if proof:
        proof_group = _element(root, "g", id="proof-guides", pointer_events="none")
        proof_size, proof_line_height, proof_status = _typography_steps(
            mapping, "proof_label"
        )[0]
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
                stroke_width=STROKE_LINE,
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
                font_feature_settings="'tnum' 1, 'lnum' 1"
                if any(character.isdigit() for character in label)
                else None,
                text_anchor=anchor,
                data_role=f"proof-label-{key}",
                data_font_role="sans_bold",
                data_type_size_step=proof_size,
                data_line_height=proof_line_height,
                data_type_step_status=proof_status,
            ).text = label

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def rasterize_svg(svg_bytes: bytes, width: int, height: int) -> bytes:
    """Rasterise an SVG directly at its requested final pixel dimensions."""

    fonts = _resolve_fonts()
    try:
        import resvg_py  # type: ignore[import-not-found]
    except ImportError:
        executable = shutil.which("rsvg-convert")
        if not executable:
            raise RenderError("Weder resvg_py noch rsvg-convert ist verfügbar") from None
        completed = subprocess.run(
            [executable, "--format=png", f"--width={width}", f"--height={height}"],
            input=svg_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            raise RenderError(
                "rsvg-convert ist fehlgeschlagen: "
                + completed.stderr.decode("utf-8", errors="replace").strip()
            )
        return completed.stdout
    return resvg_py.svg_to_bytes(
        svg_string=svg_bytes.decode("utf-8"),
        width=width,
        height=height,
        dpi=600,
        background="#171A1E",
        skip_system_fonts=True,
        font_files=[str(path) for path in fonts.values()],
        shape_rendering="geometric_precision",
        text_rendering="geometric_precision",
        image_rendering="optimize_quality",
    )


def _srgb_profile_bytes() -> bytes:
    """Return Pillow's pinned sRGB profile with a reproducible ICC header."""

    profile = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    # Bytes 24..35 are the ICC creation timestamp.  Pillow/lcms writes the
    # current second there, even though the actual colour profile is identical.
    # A fixed, valid date keeps independently executed builds byte-identical.
    profile[24:36] = struct.pack(">6H", 2026, 8, 28, 0, 0, 0)
    return bytes(profile)


def finalize_png(png_bytes: bytes, profile: Mapping[str, Any]) -> bytes:
    """Normalise renderer output to the printer portal's PNG contract."""

    output = profile["upload_png"]
    with Image.open(io.BytesIO(png_bytes)) as source:
        source.load()
        if source.size != (output["width"], output["height"]):
            raise RenderError(
                f"Rastergröße {source.width}×{source.height} statt "
                f"{output['width']}×{output['height']}"
            )
        image = source.convert("RGB")
    buffer = io.BytesIO()
    image.save(
        buffer,
        format="PNG",
        compress_level=9,
        optimize=False,
        dpi=(output["dpi"], output["dpi"]),
        icc_profile=_srgb_profile_bytes(),
    )
    result = buffer.getvalue()
    if len(result) > output["max_file_size"]["bytes"]:
        raise RenderError(
            f"PNG ist {len(result)} Bytes groß und überschreitet "
            f"{output['max_file_size']['bytes']} Bytes"
        )
    inspect_png(result, profile)
    return result


def inspect_png(
    png_bytes: bytes,
    profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return technical PNG facts and optionally enforce the profile."""

    with Image.open(io.BytesIO(png_bytes)) as image:
        image.load()
        dpi = image.info.get("dpi", (0.0, 0.0))
        report = {
            "width": image.width,
            "height": image.height,
            "size": [image.width, image.height],
            "mode": image.mode,
            "format": image.format,
            "dpi": [round(float(dpi[0]), 3), round(float(dpi[1]), 3)],
            "has_alpha": "A" in image.getbands() or "transparency" in image.info,
            "icc_profile": bool(image.info.get("icc_profile")),
            "bytes": len(png_bytes),
            "sha256": _sha256_bytes(png_bytes),
        }
    if profile is not None:
        output = profile["upload_png"]
        problems = []
        if report["size"] != [output["width"], output["height"]]:
            problems.append("falsche Pixelmaße")
        if report["mode"] != "RGB" or report["has_alpha"]:
            problems.append("nicht opakes RGB")
        if not report["icc_profile"]:
            problems.append("sRGB-ICC fehlt")
        if any(abs(value - output["dpi"]) > 1 for value in report["dpi"]):
            problems.append("600-dpi-Metadaten fehlen")
        if report["bytes"] > output["max_file_size"]["bytes"]:
            problems.append("Dateigröße über 32 MB")
        if problems:
            raise RenderError("PNG-Preflight: " + ", ".join(problems))
    return report


def _assert_print_ready(
    card: Mapping[str, str],
    artwork_path: Path,
    mapping: Mapping[str, Any],
) -> None:
    content_blocked, artwork_blocked = _review_flags(card["card_id"], mapping)
    problems = []
    if content_blocked:
        problems.append("Content-Review offen")
    if artwork_blocked:
        problems.append("Artwork-Review offen")
    if not artwork_path.is_file():
        problems.append("Illustration fehlt")
    if problems:
        raise RenderError(f"{card['card_id']}: Print-Gate: " + "; ".join(problems))


def _validate_print_source(csv_path: str | Path, layout: Mapping[str, Any]) -> None:
    source = Path(csv_path).resolve()
    if source != DEFAULT_CARDS.resolve():
        raise RenderError("Der Print-Modus akzeptiert ausschließlich die kanonische data/cards.csv")
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_cards.py")],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise RenderError(f"Kanonische Kartenvalidierung fehlgeschlagen: {details}")
    if layout.get("status") != "final":
        raise RenderError(f"Print-Gate: Layoutstatus {layout.get('status', 'leer')} statt final")
    if _tool_versions().get("resvg_py") != "0.5.0":
        raise RenderError("Print-Gate: resvg_py 0.5.0 ist nicht aktiv")


def render_selected(
    *,
    profile_path: str | Path = DEFAULT_PROFILE,
    csv_path: str | Path = DEFAULT_CARDS,
    artwork_dir: str | Path = DEFAULT_ARTWORK_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT,
    card_ids: Sequence[str] | None = None,
    proof: bool = False,
    mode: str = "preview",
    keep_svg: bool = True,
) -> dict[str, Any]:
    """Render a selected set and write PNGs, SVG masters, and a hash manifest."""

    if mode not in {"preview", "print"}:
        raise RenderError(f"Unbekannter Modus: {mode}")
    mapping = _load_layout()
    art_treatment = str(_art_treatment_spec(mapping)["id"])
    if mode == "print" and proof:
        raise RenderError("Proof-Guides sind im Print-Modus verboten")
    profile = load_profile(profile_path)
    cards = load_cards(csv_path)
    by_id = {card["card_id"]: card for card in cards}
    selected_ids = list(card_ids or profile["golden_card_ids"])
    unknown = [card_id for card_id in selected_ids if card_id not in by_id]
    if unknown:
        raise RenderError("Unbekannte Karten-IDs: " + ", ".join(unknown))
    if len(selected_ids) != len(set(selected_ids)):
        raise RenderError("Karten-Auswahl enthält doppelte IDs")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    svg_dir = destination / "svg"
    if keep_svg:
        svg_dir.mkdir(parents=True, exist_ok=True)
    if mode == "print":
        _validate_print_source(csv_path, mapping)
    fonts = _resolve_fonts()
    font_manifest = {
        role: {"name": path.name, "sha256": _sha256_file(path)} for role, path in fonts.items()
    }
    manifest: dict[str, Any] = {
        "schema": "dhk-card-render-manifest/v1",
        "renderer_version": RENDERER_VERSION,
        "renderer_sha256": _renderer_sha256(),
        "mode": mode,
        "art_treatment": art_treatment,
        "proof": proof,
        "profile_sha256": profile["_sha256"],
        "source_template_sha256": profile["source_template"]["sha256"],
        "layout_config_sha256": mapping["_sha256"],
        "source_csv_sha256": cards[0]["_source_csv_sha256"],
        "tools": _tool_versions(),
        "fonts": font_manifest,
        "icons": _icon_manifest_metadata(),
        "cards": [],
    }
    width = profile["upload_png"]["width"]
    height = profile["upload_png"]["height"]
    for card_id in selected_ids:
        card = dict(by_id[card_id])
        card["_render_mode"] = mode
        try:
            artwork_path = resolve_artwork(card_id, artwork_dir, mode=mode)
        except RenderError:
            if mode == "print":
                raise
            artwork_path = None
        if mode == "print":
            assert artwork_path is not None
            _assert_print_ready(card, artwork_path, mapping)
        svg_bytes = build_card_svg(
            card,
            profile,
            artwork_path,
            proof=proof,
        )
        svg_root = ET.fromstring(svg_bytes)
        svg_metadata = next(
            element
            for element in svg_root
            if element.tag.rsplit("}", 1)[-1] == "metadata"
        )
        card_metadata = json.loads(svg_metadata.text or "{}")
        raster_bytes = rasterize_svg(svg_bytes, width, height)
        png_bytes = finalize_png(raster_bytes, profile)
        png_path = destination / f"{card_id}.png"
        png_path.write_bytes(png_bytes)
        svg_path = svg_dir / f"{card_id}.svg"
        if keep_svg:
            svg_path.write_bytes(svg_bytes)
        inspection = inspect_png(png_bytes, profile)
        manifest["cards"].append(
            {
                "card_id": card_id,
                "artwork_sha256": _sha256_file(artwork_path) if artwork_path else "",
                "svg_sha256": _sha256_bytes(svg_bytes),
                "png_sha256": inspection["sha256"],
                "png_bytes": inspection["bytes"],
                "icons": card_metadata.get("icons", {}),
                "typography_exceptions": card_metadata.get("typography_exceptions", []),
            }
        )
    manifest_path = destination / "manifest.json"
    manifest_path.write_bytes(_json_bytes(manifest))
    return manifest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Erzeugt selbstenthaltene SVG-Master und 600-dpi-PNG-Kartenvorschauen."
    )
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--cards", type=Path, default=DEFAULT_CARDS)
    parser.add_argument("--artwork-dir", type=Path, default=DEFAULT_ARTWORK_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--card", action="append", dest="card_ids", metavar="KAT-ID")
    parser.add_argument("--all", action="store_true", help="Alle 82 Motive statt der vier Goldens")
    parser.add_argument("--proof", action="store_true", help="Schnitt- und Safe-Guides einblenden")
    parser.add_argument("--mode", choices=("preview", "print"), default="preview")
    parser.add_argument("--no-svg", action="store_true", help="Nur PNG und Manifest schreiben")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        cards = load_cards(args.cards)
        if args.all and args.card_ids:
            raise RenderError("--all und --card können nicht kombiniert werden")
        selected = [card["card_id"] for card in cards] if args.all else args.card_ids
        manifest = render_selected(
            profile_path=args.profile,
            csv_path=args.cards,
            artwork_dir=args.artwork_dir,
            output_dir=args.output,
            card_ids=selected,
            proof=args.proof,
            mode=args.mode,
            keep_svg=not args.no_svg,
        )
    except RenderError as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        return 1
    print(
        f"OK: {len(manifest['cards'])} Karten als {manifest['mode']} "
        f"[{manifest['art_treatment']}] in {args.output} "
        "(SVG-Master → 1644×2244 PNG, 600 dpi, RGB/sRGB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
