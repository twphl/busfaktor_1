"""Print the Python renderer's SVG for every canonical card as JSON.

Used by check_renderer_parity.mjs. Artwork is left out on both sides, so the
comparison covers the placeholder branch plus every text and geometry rule.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_cards as rc  # noqa: E402

profile = rc.load_profile()
cards = rc.load_cards()
json.dump(
    {card['card_id']: rc.build_card_svg(card, profile, None).decode('utf-8') for card in cards},
    sys.stdout,
    ensure_ascii=False,
)
