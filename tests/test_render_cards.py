from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from unittest.mock import patch

from PIL import Image, ImageCms


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "data" / "render_profile.json"
CARDS_PATH = ROOT / "data" / "cards.csv"
ARTWORK_DIR = ROOT / "data" / "cards"
sys.path.insert(0, str(ROOT))

# This import is intentionally direct: a missing renderer or an unavailable
# production dependency must fail test discovery instead of silently skipping
# the print contract.
from scripts import render_cards as renderer  # noqa: E402


GOLDEN_CARDS = {
    "KAT-C12": ("common", "Projektfaktor"),
    "KAT-R12": ("rare", "Projekt"),
    "KAT-U26": ("uncommon", "Ereignis"),
    "KAT-M07": ("mythic", "Ereignis"),
}

MASTER_VIEWBOX = (0, 0, 822, 1122)
PHYSICAL_RECTS = {
    "outer": (0.0, 0.0, 69.6, 95.0),
    "trim": (3.05, 3.05, 63.5, 88.9),
    "vendor_safe": (5.6, 5.6, 58.4, 83.8),
    "internal_text_safe": (6.6, 6.6, 56.4, 81.8),
}
MASTER_RECTS = {
    "outer": (0, 0, 822, 1122),
    "trim": (36, 36, 750, 1050),
    "vendor_safe": (66, 66, 690, 990),
    "internal_text_safe": (78, 78, 666, 966),
}
OUTPUT_RECTS = {
    "outer": (0, 0, 1644, 2244),
    "trim": (72, 72, 1500, 2100),
    "vendor_safe": (132, 132, 1380, 1980),
    "internal_text_safe": (156, 156, 1332, 1932),
}
OUTPUT_SIZE = (1644, 2244)
OUTPUT_DPI = 600
MAX_OUTPUT_BYTES = 32_000_000

FORBIDDEN_TRADE_DRESS_TERMS = (
    "beleren",
    "jacebeleren",
    "jace beleren",
    "mplantin",
    "magic: the gathering",
    "magic the gathering",
    "wizards of the coast",
)

URL_FUNCTION = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)

TYPOGRAPHY_CONTRACT = {
    "title": ("bold", ((26, 36, "standard"),)),
    "type_primary": ("sans_bold", ((22, 28, "standard"),)),
    "type_secondary": ("sans_regular", ((14, 18, "standard"),)),
    "section_label": ("sans_bold", ((14, 18, "standard"),)),
    "factor_rules": ("regular", ((27, 38, "standard"),)),
    "event_rules": ("regular", ((25, 35, "standard"),)),
    "project_requirements": ("regular", ((23, 32, "standard"),)),
    "project_goal": ("regular", ((20, 28, "standard"),)),
    "flavor": ("italic", ((16, 23, "standard"),)),
    "points": ("sans_bold", ((14, 18, "standard"),)),
    "footer_identity": ("sans_bold", ((14, 18, "standard"),)),
    "footer_brand": ("sans_regular", ((12, 15, "standard"),)),
    "artwork_placeholder": ("sans_bold", ((18, 23, "standard"),)),
    "review_badge": ("sans_bold", ((12, 15, "standard"),)),
    "proof_label": ("sans_bold", ((12, 15, "standard"),)),
    "board_heading": ("bold", ((36, 44, "standard"),)),
    "board_meta": ("regular", ((20, 28, "standard"),)),
}

SVG_ROLE_TO_TYPOGRAPHY = {
    "card-title": "title",
    "card-type": "type_primary",
    "card-category": "type_secondary",
    "event-keyword": "type_secondary",
    "section-label": "section_label",
    "project-goal-text": "project_goal",
    "project-requirements-text": "project_requirements",
    "flavor-text": "flavor",
    "project-points-label": "points",
    "footer-card-id": "footer_identity",
    "footer-identity-separator": "footer_identity",
    "footer-rarity": "footer_identity",
    "footer-brand": "footer_brand",
    "review-badge-label": "review_badge",
}

FONT_ROLE_CONTRACT = {
    "regular": ("Noto Serif", "400", "normal"),
    "bold": ("Noto Serif", "700", "normal"),
    "italic": ("Noto Serif", "400", "italic"),
    "sans_regular": ("Noto Sans", "400", "normal"),
    "sans_bold": ("Noto Sans", "700", "normal"),
}

TABULAR_FIGURE_FEATURES = "'tnum' 1, 'lnum' 1"


