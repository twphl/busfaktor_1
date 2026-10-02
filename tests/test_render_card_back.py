"""Contract tests for the card back.

The back has one property the front does not need and must never lose: a card
lying face down must not betray which way round it is.  Finding 5.1 of the panel
review caught exactly that.  The tests below pin the fix at both levels — the
drawing that guarantees it, and the raster it produces.
"""

from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_card_back as back  # noqa: E402
from render_cards import (  # noqa: E402
    INNER_CARD_FIELD_INSET,
    finalize_png,
    load_profile,
    rasterize_svg,
)

SVG_NS = "http://www.w3.org/2000/svg"

# Sub-pixel antialiasing is the only asymmetry the rasteriser may introduce: a
# glyph and its 180-degree twin round their coverage differently.  The deltas it
# produces are edge-local, so they wash out as soon as the image is resampled.
# A structural asymmetry — a shifted or missing line — would survive that and
# push the full-resolution delta towards 246, the ink-on-black contrast.
#
# A single sharp vertex (a lozenge tip, a ring-lettering serif) can hit that
# same ink-on-black delta at the one pixel straddling its point, purely because
# the twin's rotation lands its point at a different sub-pixel phase.  That is
# still antialiasing, not a structural asymmetry — the tell is how many pixels
# it touches.  A shifted or missing line darkens or lightens a run of pixels
# along its whole length, not a handful at isolated vertices, so a small budget
# of outliers is where the vertex case and the structural case actually part.
MAX_ASYMMETRIC_PIXEL_SHARE = 0.05
MAX_ASYMMETRIC_CHANNEL_DELTA = 96
MAX_ASYMMETRIC_CHANNEL_DELTA_OUTLIERS = 8
MAX_ASYMMETRIC_CHANNEL_DELTA_RESAMPLED = 32
RESAMPLE_FACTOR = 4


