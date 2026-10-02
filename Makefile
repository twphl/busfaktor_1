.PHONY: validate collate prompts cards cards-goldens cards-proof cards-back cards-back-proof cards-blank cards-test cards-a4 print-run print-run-draft rulebook rulebook-10x15 clean website website-parity website-game website-game-ui website-serve

DHK_UV_CACHE ?= /tmp/dhk-tcg-uv-cache
# Auflagenprofil aus data/print_runs (ADR 0019). Der 612er-Plan bleibt
# ausführbar: make collate DHK_PRINT_RUN=612-plus-18
DHK_PRINT_RUN ?= 234-plus-18

validate:
	python3 scripts/validate_cards.py --print-run $(DHK_PRINT_RUN)

collate: validate
	python3 scripts/collate_boosters.py --seed 20260804 --print-run $(DHK_PRINT_RUN)

prompts: validate
	python3 scripts/generate_illustration_prompts.py

cards-goldens: validate
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_cards.py --output build/cards-preview

cards: validate
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_cards.py --all --output build/cards-preview

cards-proof: validate
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_cards.py --proof --output build/cards-proof

cards-back:
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_card_back.py --output build/card-back

cards-back-proof:
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_card_back.py --proof --output build/card-back-proof

cards-blank:
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_blank_cards.py --output build/cards-blank

print-run: collate
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/export_print_run.py --print-run $(DHK_PRINT_RUN) --output build/print-run

print-run-draft: collate
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/export_print_run.py --print-run $(DHK_PRINT_RUN) --draft --output build/print-run-draft

# Alle Kartenmotive einmal auf A4, unabhaengig von den Auflagenmengen.
cards-a4: validate
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_print_and_play.py

cards-test:
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python -m unittest tests.test_render_cards tests.test_render_card_back -v

# Regelheft aus docs/10-spielregeln.md: Lesefolge zum Pruefen, Druckbogen im
# Rueckstich. §18 steht auf der Umschlagrueckseite. DHK_RULEBOOK_ARGS reicht
# weitere Schalter durch, etwa:
#   make rulebook DHK_RULEBOOK_ARGS="--duplex"        Vorderseiten und Rueck-
#                                                     seiten in beiden Reihen-
#                                                     folgen, fuer den Druck
#                                                     von Hand
#   make rulebook DHK_RULEBOOK_ARGS="--kalibrierung"  zwei Testblaetter, die
#                                                     Wendeart und Reihenfolge
#                                                     des Druckers zeigen
rulebook:
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_rulebook.py $(DHK_RULEBOOK_ARGS)

# Dasselbe Heft auf 100 x 150 mm, Dateien build/regelheft/regelheft-10x15-*.
rulebook-10x15:
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python scripts/render_rulebook.py --format 10x15 $(DHK_RULEBOOK_ARGS)

clean:
	rm -f build/boosters-*.csv build/booster-summary-*.json
	rm -rf build/illustration-prompts build/review
	rm -rf build/cards-preview build/cards-proof build/cards-print build/card-back build/card-back-proof
	rm -rf build/cards-blank build/print-run build/print-run-draft build/regelheft

# Website mit Kartengenerator: Assets übernehmen und Rendererdaten aus
# scripts/render_cards.py exportieren (website/renderer-data.js).
website: validate
	env UV_CACHE_DIR=$(DHK_UV_CACHE) uv run python website/prepare.py

# Vergleicht website/renderer.js im Browser mit dem Python-Renderer, alle Karten.
# Braucht Node und Playwright; PLAYWRIGHT_MODULE und CHROMIUM_PATH überschreiben
# die Fundorte.
website-parity:
	env UV_CACHE_DIR=$(DHK_UV_CACHE) DHK_PYTHON="uv run python" node website/tests/check_renderer_parity.mjs

# Regeln der Browser-Partie: Engine, Bots und die maskierte Netzsicht
# (website/game-engine.js) gegen docs/10-spielregeln.md. Braucht nur Node.
website-game:
	node --test website/tests/

# Spielt spielen.html in Chromium durch: allein gegen Bots, zu zweit an einem
# Gerät und einmal mit Neuladen. Braucht Node und Playwright; PLAYWRIGHT_MODULE
# und CHROMIUM_PATH überschreiben die Fundorte.
website-game-ui:
	node website/tests/check_game_ui.mjs

website-serve:
	python3 -m http.server 8000 --directory website