def _value(item: Any, key: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(key)
    return getattr(item, key, None)


def _cards_by_id(cards: Any) -> dict[str, Any]:
    """Normalize the two practical load_cards return shapes for assertions.

    The public API may return either an ordered sequence of card records or a
    mapping keyed by card ID. Additional card fields are deliberately ignored.
    """

    if isinstance(cards, Mapping):
        result: dict[str, Any] = {}
        for key, card in cards.items():
            card_id = _value(card, "card_id") or str(key)
            result[str(card_id)] = card
        return result

    if isinstance(cards, Sequence) and not isinstance(cards, (str, bytes, bytearray)):
        result = {}
        for card in cards:
            card_id = _value(card, "card_id")
            if not card_id:
                raise AssertionError("load_cards() returned a card without card_id")
            result[str(card_id)] = card
        return result

    raise AssertionError("load_cards() must return a mapping or a sequence of card records")


def _rect_tuple(rect: Mapping[str, Any]) -> tuple[int, int, int, int]:
    return tuple(int(rect[key]) for key in ("x", "y", "width", "height"))


def _float_rect_tuple(rect: Mapping[str, Any]) -> tuple[float, float, float, float]:
    return tuple(float(rect[key]) for key in ("x", "y", "width", "height"))


def _report_value(report: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in report:
            return report[key]
    raise AssertionError(f"inspect_png() report is missing one of {keys!r}")


def _text_lines(element: ET.Element) -> tuple[str, ...]:
    return tuple(
        child.text or ""
        for child in list(element)
        if child.tag.rsplit("}", 1)[-1] == "tspan"
    )


def _text_content(element: ET.Element) -> str:
    lines = _text_lines(element)
    return " ".join(lines) if lines else (element.text or "")


def _expected_tracking(text: str, size: float, family: str) -> float:
    if family == "Noto Serif" and size >= 36:
        return round(size * -0.0075, 2)
    if family != "Noto Sans" or not text.isupper():
        return 0.0
    if text in renderer.RARITY_TRACKING_LABELS:
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


class RenderCardsContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = renderer.load_profile(PROFILE_PATH)
        cls.cards = renderer.load_cards(CARDS_PATH)
        cls.cards_by_id = _cards_by_id(cls.cards)
        cls._svg_cache: dict[tuple[str, bool], bytes] = {}
        cls._png_cache: dict[str, bytes] = {}

    @classmethod
    def build_svg(cls, card_id: str, *, proof: bool = False) -> bytes:
        cache_key = (card_id, proof)
        if cache_key not in cls._svg_cache:
            artwork = renderer.resolve_artwork(card_id, ARTWORK_DIR)
            svg = renderer.build_card_svg(
                cls.cards_by_id[card_id], cls.profile, artwork, proof=proof
            )
            if not isinstance(svg, bytes):
                raise AssertionError("build_card_svg() must return UTF-8 encoded bytes")
            cls._svg_cache[cache_key] = svg
        return cls._svg_cache[cache_key]

    @classmethod
    def build_png(cls, card_id: str) -> bytes:
        if card_id not in cls._png_cache:
            svg = cls.build_svg(card_id)
            raster = renderer.rasterize_svg(svg, *OUTPUT_SIZE)
            if not isinstance(raster, bytes):
                raise AssertionError("rasterize_svg() must return PNG bytes")
            final = renderer.finalize_png(raster, cls.profile)
            if not isinstance(final, bytes):
                raise AssertionError("finalize_png() must return PNG bytes")
            cls._png_cache[card_id] = final
        return cls._png_cache[card_id]

    @staticmethod
    def visible_text(root: ET.Element) -> list[str]:
        return [
            element.text.strip()
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] in {"text", "tspan"}
            and element.text
            and element.text.strip()
        ]

    def assert_svg_contract(self, svg: bytes, card_id: str) -> ET.Element:
        try:
            root = ET.fromstring(svg)
        except (ET.ParseError, UnicodeDecodeError) as error:
            self.fail(f"{card_id}: SVG is not well-formed UTF-8 XML: {error}")

        self.assertEqual(root.tag.rsplit("}", 1)[-1], "svg")
        view_box = tuple(int(float(value)) for value in root.attrib["viewBox"].split())
        self.assertEqual(view_box, MASTER_VIEWBOX)

        decoded = svg.decode("utf-8")
        lowered = decoded.casefold()
        self.assertIn(card_id, decoded)
        self.assertNotIn("@import", lowered)
        for term in FORBIDDEN_TRADE_DRESS_TERMS:
            self.assertNotIn(term, lowered, f"{card_id}: forbidden trade-dress term {term!r}")

        # Namespace declarations legitimately contain W3C URLs. Only values
        # that a renderer could dereference count as external resources.
        for match in URL_FUNCTION.finditer(decoded):
            reference = match.group(2).strip()
            self.assertTrue(
                reference.startswith("#") or reference.startswith("data:"),
                f"{card_id}: external CSS URL {reference!r}",
            )

        image_references = 0
        for element in root.iter():
            self.assertNotEqual(element.tag.rsplit("}", 1)[-1], "script")
            for attribute, value in element.attrib.items():
                local_name = attribute.rsplit("}", 1)[-1].casefold()
                if local_name in {"href", "src"}:
                    if value.startswith("data:image/"):
                        image_references += 1
                    self.assertTrue(
                        value.startswith("#") or value.startswith("data:"),
                        f"{card_id}: external SVG reference {value!r}",
                    )

        self.assertGreaterEqual(image_references, 1, f"{card_id}: artwork is not embedded")
        return root

    def assert_png_contract(self, png: bytes, card_id: str) -> None:
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"), f"{card_id}: bad PNG signature")
        self.assertLess(len(png), MAX_OUTPUT_BYTES, f"{card_id}: PNG exceeds portal limit")

        with Image.open(io.BytesIO(png)) as image:
            image.load()
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, OUTPUT_SIZE)
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.getbands(), ("R", "G", "B"))
            self.assertNotIn("transparency", image.info)

            dpi = image.info.get("dpi")
            self.assertIsNotNone(dpi, f"{card_id}: PNG has no physical resolution metadata")
            assert dpi is not None
            self.assertAlmostEqual(float(dpi[0]), OUTPUT_DPI, delta=0.1)
            self.assertAlmostEqual(float(dpi[1]), OUTPUT_DPI, delta=0.1)

            icc_profile = image.info.get("icc_profile")
            self.assertIsInstance(icc_profile, bytes, f"{card_id}: PNG has no ICC profile")
            self.assertGreater(len(icc_profile), 100)
            try:
                opened_profile = ImageCms.getOpenProfile(io.BytesIO(icc_profile))
                description = ImageCms.getProfileDescription(opened_profile).casefold()
            except Exception as error:  # Pillow raises several backend-specific error types.
                self.fail(f"{card_id}: embedded ICC profile is invalid: {error}")
            self.assertIn("srgb", description.replace(" ", ""))

    def test_public_api_is_present(self) -> None:
        for name in (
            "load_profile",
            "load_cards",
            "resolve_artwork",
            "build_card_svg",
            "rasterize_svg",
            "finalize_png",
            "inspect_png",
            "render_selected",
        ):
            self.assertTrue(callable(getattr(renderer, name, None)), name)

    def test_load_cards_distinguishes_intentionally_blank_flavor(self) -> None:
        fieldnames = (
            "card_id",
            "name",
            "rarity",
            "card_type",
            "rules_text",
            "flavor_text",
        )
        row = {
            "card_id": "TEST-01",
            "name": "Testkarte",
            "rarity": "common",
            "card_type": "Ereignis",
            "rules_text": "Testregel.",
            "flavor_text": "",
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            cards_path = Path(temporary_directory) / "cards.csv"
            with cards_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row)
            self.assertEqual(renderer.load_cards(cards_path)[0]["flavor_text"], "")

            missing_column_path = Path(temporary_directory) / "missing.csv"
            without_flavor = tuple(
                field for field in fieldnames if field != "flavor_text"
            )
            with missing_column_path.open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=without_flavor)
                writer.writeheader()
                writer.writerow({key: value for key, value in row.items() if key in without_flavor})
            with self.assertRaisesRegex(renderer.RenderError, "flavor_text"):
                renderer.load_cards(missing_column_path)

            malformed_path = Path(temporary_directory) / "malformed.csv"
            malformed_path.write_text(
                ",".join(fieldnames) + "\n"
                + "TEST-01,Testkarte,common,Ereignis,Testregel.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(renderer.RenderError, "flavor_text"):
                renderer.load_cards(malformed_path)

            whitespace_path = Path(temporary_directory) / "whitespace.csv"
            with whitespace_path.open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({**row, "flavor_text": "   "})
            with self.assertRaisesRegex(renderer.RenderError, "nur Leerraum"):
                renderer.load_cards(whitespace_path)

    def test_layout_configuration_is_renderer_native(self) -> None:
        layout_path = ROOT / "data" / "card_layout.json"
        self.assertEqual(renderer.LAYOUT_PATH.resolve(), layout_path.resolve())
        layout_text = layout_path.read_text(encoding="utf-8")
        layout = json.loads(layout_text)
        self.assertEqual(layout["schema"], "dhk-card-layout/v1")
        self.assertEqual(layout["version"], "1.25.0")
        self.assertEqual(renderer.RENDERER_VERSION, "0.30.0")
        self.assertNotIn("figma", layout_text.casefold())
        for term in FORBIDDEN_TRADE_DRESS_TERMS:
            self.assertNotIn(term, layout_text.casefold())

    def test_front_uses_three_step_stroke_scale(self) -> None:
        self.assertEqual(renderer.PRODUCTION_STROKE_SCALE, (1.0, 1.5, 2.25))
        production_widths: set[float] = set()

        for card_id, card in self.cards_by_id.items():
            with self.subTest(card_id=card_id):
                root = ET.fromstring(
                    renderer.build_card_svg(card, self.profile, None, proof=False)
                )
                identity_stamp = next(
                    element
                    for element in root.iter()
                    if element.attrib.get("data-role") == "card-type-badge"
                )
                identity_strokes = {
                    id(element)
                    for element in identity_stamp.iter()
                    if "stroke-width" in element.attrib
                }
                self.assertTrue(identity_strokes)

                for element in root.iter():
                    if "stroke-width" not in element.attrib:
                        continue
                    stroke_width = float(element.attrib["stroke-width"])
                    role = element.attrib.get("data-role", "")
                    if role == "artwork-placeholder-hatch":
                        self.assertEqual(
                            stroke_width,
                            renderer.INTERNAL_PLACEHOLDER_HATCH_STROKE,
                        )
                        continue

                    production_widths.add(stroke_width)
                    self.assertIn(stroke_width, renderer.PRODUCTION_STROKE_SCALE)
                    if stroke_width == renderer.STROKE_EMPHASIS:
                        self.assertIn(id(element), identity_strokes)

                self.assertEqual(
                    {
                        float(element.attrib["stroke-width"])
                        for element in identity_stamp.iter()
                        if "stroke-width" in element.attrib
                    },
                    {renderer.STROKE_EMPHASIS},
                )

        self.assertEqual(production_widths, set(renderer.PRODUCTION_STROKE_SCALE))

        proof_root = ET.fromstring(
            renderer.build_card_svg(
                self.cards_by_id["KAT-C12"],
                self.profile,
                None,
                proof=True,
            )
        )
        proof_strokes = {
            float(element.attrib["stroke-width"])
            for element in proof_root.iter()
            if element.attrib.get("data-role", "").startswith("proof-")
            and "stroke-width" in element.attrib
        }
        self.assertEqual(proof_strokes, {renderer.STROKE_LINE})

    def test_typography_configuration_defines_only_fixed_descending_steps(self) -> None:
        layout = renderer._load_layout()
        self.assertEqual(set(layout["typography"]), set(TYPOGRAPHY_CONTRACT))

        for typography_role, (font_role, expected_steps) in TYPOGRAPHY_CONTRACT.items():
            with self.subTest(typography_role=typography_role):
                spec = layout["typography"][typography_role]
                self.assertEqual(spec["font_role"], font_role)
                self.assertNotIn("size", spec)
                self.assertNotIn("line_height", spec)
                actual_steps = tuple(
                    (
                        int(step["size"]),
                        int(step["line_height"]),
                        step.get("status", "standard"),
                    )
                    for step in spec["steps"]
                )
                self.assertEqual(actual_steps, expected_steps)
                self.assertEqual(
                    tuple(size for size, _, _ in actual_steps),
                    tuple(sorted((size for size, _, _ in actual_steps), reverse=True)),
                )
                self.assertTrue(
                    all(
                        isinstance(step["size"], int)
                        and isinstance(step["line_height"], int)
                        for step in spec["steps"]
                    )
                )
                self.assertEqual(
                    renderer._typography_steps(layout, typography_role),
                    tuple(
                        (float(size), float(line_height), status)
                        for size, line_height, status in expected_steps
                    ),
                )

    def test_fit_text_selects_a_declared_step_or_fails_without_interpolation(self) -> None:
        fonts = renderer._resolve_fonts()
        text = "WWWWWWWWWWWWWWWWWW"
        large_font = renderer._font(fonts, "regular", 20)
        small_font = renderer._font(fonts, "regular", 16)
        large_width = renderer._text_width(text, large_font)
        small_width = renderer._text_width(text, small_font)
        available_width = (large_width + small_width) / 2
        steps = ((20.0, 28.0, "standard"), (16.0, 20.0, "prototype-emergency"))

        fitted = renderer._fit_text(
            text,
            fonts,
            "regular",
            steps,
            available_width,
            40,
            family="Noto Serif",
            single_line=True,
        )
        self.assertEqual(fitted[:2], (16.0, 20.0))
        self.assertEqual(fitted[4], "prototype-emergency")
        self.assertNotIn(fitted[0], {16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5})

        with self.assertRaises(renderer.RenderError):
            renderer._fit_text(
                text,
                fonts,
                "regular",
                steps,
                small_width - 1,
                40,
                family="Noto Serif",
                single_line=True,
            )

    def test_all_card_types_share_one_3_2_art_window_and_have_type_symbols(self) -> None:
        layout = json.loads((ROOT / "data" / "card_layout.json").read_text(encoding="utf-8"))
        art_rectangles = {
            _float_rect_tuple(spec["art"])
            for spec in layout["geometry"]["layouts"].values()
        }
        self.assertEqual(art_rectangles, {(78.0, 131.8644, 534.0, 356.0)})
        _, _, art_width, art_height = next(iter(art_rectangles))
        self.assertEqual(art_width * 2, art_height * 3)
        self.assertEqual(
            {
                _float_rect_tuple(spec["art_surface"])
                for spec in layout["geometry"]["layouts"].values()
            },
            {(70.0, 123.8644, 550.0, 372.0)},
        )
        for spec in layout["geometry"]["layouts"].values():
            surface_x, surface_y, surface_width, surface_height = _float_rect_tuple(
                spec["art_surface"]
            )
            art_x, art_y, art_width, art_height = _float_rect_tuple(spec["art"])
            self.assertEqual(
                tuple(
                    round(value, 4)
                    for value in (
                        art_x - surface_x,
                        art_y - surface_y,
                        surface_x + surface_width - (art_x + art_width),
                        surface_y + surface_height - (art_y + art_height),
                    )
                ),
                (8.0, 8.0, 8.0, 8.0),
            )
            self.assertEqual(spec["title_surface"]["x"], spec["art_surface"]["x"])
            self.assertEqual(
                spec["title_surface"]["width"], spec["art_surface"]["width"]
            )
            self.assertEqual(spec["art_surface"]["x"], spec["type_surface"]["x"])
            self.assertEqual(
                spec["art_surface"]["width"], spec["type_surface"]["width"]
            )
            self.assertEqual(spec["art_surface"]["x"], spec["content_surface"]["x"])
            self.assertEqual(
                spec["art_surface"]["width"], spec["content_surface"]["width"]
            )
            self.assertEqual(spec["art_surface"]["x"], spec["footer_surface"]["x"])
            self.assertEqual(
                spec["art_surface"]["width"], spec["footer_surface"]["width"]
            )
        self.assertEqual(
            {_rect_tuple(spec["title"]) for spec in layout["geometry"]["layouts"].values()},
            {(126, 73, 490, 44)},
        )
        self.assertEqual(
            {
                _float_rect_tuple(spec["title_surface"])
                for spec in layout["geometry"]["layouts"].values()
            },
            {(70.0, 69.8644, 550.0, 50.0)},
        )
        self.assertEqual(
            {
                _float_rect_tuple(spec["footer_surface"])
                for spec in layout["geometry"]["layouts"].values()
            },
            {(70.0, 840.1356, 550.0, 30.0)},
        )
        self.assertEqual(
            {
                _float_rect_tuple(spec["footer"])
                for spec in layout["geometry"]["layouts"].values()
            },
            {(78.0, 844.1356, 534.0, 22.0)},
        )
        shared_inner_edges = {
            float(spec["type"]["x"])
            for spec in layout["geometry"]["layouts"].values()
        }
        self.assertEqual(shared_inner_edges, {78.0})
        shared_inner_edge = next(iter(shared_inner_edges))

        for card_id in GOLDEN_CARDS:
            root = self.assert_svg_contract(self.build_svg(card_id), card_id)
            roles = {element.attrib.get("data-role") for element in root.iter()}
            self.assertIn("card-type-symbol", roles, card_id)
            self.assertIn("card-type-badge", roles, card_id)
            self.assertNotIn("identity-code", roles, card_id)
            self.assertNotIn("accent-frame", roles, card_id)
            self.assertNotIn("archive-spine", roles, card_id)
            badge = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-type-badge"
            )
            self.assertEqual(badge.attrib["transform"], "translate(76 74.8644)")
            carrier = next(
                element
                for element in list(badge)
                if element.attrib.get("data-role") == "card-type-carrier"
            )
            self.assertEqual(carrier.tag.rsplit("}", 1)[-1], "ellipse")
            transform = re.fullmatch(
                r"translate\(([-\d.]+) ([-\d.]+)\)", badge.attrib["transform"]
            )
            self.assertIsNotNone(transform)
            assert transform is not None
            carrier_left = (
                float(transform.group(1))
                + float(carrier.attrib["cx"])
                - float(carrier.attrib["rx"])
            )
            self.assertEqual(carrier_left, shared_inner_edge)
            type_symbol = next(
                element
                for element in badge.iter()
                if element.attrib.get("data-role") == "card-type-symbol"
            )
            expected_icon = {
                "Projekt": "project",
                "Projektfaktor": "project_factor",
                "Ereignis": "event",
            }[str(_value(self.cards_by_id[card_id], "card_type"))]
            self.assertEqual(type_symbol.attrib["data-icon"], expected_icon)
            self.assertEqual(type_symbol.attrib["data-icon-version"], "2.1.1")
            self.assertEqual(type_symbol.attrib["data-icon-weight"], "bold")

            layout = renderer._load_layout()
            neutral = renderer._color(layout, "line/default")
            paper = renderer._color(layout, "background/paper")
            self.assertEqual(carrier.attrib["fill"], paper)
            self.assertEqual(carrier.attrib["data-fill-mode"], "neutral-paper")
            self.assertEqual(carrier.attrib["data-fill-token"], "background/paper")
            self.assertNotIn("opacity", carrier.attrib)
            self.assertNotIn("fill-opacity", carrier.attrib)
            self.assertEqual(carrier.attrib["stroke"], neutral)
            self.assertEqual(type_symbol.attrib["fill"], neutral)

    def test_all_titles_use_one_size_and_keep_ink_inside_the_title_zone(self) -> None:
        title_sizes: dict[str, float] = {}
        title_widths: dict[str, float] = {}
        top_margins: dict[str, float] = {}
        bottom_margins: dict[str, float] = {}
        fonts = renderer._resolve_fonts()
        title_font = renderer._font(fonts, "bold", 26)
        title_zone = renderer._load_layout()["geometry"]["layouts"]["project"][
            "title"
        ]
        for card_id, card in self.cards_by_id.items():
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            title = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-title"
            )
            title_sizes[card_id] = float(title.attrib["font-size"])
            title_widths[card_id] = renderer._text_width(
                str(_value(card, "name")),
                title_font,
                float(title.attrib.get("letter-spacing", "0")),
            )
            _, ink_top, _, ink_bottom = title_font.getbbox(
                str(_value(card, "name")), anchor="ls"
            )
            baseline = float(title.attrib["y"])
            top_margins[card_id] = baseline + ink_top / 4 - float(title_zone["y"])
            bottom_margins[card_id] = (
                float(title_zone["y"])
                + float(title_zone["height"])
                - baseline
                - ink_bottom / 4
            )
            self.assertNotIn("RANDNOTIZ", self.visible_text(root), card_id)
        self.assertEqual(set(title_sizes.values()), {26.0})
        self.assertEqual(max(title_widths, key=title_widths.get), "KAT-R14")
        self.assertLessEqual(max(title_widths.values()), float(title_zone["width"]))
        self.assertAlmostEqual(
            float(title_zone["width"]) - max(title_widths.values()), 36.5, places=1
        )
        self.assertGreaterEqual(min(top_margins.values()), 8.0)
        self.assertGreaterEqual(min(bottom_margins.values()), 5.5)

    def test_modules_and_content_use_the_shared_horizontal_edges(self) -> None:
        layout = renderer._load_layout()["geometry"]["layouts"]
        for layout_name, spec in layout.items():
            with self.subTest(layout=layout_name):
                for zone_name in (
                    "title_surface",
                    "art_surface",
                    "type_surface",
                    "content_surface",
                    "footer_surface",
                ):
                    zone = spec[zone_name]
                    self.assertEqual(
                        (float(zone["x"]), float(zone["x"] + zone["width"])),
                        (70.0, 620.0),
                    )

                for zone_name in {
                    "type",
                    "goal",
                    "rules",
                    "flavor",
                    "footer",
                }.intersection(spec):
                    zone = spec[zone_name]
                    self.assertEqual(float(zone["x"]), 78.0)
                    if zone_name != "type":
                        self.assertEqual(float(zone["x"] + zone["width"]), 612.0)

        project = self.assert_svg_contract(self.build_svg("KAT-R12"), "KAT-R12")
        factor = self.assert_svg_contract(self.build_svg("KAT-C12"), "KAT-C12")
        event = self.assert_svg_contract(self.build_svg("KAT-U26"), "KAT-U26")

        def role(root: ET.Element, name: str) -> ET.Element:
            return next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == name
            )

        for root in (project, factor, event):
            art_keyline = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "plate-keyline"
                and element.attrib.get("data-plate-role") == "art-mat"
            )
            keyline_stroke = float(art_keyline.attrib["stroke-width"])
            self.assertEqual(
                (
                    float(art_keyline.attrib["x"]) - keyline_stroke / 2,
                    float(art_keyline.attrib["x"])
                    + float(art_keyline.attrib["width"])
                    + keyline_stroke / 2,
                ),
                (70.0, 620.0),
            )
            for text_role in ("card-type", "flavor-text", "footer-card-id"):
                text = role(root, text_role)
                self.assertEqual(float(text.attrib["x"]), 78.0)
                self.assertEqual(text.attrib["text-anchor"], "start")
                self.assertTrue(
                    all(float(tspan.attrib["x"]) == 78.0 for tspan in list(text)),
                    text_role,
                )
            flavor_divider = role(root, "flavor-divider")
            self.assertEqual(
                (
                    float(flavor_divider.attrib["x1"]),
                    float(flavor_divider.attrib["x2"]),
                ),
                (78.0, 612.0),
            )
            footer_brand = role(root, "footer-brand")
            self.assertEqual(float(footer_brand.attrib["x"]), 612.0)
            self.assertEqual(footer_brand.attrib["text-anchor"], "end")
            self.assertTrue(
                all(float(tspan.attrib["x"]) == 612.0 for tspan in list(footer_brand))
            )
            for panel_name in ("type-panel", "content-panel"):
                accent = role(root, f"{panel_name}-accent")
                self.assertEqual(
                    (
                        float(accent.attrib["x"]),
                        float(accent.attrib["x"])
                        + float(accent.attrib["width"]),
                    ),
                    (78.0, 612.0),
                )

        for name in (
            "section-label",
            "project-goal-text",
            "project-requirements-text",
        ):
            matching = [
                element
                for element in project.iter()
                if element.attrib.get("data-role") == name
            ]
            self.assertTrue(matching, name)
            self.assertTrue(
                all(float(element.attrib["x"]) == 78.0 for element in matching),
                name,
            )
            self.assertTrue(
                all(element.attrib["text-anchor"] == "start" for element in matching),
                name,
            )
            self.assertTrue(
                all(
                    float(tspan.attrib["x"]) == 78.0
                    for element in matching
                    for tspan in list(element)
                ),
                name,
            )
        for divider in (
            element
            for element in project.iter()
            if element.attrib.get("data-role") == "section-divider"
        ):
            self.assertEqual(
                (float(divider.attrib["x1"]), float(divider.attrib["x2"])),
                (78.0, 612.0),
            )
        event_rules_text = role(event, "rules-text")
        self.assertEqual(float(event_rules_text.attrib["x"]), 78.0)
        self.assertEqual(event_rules_text.attrib["text-anchor"], "start")
        self.assertTrue(
            all(
                float(tspan.attrib["x"]) == 78.0
                for tspan in list(event_rules_text)
            )
        )

    def test_domain_accent_rules_share_width_span_and_opacity(self) -> None:
        layout = renderer._load_layout()
        structural_roles = {
            "type-panel-accent",
            "content-panel-accent",
            "flavor-divider",
            "section-divider",
        }
        expected_span = (
            float(renderer.ACCENT_RULE_X_START),
            float(renderer.ACCENT_RULE_X_END),
        )

        for card_id, card in self.cards_by_id.items():
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            layout_key = renderer._layout_key(card)
            appearance = renderer._appearance(card, layout, layout_key)
            expected_color = renderer._color(layout, appearance["accent_token"])
            accents = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") in structural_roles
            ]
            expected_counts = {
                "type-panel-accent": 1,
                "content-panel-accent": 1,
                "flavor-divider": 1,
                "section-divider": 2 if layout_key == "project" else 0,
            }
            self.assertEqual(
                {
                    role: sum(
                        element.attrib["data-role"] == role for element in accents
                    )
                    for role in structural_roles
                },
                expected_counts,
                card_id,
            )

            for element in accents:
                role = element.attrib["data-role"]
                if element.tag.rsplit("}", 1)[-1] == "line":
                    span = (
                        float(element.attrib["x1"]),
                        float(element.attrib["x2"]),
                    )
                    thickness = float(element.attrib["stroke-width"])
                    color = element.attrib["stroke"]
                else:
                    span = (
                        float(element.attrib["x"]),
                        float(element.attrib["x"])
                        + float(element.attrib["width"]),
                    )
                    thickness = float(
                        element.attrib.get("stroke-width", element.attrib["height"])
                    )
                    color = element.attrib.get("stroke", element.attrib["fill"])
                self.assertEqual(span, expected_span, f"{card_id}:{role}")
                self.assertEqual(
                    thickness,
                    renderer.ACCENT_RULE_STROKE_WIDTH,
                    f"{card_id}:{role}",
                )
                self.assertEqual(color, expected_color, f"{card_id}:{role}")
                if role == "flavor-divider":
                    self.assertEqual(
                        float(element.attrib["opacity"]),
                        renderer.FLAVOR_RULE_OPACITY,
                    )
                else:
                    self.assertNotIn("opacity", element.attrib, f"{card_id}:{role}")

    def test_module_stack_uses_four_equal_gaps_and_matching_outer_margins(self) -> None:
        geometry = renderer._load_layout()["geometry"]
        module_names = (
            "title_surface",
            "art_surface",
            "type_surface",
            "content_surface",
            "footer_surface",
        )

        for layout_name, spec in geometry["layouts"].items():
            with self.subTest(layout=layout_name):
                modules = [spec[name] for name in module_names]
                gaps = tuple(
                    float(lower["y"])
                    - (float(upper["y"]) + float(upper["height"]))
                    for upper, lower in zip(modules, modules[1:])
                )
                self.assertEqual(
                    tuple(round(gap, 4) for gap in gaps),
                    (4.0, 4.0, 4.0, 4.0),
                )

                view_box = self.profile["master_svg"]["view_box"]
                scale_x = float(view_box[2]) / float(geometry["document"]["width"])
                scale_y = float(view_box[3]) / float(geometry["document"]["height"])
                vendor_safe = self.profile["master_svg"]["rectangles"]["vendor_safe"]
                card_field = {
                    "left": float(vendor_safe["x"]) + renderer.INNER_CARD_FIELD_INSET,
                    "top": float(vendor_safe["y"]) + renderer.INNER_CARD_FIELD_INSET,
                    "right": float(vendor_safe["x"])
                    + float(vendor_safe["width"])
                    - renderer.INNER_CARD_FIELD_INSET,
                    "bottom": float(vendor_safe["y"])
                    + float(vendor_safe["height"])
                    - renderer.INNER_CARD_FIELD_INSET,
                }
                margins = (
                    float(modules[0]["x"]) * scale_x - card_field["left"],
                    card_field["right"]
                    - (
                        float(modules[0]["x"]) + float(modules[0]["width"])
                    )
                    * scale_x,
                    float(modules[0]["y"]) * scale_y - card_field["top"],
                    card_field["bottom"]
                    - (
                        float(modules[-1]["y"])
                        + float(modules[-1]["height"])
                    )
                    * scale_y,
                )
                for margin in margins[1:]:
                    self.assertAlmostEqual(margin, margins[0], places=4)

    def test_trade_dress_copy_and_information_hierarchy(self) -> None:
        project = self.assert_svg_contract(self.build_svg("KAT-R12"), "KAT-R12")
        factor = self.assert_svg_contract(self.build_svg("KAT-C12"), "KAT-C12")
        event_positive = self.assert_svg_contract(self.build_svg("KAT-U26"), "KAT-U26")
        event_negative = self.assert_svg_contract(self.build_svg("KAT-C03"), "KAT-C03")

        project_text = self.visible_text(project)
        factor_text = self.visible_text(factor)
        positive_text = self.visible_text(event_positive)
        negative_text = self.visible_text(event_negative)
        all_text = project_text + factor_text + positive_text + negative_text

        self.assertIn("ANFORDERUNGEN", project_text)
        self.assertNotIn("WIRKUNG", all_text)
        self.assertNotIn("AUSWIRKUNG", all_text)
        for forbidden_label in ("POSITIV", "NEGATIV", "AMBIVALENT"):
            self.assertNotIn(forbidden_label, all_text)
        for obsolete_code in ("PRJ", "FAK", "ERE", "POS", "NEG", "AMB"):
            self.assertNotIn(obsolete_code, all_text)
        self.assertNotIn("RANDNOTIZ", all_text)
        self.assertNotIn("Abschluss:", project_text)
        self.assertIn("4P", project_text)
        self.assertNotIn("4 P", project_text)
        self.assertNotIn("PUNKTE", project_text)
        self.assertIn("NACHZIEHEN", positive_text)
        self.assertFalse(
            any(
                element.attrib.get("data-role") == "event-parameters"
                for element in event_positive.iter()
            )
        )

        for root in (project, factor):
            primary = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-type"
            )
            category = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-category"
            )
            self.assertLess(float(category.attrib["font-size"]), float(primary.attrib["font-size"]))

    def test_events_and_factors_render_rules_without_a_wirkung_label(self) -> None:
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") == "Projekt":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            self.assertNotIn("WIRKUNG", self.visible_text(root), card_id)
            rules = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "rules-text"
            ]
            self.assertEqual(len(rules), 1, card_id)

    def test_all_flavor_text_uses_16_23_in_one_line_at_the_bottom(self) -> None:
        layout = renderer._load_layout()
        flavor_font = renderer._font(renderer._resolve_fonts(), "italic", 16)
        flavor_zones = {
            _float_rect_tuple(spec["flavor"])
            for spec in layout["geometry"]["layouts"].values()
        }
        self.assertEqual(flavor_zones, {(78.0, 790.1356, 534.0, 46.0)})
        for spec in layout["geometry"]["layouts"].values():
            flavor_zone = spec["flavor"]
            content_zone = spec["content_surface"]
            self.assertEqual(flavor_zone["x"], content_zone["x"] + 8)
            self.assertEqual(flavor_zone["width"], content_zone["width"] - 16)
            self.assertAlmostEqual(
                flavor_zone["y"] + flavor_zone["height"],
                content_zone["y"] + content_zone["height"],
                places=4,
            )

        baselines: set[float] = set()
        divider_positions: set[float] = set()
        for card_id, card in self.cards_by_id.items():
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            flavor = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "flavor-text"
            )
            self.assertEqual(
                (
                    float(flavor.attrib["font-size"]),
                    float(flavor.attrib["data-line-height"]),
                    flavor.attrib["font-style"],
                ),
                (16.0, 23.0, "italic"),
                card_id,
            )
            lines = _text_lines(flavor)
            self.assertEqual(lines, (str(_value(card, "flavor_text")),), card_id)
            zone = layout["geometry"]["layouts"][renderer._layout_key(card)]["flavor"]
            zone_bottom = float(zone["y"]) + float(zone["height"])
            size = float(flavor.attrib["font-size"])
            line_height = float(flavor.attrib["data-line-height"])
            baseline = float(flavor.attrib["y"])
            baselines.add(baseline)
            block_top = baseline - size
            block_bottom = baseline - size + len(lines) * line_height
            self.assertEqual(
                zone_bottom - block_bottom,
                float(renderer.FLAVOR_BOTTOM_INSET),
                card_id,
            )
            last_baseline = baseline + (len(lines) - 1) * line_height
            ink_bottom = flavor_font.getbbox(lines[-1], anchor="ls")[3] / 4
            self.assertGreaterEqual(zone_bottom - last_baseline - ink_bottom, 5.0, card_id)
            self.assertLessEqual(zone_bottom - last_baseline - ink_bottom, 10.0, card_id)
            divider = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "flavor-divider"
            )
            expected_divider_y = block_top - float(renderer.FLAVOR_DIVIDER_GAP)
            self.assertAlmostEqual(float(divider.attrib["y1"]), expected_divider_y, places=4)
            self.assertAlmostEqual(float(divider.attrib["y2"]), expected_divider_y, places=4)
            self.assertLessEqual(float(divider.attrib["y1"]), block_top, card_id)
            divider_positions.add(float(divider.attrib["y1"]))

        self.assertEqual(baselines, {827.1356})
        self.assertEqual(divider_positions, {803.1356})

    def test_all_card_text_uses_configured_roles_weights_tracking_and_leading(self) -> None:
        layout = renderer._load_layout()
        encountered_typography_roles: set[str] = set()
        rendered_sizes: dict[str, set[float]] = {}

        for card_id, card in self.cards_by_id.items():
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            for element in root.iter():
                if (
                    element.tag.rsplit("}", 1)[-1] != "text"
                    or "data-type-size-step" not in element.attrib
                ):
                    continue

                text = _text_content(element)
                svg_role = element.attrib.get("data-role")
                if svg_role is None and text in {
                    "BILDREVIEW OFFEN",
                    "ILLUSTRATION FEHLT",
                }:
                    typography_role = "artwork_placeholder"
                elif svg_role == "rules-text":
                    typography_role = (
                        "event_rules"
                        if _value(card, "card_type") == "Ereignis"
                        else "factor_rules"
                    )
                else:
                    self.assertIn(svg_role, SVG_ROLE_TO_TYPOGRAPHY, card_id)
                    assert svg_role is not None
                    typography_role = SVG_ROLE_TO_TYPOGRAPHY[svg_role]

                encountered_typography_roles.add(typography_role)
                size = float(element.attrib["font-size"])
                size_step = float(element.attrib["data-type-size-step"])
                line_height = float(element.attrib["data-line-height"])
                status = element.attrib["data-type-step-status"]
                rendered_sizes.setdefault(typography_role, set()).add(size)

                self.assertEqual(size, size_step, card_id)
                self.assertTrue(size.is_integer(), card_id)
                self.assertTrue(line_height.is_integer(), card_id)
                allowed_steps = {
                    (
                        float(step["size"]),
                        float(step["line_height"]),
                        step.get("status", "standard"),
                    )
                    for step in layout["typography"][typography_role]["steps"]
                }
                self.assertIn((size, line_height, status), allowed_steps, card_id)

                font_role = layout["typography"][typography_role]["font_role"]
                self.assertEqual(element.attrib["data-font-role"], font_role, card_id)
                expected_family, expected_weight, expected_style = FONT_ROLE_CONTRACT[
                    font_role
                ]
                self.assertEqual(element.attrib["font-family"], expected_family, card_id)
                self.assertEqual(element.attrib["font-weight"], expected_weight, card_id)
                self.assertEqual(element.attrib["font-style"], expected_style, card_id)

                actual_tracking = float(element.attrib.get("letter-spacing", "0"))
                self.assertEqual(
                    actual_tracking,
                    _expected_tracking(text, size, expected_family),
                    card_id,
                )
                spans = [
                    child
                    for child in list(element)
                    if child.tag.rsplit("}", 1)[-1] == "tspan"
                ]
                self.assertTrue(spans, card_id)
                self.assertEqual(float(spans[0].attrib["dy"]), 0.0, card_id)
                self.assertTrue(
                    all(
                        float(span.attrib["dy"]) == line_height
                        for span in spans[1:]
                    ),
                    card_id,
                )

                expected_features = (
                    TABULAR_FIGURE_FEATURES
                    if any(character.isdigit() for character in text)
                    else None
                )
                self.assertEqual(
                    element.attrib.get("font-feature-settings"),
                    expected_features,
                    card_id,
                )
                self.assertGreaterEqual(size, 12.0, card_id)

        expected_card_roles = set(SVG_ROLE_TO_TYPOGRAPHY.values()) | {
            "artwork_placeholder",
            "event_rules",
            "factor_rules",
        }
        if not layout["review_gates"]["artwork_blocked_card_ids"] and not layout[
            "review_gates"
        ]["content_blocked_card_ids"]:
            # The review badge only exists on a blocked card, and the canonical
            # set has none while every gate is cleared; its typography is
            # covered by test_review_badge_uses_its_configured_typography.
            expected_card_roles.discard("review_badge")
        self.assertEqual(encountered_typography_roles, expected_card_roles)
        self.assertEqual(rendered_sizes["points"], {14.0})
        self.assertEqual(rendered_sizes["footer_identity"], {14.0})
        self.assertEqual(rendered_sizes["footer_brand"], {12.0})
        self.assertEqual(rendered_sizes["project_requirements"], {23.0})
        self.assertEqual(rendered_sizes["project_goal"], {20.0})

    def test_review_badge_uses_its_configured_typography(self) -> None:
        # Every gate in the canonical layout is cleared, so the badge is
        # exercised against a copy that blocks one card.
        card_id, card = next(iter(self.cards_by_id.items()))
        blocked = dict(renderer._load_layout())
        blocked["review_gates"] = {
            "content_blocked_card_ids": [card_id],
            "artwork_blocked_card_ids": [card_id],
        }
        with patch.object(renderer, "_load_layout", return_value=blocked):
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
        labels = [
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "review-badge-label"
        ]
        self.assertEqual(len(labels), 1, card_id)
        self.assertEqual(_text_content(labels[0]), "REVIEW · INHALT+BILD")
        _font_role, steps = TYPOGRAPHY_CONTRACT["review_badge"]
        size, line_height, _status = steps[0]
        self.assertEqual(float(labels[0].attrib["font-size"]), float(size))
        self.assertEqual(float(labels[0].attrib["data-line-height"]), float(line_height))

    def test_project_sections_use_fixed_hierarchy_steps(self) -> None:
        goal_cards_by_line_count: dict[int, set[str]] = {}
        project_count = 0
        for card_id, card in self.cards_by_id.items():
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            emergency_elements = [
                element
                for element in root.iter()
                if element.attrib.get("data-type-step-status")
                == "prototype-emergency"
            ]
            self.assertFalse(emergency_elements, card_id)
            if _value(card, "card_type") != "Projekt":
                continue
            project_count += 1
            goal = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-goal-text"
            )
            requirements = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-requirements-text"
            )
            self.assertEqual(goal.attrib["data-type-step-status"], "standard", card_id)
            self.assertEqual(
                requirements.attrib["data-type-step-status"], "standard", card_id
            )
            self.assertEqual(
                (requirements.attrib["font-size"], requirements.attrib["data-line-height"]),
                ("23", "32"),
                card_id,
            )
            self.assertEqual(
                (goal.attrib["font-size"], goal.attrib["data-line-height"]),
                ("20", "28"),
                card_id,
            )
            expected_requirements = _value(card, "rules_text")
            if expected_requirements.casefold().startswith("abschluss:"):
                expected_requirements = expected_requirements[len("Abschluss:") :].lstrip()
            self.assertEqual(_text_content(requirements), expected_requirements, card_id)
            self.assertEqual(_text_content(goal), _value(card, "project_goal"), card_id)
            requirement_line_count = len(_text_lines(requirements))
            goal_line_count = len(_text_lines(goal))
            self.assertEqual(requirement_line_count, 2, card_id)
            self.assertEqual(72 - requirement_line_count * 32, 8, card_id)
            self.assertGreaterEqual(120 - goal_line_count * 28, 8, card_id)
            goal_cards_by_line_count.setdefault(goal_line_count, set()).add(card_id)

        self.assertEqual(project_count, 16)
        self.assertEqual(
            goal_cards_by_line_count,
            {
                2: {"KAT-C11", "KAT-C18", "KAT-R09", "KAT-R10", "KAT-R17"},
                3: {"KAT-C02", "KAT-R03", "KAT-R07", "KAT-R14"},
                4: {
                    "KAT-C22",
                    "KAT-R04",
                    "KAT-R08",
                    "KAT-R11",
                    "KAT-R12",
                    "KAT-R13",
                    "KAT-R18",
                },
            },
        )

    def test_typography_exceptions_are_empty_in_svg_and_manifest(self) -> None:
        preview_root = ET.fromstring(
            renderer.build_card_svg(
                self.cards_by_id["KAT-R12"], self.profile, None, proof=False
            )
        )
        metadata_element = next(
            element
            for element in preview_root
            if element.tag.rsplit("}", 1)[-1] == "metadata"
        )
        metadata = json.loads(metadata_element.text or "{}")
        self.assertEqual(metadata["typography_exceptions"], [])

        with (
            tempfile.TemporaryDirectory() as output_dir,
            patch.object(renderer, "rasterize_svg", return_value=b"raster"),
            patch.object(renderer, "finalize_png", return_value=b"png"),
            patch.object(
                renderer,
                "inspect_png",
                return_value={"sha256": hashlib.sha256(b"png").hexdigest(), "bytes": 3},
            ),
        ):
            manifest = renderer.render_selected(
                profile_path=PROFILE_PATH,
                csv_path=CARDS_PATH,
                artwork_dir=ARTWORK_DIR,
                output_dir=Path(output_dir),
                card_ids=["KAT-R12"],
                mode="preview",
            )
            self.assertEqual(
                manifest["cards"][0]["typography_exceptions"],
                [],
            )
            written_manifest = json.loads(
                Path(output_dir, "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(written_manifest, manifest)

    def test_reference_rules_have_deterministic_line_breaks(self) -> None:
        expectations = {
            ("KAT-C17", "rules-text", "rules_text"): (
                "Wähle einen angelegten Betriebsfaktor.",
                "Gib ihn der kontrollierenden Person",
                "auf die Hand zurück.",
            ),
            ("KAT-U03", "rules-text", "rules_text"): (
                "Erfüllt wahlweise eine Team-",
                "oder Methoden-Anforderung.",
            ),
            ("KAT-U25", "rules-text", "rules_text"): (
                "Erfüllt wahlweise eine Daten-",
                "oder Methoden-Anforderung.",
            ),
        }

        for (card_id, data_role, source_field), expected_lines in expectations.items():
            card = self.cards_by_id[card_id]
            first_svg = renderer.build_card_svg(card, self.profile, None, proof=False)
            second_svg = renderer.build_card_svg(card, self.profile, None, proof=False)
            first_root = ET.fromstring(first_svg)
            second_root = ET.fromstring(second_svg)
            first_element = next(
                element
                for element in first_root.iter()
                if element.attrib.get("data-role") == data_role
            )
            second_element = next(
                element
                for element in second_root.iter()
                if element.attrib.get("data-role") == data_role
            )
            with self.subTest(card_id=card_id, data_role=data_role):
                self.assertEqual(_text_lines(first_element), expected_lines)
                self.assertEqual(_text_lines(second_element), expected_lines)
                source_tokens = re.findall(r"\S+", str(_value(card, source_field)))
                rendered_tokens = re.findall(r"\S+", " ".join(expected_lines))
                self.assertEqual(rendered_tokens, source_tokens)

    def test_flavor_fallback_keeps_german_phrase_groups(self) -> None:
        text = "Damit ist zumindest ausgeschlossen, dass dieser Fehler im Schema steht."
        font = renderer._font(renderer._resolve_fonts(), "italic", 16)
        self.assertEqual(
            renderer._wrap_words(text, font, 518, flavor_aware=True),
            [
                "Damit ist zumindest ausgeschlossen,",
                "dass dieser Fehler im Schema steht.",
            ],
        )

    def test_paragraph_balance_preserves_explicit_breaks_line_count_and_tokens(
        self,
    ) -> None:
        class FixedWidthFont:
            @staticmethod
            def getlength(text: str) -> int:
                return len(text) * 4

        text = (
            "eins zwei drei vier fünf sechs sieben\n\n"
            "alpha beta gamma delta epsilon"
        )
        greedy = renderer._wrap_words(
            text,
            FixedWidthFont(),
            15,
            balance_last_line=False,
        )
        balanced = renderer._wrap_words(text, FixedWidthFont(), 15)
        self.assertEqual(len(balanced), len(greedy))
        self.assertEqual(
            greedy,
            [
                "eins zwei drei",
                "vier fünf sechs",
                "sieben",
                "",
                "alpha beta",
                "gamma delta",
                "epsilon",
            ],
        )
        self.assertEqual(
            balanced,
            [
                "eins zwei drei",
                "vier fünf",
                "sechs sieben",
                "",
                "alpha beta",
                "gamma delta",
                "epsilon",
            ],
        )
        self.assertEqual(renderer._wrap_words(text, FixedWidthFont(), 15), balanced)
        self.assertEqual(re.findall(r"\S+", " ".join(balanced)), re.findall(r"\S+", text))

    def test_footer_contains_only_public_identity_rarity_and_brand_copy(self) -> None:
        fonts = renderer._resolve_fonts()
        pip_track_left_edges: set[float] = set()
        layout = renderer._load_layout()
        document_center = float(layout["geometry"]["document"]["width"]) / 2
        for card_id in GOLDEN_CARDS:
            root = self.assert_svg_contract(self.build_svg(card_id), card_id)
            footer = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-footer"
            )
            footer_text = " ".join(self.visible_text(footer))
            rarity_label = renderer._load_layout()["rarities"][GOLDEN_CARDS[card_id][0]][
                "label"
            ]
            self.assertIn(card_id, footer_text)
            self.assertIn(rarity_label, footer_text)
            self.assertIn("OTTERS OF THE COAST™", footer_text)
            self.assertIn("© 2026", footer_text)
            self.assertNotIn("CSV", footer_text)
            self.assertNotIn("VORSCHAU", footer_text)

            footer_elements = set(footer.iter())
            rarity_marks = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "rarity-mark"
            ]
            expected_filled = int(
                renderer._load_layout()["rarities"][GOLDEN_CARDS[card_id][0]]["marks"]
            )
            self.assertEqual(len(rarity_marks), renderer.RARITY_PIP_COUNT)
            self.assertTrue(all(mark in footer_elements for mark in rarity_marks))
            self.assertEqual(
                [mark.attrib["data-index"] for mark in rarity_marks],
                ["1", "2", "3", "4"],
            )
            self.assertEqual(
                [mark.attrib["data-state"] for mark in rarity_marks],
                ["filled"] * expected_filled
                + ["empty"] * (renderer.RARITY_PIP_COUNT - expected_filled),
            )
            mark_color = renderer._color(renderer._load_layout(), "line/highlight")
            for mark in rarity_marks[:expected_filled]:
                self.assertEqual(mark.attrib["fill"], mark_color)
                self.assertNotIn("stroke", mark.attrib)
            for mark in rarity_marks[expected_filled:]:
                self.assertEqual(mark.attrib["fill"], "none")
                self.assertEqual(mark.attrib["stroke"], mark_color)
                self.assertEqual(
                    float(mark.attrib["stroke-width"]),
                    float(renderer.RARITY_PIP_OUTLINE_WIDTH),
                )
            visible_boxes: list[tuple[float, float, float, float]] = []
            for mark in rarity_marks:
                stroke_width = float(mark.attrib.get("stroke-width", 0))
                stroke_outset = stroke_width / 2
                left = float(mark.attrib["x"]) - stroke_outset
                top = float(mark.attrib["y"]) - stroke_outset
                right = float(mark.attrib["x"]) + float(mark.attrib["width"]) + stroke_outset
                bottom = float(mark.attrib["y"]) + float(mark.attrib["height"]) + stroke_outset
                visible_boxes.append((left, top, right, bottom))
                self.assertEqual(right - left, float(renderer.RARITY_PIP_SIZE))
                self.assertEqual(bottom - top, float(renderer.RARITY_PIP_SIZE))
            visible_centers = [
                ((left + right) / 2, (top + bottom) / 2)
                for left, top, right, bottom in visible_boxes
            ]
            pip_track_left_edges.add(visible_boxes[0][0])
            pip_track_center = (visible_boxes[0][0] + visible_boxes[-1][2]) / 2
            footer_zone = layout["geometry"]["layouts"][
                renderer._layout_key(self.cards_by_id[card_id])
            ]["footer"]
            footer_center = float(footer_zone["x"]) + float(footer_zone["width"]) / 2
            self.assertEqual(pip_track_center, footer_center, card_id)
            self.assertEqual(pip_track_center, document_center, card_id)
            self.assertEqual(
                [
                    visible_centers[index + 1][0] - visible_centers[index][0]
                    for index in range(renderer.RARITY_PIP_COUNT - 1)
                ],
                [float(renderer.RARITY_PIP_STEP)] * (renderer.RARITY_PIP_COUNT - 1),
            )
            self.assertEqual(len({center[1] for center in visible_centers}), 1)
            self.assertEqual(footer.attrib["data-rarity-filled"], str(expected_filled))
            self.assertEqual(
                footer.attrib["data-rarity-total"],
                str(renderer.RARITY_PIP_COUNT),
            )

            brand = next(
                element
                for element in footer.iter()
                if element.attrib.get("data-role") == "footer-brand"
            )
            identity_group = next(
                element
                for element in footer.iter()
                if element.attrib.get("data-role") == "footer-identity-rarity"
            )
            identity_segments = [
                element
                for element in list(identity_group)
                if element.tag.rsplit("}", 1)[-1] == "text"
            ]
            self.assertEqual(
                [element.attrib.get("data-role") for element in identity_segments],
                ["footer-card-id", "footer-identity-separator", "footer-rarity"],
                card_id,
            )
            self.assertEqual(
                " ".join(self.visible_text(identity_group)),
                f"{card_id} · {rarity_label}",
                card_id,
            )
            card_id_text, separator, rarity_text = identity_segments
            self.assertEqual(_text_content(card_id_text), card_id)
            self.assertEqual(_text_content(separator), "·")
            self.assertEqual(_text_content(rarity_text), rarity_label)
            card_id_tracking = float(card_id_text.attrib.get("letter-spacing", "0"))
            rarity_tracking = float(rarity_text.attrib.get("letter-spacing", "0"))
            self.assertEqual(
                card_id_tracking,
                renderer._tracking_for_text(card_id, 14, "Noto Sans"),
                card_id,
            )
            self.assertEqual(
                rarity_tracking,
                renderer._tracking_for_text(rarity_label, 14, "Noto Sans"),
                card_id,
            )
            self.assertGreater(rarity_tracking, card_id_tracking, card_id)
            self.assertNotIn("letter-spacing", separator.attrib)
            self.assertNotIn("·", " ".join(self.visible_text(brand)))
            self.assertLess(
                float(brand.attrib["font-size"]),
                float(card_id_text.attrib["font-size"]),
            )
            self.assertEqual(
                brand.attrib["fill"],
                renderer._color(renderer._load_layout(), "text/on-dark-muted"),
            )
            brand_size = float(brand.attrib["font-size"])
            brand_tracking = float(brand.attrib.get("letter-spacing", "0"))
            brand_left = float(brand.attrib["x"]) - renderer._text_width(
                _text_content(brand),
                renderer._font(fonts, "sans_regular", brand_size),
                brand_tracking,
            )
            self.assertGreaterEqual(brand_left - visible_boxes[-1][2], 10.0, card_id)

        expected_track_left = (
            document_center - float(renderer.RARITY_PIP_TRACK_WIDTH) / 2
        )
        self.assertEqual(pip_track_left_edges, {expected_track_left})

        self.assertEqual(
            {
                key: (rarity["label"], rarity["marks"])
                for key, rarity in renderer._load_layout()["rarities"].items()
            },
            {
                "common": ("COMMON", 1),
                "uncommon": ("UNCOMMON", 2),
                "rare": ("RARE", 3),
                "mythic": ("MYTHIC", 4),
            },
        )

    def test_project_type_line_uses_family_and_circled_requirement_icons(self) -> None:
        root = self.assert_svg_contract(self.build_svg("KAT-R12"), "KAT-R12")
        family_symbol = next(
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "project-family-symbol"
        )
        self.assertEqual(family_symbol.attrib["data-icon"], "operations")
        self.assertEqual(family_symbol.attrib["data-icon-size"], "20")

        requirement_carriers = [
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "project-requirement-carrier"
        ]
        self.assertEqual(len(requirement_carriers), 4)
        self.assertEqual(
            [carrier.tag.rsplit("}", 1)[-1] for carrier in requirement_carriers],
            ["ellipse"] * 4,
        )
        self.assertEqual(
            {
                (carrier.attrib["rx"], carrier.attrib["ry"])
                for carrier in requirement_carriers
            },
            {("13.5", "13.5")},
        )
        self.assertEqual(
            {carrier.attrib["stroke-width"] for carrier in requirement_carriers},
            {"1.5"},
        )
        self.assertEqual(
            [carrier.attrib["data-family"] for carrier in requirement_carriers],
            ["team", "data", "operations", "operations"],
        )
        self.assertEqual(
            [carrier.attrib["data-slot"] for carrier in requirement_carriers],
            ["1", "2", "3", "4"],
        )
        self.assertEqual(
            {carrier.attrib["data-count"] for carrier in requirement_carriers},
            {"1"},
        )

        requirement_symbols = [
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "project-requirement-symbol"
        ]
        self.assertEqual(len(requirement_symbols), 4)
        self.assertEqual(
            [symbol.attrib["data-icon"] for symbol in requirement_symbols],
            ["team", "data", "operations", "operations"],
        )
        self.assertEqual(
            {symbol.attrib["data-icon-size"] for symbol in requirement_symbols},
            {"18"},
        )
        forbidden_icon_children = {"text", "rect", "ellipse", "circle"}
        for symbol in (family_symbol, *requirement_symbols):
            self.assertTrue(
                forbidden_icon_children.isdisjoint(
                    element.tag.rsplit("}", 1)[-1] for element in symbol.iter()
                )
            )

        roles = {element.attrib.get("data-role") for element in root.iter()}
        self.assertNotIn("requirement-module", roles)
        self.assertNotIn("requirement-label", roles)
        self.assertNotIn("family-symbol", roles)
        self.assertNotIn("family-icon", roles)
        text = self.visible_text(root)
        self.assertEqual(text.count("BETRIEB"), 1)  # project family only
        self.assertNotIn("TEAM", text)
        self.assertNotIn("DATEN", text)

        layout = renderer._load_layout()["geometry"]["layouts"]["project"]
        self.assertNotIn("requirements", layout)
        self.assertNotIn("goal", layout)
        self.assertNotIn("rules", layout)
        self.assertEqual(
            layout["content_stack"],
            {
                "requirements_fit_height": 72,
                "goal_fit_height": 120,
                "section_gap": 4,
            },
        )

        points_circle = next(
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "project-points"
        )
        self.assertEqual(points_circle.tag.rsplit("}", 1)[-1], "ellipse")
        self.assertEqual(
            tuple(points_circle.attrib[key] for key in ("rx", "ry")),
            ("13.5", "13.5"),
        )
        self.assertEqual(points_circle.attrib["stroke-width"], "1.5")
        mapping = renderer._load_layout()
        self.assertEqual(
            points_circle.attrib["fill"],
            renderer._color(mapping, "background/paper-raised"),
        )
        self.assertEqual(
            points_circle.attrib["stroke"], renderer._color(mapping, "line/default")
        )
        points_label = next(
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "project-points-label"
        )
        self.assertEqual(_text_content(points_label), "4P")
        self.assertEqual(points_label.attrib["font-size"], "14")
        self.assertEqual(points_label.attrib["data-line-height"], "18")
        self.assertEqual(
            points_label.attrib["fill"], renderer._color(mapping, "line/default")
        )

    def test_project_section_labels_clear_their_dividers(self) -> None:
        self.assertEqual(renderer.SECTION_LABEL_Y_OFFSET, -12.75)
        self.assertEqual(renderer.SECTION_DIVIDER_OFFSET, 9)
        self.assertEqual(renderer.SECTION_BODY_TOP_OFFSET, 11)
        root = self.assert_svg_contract(self.build_svg("KAT-R12"), "KAT-R12")
        labels = [
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "section-label"
        ]
        dividers = [
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "section-divider"
        ]
        self.assertEqual(len(labels), 2)
        self.assertEqual(len(dividers), 2)
        self.assertEqual(
            [divider.attrib["data-section"] for divider in dividers],
            ["anforderungen", "projektziel"],
        )
        self.assertEqual(
            [_text_content(label) for label in labels],
            ["ANFORDERUNGEN", "PROJEKTZIEL"],
        )

        font = renderer._font(renderer._resolve_fonts(), "sans_bold", 14)
        expected_ink_clearance = {
            "PROJEKTZIEL": 4.25,
            "ANFORDERUNGEN": 6.75,
        }
        for label, divider in zip(labels, dividers, strict=True):
            label_text = _text_content(label)
            label_size = float(label.attrib["font-size"])
            label_ink_bottom = (
                float(label.attrib["y"])
                + font.getbbox(label_text, anchor="ls")[3] / 4
            )
            divider_y = float(divider.attrib["y1"])
            divider_top = divider_y - float(divider.attrib["stroke-width"]) / 2
            clearance = divider_top - label_ink_bottom
            self.assertGreaterEqual(clearance, 4.0, label_text)
            self.assertAlmostEqual(
                clearance,
                expected_ink_clearance[label_text],
                places=4,
                msg=label_text,
            )
            self.assertEqual(divider.attrib["y1"], divider.attrib["y2"])
            dynamic_zone_y = (
                float(label.attrib["y"])
                - label_size
                - float(renderer.SECTION_LABEL_Y_OFFSET)
            )
            self.assertEqual(
                divider_y,
                dynamic_zone_y + float(renderer.SECTION_DIVIDER_OFFSET),
            )
            divider_bottom = (
                divider_y + float(divider.attrib["stroke-width"]) / 2
            )
            self.assertLessEqual(
                divider_bottom,
                dynamic_zone_y + float(renderer.SECTION_BODY_TOP_OFFSET),
            )

    def test_all_project_inkbox_gates_clear_following_sections(self) -> None:
        fonts = renderer._resolve_fonts()
        requirements_to_goal_gaps: dict[str, float] = {}
        goal_to_flavor_gaps: dict[str, float] = {}

        def tspan_baselines(element: ET.Element) -> list[tuple[ET.Element, float]]:
            baseline = float(element.attrib["y"])
            result: list[tuple[ET.Element, float]] = []
            for tspan in list(element):
                baseline += float(tspan.attrib.get("dy", "0"))
                result.append((tspan, baseline))
            return result

        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Projekt":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            requirements = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-requirements-text"
            )
            goal_label = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "section-label"
                and _text_content(element) == "PROJEKTZIEL"
            )
            self.assertEqual(requirements.attrib["font-family"], "Noto Serif", card_id)

            requirement_tspan, requirement_baseline = tspan_baselines(requirements)[-1]
            label_tspan, label_baseline = tspan_baselines(goal_label)[0]
            requirement_font = renderer._font(
                fonts,
                requirements.attrib["data-font-role"],
                float(requirements.attrib["font-size"]),
            )
            label_font = renderer._font(
                fonts,
                goal_label.attrib["data-font-role"],
                float(goal_label.attrib["font-size"]),
            )
            requirement_ink_bottom = (
                requirement_baseline
                + requirement_font.getbbox(
                    requirement_tspan.text or "", anchor="ls"
                )[3]
                / 4
            )
            label_ink_top = (
                label_baseline
                + label_font.getbbox(label_tspan.text or "", anchor="ls")[1] / 4
            )
            gap = label_ink_top - requirement_ink_bottom
            requirements_to_goal_gaps[card_id] = gap
            self.assertGreaterEqual(gap, 4.0, card_id)

            goal = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-goal-text"
            )
            flavor_divider = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "flavor-divider"
            )
            last_goal, goal_baseline = tspan_baselines(goal)[-1]
            goal_font = renderer._font(
                fonts,
                goal.attrib["data-font-role"],
                float(goal.attrib["font-size"]),
            )
            goal_ink_bottom = (
                goal_baseline
                + goal_font.getbbox(last_goal.text or "", anchor="ls")[3] / 4
            )
            flavor_divider_top = (
                float(flavor_divider.attrib["y1"])
                - float(flavor_divider.attrib["stroke-width"]) / 2
            )
            goal_to_flavor_gap = flavor_divider_top - goal_ink_bottom
            goal_to_flavor_gaps[card_id] = goal_to_flavor_gap
            self.assertGreaterEqual(goal_to_flavor_gap, 4.0, card_id)

        self.assertEqual(len(requirements_to_goal_gaps), 16)
        self.assertEqual(len(goal_to_flavor_gaps), 16)
        self.assertAlmostEqual(
            min(requirements_to_goal_gaps.values()), 16.5, places=4
        )
        self.assertAlmostEqual(
            min(goal_to_flavor_gaps.values()), 15.7742, places=4
        )

    def test_all_project_requirement_circles_preserve_order_and_are_right_aligned(self) -> None:
        mapping = renderer._load_layout()
        paper = renderer._color(mapping, "background/paper-raised")
        neutral = renderer._color(mapping, "line/default")
        right_edges: set[float] = set()
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Projekt":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            carriers = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-requirement-carrier"
            ]
            symbols = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-requirement-symbol"
            ]
            expected = str(_value(card, "requirements")).split("+")
            self.assertEqual(
                [carrier.attrib["data-family"] for carrier in carriers],
                expected,
                card_id,
            )
            self.assertEqual(
                [carrier.attrib["data-slot"] for carrier in carriers],
                [str(index) for index in range(1, len(expected) + 1)],
                card_id,
            )
            self.assertEqual(
                [carrier.attrib["data-count"] for carrier in carriers],
                ["1"] * len(expected),
                card_id,
            )
            self.assertEqual(
                [symbol.attrib["data-icon"] for symbol in symbols], expected, card_id
            )
            self.assertTrue(
                all(symbol.attrib["data-icon-size"] == "18" for symbol in symbols),
                card_id,
            )
            self.assertTrue(
                all(
                    carrier.tag.rsplit("}", 1)[-1] == "ellipse"
                    and carrier.attrib["rx"] == "13.5"
                    and carrier.attrib["ry"] == "13.5"
                    and carrier.attrib["stroke-width"] == "1.5"
                    for carrier in carriers
                ),
                card_id,
            )
            expected_colors = [
                renderer._color(mapping, mapping["families"][family]["color_token"])
                for family in expected
            ]
            self.assertEqual(
                [carrier.attrib["stroke"] for carrier in carriers],
                expected_colors,
                card_id,
            )
            self.assertEqual(
                [carrier.attrib["fill"] for carrier in carriers],
                [paper] * len(carriers),
                card_id,
            )
            self.assertEqual(
                [symbol.attrib["fill"] for symbol in symbols],
                expected_colors,
                card_id,
            )

            centers = [
                (float(carrier.attrib["cx"]), float(carrier.attrib["cy"]))
                for carrier in carriers
            ]
            self.assertEqual(
                [
                    round(centers[index + 1][0] - centers[index][0], 4)
                    for index in range(len(centers) - 1)
                ],
                [34.0] * (len(centers) - 1),
                card_id,
            )
            self.assertEqual(len({center[1] for center in centers}), 1, card_id)
            self.assertEqual(centers[0][1], 520.3644, card_id)

            for carrier, symbol in zip(carriers, symbols, strict=True):
                match = re.fullmatch(
                    r"translate\(([-0-9.]+) ([-0-9.]+)\) scale\([-0-9.]+\)",
                    symbol.attrib["transform"],
                )
                self.assertIsNotNone(match, card_id)
                assert match is not None
                self.assertEqual(
                    (
                        round(float(match.group(1)) + 9, 4),
                        round(float(match.group(2)) + 9, 4),
                    ),
                    (
                        round(float(carrier.attrib["cx"]), 4),
                        round(float(carrier.attrib["cy"]), 4),
                    ),
                    card_id,
                )

            right_edge = centers[-1][0] + 13.5
            right_edges.add(round(right_edge, 4))

            points_circle = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-points"
            )
            self.assertEqual(points_circle.tag.rsplit("}", 1)[-1], "ellipse", card_id)
            self.assertEqual(
                (points_circle.attrib["rx"], points_circle.attrib["ry"]),
                ("13.5", "13.5"),
                card_id,
            )
            self.assertEqual(points_circle.attrib["fill"], paper, card_id)
            self.assertEqual(points_circle.attrib["stroke"], neutral, card_id)
            self.assertEqual(points_circle.attrib["stroke-width"], "1.5", card_id)
            self.assertEqual(
                round(float(points_circle.attrib["cx"]) - centers[-1][0] - 28, 4),
                10.0,
                card_id,
            )
            self.assertEqual(
                round(float(points_circle.attrib["cx"]) - 13.5 - right_edge, 4),
                11.0,
                card_id,
            )
            self.assertEqual(
                float(points_circle.attrib["cy"]), centers[-1][1], card_id
            )
            points_label = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-points-label"
            )
            self.assertEqual(
                _text_content(points_label), f"{_value(card, 'points')}P", card_id
            )
            self.assertEqual(points_label.attrib["fill"], neutral, card_id)
            self.assertNotIn("Abschluss:", self.visible_text(root), card_id)
            self.assertNotIn("PUNKTE", self.visible_text(root), card_id)

        self.assertEqual(len(right_edges), 1)

    def test_factors_use_one_large_family_emblem_and_centered_rules(self) -> None:
        mapping = renderer._load_layout()
        layout = mapping["geometry"]["layouts"]["factor"]
        self.assertNotIn("rules_panel", layout)
        self.assertNotIn("flavor_panel", layout)
        self.assertNotIn("rules", layout)
        self.assertEqual(
            layout["content_stack"],
            {
                "text_side_inset": 27,
                "carrier_size": 96,
                "icon_size": 63,
                "painted_emblem_to_text_gap": 8,
                "max_text_lines": 2,
            },
        )
        fonts = renderer._resolve_fonts()

        one_line_cards: set[str] = set()
        two_line_cards: set[str] = set()
        linebox_gaps: dict[str, float] = {}
        inkbox_gaps: dict[str, float] = {}
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Projektfaktor":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            ordered = list(root.iter())
            stack = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "content-stack"
            )
            self.assertEqual(stack.attrib["data-layout"], "factor", card_id)
            groups = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "factor-family-emblem"
            ]
            carriers = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "factor-family-emblem-carrier"
            ]
            symbols = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "factor-family-emblem-symbol"
            ]
            self.assertEqual(len(groups), 1, card_id)
            self.assertEqual(len(carriers), 1, card_id)
            self.assertEqual(len(symbols), 1, card_id)

            family_key = str(_value(card, "factor_family") or "wildcard")
            self.assertEqual(groups[0].attrib["data-family"], family_key, card_id)
            family_color = renderer._color(
                mapping, mapping["families"][family_key]["color_token"]
            )
            carrier = carriers[0]
            self.assertIn(carrier, list(groups[0]), card_id)
            self.assertEqual(carrier.tag.rsplit("}", 1)[-1], "ellipse", card_id)
            self.assertEqual(
                (
                    float(carrier.attrib["cx"]) - float(carrier.attrib["rx"]),
                    float(carrier.attrib["cy"]) - float(carrier.attrib["ry"]),
                    2 * float(carrier.attrib["rx"]),
                    2 * float(carrier.attrib["ry"]),
                ),
                (
                    297.0,
                    float(stack.attrib["data-stack-top"])
                    + float(carrier.attrib["stroke-width"]) / 2,
                    96.0,
                    96.0,
                ),
                card_id,
            )
            self.assertEqual(carrier.attrib["fill"], "none", card_id)
            self.assertEqual(carrier.attrib["stroke"], family_color, card_id)
            self.assertEqual(carrier.attrib["stroke-width"], "1.5", card_id)
            self.assertEqual(carrier.attrib["opacity"], "0.28", card_id)
            self.assertEqual(carrier.attrib["data-family"], family_key, card_id)

            symbol = symbols[0]
            self.assertIn(symbol, list(groups[0]), card_id)
            self.assertEqual(symbol.attrib["data-family"], family_key, card_id)
            self.assertEqual(symbol.attrib["data-icon-size"], "63", card_id)
            self.assertEqual(symbol.attrib["fill"], family_color, card_id)
            self.assertEqual(symbol.attrib["opacity"], "0.22", card_id)
            self.assertEqual(
                symbol.attrib["data-icon"],
                mapping["families"][family_key]["icon"],
                card_id,
            )
            match = re.fullmatch(
                r"translate\(([-0-9.]+) ([-0-9.]+)\) scale\([-0-9.]+\)",
                symbol.attrib["transform"],
            )
            self.assertIsNotNone(match, card_id)
            assert match is not None
            self.assertEqual(
                (float(match.group(1)), float(match.group(2))),
                (
                    313.5,
                    float(stack.attrib["data-stack-top"])
                    + float(carrier.attrib["stroke-width"]) / 2
                    + 16.5,
                ),
                card_id,
            )

            rules = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "rules-text"
            )
            self.assertLess(ordered.index(groups[0]), ordered.index(rules), card_id)
            lines = _text_lines(rules)
            (two_line_cards if len(lines) == 2 else one_line_cards).add(card_id)
            self.assertIn(len(lines), {1, 2}, card_id)
            self.assertEqual(float(rules.attrib["x"]), 345.0, card_id)
            self.assertEqual(rules.attrib["text-anchor"], "middle", card_id)
            self.assertEqual(rules.attrib["font-size"], "27", card_id)
            self.assertEqual(rules.attrib["data-line-height"], "38", card_id)
            self.assertEqual(rules.attrib["data-type-step-status"], "standard", card_id)
            expected_linebox_top = (
                float(stack.attrib["data-stack-top"])
                + 96
                + float(carrier.attrib["stroke-width"])
                + 8
            )
            expected_baseline = expected_linebox_top + 27
            self.assertEqual(float(rules.attrib["y"]), expected_baseline, card_id)
            self.assertEqual(
                float(stack.attrib["data-stack-height"]),
                96 + float(carrier.attrib["stroke-width"]) + 8 + len(lines) * 38,
                card_id,
            )
            self.assertEqual(
                [float(tspan.attrib["x"]) for tspan in list(rules)],
                [345.0] * len(lines),
                card_id,
            )
            self.assertEqual(
                [float(tspan.attrib["dy"]) for tspan in list(rules)],
                [0.0] + [38.0] * (len(lines) - 1),
                card_id,
            )

            first_line = list(rules)[0]
            first_baseline = float(rules.attrib["y"]) + float(
                first_line.attrib.get("dy", "0")
            )
            carrier_painted_bottom = (
                float(carrier.attrib["cy"])
                + float(carrier.attrib["ry"])
                + float(carrier.attrib["stroke-width"]) / 2
            )
            linebox_gap = (
                first_baseline
                - float(rules.attrib["font-size"])
                - carrier_painted_bottom
            )
            font = renderer._font(
                fonts,
                rules.attrib["data-font-role"],
                float(rules.attrib["font-size"]),
            )
            inkbox_gap = (
                first_baseline
                + font.getbbox(first_line.text or "", anchor="ls")[1] / 4
                - carrier_painted_bottom
            )
            linebox_gaps[card_id] = linebox_gap
            inkbox_gaps[card_id] = inkbox_gap
            self.assertEqual(linebox_gap, 8.0, card_id)
            self.assertGreaterEqual(inkbox_gap, 14.25, card_id)

            roles = {element.attrib.get("data-role") for element in root.iter()}
            self.assertNotIn("factor-effect-panel", roles, card_id)
            self.assertNotIn("factor-note-panel", roles, card_id)

        self.assertEqual(two_line_cards, {"KAT-U03", "KAT-U25"})
        self.assertEqual(len(one_line_cards), 36)
        self.assertEqual(len(linebox_gaps), 38)
        self.assertEqual(len(inkbox_gaps), 38)
        self.assertEqual(set(linebox_gaps.values()), {8.0})
        self.assertAlmostEqual(min(inkbox_gaps.values()), 14.25, places=4)

    def test_all_layouts_use_one_strict_45_55_content_stack_frame(self) -> None:
        mapping = renderer._load_layout()
        frame = mapping["geometry"]["content_stack_frame"]
        self.assertEqual(
            frame,
            {
                "x": 78,
                "y": 552.1144,
                "width": 534,
                "free_above_ratio": 0.45,
                "free_below_ratio": 0.55,
            },
        )
        layout_counts = {"project": 0, "factor": 0, "event": 0}
        project_stack_heights: list[float] = []
        project_free_above: list[float] = []
        project_free_below: list[float] = []

        for card_id, card in self.cards_by_id.items():
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            stacks = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "content-stack"
            ]
            self.assertEqual(len(stacks), 1, card_id)
            stack = stacks[0]
            layout_key = renderer._layout_key(card)
            layout_counts[layout_key] += 1
            self.assertEqual(stack.attrib["data-layout"], layout_key, card_id)

            frame_top = float(stack.attrib["data-frame-top"])
            frame_bottom = float(stack.attrib["data-frame-bottom"])
            stack_top = float(stack.attrib["data-stack-top"])
            stack_bottom = float(stack.attrib["data-stack-bottom"])
            stack_height = float(stack.attrib["data-stack-height"])
            free_above = float(stack.attrib["data-free-above"])
            free_below = float(stack.attrib["data-free-below"])
            self.assertEqual(frame_top, 552.1144, card_id)
            self.assertGreaterEqual(free_above, 0, card_id)
            self.assertGreaterEqual(free_below, 0, card_id)
            self.assertAlmostEqual(stack_top, frame_top + free_above, places=4)
            self.assertAlmostEqual(stack_bottom, stack_top + stack_height, places=4)
            self.assertAlmostEqual(frame_bottom, stack_bottom + free_below, places=4)
            self.assertAlmostEqual(free_above / (free_above + free_below), 0.45, places=4)
            self.assertAlmostEqual(free_below / (free_above + free_below), 0.55, places=4)
            self.assertEqual(stack.attrib["data-free-above-ratio"], "0.45")
            self.assertEqual(stack.attrib["data-free-below-ratio"], "0.55")

            if layout_key == "project":
                project_stack_heights.append(stack_height)
                project_free_above.append(free_above)
                project_free_below.append(free_below)
                stack_children = list(stack)
                section_labels = [
                    element
                    for element in stack_children
                    if element.attrib.get("data-role") == "section-label"
                ]
                section_dividers = [
                    element
                    for element in stack_children
                    if element.attrib.get("data-role") == "section-divider"
                ]
                goal_text = next(
                    element
                    for element in stack_children
                    if element.attrib.get("data-role") == "project-goal-text"
                )
                requirements_text = next(
                    element
                    for element in stack_children
                    if element.attrib.get("data-role")
                    == "project-requirements-text"
                )
                self.assertEqual(len(section_labels), 2, card_id)
                self.assertEqual(len(section_dividers), 2, card_id)
                self.assertEqual(stack.attrib["data-section-gap"], "4", card_id)
                self.assertEqual(
                    stack.attrib["data-section-order"],
                    "anforderungen,projektziel",
                    card_id,
                )
                self.assertEqual(
                    [element.attrib.get("data-role") for element in stack_children],
                    [
                        "section-divider",
                        "section-label",
                        "project-requirements-text",
                        "section-divider",
                        "section-label",
                        "project-goal-text",
                    ],
                    card_id,
                )
                requirements_label = next(
                    element
                    for element in section_labels
                    if _text_content(element) == "ANFORDERUNGEN"
                )
                self.assertAlmostEqual(
                    float(requirements_label.attrib["y"])
                    - float(requirements_label.attrib["font-size"]),
                    stack_top,
                    places=4,
                    msg=card_id,
                )
                goal_bottom = (
                    float(goal_text.attrib["y"])
                    - float(goal_text.attrib["font-size"])
                    + len(_text_lines(goal_text))
                    * float(goal_text.attrib["data-line-height"])
                )
                self.assertAlmostEqual(
                    goal_bottom,
                    stack_bottom,
                    places=4,
                    msg=card_id,
                )
                project_roles = {
                    "section-label",
                    "section-divider",
                    "project-goal-text",
                    "project-requirements-text",
                }
                self.assertTrue(
                    all(
                        element in stack_children
                        for element in stack.iter()
                        if element.attrib.get("data-role") in project_roles
                    ),
                    card_id,
                )
                self.assertIsNotNone(goal_text, card_id)

            divider = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "flavor-divider"
            )
            divider_painted_top = (
                float(divider.attrib["y1"])
                - float(divider.attrib["stroke-width"]) / 2
            )
            self.assertAlmostEqual(frame_bottom, divider_painted_top, places=4)

        self.assertEqual(layout_counts, {"project": 16, "factor": 38, "event": 28})
        self.assertEqual(max(project_stack_heights), 227.5)
        self.assertAlmostEqual(min(project_free_above), 10.247, places=4)
        self.assertAlmostEqual(min(project_free_below), 12.5242, places=4)

        self.assertEqual(
            renderer._balanced_stack_top(
                "TEST",
                frame_top=0,
                frame_bottom=100,
                stack_height=20,
                free_above_ratio=0.45,
            ),
            36,
        )
        with self.assertRaisesRegex(renderer.RenderError, "ohne Fallback"):
            renderer._balanced_stack_top(
                "TEST",
                frame_top=0,
                frame_bottom=100,
                stack_height=100.1,
                free_above_ratio=0.45,
            )
        with self.assertRaisesRegex(renderer.RenderError, "freien Raum für 45/55"):
            renderer._balanced_stack_top(
                "TEST",
                frame_top=0,
                frame_bottom=100,
                stack_height=100,
                free_above_ratio=0.45,
            )
        with self.assertRaisesRegex(renderer.RenderError, "Ungültige"):
            renderer._balanced_stack_top(
                "TEST",
                frame_top=0,
                frame_bottom=100,
                stack_height=20,
                free_above_ratio=1.1,
            )

        no_flavor_card = dict(self.cards_by_id["KAT-U22"])
        no_flavor_card["flavor_text"] = ""
        no_flavor_root = ET.fromstring(
            renderer.build_card_svg(no_flavor_card, self.profile, None, proof=False)
        )
        no_flavor_roles = {
            element.attrib.get("data-role") for element in no_flavor_root.iter()
        }
        self.assertNotIn("flavor-text", no_flavor_roles)
        self.assertNotIn("flavor-divider", no_flavor_roles)
        no_flavor_stack = next(
            element
            for element in no_flavor_root.iter()
            if element.attrib.get("data-role") == "content-stack"
        )
        event_flavor_y = mapping["geometry"]["layouts"]["event"]["flavor"]["y"]
        self.assertEqual(
            float(no_flavor_stack.attrib["data-frame-bottom"]),
            float(event_flavor_y),
        )

        overflowing_event = dict(self.cards_by_id["KAT-U22"])
        overflowing_event["rules_text"] = "\n".join(
            f"Explizite Zeile {index}" for index in range(1, 8)
        )
        with self.assertRaisesRegex(
            renderer.RenderError, r"KAT-U22: Ereignis-Regeltext passt nicht"
        ):
            renderer.build_card_svg(
                overflowing_event, self.profile, None, proof=False
            )

        overflowing_project = dict(self.cards_by_id["KAT-R12"])
        overflowing_project["project_goal"] = "\n".join(
            f"Explizite Zielzeile {index}" for index in range(1, 6)
        )
        with self.assertRaisesRegex(
            renderer.RenderError, r"KAT-R12: Projekttext passt nicht"
        ):
            renderer.build_card_svg(
                overflowing_project, self.profile, None, proof=False
            )

        overflowing_requirements = dict(self.cards_by_id["KAT-R12"])
        overflowing_requirements["rules_text"] = "Abschluss: " + "\n".join(
            f"Explizite Anforderungszeile {index}" for index in range(1, 4)
        )
        with self.assertRaisesRegex(
            renderer.RenderError, r"KAT-R12: Projekttext passt nicht"
        ):
            renderer.build_card_svg(
                overflowing_requirements, self.profile, None, proof=False
            )

        overflowing_factor = dict(self.cards_by_id["KAT-C01"])
        overflowing_factor["rules_text"] = "\n".join(
            f"Explizite Faktorzeile {index}" for index in range(1, 4)
        )
        with self.assertRaisesRegex(
            renderer.RenderError, r"KAT-C01: Faktor-Regeltext passt nicht"
        ):
            renderer.build_card_svg(
                overflowing_factor, self.profile, None, proof=False
            )

        missing_flavor = dict(self.cards_by_id["KAT-U22"])
        del missing_flavor["flavor_text"]
        with self.assertRaisesRegex(
            renderer.RenderError, r"KAT-U22: flavor_text fehlt"
        ):
            renderer.build_card_svg(
                missing_flavor, self.profile, None, proof=False
            )

    def test_events_use_one_25_35_rule_text_step_in_the_common_frame(self) -> None:
        mapping = renderer._load_layout()
        event_layout = mapping["geometry"]["layouts"]["event"]
        self.assertNotIn("rules", event_layout)
        self.assertEqual(event_layout["content_stack"], {"max_text_lines": 6})
        fonts = renderer._resolve_fonts()
        line_distribution: dict[int, int] = {}
        top_ink_gaps: dict[str, float] = {}
        bottom_ink_gaps: dict[str, float] = {}

        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Ereignis":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            stack = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "content-stack"
            )
            rules = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "rules-text"
            )
            lines = list(rules)
            line_distribution[len(lines)] = line_distribution.get(len(lines), 0) + 1
            self.assertEqual(stack.attrib["data-layout"], "event", card_id)
            self.assertEqual(float(rules.attrib["x"]), 78.0, card_id)
            self.assertEqual(rules.attrib["text-anchor"], "start", card_id)
            self.assertEqual(rules.attrib["font-size"], "25", card_id)
            self.assertEqual(rules.attrib["data-line-height"], "35", card_id)
            self.assertEqual(rules.attrib["data-type-step-status"], "standard", card_id)
            self.assertEqual(
                float(stack.attrib["data-stack-height"]), len(lines) * 35, card_id
            )
            self.assertEqual(
                float(rules.attrib["y"]),
                float(stack.attrib["data-stack-top"]) + 25,
                card_id,
            )

            font = renderer._font(fonts, "regular", 25)
            first_ink_top = (
                float(rules.attrib["y"])
                + font.getbbox(lines[0].text or "", anchor="ls")[1] / 4
            )
            last_baseline = float(rules.attrib["y"]) + (len(lines) - 1) * 35
            last_ink_bottom = (
                last_baseline
                + font.getbbox(lines[-1].text or "", anchor="ls")[3] / 4
            )
            top_ink_gaps[card_id] = (
                first_ink_top - float(stack.attrib["data-frame-top"])
            )
            bottom_ink_gaps[card_id] = (
                float(stack.attrib["data-frame-bottom"]) - last_ink_bottom
            )

        self.assertEqual(line_distribution, {2: 3, 3: 7, 4: 6, 5: 7, 6: 5})
        self.assertEqual(len(top_ink_gaps), 28)
        self.assertAlmostEqual(min(top_ink_gaps.values()), 23.622, places=4)
        self.assertAlmostEqual(min(bottom_ink_gaps.values()), 26.1492, places=4)

    def test_projects_use_their_primary_domain_accent_and_neutral_family_label(self) -> None:
        layout = renderer._load_layout()
        neutral = renderer._color(layout, "text/primary")
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Projekt":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            family = layout["families"][str(_value(card, "domain_primary"))]
            expected = layout["colors"][family["color_token"]]["hex"]
            for role, attribute in (
                ("card-type", "fill"),
                ("project-family-symbol", "fill"),
                ("type-panel-accent", "fill"),
                ("content-panel-accent", "fill"),
            ):
                element = next(
                    element
                    for element in root.iter()
                    if element.attrib.get("data-role") == role
                )
                self.assertEqual(element.attrib[attribute], expected, f"{card_id}:{role}")
            category = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-category"
            )
            self.assertEqual(_text_content(category), family["label"], card_id)
            self.assertEqual(category.attrib["fill"], neutral, card_id)
            art_keyline = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "plate-keyline"
                and element.attrib.get("data-plate-role") == "art-mat"
            )
            self.assertEqual(art_keyline.attrib["data-color-token"], "line/default")
            self.assertEqual(
                art_keyline.attrib["stroke"], layout["colors"]["line/default"]["hex"]
            )

    def test_project_factors_keep_family_accents_and_use_neutral_family_labels(self) -> None:
        layout = renderer._load_layout()
        neutral = renderer._color(layout, "text/primary")
        rendered_factors: set[str] = set()

        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Projektfaktor":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            family_key = str(_value(card, "factor_family") or "wildcard")
            family = layout["families"][family_key]
            accent = renderer._color(layout, family["color_token"])

            primary = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-type"
            )
            category = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-category"
            )
            symbol = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "factor-family-symbol"
            )

            self.assertEqual(_text_content(primary), "PROJEKTFAKTOR", card_id)
            self.assertEqual(primary.attrib["fill"], accent, card_id)
            self.assertEqual(_text_content(category), family["label"], card_id)
            self.assertEqual(category.attrib["fill"], neutral, card_id)
            self.assertEqual(symbol.attrib["data-icon"], family["icon"], card_id)
            self.assertEqual(symbol.attrib["fill"], accent, card_id)
            for role in ("type-panel-accent", "content-panel-accent"):
                element = next(
                    element
                    for element in root.iter()
                    if element.attrib.get("data-role") == role
                )
                self.assertEqual(element.attrib["fill"], accent, f"{card_id}:{role}")
            rendered_factors.add(card_id)

        self.assertEqual(len(rendered_factors), 38)

    def test_accent_lightness_and_type_line_contrast_contract(self) -> None:
        def relative_luminance(hex_color: str) -> float:
            channels = [
                int(hex_color[index : index + 2], 16) / 255
                for index in (1, 3, 5)
            ]
            linear = [
                channel / 12.92
                if channel <= 0.04045
                else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def contrast_ratio(first: str, second: str) -> float:
            lighter, darker = sorted(
                (relative_luminance(first), relative_luminance(second)),
                reverse=True,
            )
            return (lighter + 0.05) / (darker + 0.05)

        colors = renderer._load_layout()["colors"]
        values = [
            relative_luminance(colors[f"family/{family}"]["hex"])
            for family in ("team", "data", "operations", "methods")
        ]
        self.assertEqual(values, sorted(values))
        self.assertGreaterEqual(values[-1] - values[0], 0.11)
        methods = colors["family/methods"]["hex"]
        paper_raised = colors["background/paper-raised"]["hex"]
        self.assertGreaterEqual(contrast_ratio(methods, paper_raised), 4.5)
        self.assertGreaterEqual(
            contrast_ratio(colors["event/base"]["hex"], paper_raised), 4.5
        )
        self.assertGreaterEqual(
            contrast_ratio(colors["text/primary"]["hex"], paper_raised), 7.0
        )

    def test_plates_use_inset_accents_and_only_outer_corners_are_rounded(self) -> None:
        def box_value(element: ET.Element, key: str) -> str:
            return element.attrib.get(key) or element.attrib[f"data-box-{key}"]

        corner_modes = {
            "title-panel": "top",
            "art-mat": "none",
            "type-panel": "none",
            "content-panel": "none",
            "footer-panel": "bottom",
        }
        for card_id in GOLDEN_CARDS:
            root = self.assert_svg_contract(self.build_svg(card_id), card_id)
            for role, corner_mode in corner_modes.items():
                panel = next(
                    element
                    for element in root.iter()
                    if element.attrib.get("data-role") == role
                )
                if corner_mode == "none":
                    self.assertEqual(panel.tag.rsplit("}", 1)[-1], "rect")
                    self.assertNotIn("rx", panel.attrib, f"{card_id}:{role}")
                else:
                    self.assertEqual(panel.tag.rsplit("}", 1)[-1], "path")
                    self.assertEqual(panel.attrib["data-corner-mode"], corner_mode)
                    self.assertEqual(panel.attrib["data-corner-radius"], "4")
                    self.assertIn(" A 4 4 ", panel.attrib["d"])
                    self.assertNotIn(" Q ", panel.attrib["d"])
            for role in ("type-panel", "content-panel"):
                panel = next(
                    element
                    for element in root.iter()
                    if element.attrib.get("data-role") == role
                )
                accent = next(
                    element
                    for element in root.iter()
                    if element.attrib.get("data-role") == f"{role}-accent"
                )
                self.assertAlmostEqual(
                    float(box_value(accent, "x")),
                    float(box_value(panel, "x")) + 8,
                )
                self.assertAlmostEqual(
                    float(box_value(accent, "y")),
                    float(box_value(panel, "y")) + 2.5,
                )
                self.assertAlmostEqual(
                    float(box_value(accent, "width")),
                    float(box_value(panel, "width")) - 16,
                )
                self.assertEqual(box_value(accent, "height"), "1.5")
                self.assertEqual(accent.attrib["data-accent-mode"], "inset-rule")
                self.assertNotIn("opacity", accent.attrib)
            roles = {element.attrib.get("data-role") for element in root.iter()}
            self.assertNotIn("title-panel-accent", roles)
            self.assertNotIn("footer-accent", roles)
            footer = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "footer-panel"
            )
            self.assertEqual(box_value(footer, "height"), "30")

            title = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "title-panel"
            )
            title_x = float(title.attrib["data-box-x"])
            title_width = float(title.attrib["data-box-width"])
            footer_x = float(footer.attrib["data-box-x"])
            footer_width = float(footer.attrib["data-box-width"])
            self.assertEqual((title_x, title_width), (70.0, 550.0))
            self.assertEqual((footer_x, footer_width), (70.0, 550.0))
            self.assertFalse(
                any(
                    element.attrib.get("data-role") == "art-frame"
                    for element in root.iter()
                )
            )

    def test_main_boxes_use_one_neutral_inset_keyline_without_relief(self) -> None:
        def box_value(element: ET.Element, key: str) -> float:
            value = element.attrib.get(key) or element.attrib[f"data-box-{key}"]
            return float(value)

        expected_roles = {
            "title-panel",
            "art-mat",
            "type-panel",
            "content-panel",
            "footer-panel",
        }
        layout = renderer._load_layout()
        for card_id in GOLDEN_CARDS:
            root = self.assert_svg_contract(self.build_svg(card_id), card_id)
            ordered = list(root.iter())
            panels = {
                element.attrib["data-role"]: element
                for element in ordered
                if element.attrib.get("data-role") in expected_roles
            }
            self.assertEqual(set(panels), expected_roles, card_id)
            self.assertTrue(
                all("stroke" not in panel.attrib for panel in panels.values()),
                card_id,
            )

            keylines = {
                element.attrib["data-plate-role"]: element
                for element in ordered
                if element.attrib.get("data-role") == "plate-keyline"
            }
            self.assertEqual(set(keylines), expected_roles, card_id)
            self.assertFalse(
                {
                    "art-keyline",
                    "letterpress-keylines",
                    "letterpress-keyline",
                }
                & {element.attrib.get("data-role") for element in ordered},
                card_id,
            )
            for role, keyline in keylines.items():
                self.assertEqual(float(keyline.attrib["data-inset"]), 0.5)
                self.assertEqual(float(keyline.attrib["data-stroke-width"]), 1.0)
                self.assertEqual(keyline.attrib["data-relief"], "flat")
                self.assertEqual(keyline.attrib["data-color-token"], "line/default")
                self.assertEqual(keyline.attrib["fill"], "none")
                self.assertEqual(
                    keyline.attrib["stroke"], layout["colors"]["line/default"]["hex"]
                )
                self.assertEqual(float(keyline.attrib["stroke-width"]), 1.0)
                self.assertNotIn("opacity", keyline.attrib)
                self.assertNotIn("data-edge", keyline.attrib)
                self.assertLess(ordered.index(panels[role]), ordered.index(keyline))

                panel_box = tuple(
                    box_value(panels[role], key)
                    for key in ("x", "y", "width", "height")
                )
                keyline_box = tuple(
                    box_value(keyline, key)
                    for key in ("x", "y", "width", "height")
                )
                self.assertEqual(
                    keyline_box,
                    (
                        panel_box[0] + 0.5,
                        panel_box[1] + 0.5,
                        panel_box[2] - 1.0,
                        panel_box[3] - 1.0,
                    ),
                )
                self.assertEqual(
                    (
                        keyline_box[0] - 0.5,
                        keyline_box[1] - 0.5,
                        keyline_box[2] + 1.0,
                        keyline_box[3] + 1.0,
                    ),
                    panel_box,
                )
                if role in {"title-panel", "footer-panel"}:
                    self.assertEqual(keyline.tag.rsplit("}", 1)[-1], "path")
                    self.assertEqual(float(keyline.attrib["data-corner-radius"]), 3.5)
                    self.assertIn("A 3.5 3.5", keyline.attrib["d"])
                else:
                    self.assertEqual(keyline.tag.rsplit("}", 1)[-1], "rect")
                    self.assertNotIn("rx", keyline.attrib)
            expected_fill_tokens = {
                "title-panel": "background/paper-raised",
                "art-mat": "background/paper-raised",
                "type-panel": "background/paper-raised",
                "content-panel": "background/paper-raised",
                "footer-panel": "background/shell-raised-bottom",
            }
            self.assertEqual(
                {
                    role: panel.attrib["fill"]
                    for role, panel in panels.items()
                },
                {
                    role: layout["colors"][token]["hex"]
                    for role, token in expected_fill_tokens.items()
                },
                card_id,
            )

    def test_renderer_does_not_simulate_paper_tooth_before_press_proof(self) -> None:
        root = self.assert_svg_contract(self.build_svg("KAT-R12"), "KAT-R12")
        roles = {element.attrib.get("data-role") for element in root.iter()}
        self.assertNotIn("paper-tooth-pattern", roles)
        self.assertNotIn("paper-tooth-tile", roles)
        self.assertNotIn("paper-tooth-overlay", roles)
        self.assertNotIn("paper-tooth", self.build_svg("KAT-R12").decode("utf-8"))

    def test_artwork_uses_filter_free_warm_rim_and_top_inner_shadow(self) -> None:
        layout = renderer._load_layout()
        warm_color = layout["colors"]["material/art-warm"]["hex"]
        project_layout = layout["geometry"]["layouts"]["project"]
        art_box = _float_rect_tuple(project_layout["art"])
        art_surface_box = _float_rect_tuple(project_layout["art_surface"])
        x, y, width, height = art_box
        self.assertEqual(
            art_box,
            (
                art_surface_box[0] + 8,
                art_surface_box[1] + 8,
                art_surface_box[2] - 16,
                art_surface_box[3] - 16,
            ),
        )
        keyline_inset = renderer.MAIN_BOX_KEYLINE_STROKE_WIDTH / 2
        expected_keyline_box = (
            art_surface_box[0] + keyline_inset,
            art_surface_box[1] + keyline_inset,
            art_surface_box[2] - 2 * keyline_inset,
            art_surface_box[3] - 2 * keyline_inset,
        )
        expected_edges = {
            "left": (x, y, 5.0, height),
            "right": (x + width - 5, y, 5.0, height),
            "top": (x, y, width, 5.0),
            "bottom": (x, y + height - 5, width, 5.0),
        }
        forbidden_roles = {
            "shell-guilloche-layer",
            "art-frame",
            "artwork-mat",
        }
        forbidden_filter_tags = {
            "filter",
            "feTurbulence",
            "feDropShadow",
            "feGaussianBlur",
            "feOffset",
        }

        for card_id in GOLDEN_CARDS:
            root = self.assert_svg_contract(self.build_svg(card_id), card_id)
            ordered = list(root.iter())
            roles = {element.attrib.get("data-role") for element in ordered}
            self.assertTrue(forbidden_roles.isdisjoint(roles), card_id)
            self.assertTrue(
                all(
                    element.tag.rsplit("}", 1)[-1] not in forbidden_filter_tags
                    for element in ordered
                ),
                card_id,
            )
            artwork = next(
                element
                for element in ordered
                if element.attrib.get("data-role") == "artwork"
            )
            self.assertEqual(artwork.attrib["preserveAspectRatio"], "xMidYMid slice")
            self.assertEqual(_float_rect_tuple(artwork.attrib), art_box)
            rims = [
                element
                for element in ordered
                if element.attrib.get("data-role") == "artwork-warm-rim"
            ]
            self.assertEqual(len(rims), 1, card_id)
            rim = rims[0]
            self.assertLess(ordered.index(artwork), ordered.index(rim))
            self.assertEqual(rim.attrib["clip-path"], f"url(#art-clip-{card_id})")
            self.assertEqual(float(rim.attrib["data-depth"]), 5.0)
            self.assertEqual(float(rim.attrib["data-strength"]), 0.04)

            edges = {
                element.attrib["data-edge"]: _float_rect_tuple(element.attrib)
                for element in list(rim)
                if element.attrib.get("data-role") == "artwork-warm-edge"
            }
            self.assertEqual(edges, expected_edges, card_id)
            self.assertTrue(
                all(
                    element.attrib.get("style") == "mix-blend-mode:multiply"
                    for element in list(rim)
                ),
                card_id,
            )

            gradients = [
                element
                for element in ordered
                if element.attrib.get("data-role") == "art-edge-warmth-gradient"
            ]
            self.assertEqual(
                {element.attrib["data-edge"] for element in gradients},
                {"left", "right", "top", "bottom"},
            )
            for gradient in gradients:
                stops = list(gradient)
                self.assertEqual(
                    {float(stop.attrib["stop-opacity"]) for stop in stops},
                    {0.0, 0.04},
                )
                self.assertTrue(
                    all(stop.attrib["stop-color"] == warm_color for stop in stops)
                )

            shadows = [
                element
                for element in ordered
                if element.attrib.get("data-role") == "artwork-top-inner-shadow"
            ]
            self.assertEqual(len(shadows), 1, card_id)
            shadow = shadows[0]
            self.assertLess(ordered.index(rim), ordered.index(shadow))
            self.assertEqual(_float_rect_tuple(shadow.attrib), (x, y, width, 7.0))
            self.assertEqual(shadow.attrib["fill"], "url(#art-top-inner-shadow)")
            self.assertEqual(shadow.attrib["clip-path"], f"url(#art-clip-{card_id})")
            self.assertEqual(shadow.attrib["data-edge"], "top")
            self.assertEqual(float(shadow.attrib["data-max-opacity"]), 0.03)

            shadow_gradients = [
                element
                for element in ordered
                if element.attrib.get("data-role")
                == "artwork-top-inner-shadow-gradient"
            ]
            self.assertEqual(len(shadow_gradients), 1, card_id)
            shadow_stops = list(shadow_gradients[0])
            self.assertEqual(
                [stop.attrib["offset"] for stop in shadow_stops],
                ["0%", "35%", "100%"],
            )
            self.assertEqual(
                [float(stop.attrib["stop-opacity"]) for stop in shadow_stops],
                [0.03, 0.018, 0.0],
            )
            self.assertTrue(
                all(stop.attrib["stop-color"] == "#000000" for stop in shadow_stops)
            )

            art_keyline = next(
                element
                for element in ordered
                if element.attrib.get("data-role") == "plate-keyline"
                and element.attrib.get("data-plate-role") == "art-mat"
            )
            self.assertEqual(
                _float_rect_tuple(art_keyline.attrib),
                expected_keyline_box,
            )
            self.assertEqual(art_keyline.attrib["fill"], "none")
            self.assertEqual(
                float(art_keyline.attrib["stroke-width"]),
                renderer.MAIN_BOX_KEYLINE_STROKE_WIDTH,
            )
            self.assertEqual(art_keyline.attrib["data-color-token"], "line/default")
            self.assertEqual(
                art_keyline.attrib["stroke"],
                layout["colors"]["line/default"]["hex"],
            )
            self.assertNotIn("opacity", art_keyline.attrib)
            self.assertNotIn("rx", art_keyline.attrib)
            self.assertLess(ordered.index(shadow), ordered.index(art_keyline))
            self.assertEqual(
                (
                    expected_keyline_box[0]
                    - renderer.MAIN_BOX_KEYLINE_STROKE_WIDTH / 2,
                    expected_keyline_box[1]
                    - renderer.MAIN_BOX_KEYLINE_STROKE_WIDTH / 2,
                    expected_keyline_box[2]
                    + renderer.MAIN_BOX_KEYLINE_STROKE_WIDTH,
                    expected_keyline_box[3]
                    + renderer.MAIN_BOX_KEYLINE_STROKE_WIDTH,
                ),
                art_surface_box,
            )
            self.assertEqual(
                (
                    art_surface_box[0],
                    art_surface_box[2],
                ),
                (70.0, 550.0),
            )

        placeholder_card = dict(self.cards_by_id["KAT-C12"])
        placeholder_card["artwork_status"] = "draft"
        placeholder_root = ET.fromstring(
            renderer.build_card_svg(placeholder_card, self.profile, None, proof=False)
        )
        placeholder_order = list(placeholder_root.iter())
        placeholder_group = next(
            element
            for element in placeholder_order
            if element.attrib.get("data-role") == "artwork-placeholder-group"
        )
        placeholder = next(
            element
            for element in placeholder_order
            if element.attrib.get("data-role") == "artwork-placeholder"
        )
        placeholder_keyline = next(
            element
            for element in placeholder_order
            if element.attrib.get("data-role") == "plate-keyline"
            and element.attrib.get("data-plate-role") == "art-mat"
        )
        self.assertEqual(
            placeholder_group.attrib["clip-path"],
            "url(#art-clip-KAT-C12)",
        )
        self.assertIn(placeholder, list(placeholder_group))
        self.assertTrue(
            any(
                element.attrib.get("data-role") == "artwork-placeholder-hatch"
                for element in list(placeholder_group)
            )
        )
        self.assertLess(
            placeholder_order.index(placeholder_group),
            placeholder_order.index(placeholder_keyline),
        )

    def test_light_mat_is_the_only_art_treatment(self) -> None:
        layout = renderer._load_layout()
        self.assertNotIn("art_treatments", layout)
        spec = layout["art_treatment"]
        self.assertEqual(
            set(spec),
            {
                "id",
                "label",
                "mat_color_token",
                "clear_mat",
                "outer_radius",
                "art_radius",
            },
        )
        self.assertEqual(spec["id"], "light-mat")
        self.assertEqual(renderer.ART_TREATMENT, "light-mat")

        def art_plate_keyline(root: ET.Element) -> ET.Element:
            matching = [
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "plate-keyline"
                and element.attrib.get("data-plate-role") == "art-mat"
            ]
            self.assertEqual(len(matching), 1)
            return matching[0]

        self.assertEqual(spec["mat_color_token"], "background/paper-raised")
        self.assertEqual(float(spec["clear_mat"]), 8.0)
        self.assertEqual(float(spec["outer_radius"]), 0.0)
        self.assertEqual(float(spec["art_radius"]), 4.0)
        self.assertNotIn("keyline_radius", spec)
        for layout_name, zones in layout["geometry"]["layouts"].items():
            with self.subTest(layout=layout_name):
                self.assertEqual(
                    _float_rect_tuple(zones["art_surface"]),
                    (70.0, 123.8644, 550.0, 372.0),
                )
                self.assertEqual(
                    _float_rect_tuple(zones["art"]),
                    (78.0, 131.8644, 534.0, 356.0),
                )
                self.assertEqual(zones["art"]["width"] * 2, zones["art"]["height"] * 3)
                self.assertEqual(
                    (zones["art"]["x"], zones["art"]["x"] + zones["art"]["width"]),
                    (
                        zones["flavor"]["x"],
                        zones["flavor"]["x"] + zones["flavor"]["width"],
                    ),
                )
                top_gap = zones["art_surface"]["y"] - (
                    zones["title_surface"]["y"] + zones["title_surface"]["height"]
                )
                bottom_gap = zones["type_surface"]["y"] - (
                    zones["art_surface"]["y"] + zones["art_surface"]["height"]
                )
                self.assertEqual((top_gap, bottom_gap), (4.0, 4.0))

        card = dict(self.cards_by_id["KAT-C12"])
        artwork_path = renderer.resolve_artwork("KAT-C12", ARTWORK_DIR)
        root = ET.fromstring(
            renderer.build_card_svg(
                card,
                self.profile,
                artwork_path,
                proof=False,
            )
        )
        self.assertEqual(root.attrib["data-art-treatment"], "light-mat")
        ordered = list(root.iter())
        mat = next(
            element
            for element in ordered
            if element.attrib.get("data-role") == "art-mat"
        )
        artwork = next(
            element
            for element in ordered
            if element.attrib.get("data-role") == "artwork"
        )
        keyline = art_plate_keyline(root)
        self.assertEqual(
            _float_rect_tuple(mat.attrib),
            (70.0, 123.8644, 550.0, 372.0),
        )
        self.assertEqual(
            mat.attrib["fill"],
            layout["colors"]["background/paper-raised"]["hex"],
        )
        self.assertNotIn("stroke", mat.attrib)
        self.assertNotIn("rx", mat.attrib)
        self.assertEqual(
            _float_rect_tuple(artwork.attrib),
            (78.0, 131.8644, 534.0, 356.0),
        )
        self.assertEqual(
            _float_rect_tuple(keyline.attrib),
            (70.5, 124.3644, 549.0, 371.0),
        )
        self.assertEqual(
            float(keyline.attrib["stroke-width"]),
            renderer.MAIN_BOX_KEYLINE_STROKE_WIDTH,
        )
        self.assertEqual(keyline.attrib["data-color-token"], "line/default")
        self.assertEqual(
            keyline.attrib["stroke"], layout["colors"]["line/default"]["hex"]
        )
        self.assertEqual(keyline.attrib["fill"], "none")
        self.assertNotIn("rx", keyline.attrib)
        art_clip = next(
            element
            for element in ordered
            if element.tag.rsplit("}", 1)[-1] == "clipPath"
            and element.attrib.get("id") == "art-clip-KAT-C12"
        )
        self.assertEqual(float(list(art_clip)[0].attrib["rx"]), 4.0)

        default_root = ET.fromstring(self.build_svg("KAT-C12"))
        default_keyline = art_plate_keyline(default_root)
        self.assertEqual(keyline.attrib["stroke"], default_keyline.attrib["stroke"])
        self.assertLess(ordered.index(mat), ordered.index(artwork))
        self.assertLess(ordered.index(artwork), ordered.index(keyline))
        keyline_stroke = float(keyline.attrib["stroke-width"])
        self.assertEqual(
            (
                float(keyline.attrib["x"]) - keyline_stroke / 2,
                float(keyline.attrib["y"]) - keyline_stroke / 2,
                float(keyline.attrib["width"]) + keyline_stroke,
                float(keyline.attrib["height"]) + keyline_stroke,
            ),
            _float_rect_tuple(mat.attrib),
        )
        self.assertLess(
            float(keyline.attrib["x"]) + keyline_stroke / 2,
            float(artwork.attrib["x"]),
        )
        self.assertLess(
            float(keyline.attrib["y"]) + keyline_stroke / 2,
            float(artwork.attrib["y"]),
        )
        self.assertNotIn(
            "art-keyline",
            {element.attrib.get("data-role") for element in ordered},
        )

        clear_mats = (
            float(artwork.attrib["x"]) - float(mat.attrib["x"]),
            float(artwork.attrib["y"]) - float(mat.attrib["y"]),
            float(mat.attrib["x"])
            + float(mat.attrib["width"])
            - (float(artwork.attrib["x"]) + float(artwork.attrib["width"])),
            float(mat.attrib["y"])
            + float(mat.attrib["height"])
            - (float(artwork.attrib["y"]) + float(artwork.attrib["height"])),
        )
        self.assertEqual(
            tuple(round(clearance, 4) for clearance in clear_mats),
            (8.0, 8.0, 8.0, 8.0),
        )

        metadata_element = next(
            element
            for element in root
            if element.tag.rsplit("}", 1)[-1] == "metadata"
        )
        metadata = json.loads(metadata_element.text or "{}")
        self.assertEqual(metadata["art_treatment"], "light-mat")

        placeholder_root = ET.fromstring(
            renderer.build_card_svg(
                card,
                self.profile,
                None,
                proof=False,
            )
        )
        placeholder = next(
            element
            for element in placeholder_root.iter()
            if element.attrib.get("data-role") == "artwork-placeholder"
        )
        placeholder_clip = next(
            element
            for element in placeholder_root.iter()
            if element.tag.rsplit("}", 1)[-1] == "clipPath"
            and element.attrib.get("id") == "art-clip-KAT-C12"
        )
        self.assertEqual(float(placeholder.attrib["rx"]), 4.0)
        self.assertEqual(float(list(placeholder_clip)[0].attrib["rx"]), 4.0)

        self.assertEqual(default_root.attrib["data-art-treatment"], "light-mat")
        self.assertTrue(
            any(
                element.attrib.get("data-role") == "art-mat"
                for element in default_root.iter()
            )
        )
        self.assertEqual(
            self.build_svg("KAT-C12"),
            renderer.build_card_svg(
                card,
                self.profile,
                artwork_path,
                proof=False,
            ),
        )

        print_card = dict(card)
        print_card["_render_mode"] = "print"
        print_default = ET.fromstring(
            renderer.build_card_svg(
                print_card,
                self.profile,
                artwork_path,
                proof=False,
            )
        )
        self.assertEqual(print_default.attrib["data-art-treatment"], "light-mat")
        self.assertFalse(hasattr(renderer.parse_args([]), "art_treatment"))

        with (
            tempfile.TemporaryDirectory() as output_dir,
            patch.object(renderer, "rasterize_svg", return_value=b"raster"),
            patch.object(renderer, "finalize_png", return_value=b"png"),
            patch.object(
                renderer,
                "inspect_png",
                return_value={
                    "sha256": hashlib.sha256(b"png").hexdigest(),
                    "bytes": 3,
                },
            ),
        ):
            manifest = renderer.render_selected(
                profile_path=PROFILE_PATH,
                csv_path=CARDS_PATH,
                artwork_dir=ARTWORK_DIR,
                output_dir=Path(output_dir),
                card_ids=["KAT-C12"],
                mode="preview",
            )
            self.assertEqual(manifest["art_treatment"], "light-mat")
            written_svg = ET.fromstring(
                Path(output_dir, "svg", "KAT-C12.svg").read_bytes()
            )
            self.assertEqual(written_svg.attrib["data-art-treatment"], "light-mat")
            written_metadata_element = next(
                element
                for element in written_svg
                if element.tag.rsplit("}", 1)[-1] == "metadata"
            )
            written_metadata = json.loads(written_metadata_element.text or "{}")
            self.assertEqual(written_metadata["art_treatment"], "light-mat")

    def test_passepartout_and_main_panels_share_the_exact_paper_fill(self) -> None:
        layout = renderer._load_layout()
        paper_token = "background/paper-raised"
        paper = renderer._color(layout, paper_token)
        self.assertEqual(paper, "#F5EEDB")
        self.assertEqual(
            layout["art_treatment"]["mat_color_token"],
            paper_token,
        )

        for card_id in ("KAT-R12", "KAT-C12", "KAT-U26"):
            with self.subTest(card_id=card_id):
                svg = self.build_svg(card_id)
                root = ET.fromstring(svg)
                panels = {
                    role: [
                        element
                        for element in root.iter()
                        if element.attrib.get("data-role") == role
                    ]
                    for role in (
                        "art-mat",
                        "title-panel",
                        "type-panel",
                        "content-panel",
                    )
                }
                self.assertEqual(
                    {role: len(elements) for role, elements in panels.items()},
                    {role: 1 for role in panels},
                )
                self.assertEqual(
                    {
                        elements[0].attrib["fill"]
                        for elements in panels.values()
                    },
                    {paper},
                )
                roles = {element.attrib.get("data-role") for element in root.iter()}
                self.assertTrue(
                    {
                        "paper-tooth-pattern",
                        "paper-tooth-tile",
                        "paper-tooth-overlay",
                    }.isdisjoint(roles)
                )
                self.assertNotIn("paper-tooth", svg.decode("utf-8"))

    def test_event_identity_badges_contain_only_the_event_icon(self) -> None:
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Ereignis":
                continue
            root = ET.fromstring(self.build_svg(card_id))
            badge = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "card-type-badge"
            )
            self.assertEqual(
                [
                    element.attrib["data-icon"]
                    for element in badge.iter()
                    if "data-icon" in element.attrib
                ],
                ["event"],
                card_id,
            )
            badge_roles = {element.attrib.get("data-role") for element in badge.iter()}
            self.assertTrue(
                {
                    "event-polarity",
                    "event-polarity-carrier",
                    "event-polarity-symbol",
                }.isdisjoint(badge_roles),
                card_id,
            )

    def test_all_event_type_lines_use_shared_accent_without_visible_polarity(self) -> None:
        layout = renderer._load_layout()
        event_token = layout["card_types"]["Ereignis"]["color_token"]
        self.assertEqual(event_token, "event/base")
        self.assertEqual(
            {token for token in layout["colors"] if token.startswith("event/")},
            {"event/base"},
        )
        event_color = renderer._color(layout, event_token)
        neutral = renderer._color(layout, "text/primary")
        self.assertEqual(event_color, "#60457A")
        expected_polarities = {"positive", "negative", "ambivalent"}
        self.assertEqual(set(layout["polarities"]), expected_polarities)
        self.assertTrue(
            all("symbol" not in spec for spec in layout["polarities"].values())
        )

        fonts = renderer._resolve_fonts()
        seen_cards: set[str] = set()
        seen_polarities: set[str] = set()

        roles = (
            "card-type",
            "event-effect-symbol",
            "event-keyword",
        )
        forbidden_polarity_roles = {
            "event-polarity",
            "event-polarity-carrier",
            "event-polarity-symbol",
        }
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Ereignis":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            ordered = list(root.iter())
            matches = {
                role: [
                    element
                    for element in ordered
                    if element.attrib.get("data-role") == role
                ]
                for role in roles
            }
            for role, elements in matches.items():
                self.assertEqual(len(elements), 1, f"{card_id}:{role}")

            primary = matches["card-type"][0]
            effect_symbol = matches["event-effect-symbol"][0]
            keyword = matches["event-keyword"][0]
            polarity_key = str(_value(card, "polarity"))
            self.assertEqual(root.attrib["data-polarity"], polarity_key, card_id)

            self.assertEqual(
                renderer._appearance(card, layout, "event")["accent_token"],
                event_token,
                card_id,
            )
            self.assertEqual(_text_content(primary), "EREIGNIS", card_id)
            self.assertEqual(primary.attrib["fill"], event_color, card_id)
            self.assertEqual(effect_symbol.attrib["fill"], event_color, card_id)
            self.assertEqual(keyword.attrib["fill"], neutral, card_id)
            for role in ("type-panel-accent", "content-panel-accent"):
                accent = next(
                    element
                    for element in ordered
                    if element.attrib.get("data-role") == role
                )
                self.assertEqual(accent.attrib["fill"], event_color, f"{card_id}:{role}")
            flavor_divider = next(
                element
                for element in ordered
                if element.attrib.get("data-role") == "flavor-divider"
            )
            self.assertEqual(flavor_divider.attrib["stroke"], event_color, card_id)
            self.assertTrue(
                forbidden_polarity_roles.isdisjoint(
                    {element.attrib.get("data-role") for element in ordered}
                ),
                card_id,
            )

            primary_text = _text_content(primary)
            primary_size = float(primary.attrib["font-size"])
            primary_width = renderer._text_width(
                primary_text,
                renderer._font(
                    fonts, primary.attrib["data-font-role"], primary_size
                ),
                float(primary.attrib.get("letter-spacing", "0")),
            )
            effect_transform = re.fullmatch(
                r"translate\(([-0-9.]+) ([-0-9.]+)\) scale\([-0-9.]+\)",
                effect_symbol.attrib["transform"],
            )
            self.assertIsNotNone(effect_transform, card_id)
            assert effect_transform is not None
            effect_left = float(effect_transform.group(1))
            self.assertAlmostEqual(
                effect_left,
                float(primary.attrib["x"]) + primary_width + 5,
                places=4,
                msg=card_id,
            )
            self.assertLess(ordered.index(primary), ordered.index(effect_symbol), card_id)
            self.assertLess(ordered.index(effect_symbol), ordered.index(keyword), card_id)

            seen_cards.add(card_id)
            seen_polarities.add(polarity_key)

        self.assertEqual(len(seen_cards), 28)
        self.assertEqual(seen_polarities, expected_polarities)

        invalid_event = dict(self.cards_by_id["KAT-C03"])
        invalid_event["effect_template"] = ""
        invalid_event["target_family"] = ""
        invalid_event["polarity"] = ""
        with self.assertRaisesRegex(renderer.RenderError, "Polarität fehlt"):
            renderer.build_card_svg(invalid_event, self.profile, None, proof=False)
        invalid_event["polarity"] = "unbekannt"
        with self.assertRaisesRegex(renderer.RenderError, "Unbekannte Polarität"):
            renderer.build_card_svg(invalid_event, self.profile, None, proof=False)

    def test_project_factor_and_event_type_lines_use_semantic_icons(self) -> None:
        layout = renderer._load_layout()
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Projekt":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            symbol = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "project-family-symbol"
            )
            family_key = str(_value(card, "domain_primary"))
            self.assertEqual(
                symbol.attrib["data-icon"], layout["families"][family_key]["icon"], card_id
            )
            self.assertEqual(symbol.attrib["data-icon-size"], "20", card_id)

        expected_factors = {"KAT-C12": "data", "KAT-U03": "joker"}
        for card_id, icon_key in expected_factors.items():
            root = ET.fromstring(self.build_svg(card_id))
            symbol = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "factor-family-symbol"
            )
            self.assertEqual(symbol.attrib["data-icon"], icon_key)

        expected_effects = {
            "E1": ("inspect", "Eye", "SICHTEN"),
            "E2": ("draw", "CardsThree", "NACHZIEHEN"),
            "E3": ("retrieve", "ArrowCounterClockwise", "RÜCKHOLEN"),
            "E4": ("redistribute", "ArrowsLeftRight", "UMVERTEILEN"),
            "E5": ("joker", "Asterisk", "JOKER"),
            "E6": ("extra_effort", "HourglassMedium", "MEHRAUFWAND"),
            "E7": ("negative", "TrendDown", "RÜCKSCHLAG"),
            "E8": ("safeguard", "ShieldCheck", "ABSICHERUNG"),
        }
        self.assertEqual(
            layout["effect_icons"],
            {key: values[0] for key, values in expected_effects.items()},
        )
        self.assertEqual(
            layout["effect_templates"],
            {key: values[2] for key, values in expected_effects.items()},
        )
        manifest = renderer._load_icon_manifest()
        for effect, (icon_key, phosphor_name, _label) in expected_effects.items():
            with self.subTest(effect=effect):
                self.assertEqual(
                    tuple(manifest["icons"][icon_key]["phosphor"]),
                    (phosphor_name,),
                )

        event_cards = {
            card_id: card
            for card_id, card in self.cards_by_id.items()
            if _value(card, "card_type") == "Ereignis"
        }
        self.assertEqual(len(event_cards), 28)
        seen_effects: set[str] = set()
        for card_id, card in event_cards.items():
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            ordered = list(root.iter())
            symbols = [
                element
                for element in ordered
                if element.attrib.get("data-role") == "event-effect-symbol"
            ]
            effect = str(_value(card, "effect_template"))
            seen_effects.add(effect)
            expected_icon, _phosphor_name, expected_label = expected_effects[effect]
            self.assertEqual(len(symbols), 1, card_id)
            symbol = symbols[0]
            self.assertEqual(symbol.attrib["data-icon"], expected_icon, card_id)
            self.assertEqual(symbol.attrib["data-icon-size"], "18", card_id)
            accent_token = renderer._appearance(card, layout, "event")["accent_token"]
            self.assertEqual(
                symbol.attrib["fill"], renderer._color(layout, accent_token), card_id
            )
            keyword = next(
                element
                for element in ordered
                if element.attrib.get("data-role") == "event-keyword"
            )
            self.assertLess(ordered.index(symbol), ordered.index(keyword), card_id)
            self.assertTrue(
                " ".join(self.visible_text(keyword)).startswith(expected_label),
                card_id,
            )

        self.assertEqual(seen_effects, set(expected_effects))

    def test_all_events_fit_one_line_in_the_wide_type_surface(self) -> None:
        layout = renderer._load_layout()
        event_layout = layout["geometry"]["layouts"]["event"]
        text_right = (
            float(event_layout["type_surface"]["x"])
            + float(event_layout["type_surface"]["width"])
            - 12
        )
        narrow_type_right = (
            float(event_layout["type"]["x"])
            + float(event_layout["type"]["width"])
        )
        self.assertEqual(text_right, 608.0)
        self.assertEqual(narrow_type_right, 478.0)
        self.assertGreater(text_right, narrow_type_right)

        fonts = renderer._resolve_fonts()
        right_gaps: dict[str, float] = {}
        forbidden_right_controls = {
            "event-parameters",
            "event-controls",
            "project-requirements",
            "project-requirement-carrier",
            "project-requirement-symbol",
            "project-points",
            "project-points-label",
        }
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Ereignis":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            keyword = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "event-keyword"
            )
            lines = _text_lines(keyword)
            self.assertEqual(len(lines), 1, card_id)
            text = lines[0]
            size = float(keyword.attrib["font-size"])
            width = renderer._text_width(
                text,
                renderer._font(fonts, keyword.attrib["data-font-role"], size),
                float(keyword.attrib.get("letter-spacing", "0")),
            )
            gap = text_right - (float(keyword.attrib["x"]) + width)
            right_gaps[card_id] = gap
            self.assertGreaterEqual(gap, 0.0, card_id)
            roles = {element.attrib.get("data-role") for element in root.iter()}
            self.assertTrue(forbidden_right_controls.isdisjoint(roles), card_id)

        self.assertEqual(len(right_gaps), 28)
        self.assertEqual(min(right_gaps, key=right_gaps.get), "KAT-U17")
        self.assertAlmostEqual(right_gaps["KAT-U17"], 106.99735, places=3)

    def test_svg_metadata_records_icon_manifest_and_used_asset_hashes(self) -> None:
        root = ET.fromstring(self.build_svg("KAT-C03"))
        manifest = renderer._load_icon_manifest()
        self.assertEqual(
            root.attrib["data-icon-manifest-sha256"], manifest["_sha256"]
        )
        metadata_element = next(
            element
            for element in root
            if element.tag.rsplit("}", 1)[-1] == "metadata"
        )
        metadata = json.loads(metadata_element.text or "{}")
        self.assertEqual(metadata["icon_manifest_sha256"], manifest["_sha256"])
        self.assertEqual(
            set(metadata["icons"]), {"event", "extra_effort"}
        )
        for icon in metadata["icons"].values():
            self.assertTrue(icon["file"].startswith("data/assets/icons/"))
            self.assertRegex(icon["sha256"], r"^[0-9a-f]{64}$")

    def test_all_events_put_defined_keywords_in_the_type_line(self) -> None:
        layout = renderer._load_layout()
        for card_id, card in self.cards_by_id.items():
            if _value(card, "card_type") != "Ereignis":
                continue
            root = ET.fromstring(
                renderer.build_card_svg(card, self.profile, None, proof=False)
            )
            keyword = next(
                element
                for element in root.iter()
                if element.attrib.get("data-role") == "event-keyword"
            )
            effect = layout["effect_templates"][str(_value(card, "effect_template"))]
            targets = [key for key in str(_value(card, "target_family") or "").split("+") if key]
            target_label = " + ".join(layout["families"][key]["label"] for key in targets)
            expected = effect + (f" · ZIEL: {target_label}" if target_label else "")
            self.assertEqual(" ".join(self.visible_text(keyword)), expected, card_id)
            self.assertEqual(float(keyword.attrib["font-size"]), 14.0, card_id)
            self.assertEqual(float(keyword.attrib["data-line-height"]), 18.0, card_id)
            self.assertFalse(
                any(
                    element.attrib.get("data-role") == "event-parameters"
                    for element in root.iter()
                ),
                card_id,
            )

    def test_project_visible_copy_spells_out_all_numbers(self) -> None:
        for card in self.cards_by_id.values():
            if _value(card, "card_type") != "Projekt":
                continue
            for field in ("name", "project_goal", "rules_text", "flavor_text"):
                with self.subTest(card_id=_value(card, "card_id"), field=field):
                    self.assertNotRegex(str(_value(card, field) or ""), r"[0-9]")

    def test_bleed_black_frame_and_inset_card_field_use_exact_geometry(self) -> None:
        root = self.assert_svg_contract(self.build_svg("KAT-C12"), "KAT-C12")
        bleed = next(
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "full-bleed-background"
        )
        self.assertEqual(bleed.attrib["fill"], "#D7DADD")

        trim_background = next(
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "trim-background"
        )
        self.assertEqual(trim_background.tag.rsplit("}", 1)[-1], "rect")
        self.assertEqual(trim_background.attrib["fill"], "#090B0D")
        self.assertEqual(
            tuple(
                int(trim_background.attrib[key]) for key in ("x", "y", "width", "height")
            ),
            MASTER_RECTS["trim"],
        )

        interior = next(
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "inner-card-field"
        )
        self.assertEqual(interior.attrib["fill"], "url(#inner-card-field-gradient)")
        self.assertEqual(
            tuple(int(interior.attrib[key]) for key in ("x", "y", "width", "height")),
            (69, 69, 684, 984),
        )
        self.assertEqual(interior.attrib["rx"], "16")

        face = next(
            element
            for element in root.iter()
            if element.attrib.get("id") == "card-face"
        )
        scale = renderer._card_face_scale(self.profile)
        self.assertEqual(
            face.attrib["transform"],
            f"translate(411 561) scale({scale:.12f}) translate(-411 -561)",
        )
        trim = MASTER_RECTS["trim"]
        centre = (trim[0] + trim[2] / 2, trim[1] + trim[3] / 2)
        field_left = centre[0] + (69 - centre[0]) * scale
        field_top = centre[1] + (69 - centre[1]) * scale
        internal_safe = MASTER_RECTS["internal_text_safe"]
        # The narrow axis is the tight one, so the shrink is measured there: the
        # field lands on the internal DHK safe and the vendor's red mark keeps a
        # full millimetre of black to itself on all four edges.
        self.assertAlmostEqual(field_left, internal_safe[0], places=6)
        self.assertGreater(field_top, internal_safe[1])
        vendor_safe = MASTER_RECTS["vendor_safe"]
        self.assertAlmostEqual(field_left - vendor_safe[0], 12.0, places=6)
        self.assertGreaterEqual(field_top - vendor_safe[1], 12.0)

        gradients = [
            element
            for element in root.iter()
            if element.attrib.get("data-role") == "inner-card-field-gradient"
        ]
        self.assertEqual(len(gradients), 1)
        gradient = gradients[0]
        self.assertEqual(
            tuple(gradient.attrib[key] for key in ("x1", "y1", "x2", "y2")),
            ("0%", "0%", "0%", "100%"),
        )
        layout = renderer._load_layout()
        expected_stops = (
            ("0%", "background/shell-raised-top"),
            ("50%", "background/shell-raised"),
            ("100%", "background/shell-raised-bottom"),
        )
        self.assertEqual(
            [
                (
                    stop.attrib["offset"],
                    stop.attrib["data-color-token"],
                    stop.attrib["stop-color"],
                )
                for stop in list(gradient)
            ],
            [
                (offset, token, layout["colors"][token]["hex"])
                for offset, token in expected_stops
            ],
        )

        design_clip = next(
            element
            for element in root.iter()
            if element.attrib.get("id") == "card-design-clip"
        )
        self.assertEqual(design_clip.attrib["clip-path"], "url(#trim-clip-KAT-C12)")

    def test_rasterized_bleed_and_safety_band_colors_on_all_four_edges(self) -> None:
        with Image.open(io.BytesIO(self.build_png("KAT-C12"))) as image:
            outer_samples = ((36, 1122), (1608, 1122), (822, 36), (822, 2208))
            band_samples = ((102, 1122), (1542, 1122), (822, 102), (822, 2142))
            inner_band_samples = ((134, 1122), (1510, 1122), (822, 134), (822, 2110))
            # One millimetre inside the vendor safe the border is still black on
            # every edge: that is the clearance the shrunken face buys.
            clearance_samples = ((154, 1122), (1490, 1122), (822, 154), (822, 2090))
            field_samples = ((170, 1122), (1474, 1122))
            rounded_corner_samples = ((146, 146), (1498, 146), (146, 2098), (1498, 2098))
            for point in outer_samples:
                with self.subTest(zone="outside-cut", point=point):
                    self.assertEqual(image.getpixel(point), (215, 218, 221))
            for point in band_samples:
                with self.subTest(zone="trim-to-vendor-safe", point=point):
                    self.assertEqual(image.getpixel(point), (9, 11, 13))
            for point in inner_band_samples:
                with self.subTest(zone="vendor-safe-to-inset-field", point=point):
                    self.assertEqual(image.getpixel(point), (9, 11, 13))
            for point in clearance_samples:
                with self.subTest(zone="vendor-safe-clearance", point=point):
                    self.assertEqual(image.getpixel(point), (9, 11, 13))
            for point in field_samples:
                with self.subTest(zone="inset-card-field", point=point):
                    self.assertEqual(image.getpixel(point), (32, 37, 42))
            gradient_samples = (
                image.getpixel((170, 400)),
                image.getpixel((170, 1122)),
                image.getpixel((170, 1850)),
            )
            luminances = tuple(sum(sample) for sample in gradient_samples)
            self.assertGreater(luminances[0], luminances[1])
            self.assertGreater(luminances[1], luminances[2])
            self.assertLess(luminances[0] - luminances[2], 40)
            for point in rounded_corner_samples:
                with self.subTest(zone="rounded-field-corner", point=point):
                    self.assertEqual(image.getpixel(point), (9, 11, 13))

    def test_visible_panels_are_inside_the_internal_safe_area(self) -> None:
        layout = json.loads((ROOT / "data" / "card_layout.json").read_text(encoding="utf-8"))
        document = layout["geometry"]["document"]
        scale_x = MASTER_VIEWBOX[2] / document["width"]
        scale_y = MASTER_VIEWBOX[3] / document["height"]
        safe = self.profile["master_svg"]["rectangles"]["internal_text_safe"]
        safe_right = safe["x"] + safe["width"]
        safe_bottom = safe["y"] + safe["height"]
        panel_names = {
            "title_surface",
            "art_surface",
            "type_surface",
            "content_surface",
            "footer_surface",
            "rules_panel",
            "flavor_panel",
        }

        for layout_name, spec in layout["geometry"]["layouts"].items():
            for zone_name in panel_names.intersection(spec):
                zone = spec[zone_name]
                with self.subTest(layout=layout_name, zone=zone_name):
                    # Two layout units cover every remaining panel stroke.
                    self.assertGreaterEqual((zone["x"] - 2) * scale_x, safe["x"])
                    self.assertGreaterEqual((zone["y"] - 2) * scale_y, safe["y"])
                    self.assertLessEqual(
                        (zone["x"] + zone["width"] + 2) * scale_x,
                        safe_right,
                    )
                    self.assertLessEqual(
                        (zone["y"] + zone["height"] + 2) * scale_y,
                        safe_bottom,
                    )

    def test_every_configured_text_zone_is_inside_the_internal_safe_area(self) -> None:
        layout = json.loads((ROOT / "data" / "card_layout.json").read_text(encoding="utf-8"))
        document = layout["geometry"]["document"]
        master_width, master_height = MASTER_VIEWBOX[2:]
        scale_x = master_width / document["width"]
        scale_y = master_height / document["height"]
        safe = self.profile["master_svg"]["rectangles"]["internal_text_safe"]
        safe_right = safe["x"] + safe["width"]
        safe_bottom = safe["y"] + safe["height"]
        text_zone_names = {
            "title",
            "type",
            "goal",
            "rules",
            "flavor",
            "meta",
            "footer",
        }

        for layout_name, spec in layout["geometry"]["layouts"].items():
            for zone_name in text_zone_names.intersection(spec):
                zone = spec[zone_name]
                with self.subTest(layout=layout_name, zone=zone_name):
                    self.assertGreaterEqual(zone["x"] * scale_x, safe["x"])
                    self.assertGreaterEqual(zone["y"] * scale_y, safe["y"])
                    self.assertLessEqual((zone["x"] + zone["width"]) * scale_x, safe_right)
                    self.assertLessEqual((zone["y"] + zone["height"]) * scale_y, safe_bottom)

        content_frame = layout["geometry"]["content_stack_frame"]
        self.assertGreaterEqual(content_frame["x"] * scale_x, safe["x"])
        self.assertGreaterEqual(content_frame["y"] * scale_y, safe["y"])
        self.assertLessEqual(
            (content_frame["x"] + content_frame["width"]) * scale_x,
            safe_right,
        )

    def test_profile_contains_exact_master_and_upload_geometry(self) -> None:
        self.assertIsInstance(self.profile, Mapping)
        source_template = self.profile["source_template"]
        self.assertEqual(source_template["path"], "data/templates/poker-size.pdf")
        self.assertEqual(source_template["declared_outer_pixels_300_dpi"], [822, 1122])
        self.assertTrue((ROOT / source_template["path"]).is_file())
        self.assertEqual(
            {
                tuple(item["declared_outer_pixels_300_dpi"])
                for item in self.profile["excluded_nonmatching_templates"]
            },
            {(816, 1110)},
        )
        self.assertEqual(tuple(self.profile["master_svg"]["view_box"]), MASTER_VIEWBOX)
        self.assertEqual(self.profile["master_svg"]["reference_dpi"], 300)

        physical_rectangles = self.profile["physical_mm"]
        master_rectangles = self.profile["master_svg"]["rectangles"]
        upload = self.profile["upload_png"]
        upload_rectangles = upload["rectangles"]

        self.assertEqual((upload["width"], upload["height"]), OUTPUT_SIZE)
        self.assertEqual(upload["dpi"], OUTPUT_DPI)
        self.assertEqual(upload["scale_from_master"], 2)
        self.assertEqual(upload["color"]["pixel_model"], "RGB")
        self.assertEqual(upload["color"]["color_space"], "sRGB")
        self.assertIs(upload["color"]["alpha"], False)
        self.assertEqual(upload["max_file_size"]["bytes"], MAX_OUTPUT_BYTES)

        for name, expected in PHYSICAL_RECTS.items():
            rect = physical_rectangles[name]
            actual = tuple(float(rect[key]) for key in ("x", "y", "width", "height"))
            self.assertEqual(actual, expected, name)
        for name, expected in MASTER_RECTS.items():
            self.assertEqual(_rect_tuple(master_rectangles[name]), expected, name)
        for name, expected in OUTPUT_RECTS.items():
            self.assertEqual(_rect_tuple(upload_rectangles[name]), expected, name)
        self.assertEqual(physical_rectangles["internal_text_safe"]["inset_from_vendor_safe"], 1.0)

    def test_upload_rectangles_are_exactly_twice_master_rectangles(self) -> None:
        master = self.profile["master_svg"]["rectangles"]
        upload = self.profile["upload_png"]["rectangles"]
        for name in MASTER_RECTS:
            self.assertEqual(
                _rect_tuple(upload[name]),
                tuple(value * 2 for value in _rect_tuple(master[name])),
                name,
            )

    def test_csv_and_artwork_directory_have_an_exact_82_card_bijection(self) -> None:
        card_ids = set(self.cards_by_id)
        artwork_paths = sorted(ARTWORK_DIR.glob("*.png"))
        artwork_ids = {path.stem for path in artwork_paths}

        self.assertEqual(len(self.cards_by_id), 82)
        self.assertEqual(len(artwork_paths), 82)
        self.assertEqual(card_ids, artwork_ids)

        for card_id in sorted(card_ids):
            resolved = renderer.resolve_artwork(card_id, ARTWORK_DIR)
            self.assertIsInstance(resolved, (str, Path))
            self.assertEqual(Path(resolved).resolve(), (ARTWORK_DIR / f"{card_id}.png").resolve())

    def test_all_82_cards_fit_the_layout_before_rasterization(self) -> None:
        # Placeholder artwork keeps this exhaustive typography/layout gate fast;
        # image embedding and raster output are covered by the golden-card tests.
        rendered_ids: set[str] = set()
        for card_id, card in self.cards_by_id.items():
            with self.subTest(card_id=card_id):
                svg = renderer.build_card_svg(card, self.profile, None, proof=False)
                self.assertTrue(svg.startswith(b"<?xml"))
                root = ET.fromstring(svg)
                self.assertEqual(root.attrib["data-card-id"], card_id)
                self.assertEqual(
                    root.attrib["data-renderer"],
                    f"dhk-card-renderer/{renderer.RENDERER_VERSION}",
                )
                text_roles = {
                    element.attrib.get("data-role")
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "text"
                }
                self.assertTrue(
                    {"card-title", "card-type", "flavor-text", "footer-brand"}
                    <= text_roles
                )
                if _value(card, "card_type") == "Projekt":
                    self.assertTrue(
                        {"project-goal-text", "project-requirements-text"}
                        <= text_roles
                    )
                else:
                    self.assertIn("rules-text", text_roles)
                rendered_ids.add(card_id)
        self.assertEqual(rendered_ids, set(self.cards_by_id))
        self.assertEqual(len(rendered_ids), 82)

    def test_resolve_artwork_rejects_missing_card(self) -> None:
        with self.assertRaises((renderer.RenderError, FileNotFoundError, ValueError)):
            renderer.resolve_artwork("KAT-X99", ARTWORK_DIR)

    def test_resolve_artwork_enforces_final_3_2_with_legacy_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artwork_dir = Path(directory)
            final_path = artwork_dir / "KAT-X01.png"
            legacy_path = artwork_dir / "KAT-X02.png"
            invalid_path = artwork_dir / "KAT-X03.png"
            Image.new("RGB", (6, 4)).save(final_path)
            Image.new("RGB", (4, 3)).save(legacy_path)
            Image.new("RGB", (5, 4)).save(invalid_path)

            self.assertEqual(
                renderer.resolve_artwork("KAT-X01", artwork_dir, mode="print"),
                final_path,
            )
            self.assertEqual(
                renderer.resolve_artwork("KAT-X02", artwork_dir, mode="preview"),
                legacy_path,
            )
            with self.assertRaisesRegex(renderer.RenderError, r"exakt 3:2"):
                renderer.resolve_artwork("KAT-X02", artwork_dir, mode="print")
            with self.assertRaisesRegex(
                renderer.RenderError, r"3:2 oder als Bestandsvorschau 4:3"
            ):
                renderer.resolve_artwork("KAT-X03", artwork_dir, mode="preview")

    def test_profile_golden_cards_cover_four_rarities_and_three_card_types(self) -> None:
        golden_ids = list(self.profile["golden_card_ids"])
        self.assertEqual(golden_ids, list(GOLDEN_CARDS))

        rarities = set()
        card_types = set()
        for card_id, expected in GOLDEN_CARDS.items():
            card = self.cards_by_id[card_id]
            actual = (_value(card, "rarity"), _value(card, "card_type"))
            self.assertEqual(actual, expected, card_id)
            rarities.add(actual[0])
            card_types.add(actual[1])

        self.assertEqual(rarities, {"common", "uncommon", "rare", "mythic"})
        self.assertEqual(card_types, {"Projekt", "Projektfaktor", "Ereignis"})

    def test_four_golden_svgs_are_self_contained_and_distinct(self) -> None:
        svgs = {}
        for card_id in GOLDEN_CARDS:
            svg = self.build_svg(card_id)
            self.assert_svg_contract(svg, card_id)
            title = _value(self.cards_by_id[card_id], "name")
            self.assertIn(str(title), svg.decode("utf-8"))
            svgs[card_id] = svg

        self.assertEqual(len(set(svgs.values())), len(GOLDEN_CARDS))

    def test_proof_svg_is_explicitly_marked_and_differs_from_print_svg(self) -> None:
        card_id = "KAT-C12"
        print_svg = self.build_svg(card_id, proof=False)
        proof_svg = self.build_svg(card_id, proof=True)
        self.assert_svg_contract(proof_svg, card_id)
        self.assertNotEqual(proof_svg, print_svg)
        proof_text = proof_svg.decode("utf-8").casefold()
        self.assertIn('id="proof-guides"', proof_text)
        self.assertTrue("vorschau" in proof_text or "proof" in proof_text)

        root = ET.fromstring(proof_svg)
        label_positions = {
            element.attrib["data-role"]: (
                int(element.attrib["x"]),
                int(element.attrib["y"]),
                element.attrib["text-anchor"],
            )
            for element in root.iter()
            if element.attrib.get("data-role", "").startswith("proof-label-")
        }
        self.assertEqual(label_positions["proof-label-trim"], (42, 52, "start"))
        self.assertEqual(label_positions["proof-label-vendor_safe"], (750, 82, "end"))
        self.assertEqual(
            label_positions["proof-label-internal_text_safe"],
            (84, 112, "start"),
        )
        self.assertGreaterEqual(
            label_positions["proof-label-internal_text_safe"][1]
            - label_positions["proof-label-vendor_safe"][1],
            24,
        )

        proof_spec = renderer._load_layout()["typography"]["proof_label"]
        proof_step = proof_spec["steps"][0]
        proof_labels = [
            element
            for element in root.iter()
            if element.attrib.get("data-role", "").startswith("proof-label-")
        ]
        self.assertEqual(len(proof_labels), 3)
        for label in proof_labels:
            text = label.text or ""
            self.assertEqual(label.attrib["data-font-role"], proof_spec["font_role"])
            self.assertEqual(float(label.attrib["font-size"]), float(proof_step["size"]))
            self.assertEqual(
                float(label.attrib["data-type-size-step"]), float(proof_step["size"])
            )
            self.assertEqual(
                float(label.attrib["data-line-height"]),
                float(proof_step["line_height"]),
            )
            self.assertEqual(label.attrib["data-type-step-status"], "standard")
            self.assertEqual(label.attrib["font-family"], "Noto Sans")
            self.assertEqual(label.attrib["font-weight"], "700")
            self.assertEqual(
                float(label.attrib.get("letter-spacing", "0")),
                _expected_tracking(text, float(proof_step["size"]), "Noto Sans"),
            )
            self.assertEqual(
                label.attrib.get("font-feature-settings"),
                TABULAR_FIGURE_FEATURES
                if any(character.isdigit() for character in text)
                else None,
            )

    def test_four_golden_pngs_meet_upload_contract(self) -> None:
        for card_id in GOLDEN_CARDS:
            with self.subTest(card_id=card_id):
                self.assert_png_contract(self.build_png(card_id), card_id)

    def test_inspect_png_reports_the_final_file_contract(self) -> None:
        card_id = "KAT-C12"
        png = self.build_png(card_id)
        report = renderer.inspect_png(png)
        self.assertIsInstance(report, Mapping)
        if "valid" in report:
            self.assertIs(report["valid"], True)

        self.assertEqual(int(_report_value(report, "width")), OUTPUT_SIZE[0])
        self.assertEqual(int(_report_value(report, "height")), OUTPUT_SIZE[1])
        self.assertEqual(_report_value(report, "mode", "pixel_model", "color_mode"), "RGB")
        self.assertFalse(bool(_report_value(report, "has_alpha", "alpha")))
        self.assertTrue(bool(_report_value(report, "has_icc_profile", "icc_profile")))
        self.assertEqual(
            int(_report_value(report, "byte_size", "size_bytes", "file_size", "bytes")),
            len(png),
        )

        report_dpi = _report_value(report, "dpi")
        if isinstance(report_dpi, Sequence) and not isinstance(report_dpi, (str, bytes)):
            dpi_x, dpi_y = report_dpi
        else:
            dpi_x = dpi_y = report_dpi
        self.assertAlmostEqual(float(dpi_x), OUTPUT_DPI, delta=0.1)
        self.assertAlmostEqual(float(dpi_y), OUTPUT_DPI, delta=0.1)

    def test_svg_raster_and_final_png_are_byte_deterministic(self) -> None:
        card_id = "KAT-C12"
        artwork = renderer.resolve_artwork(card_id, ARTWORK_DIR)
        first_svg = renderer.build_card_svg(
            self.cards_by_id[card_id], self.profile, artwork, proof=False
        )
        second_svg = renderer.build_card_svg(
            self.cards_by_id[card_id], self.profile, artwork, proof=False
        )
        self.assertEqual(first_svg, second_svg)

        first_raster = renderer.rasterize_svg(first_svg, *OUTPUT_SIZE)
        second_raster = renderer.rasterize_svg(second_svg, *OUTPUT_SIZE)
        self.assertEqual(first_raster, second_raster)

        first_png = renderer.finalize_png(first_raster, self.profile)
        second_png = renderer.finalize_png(second_raster, self.profile)
        self.assertEqual(first_png, second_png)
        self.assert_png_contract(first_png, card_id)

    def test_render_selected_writes_deterministic_named_pngs(self) -> None:
        # API assumption: render_selected is a filesystem orchestration helper
        # with these explicit keyword arguments. Its return value may contain
        # additional manifest/report data and is intentionally not constrained.
        selected = ["KAT-C12"]
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
        ):
            renderer.render_selected(
                profile_path=PROFILE_PATH,
                csv_path=CARDS_PATH,
                artwork_dir=ARTWORK_DIR,
                output_dir=Path(first_dir),
                card_ids=selected,
                proof=False,
            )
            renderer.render_selected(
                profile_path=PROFILE_PATH,
                csv_path=CARDS_PATH,
                artwork_dir=ARTWORK_DIR,
                output_dir=Path(second_dir),
                card_ids=selected,
                proof=False,
            )

            first_png = Path(first_dir, "KAT-C12.png").read_bytes()
            second_png = Path(second_dir, "KAT-C12.png").read_bytes()
            self.assertEqual(first_png, second_png)
            self.assert_png_contract(first_png, "KAT-C12")

    def test_print_mode_rejects_a_layout_that_is_not_final(self) -> None:
        # The canonical layout is released, so the gate is exercised against a
        # copy that is not; pinning the repository to `prototype` would make the
        # test fail the moment the layout it guards is signed off.
        unreleased = dict(renderer._load_layout())
        unreleased["status"] = "prototype"
        with tempfile.TemporaryDirectory() as output_dir:
            with patch.object(renderer, "_load_layout", return_value=unreleased):
                with self.assertRaisesRegex(renderer.RenderError, "Layoutstatus prototype"):
                    renderer.render_selected(
                        profile_path=PROFILE_PATH,
                        csv_path=CARDS_PATH,
                        artwork_dir=ARTWORK_DIR,
                        output_dir=Path(output_dir),
                        card_ids=["KAT-C12"],
                        mode="print",
                    )


if __name__ == "__main__":
    unittest.main()