def _qualified(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


class CardBackContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_profile()
        cls.svg_bytes = back.build_back_svg(cls.profile)
        cls.root = ET.fromstring(cls.svg_bytes)
        output = cls.profile["upload_png"]
        cls.png_bytes = finalize_png(
            rasterize_svg(cls.svg_bytes, output["width"], output["height"]), cls.profile
        )
        cls.rectangles = cls.profile["master_svg"]["rectangles"]
        cls.layout = back._load_layout()
        vendor_safe = cls.rectangles["vendor_safe"]
        cls.geometry = back._band_geometry(
            back._resolve_fonts(),
            cls.profile["master_svg"]["view_box"],
            {
                "x": vendor_safe["x"] + INNER_CARD_FIELD_INSET,
                "y": vendor_safe["y"] + INNER_CARD_FIELD_INSET,
                "width": vendor_safe["width"] - 2 * INNER_CARD_FIELD_INSET,
                "height": vendor_safe["height"] - 2 * INNER_CARD_FIELD_INSET,
            },
            cls.rectangles["internal_text_safe"],
        )

    def _halves(self, role: str) -> list[ET.Element]:
        return [
            element
            for element in self.root.iter(_qualified("g"))
            if element.get("data-role") == role
        ]

    def _runs(self) -> list[ET.Element]:
        return [
            element
            for element in self.root.iter(_qualified("text"))
            if element.get("data-role") == "band-run"
        ]

    def test_each_half_carries_the_same_number_of_lines(self) -> None:
        self.assertGreaterEqual(self.geometry["half_lines"], 1)
        self.assertEqual(len(self._runs()), 2 * self.geometry["half_lines"])

    def test_no_run_begins_or_ends_inside_the_field(self) -> None:
        """The clip has to be the only thing that ever cuts a term.

        A run that stopped short would read as a wrapped paragraph instead of as
        an endless texture, which is the whole point of the setting.
        """

        clip = self.geometry["clip_box"]
        for element in self._runs():
            start = float(element.get("x"))
            width = float(element.get("data-run-width"))
            with self.subTest(line=element.get("data-line")):
                self.assertLessEqual(
                    start, clip["left"], "die Zeile beginnt im sichtbaren Feld"
                )
                self.assertGreaterEqual(
                    start + width, clip["right"], "die Zeile endet im sichtbaren Feld"
                )

    def test_text_keeps_its_distance_from_the_frame(self) -> None:
        """The cut is meant to happen — just not on the drawn hairline.

        The clip runs parallel to the frame, one padding inside it, so a line end
        never lands on the line itself.
        """

        geometry = self.geometry
        box, clip = geometry["box"], geometry["clip_box"]
        self.assertGreater(geometry["padding"], back.FRAME_HAIRLINE_STROKE_WIDTH / 2)
        for edge, sign in (("left", 1), ("top", 1), ("right", -1), ("bottom", -1)):
            with self.subTest(edge=edge):
                self.assertAlmostEqual(
                    sign * (clip[edge] - box[edge]), geometry["padding"], delta=0.001
                )
        # A uniform offset costs the chamfer more than it costs the sides; keeping
        # the chamfer would tilt the clip away from the frame at the corners.
        self.assertLess(geometry["clip_chamfer"], back.FRAME_CHAMFER)

    def test_outer_line_is_not_shaved_by_the_frame(self) -> None:
        """``y`` is a baseline, so it is the cap top that has to clear the line.

        Spacing the lines on a fixed pitch leaves this to chance: at some sizes
        the outer line lands a fraction of a unit inside the frame and gets
        shaved.  The rhythm is solved against this, and this is the check.
        """

        geometry = self.geometry
        cap_top = min(geometry["baselines"]) - geometry["cap_rise"]
        # Against the clip, because that is what actually cuts, and it now sits
        # inside the frame.  Solving against the frame instead would shave the
        # outer line by exactly the padding.
        self.assertGreater(
            cap_top,
            geometry["clip_box"]["top"],
            "die äußerste Zeile wird vom Feldrand angeschnitten",
        )
        # Solving the pitch must not drag it far off the intended rhythm.
        target = back.PATTERN_SIZE * back.PATTERN_PITCH_RATIO
        self.assertLess(abs(geometry["pitch"] - target) / target, 0.2)

    def test_type_never_gets_louder_than_the_fronts_footer(self) -> None:
        """One sentence closes the loudness question: nothing outshouts the front.

        The front sets its card identity at 14 layout units, which is the largest
        thing it prints on anthracite.  The back's running text has to stay at or
        below that, converted into master units.
        """

        layout = self.layout["geometry"]["document"]
        scale = self.profile["master_svg"]["view_box"][2] / layout["width"]
        ceiling = back._typography_steps(self.layout, "footer_identity")[0][0] * scale
        # Every type size on the back, not just the running text: the seal used
        # to sit above this ceiling while the rule claimed otherwise.
        for name, size in (
            ("Laufsatz", back.PATTERN_SIZE),
            ("Siegelumschrift", back.SEAL_RING_TEXT_SIZE),
        ):
            with self.subTest(size=name):
                self.assertLessEqual(size, ceiling + 0.001)
        self.assertEqual(back.PATTERN_COLOR_TOKEN, "text/on-dark-muted")

    def test_seal_says_something_the_field_cannot(self) -> None:
        """An inscription that repeats the ground it sits on is a seal saying nothing."""

        overlap = set(back.SEAL_RING_TERMS) & set(back.PATTERN_TERMS)
        self.assertEqual(
            overlap, set(), f"die Umschrift wiederholt Begriffe aus dem Feld: {overlap}"
        )

    def test_inscription_fits_half_the_ring(self) -> None:
        """It has to be complete within half a turn, or the half turn breaks it."""

        radius = back.SEAL_RADIUS * back.SEAL_RING_TEXT_RADIUS_RATIO
        _, scale = back._seal_ring_run(back._resolve_fonts(), radius, back.SEAL_RING_TEXT_SIZE)
        low, high = back.SEAL_RING_TRACKING_BAND
        self.assertGreaterEqual(scale, low)
        self.assertLessEqual(scale, high)

    def test_every_symmetric_role_is_one_half_and_its_half_turn(self) -> None:
        """The lower half must be the upper half's drawing, only transformed."""

        view_box = self.profile["master_svg"]["view_box"]
        expected = f"rotate(180 {view_box[2] / 2:g} {view_box[3] / 2:g})"
        for role in ("back-band-half", "seal-ring-half", "seal-head-half", "frame-corner-half"):
            halves = self._halves(role)
            with self.subTest(role=role):
                self.assertEqual(len(halves), 2, f"{role} ist nicht als zwei Hälften gebaut")
                authored, half_turn = halves
                self.assertEqual(authored.get("data-symmetry-half"), "authored")
                self.assertEqual(half_turn.get("data-symmetry-half"), "half-turn")
                self.assertIsNone(authored.get("transform"))
                self.assertEqual(half_turn.get("transform"), expected)
                self.assertEqual(
                    [ET.tostring(child) for child in authored],
                    [ET.tostring(child) for child in half_turn],
                    f"{role}: die beiden Hälften zeichnen nicht dasselbe",
                )

    def test_rasterised_back_equals_its_own_half_turn(self) -> None:
        """The printed side itself, not just its source, must be point-symmetric."""

        import io

        with Image.open(io.BytesIO(self.png_bytes)) as image:
            card = image.convert("RGB")
        difference = ImageChops.difference(card, card.rotate(180)).convert("L")
        histogram = difference.histogram()
        differing = sum(histogram[1:])
        total = card.width * card.height
        outliers = sum(histogram[MAX_ASYMMETRIC_CHANNEL_DELTA + 1 :])
        self.assertLess(
            differing / total,
            MAX_ASYMMETRIC_PIXEL_SHARE,
            f"{differing} von {total} Pixeln sind nicht punktsymmetrisch",
        )
        self.assertLessEqual(
            outliers,
            MAX_ASYMMETRIC_CHANNEL_DELTA_OUTLIERS,
            f"{outliers} Pixel weichen zu stark für reines Antialiasing ab "
            "— zu viele für einzelne Spitzen, das sieht nach einer "
            "verschobenen oder fehlenden Linie aus",
        )
        # The decisive check: resampled below the antialiasing scale, the two
        # orientations have to converge.  A displaced line would not.
        small = card.resize(
            (card.width // RESAMPLE_FACTOR, card.height // RESAMPLE_FACTOR),
            Image.LANCZOS,
        )
        resampled = ImageChops.difference(small, small.rotate(180)).convert("L")
        self.assertLessEqual(
            max(value for value, count in enumerate(resampled.histogram()) if count),
            MAX_ASYMMETRIC_CHANNEL_DELTA_RESAMPLED,
            "Rückseite ist auch jenseits des Antialiasings nicht punktsymmetrisch",
        )

    def test_card_centre_is_shared_by_bleed_trim_and_inner_field(self) -> None:
        view_box = self.profile["master_svg"]["view_box"]
        trim = self.rectangles["trim"]
        vendor_safe = self.rectangles["vendor_safe"]
        inner = {
            "x": vendor_safe["x"] + INNER_CARD_FIELD_INSET,
            "y": vendor_safe["y"] + INNER_CARD_FIELD_INSET,
            "width": vendor_safe["width"] - 2 * INNER_CARD_FIELD_INSET,
            "height": vendor_safe["height"] - 2 * INNER_CARD_FIELD_INSET,
        }
        for box in (trim, inner):
            self.assertAlmostEqual(box["x"] + box["width"] / 2, view_box[2] / 2, places=6)
            self.assertAlmostEqual(box["y"] + box["height"] / 2, view_box[3] / 2, places=6)

    def _hairline(self) -> ET.Element:
        return next(
            element
            for element in self.root.iter(_qualified("path"))
            if element.get("data-role") == "inner-frame-hairline"
        )

    def test_hairline_stroke_stays_inside_the_internal_dhk_safe(self) -> None:
        hairline = self._hairline()
        safe = self.rectangles["internal_text_safe"]
        half_stroke = float(hairline.get("stroke-width")) / 2
        left = float(hairline.get("data-box-left")) - half_stroke
        top = float(hairline.get("data-box-top")) - half_stroke
        right = float(hairline.get("data-box-right")) + half_stroke
        bottom = float(hairline.get("data-box-bottom")) + half_stroke
        self.assertGreaterEqual(left, safe["x"] - 0.001)
        self.assertGreaterEqual(top, safe["y"] - 0.001)
        self.assertLessEqual(right, safe["x"] + safe["width"] + 0.001)
        self.assertLessEqual(bottom, safe["y"] + safe["height"] + 0.001)
        # The requested extra inset really is extra, not absorbed by the stroke.
        self.assertAlmostEqual(left - safe["x"], back.FRAME_HAIRLINE_INSET, delta=0.001)

    def test_frame_corners_carry_one_ornament_each(self) -> None:
        ornaments = [
            element
            for element in self.root.iter(_qualified("g"))
            if element.get("data-role") == "frame-corner-ornament"
        ]
        self.assertEqual(len(ornaments), 4)
        self.assertEqual(
            {element.get("data-corner") for element in ornaments},
            {"top-left", "top-right"},
            "die unteren Ecken müssen die gedrehten Kopien der oberen sein",
        )

    def test_corner_ornaments_sit_on_the_chamfer_breaks(self) -> None:
        """The frame has to open exactly where an ornament sits, not elsewhere."""

        segments = self._hairline().get("d").count("M ")
        self.assertEqual(segments, 4 + 2 * 4, "vier Kanten plus zwei Stummel je Ecke")

    def test_artwork_carries_the_cards_own_paper(self) -> None:
        """Inside the seal the head sits on paper, so it must wear the front's paper."""

        import base64
        import io
        import re
        from collections import Counter

        payload = re.search(
            r'href="data:image/png;base64,([^"]+)"', self.svg_bytes.decode("utf-8")
        ).group(1)
        with Image.open(io.BytesIO(base64.b64decode(payload))) as embedded:
            artwork = embedded.convert("RGBA")
        counts: Counter = Counter()
        for y in range(0, artwork.height, 2):
            for x in range(0, artwork.width, 2):
                red, green, blue, alpha = artwork.getpixel((x, y))
                if alpha > 250 and red > 200:
                    counts[(red, green, blue)] += 1
        dominant = counts.most_common(1)[0][0]
        expected = back._color(self.layout, back.SEAL_ART_LIGHT_TOKEN)
        target = tuple(int(expected[index : index + 2], 16) for index in (1, 3, 5))
        for actual, wanted in zip(dominant, target):
            self.assertAlmostEqual(actual, wanted, delta=2)

    def test_frame_line_is_continuous_apart_from_the_corner_breaks(self) -> None:
        """Nothing crosses the hairline any more, so nothing may cut it either.

        The running text is held inside the field the frame encloses, which is
        what lets the line stay whole instead of dashed.
        """

        self.assertIsNone(self._hairline().get("mask"), "die Rahmenlinie wird noch maskiert")
        stray = [
            element
            for element in self.root.iter()
            if (element.get("data-role") or "").startswith("hairline-gap")
        ]
        self.assertEqual(stray, [], "es gibt noch Korridore, die die Rahmenlinie öffnen")

    def test_lines_are_held_inside_the_anthracite(self) -> None:
        """The band field is clipped by the frame field, never by the trim."""

        fields = [
            element
            for element in self.root.iter(_qualified("g"))
            if element.get("data-role") == "back-band-field"
        ]
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].get("clip-path"), f"url(#{back.FIELD_CLIP_ID})")
        clip = next(
            element
            for element in self.root.iter(_qualified("clipPath"))
            if element.get("id") == back.FIELD_CLIP_ID
        )
        outline = next(iter(clip)).get("d")
        self.assertEqual(
            outline,
            back._frame_field_path(
                self.geometry["clip_box"], self.geometry["clip_chamfer"]
            ),
        )

    def test_seal_sits_at_the_card_centre_and_carries_two_heads(self) -> None:
        """A face with no upright needs a double-headed figure, like a court card."""

        heads = [
            element
            for element in self.root.iter(_qualified("use"))
            if element.get("data-role") == "seal-head"
        ]
        self.assertEqual(len(heads), 2, "das Siegel trägt nicht genau zwei Köpfe")
        view_box = self.profile["master_svg"]["view_box"]
        for role, radius in (
            ("seal-rim", back.SEAL_RADIUS),
            ("seal-field", back.SEAL_RADIUS * back.SEAL_INNER_RADIUS_RATIO),
        ):
            shape = next(
                element
                for element in self.root.iter(_qualified("ellipse"))
                if element.get("data-role") == role
            )
            with self.subTest(role=role):
                self.assertAlmostEqual(float(shape.get("cx")), view_box[2] / 2, places=6)
                self.assertAlmostEqual(float(shape.get("cy")), view_box[3] / 2, places=6)
                self.assertAlmostEqual(float(shape.get("rx")), radius, places=6)
                self.assertAlmostEqual(float(shape.get("ry")), radius, places=6)

    def test_seal_stays_clear_of_the_frame(self) -> None:
        geometry = self.geometry
        reach = back.SEAL_RADIUS + geometry["padding"] * back.SEAL_KNOCKOUT_PADDING_RATIO
        clip = geometry["clip_box"]
        self.assertLess(reach, (clip["right"] - clip["left"]) / 2)
        self.assertLess(reach, (clip["bottom"] - clip["top"]) / 2)
        knockout = next(
            element
            for element in self.root.iter(_qualified("ellipse"))
            if element.get("data-role") == "seal-knockout"
        )
        self.assertAlmostEqual(float(knockout.get("rx")), reach, places=6)
        self.assertGreater(reach, back.SEAL_RADIUS, "das Siegel hat keinen Hof")

    def test_svg_is_self_contained(self) -> None:
        text = self.svg_bytes.decode("utf-8")
        for forbidden in ("http://", "https://", "file:", "<filter", "feTurbulence"):
            if forbidden in ("http://", "https://"):
                self.assertNotIn(f'href="{forbidden}', text)
            else:
                self.assertNotIn(forbidden, text)

    def test_render_is_byte_deterministic(self) -> None:
        again = back.build_back_svg(self.profile)
        self.assertEqual(again, self.svg_bytes)
        output = self.profile["upload_png"]
        self.assertEqual(
            finalize_png(rasterize_svg(again, output["width"], output["height"]), self.profile),
            self.png_bytes,
        )

    def test_png_meets_the_upload_contract(self) -> None:
        report = back.inspect_png(self.png_bytes, self.profile)
        self.assertEqual(report["size"], [1644, 2244])
        self.assertEqual(report["mode"], "RGB")
        self.assertFalse(report["has_alpha"])
        self.assertTrue(report["icc_profile"])
        # pHYs stores pixels per metre as an integer, so 600 dpi lands a hair off.
        for axis in report["dpi"]:
            self.assertAlmostEqual(axis, 600.0, delta=1.0)

    def test_tei_and_xml_never_land_next_to_each_other(self) -> None:
        """They are two separate things and must not read back as TEI-XML.

        Every line walks the same cycle from a different starting point, so
        adjacency is a property of the list order alone — including the wrap.
        """

        terms = back.PATTERN_TERMS
        count = len(terms)
        first, second = terms.index("TEI"), terms.index("XML")
        distance = min(abs(first - second), count - abs(first - second))
        self.assertGreater(distance, 1, "TEI und XML stehen zyklisch nebeneinander")

    def test_vocabulary_is_uppercase_and_free_of_duplicates(self) -> None:
        self.assertEqual(len(set(back.PATTERN_TERMS)), len(back.PATTERN_TERMS))
        for term in back.PATTERN_TERMS:
            with self.subTest(term=term):
                self.assertEqual(term, term.upper())
                self.assertTrue(term.strip())


if __name__ == "__main__":
    unittest.main()
