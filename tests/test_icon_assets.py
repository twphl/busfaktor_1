"""Contracts for the pinned Phosphor icon assets and semantic registry."""

from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts import render_cards as renderer


ROOT = Path(__file__).resolve().parents[1]
ICON_ROOT = ROOT / "data" / "assets" / "icons"
MANIFEST_PATH = ICON_ROOT / "manifest.json"

EXPECTED_PHOSPHOR = {
    "team": ("UsersThree",),
    "data": ("Database",),
    "operations": ("GearSix",),
    "methods": ("ListChecks",),
    "joker": ("Asterisk",),
    "project": ("FolderOpen",),
    "project_factor": ("FolderOpen", "SlidersHorizontal"),
    "event": ("Lightning",),
    "inspect": ("Eye",),
    "draw": ("CardsThree",),
    "retrieve": ("ArrowCounterClockwise",),
    "redistribute": ("ArrowsLeftRight",),
    "positive": ("TrendUp",),
    "negative": ("TrendDown",),
    "ambivalent": ("Scales",),
    "rarity": ("Seal",),
    "project_seal": ("Stamp",),
    "booster_band": ("CardsThree", "TagSimple"),
    "cooperation": ("Handshake",),
    "extra_effort": ("HourglassMedium",),
    "safeguard": ("ShieldCheck",),
    "wildcard_choice": ("Asterisk", "CheckCircle"),
}

EXPECTED_BASE_FILES = {
    "arrow-counter-clockwise-bold.svg",
    "arrows-left-right-bold.svg",
    "asterisk-bold.svg",
    "cards-three-bold.svg",
    "check-circle-bold.svg",
    "database-bold.svg",
    "eye-bold.svg",
    "folder-open-bold.svg",
    "gear-six-bold.svg",
    "handshake-bold.svg",
    "hourglass-medium-bold.svg",
    "lightning-bold.svg",
    "list-checks-bold.svg",
    "scales-bold.svg",
    "seal-bold.svg",
    "shield-check-bold.svg",
    "sliders-horizontal-bold.svg",
    "stamp-bold.svg",
    "tag-simple-bold.svg",
    "trend-down-bold.svg",
    "trend-up-bold.svg",
    "users-three-bold.svg",
}


class IconAssetContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_pins_library_and_all_22_semantic_roles(self) -> None:
        self.assertEqual(self.manifest["schema"], "dhk-icon-manifest/v1")
        self.assertEqual(
            self.manifest["library"],
            {
                "name": "Phosphor Icons",
                "package": "@phosphor-icons/core",
                "version": "2.1.1",
                "weight": "bold",
                "license": "MIT",
                "license_file": "phosphor/LICENSE.phosphor.txt",
                "source": "https://registry.npmjs.org/@phosphor-icons/core/-/core-2.1.1.tgz",
            },
        )
        self.assertEqual(set(self.manifest["icons"]), set(EXPECTED_PHOSPHOR))
        self.assertEqual(set(self.manifest["icons"]), set(renderer.ICON_KEYS))
        self.assertEqual(len(self.manifest["icons"]), 22)
        self.assertEqual(
            {
                key: tuple(specification["phosphor"])
                for key, specification in self.manifest["icons"].items()
            },
            EXPECTED_PHOSPHOR,
        )

    def test_exact_22_bold_upstream_files_and_mit_license_are_present(self) -> None:
        base_dir = ICON_ROOT / "phosphor" / "2.1.1" / "bold"
        self.assertEqual({path.name for path in base_dir.glob("*.svg")}, EXPECTED_BASE_FILES)
        self.assertEqual(len(EXPECTED_BASE_FILES), 22)
        license_text = (ICON_ROOT / "phosphor" / "LICENSE.phosphor.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("MIT License", license_text)
        self.assertIn("Copyright (c) 2023 Phosphor Icons", license_text)

    def test_every_registered_svg_is_local_allowlisted_and_self_contained(self) -> None:
        for icon_key, specification in self.manifest["icons"].items():
            with self.subTest(icon=icon_key):
                relative = Path(specification["file"])
                self.assertFalse(relative.is_absolute())
                path = (ICON_ROOT / relative).resolve()
                path.relative_to(ICON_ROOT.resolve())
                raw = path.read_bytes()
                self.assertNotIn(b"<!DOCTYPE", raw.upper())
                root = ET.fromstring(raw)
                self.assertEqual(root.tag.rsplit("}", 1)[-1], "svg")
                self.assertEqual(root.attrib, {"viewBox": "0 0 256 256", "fill": "currentColor"})
                paths = [
                    element
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "path"
                ]
                self.assertGreaterEqual(len(paths), 1)
                for element in root.iter():
                    local_name = element.tag.rsplit("}", 1)[-1]
                    self.assertIn(local_name, {"svg", "g", "path"})
                    for attribute, value in element.attrib.items():
                        self.assertNotIn(attribute.rsplit("}", 1)[-1], {"href", "src", "style"})
                        self.assertNotIn("url(", value.casefold())
                        self.assertNotIn("javascript:", value.casefold())

    def test_three_composites_are_fixed_two_path_assets(self) -> None:
        expected = {
            "project_factor": "composites/projektfaktor.svg",
            "booster_band": "composites/boosterbanderole.svg",
            "wildcard_choice": "composites/wildcard-wahl.svg",
        }
        for icon_key, relative_path in expected.items():
            with self.subTest(icon=icon_key):
                self.assertEqual(self.manifest["icons"][icon_key]["file"], relative_path)
                root = ET.parse(ICON_ROOT / relative_path).getroot()
                paths = [
                    element
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "path"
                ]
                self.assertEqual(len(paths), 2)

    def test_renderer_can_inline_every_role_with_hash_metadata(self) -> None:
        for icon_key in sorted(EXPECTED_PHOSPHOR):
            with self.subTest(icon=icon_key):
                children, metadata = renderer._load_icon_asset(icon_key)
                self.assertGreaterEqual(len(children), 1)
                self.assertEqual(metadata["icon"], icon_key)
                self.assertEqual(metadata["library"], "Phosphor Icons")
                self.assertEqual(metadata["version"], "2.1.1")
                self.assertEqual(metadata["weight"], "bold")
                self.assertRegex(metadata["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
