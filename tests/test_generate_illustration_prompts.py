import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_illustration_prompts.py"
SPEC = importlib.util.spec_from_file_location("generate_illustration_prompts", SCRIPT)
assert SPEC and SPEC.loader
PROMPTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROMPTS)


class GenerateIllustrationPromptsTest(unittest.TestCase):
    def test_generates_all_prompts_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            count = PROMPTS.generate_prompts(
                ROOT / "data" / "cards.csv",
                ROOT / "prompts" / "illustration-template.md",
                output_dir,
            )

            self.assertEqual(count, 82)
            prompt_files = sorted(output_dir.glob("KAT-*.txt"))
            self.assertEqual(len(prompt_files), 82)

            masterprompt = PROMPTS.extract_masterprompt(
                ROOT / "prompts" / "illustration-template.md"
            )
            self.assertTrue(
                masterprompt.startswith("Create a horizontal 3:2 source illustration")
            )
            self.assertIn(
                "The final card fills a centered 3:2 window", masterprompt
            )
            first_prompt = (output_dir / "KAT-C01.txt").read_text(encoding="utf-8")
            self.assertTrue(
                first_prompt.startswith(
                    masterprompt + "\n\nSemantic context for image selection only."
                )
            )
            self.assertIn('Card title: "SHK mit Adminrechten"', first_prompt)
            self.assertIn("Flavor text:", first_prompt)
            self.assertIn("\n\nSzene:", first_prompt)

            with (output_dir / "manifest.csv").open(encoding="utf-8", newline="") as handle:
                manifest = list(csv.DictReader(handle))
            self.assertEqual(len(manifest), 82)
            self.assertEqual(manifest[0]["filename"], "KAT-C01.txt")


if __name__ == "__main__":
    unittest.main()
