#!/usr/bin/env python3
"""Monte-Carlo-Auswertungen für das Bühnenspiel KAT-01.

Alle Zahlen entstehen aus `data/cards.csv` und den Testregeln in
`docs/10-spielregeln.md`. Ausgabe ist Markdown.

Beispiele:

    python3 scripts/simulate.py set
    python3 scripts/simulate.py tournament --games 2000
    python3 scripts/simulate.py variants --games 3000
    python3 scripts/simulate.py handlimit --games 3000
    python3 scripts/simulate.py projects --games 3000
    python3 scripts/simulate.py repeats --games 3000
    python3 scripts/simulate.py coop --games 3000
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sim.deck import (  # noqa: E402
    FAMILIES,
    REPEAT_POLICIES,
    build_stage_set,
    draw_cost,
)
from scripts.sim.engine import GameResult, play_game  # noqa: E402
from scripts.sim.rules import RULE_VARIANTS, Rules  # noqa: E402
from scripts.sim.strategies import OPEN_NAMES, STRATEGIES, make_strategy  # noqa: E402


# --------------------------------------------------------------------- Läufe


def build_strategies(names: list[str], seed: int) -> list:
    strategies = []
    for index, name in enumerate(names):
        strategy = make_strategy(name)
        if hasattr(strategy, "rng"):
            strategy.rng = random.Random(seed * 977 + index)
        strategies.append(strategy)
    return strategies


def _play(args) -> GameResult:
    rules, names, seed = args
    return play_game(rules, build_strategies(list(names), seed), seed)


def run_games(rules: Rules, names: list[str], games: int, seed: int, jobs: int) -> list[GameResult]:
    if len(names) != rules.players:
        names = (names * rules.players)[: rules.players]
    payload = [(rules, tuple(names), seed + index) for index in range(games)]
    if jobs > 1:
        with Pool(jobs) as pool:
            return pool.map(_play, payload, chunksize=max(1, games // (jobs * 8)))
    return [_play(item) for item in payload]


@dataclass
class Cell:
    mean: float
    sd: float
    minus: float
    negative_share: float
    forced_share: float
    painful: float
    first_start: float
    completion: float
    steals: float
    options: float
    reshuffles: float


def summarize(results: list[GameResult], rules: Rules, names: set[str] | None = None) -> Cell:
    scores, minus, first, forced, painful, steals, options = [], [], [], [], [], [], []
    started = completed = 0
    for result in results:
        for player in result.players:
            if names is not None and player.strategy not in names:
                continue
            scores.append(player.score)
            minus.append(player.minus)
            first.append(player.first_start_round or rules.rounds + 1)
            forced.append(player.forced_discards)
            painful.append(player.painful_discards)
            steals.append(player.steals)
            options.append(player.mean_options)
            started += len(player.completed) + len(player.unfinished)
            completed += len(player.completed)
    turns = rules.rounds
    return Cell(
        mean=statistics.fmean(scores),
        sd=statistics.pstdev(scores) if len(scores) > 1 else 0.0,
        minus=statistics.fmean(minus),
        negative_share=sum(1 for value in scores if value < 0) / len(scores),
        forced_share=statistics.fmean(forced) / turns,
        painful=statistics.fmean(painful),
        first_start=statistics.median(first),
        completion=completed / started if started else 0.0,
        steals=statistics.fmean(steals),
        options=statistics.fmean(options),
        reshuffles=statistics.fmean([result.reshuffles for result in results]),
    )


def best_open(rules: Rules, games: int, seed: int, jobs: int) -> tuple[str, Cell]:
    """Bestes der vier offenen Selbstspiel-Profile (Methodik des Panels)."""

    best: tuple[str, Cell] | None = None
    for name in OPEN_NAMES:
        cell = summarize(run_games(rules, [name], games, seed, jobs), rules)
        if best is None or cell.mean > best[1].mean:
            best = (name, cell)
    assert best is not None
    return best


def skill_gap(rules: Rules, open_name: str, games: int, seed: int, jobs: int) -> float:
    """Sieganteil gutes Spiel minus Zufallsspiel in Prozentpunkten (2 gegen 2)."""

    if rules.players < 4:
        return float("nan")
    names = [open_name, "random"] * (rules.players // 2)
    names = names[: rules.players]
    results = run_games(rules, names, games, seed + 500_000, jobs)
    wins: Counter[str] = Counter()
    for result in results:
        winners = result.winners
        for index in winners:
            wins[result.players[index].strategy] += 1 / len(winners)
    good = wins[open_name] / len(results)
    weak = wins["random"] / len(results)
    seats = Counter(names)
    return 100 * (good / seats[open_name] - weak / seats["random"])


# ------------------------------------------------------------------ Ausgabe


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def num(value: float, digits: int = 2) -> str:
    if value != value:  # NaN
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")


def pct(value: float, digits: int = 1) -> str:
    return num(100 * value, digits) + " %"


def emit(payload: dict, args) -> None:
    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), "utf-8")
        print(f"\nJSON geschrieben: {args.json}")


# ---------------------------------------------------------------- Kommandos


def cmd_set(args) -> None:
    print(f"# Bühnensatz (Wiederholungspolicy: {args.repeats})\n")
    stage = build_stage_set(args.repeats)
    families = stage.family_counts()
    print(
        f"- {len(stage.projects)} Projekte, {len(stage.factors)} Projektfaktoren, "
        f"{len(stage.events)} Ereignisse = {len(stage.projects) + len(stage.actions)} Karten"
    )
    print(f"- Faktortypen: {dict(families)}")
    demand = Counter(
        req for card in stage.projects for req in card.defn.requirements
    )
    print(f"- Anforderungen der 16 Projekte: {dict(demand)}")
    repeats = Counter(stage.repeated_ids)
    print(f"- doppelte Faktormotive ({sum(repeats.values())}): {dict(repeats)}")
    if stage.unsupported:
        print(f"- nicht simulierte Ereignisse: {', '.join(stage.unsupported)}")
    print(
        "\nHinweis: Welche acht Faktoren im gedruckten Bühnensatz doppelt liegen, "
        "ist in `data/` nicht hinterlegt (Befund 19 der Panel-Review). Die Policy "
        "macht die Annahme explizit."
    )


def cmd_tournament(args) -> None:
    rules = rules_from(args)
    names = args.strategies.split(",")
    results = run_games(rules, names, args.games, args.seed, args.jobs)
    seats = Counter(names)
    wins: Counter[str] = Counter()
    for result in results:
        winners = result.winners
        for index in winners:
            wins[result.players[index].strategy] += 1 / len(winners)

    rows = []
    payload = {}
    for name in sorted(set(names)):
        cell = summarize(results, rules, names={name})
        rows.append(
            [
                name,
                str(seats[name]),
                num(cell.mean),
                num(cell.sd),
                num(cell.minus),
                pct(wins[name] / len(results) / seats[name]),
                num(cell.first_start, 1),
                pct(cell.completion),
            ]
        )
        payload[name] = cell.__dict__
    print(f"# Turnier — {args.games} Partien, {rules.players} Personen\n")
    print(
        table(
            ["Strategie", "Plätze", "Punkte", "sd", "Minus", "Sieganteil", "1. Start", "Abschluss"],
            rows,
        )
    )
    emit(payload, args)


def cmd_variants(args) -> None:
    base = rules_from(args)
    selected = args.variants.split(",") if args.variants else list(RULE_VARIANTS)
    rows = []
    payload = {}
    for name in selected:
        if name not in RULE_VARIANTS:
            raise SystemExit(f"unknown variant: {name} (known: {', '.join(RULE_VARIANTS)})")
        rules = base.with_(**RULE_VARIANTS[name])
        open_name, open_cell = best_open(rules, args.games, args.seed, args.jobs)
        hoard_cell = summarize(run_games(rules, ["hoard"], args.games, args.seed, args.jobs), rules)
        gap = skill_gap(rules, open_name, max(args.games // 2, 200), args.seed, args.jobs)
        rows.append(
            [
                name,
                num(open_cell.mean),
                num(hoard_cell.mean),
                num(hoard_cell.mean - open_cell.mean),
                num(open_cell.minus),
                num(open_cell.sd),
                pct(open_cell.negative_share),
                num(open_cell.first_start, 1) + " / " + num(hoard_cell.first_start, 1),
                pct(open_cell.forced_share),
                num(open_cell.painful) + " / " + num(hoard_cell.painful),
                num(gap, 1),
            ]
        )
        payload[name] = {
            "best_open": open_name,
            "open": open_cell.__dict__,
            "hoard": hoard_cell.__dict__,
            "skill_gap_pp": gap,
        }
    print(f"# Regelvarianten — {args.games} Partien je Zelle, {base.players} Personen\n")
    print(
        table(
            [
                "Variante",
                "offen",
                "Horten",
                "Vorsprung Horten",
                "Minus",
                "sd",
                "neg. %",
                "1. Start offen / Horten",
                "Zwangsabwurf",
                "schmerzhaft offen / Horten",
                "Können-Vorsprung pp",
            ],
            rows,
        )
    )
    print(
        "\n„offen\" ist das beste der vier offenen Selbstspiel-Profile, „Horten\" die "
        "Hortenlinie. Ein positiver Vorsprung heißt: Zurückhalten schlägt offenes Spiel. "
        "„1. Start\" ist der Median der Runde, in der das erste Projekt sichtbar "
        "ausliegt — die dramaturgisch entscheidende Zahl."
    )
    emit(payload, args)


def cmd_handlimit(args) -> None:
    base = rules_from(args)
    rows = []
    payload = {}
    for limit in range(args.max_limit, args.min_limit - 1, -1):
        for forced in (False, True):
            rules = base.with_(hand_limit=limit, forced_start=forced)
            open_name, open_cell = best_open(rules, args.games, args.seed, args.jobs)
            hoard_cell = summarize(
                run_games(rules, ["hoard"], args.games, args.seed, args.jobs), rules
            )
            rows.append(
                [
                    f"HL {limit}{' + Zwangsauslage' if forced else ''}",
                    num(open_cell.mean),
                    num(hoard_cell.mean),
                    num(hoard_cell.mean - open_cell.mean),
                    num(open_cell.minus),
                    pct(open_cell.forced_share),
                    num(open_cell.painful) + " / " + num(hoard_cell.painful),
                    num(open_cell.options),
                ]
            )
            payload[f"hl{limit}-{'forced' if forced else 'free'}"] = {
                "best_open": open_name,
                "open": open_cell.__dict__,
                "hoard": hoard_cell.__dict__,
            }
    print(f"# Handlimit-Sweep — {args.games} Partien je Zelle, {base.players} Personen\n")
    print(
        table(
            [
                "Variante",
                "offen",
                "Horten",
                "Vorsprung Horten",
                "Minus",
                "Zwangsabwurf",
                "schmerzhaft offen / Horten",
                "Optionen/Zug",
            ],
            rows,
        )
    )
    print(
        "\n„schmerzhaft\" zählt Abwürfe einer Karte, die der eigene Plan noch braucht — "
        "am Tisch der Satz „ich muss jetzt was wegwerfen, was ich brauche\". Im offenen "
        "Spiel ist der Wert strukturell 0, weil passende Faktoren schon in Phase 2 "
        "angelegt werden; sichtbar wird die Untergrenze des Korridors deshalb nur an "
        "der Hortenlinie."
    )
    emit(payload, args)


def cmd_projects(args) -> None:
    rules = rules_from(args)
    stage = build_stage_set(rules.repeats)
    rng = random.Random(args.seed)
    action_deck = [card for card in stage.actions if rules.events or not card.defn.is_event]

    costs = {}
    for project in stage.projects:
        samples = [
            draw_cost(project.defn.requirements, action_deck, rng) for _ in range(args.samples)
        ]
        costs[project.card_id] = statistics.fmean(samples)

    results = run_games(rules, [args.strategy], args.games, args.seed, args.jobs)
    started: Counter[str] = Counter()
    closed: Counter[str] = Counter()
    for result in results:
        started.update(result.started_projects)
        closed.update(result.completed_projects)

    rows = []
    payload = {}
    for project in sorted(stage.projects, key=lambda card: (card.defn.points, card.card_id)):
        card_id = project.card_id
        points = project.defn.points
        cost = costs[card_id]
        quote = closed[card_id] / started[card_id] if started[card_id] else 0.0
        realized = points * (2 * quote - 1)
        rows.append(
            [
                card_id,
                project.name,
                str(points),
                "+".join(project.defn.requirements),
                num(cost),
                num(points / cost, 3),
                pct(quote),
                num(realized),
            ]
        )
        payload[card_id] = {
            "points": points,
            "requirements": list(project.defn.requirements),
            "expected_cards": cost,
            "points_per_card": points / cost,
            "completion": quote,
            "realized_value": realized,
        }
    print(
        f"# Projektkarten — {args.samples} Ziehstichproben, {args.games} Partien "
        f"({args.strategy}, {rules.players} Personen)\n"
    )
    print(
        table(
            [
                "card_id",
                "Name",
                "P",
                "Profil",
                "E[Aktionskarten]",
                "Punkte/Karte",
                "Abschluss",
                "realisiert",
            ],
            rows,
        )
    )
    ratios = [entry["points_per_card"] for entry in payload.values()]
    realized = [entry["realized_value"] for entry in payload.values()]
    print(
        f"\nSpanne Punkte/Karte: {num(max(ratios) / min(ratios))}× · "
        f"sd {num(statistics.pstdev(ratios), 3)} · "
        f"Spanne realisierter Wert: {num(max(realized) - min(realized))}"
    )
    print(
        "„realisiert\" ist Punkte × (2q − 1): der Erwartungswert einer Karte, wenn ein "
        "gescheitertes Projekt denselben Wert negativ zählt."
    )
    emit(payload, args)


def cmd_repeats(args) -> None:
    base = rules_from(args)
    rows = []
    payload = {}
    for policy in REPEAT_POLICIES:
        rules = base.with_(repeats=policy)
        stage = build_stage_set(policy)
        open_name, cell = best_open(rules, args.games, args.seed, args.jobs)
        families = stage.family_counts()
        rows.append(
            [
                policy,
                str(len(stage.factors)),
                " / ".join(str(families[family]) for family in FAMILIES),
                num(cell.mean),
                num(cell.sd),
                pct(cell.completion),
                num(cell.minus),
                pct(cell.negative_share),
            ]
        )
        payload[policy] = {
            "factors": len(stage.factors),
            "families": dict(families),
            "best_open": open_name,
            "stats": cell.__dict__,
        }
    print(f"# Acht doppelte Faktormotive — {args.games} Partien je Policy\n")
    print(
        table(
            [
                "Policy",
                "Faktoren",
                "T / D / O / M",
                "Punkte",
                "sd",
                "Abschluss",
                "Minus",
                "neg. %",
            ],
            rows,
        )
    )
    print(
        "\n`commons` verteilt die acht Zusatzkopien gleichmäßig, `requirements` "
        "spiegelt die Anforderungsbilanz der 16 Projekte, `none` lässt sie weg "
        "(38 statt 46 Faktoren). Offene Frage aus der Panel-Review, Abschnitt 5."
    )
    emit(payload, args)


def cmd_coop(args) -> None:
    base = rules_from(args)
    rows = []
    payload = {}
    variants = {
        "ohne Kooperation": {"cooperation": False},
        "Kooperation (§11)": {"cooperation": True},
        "Kooperation + Einzelabschluss": {"cooperation": True, "coop_solo_close": True},
    }
    for label, changes in variants.items():
        rules = base.with_(**changes)
        names = ["coop"] if changes["cooperation"] else ["open-2-safe"]
        results = run_games(rules, names, args.games, args.seed, args.jobs)
        cell = summarize(results, rules)
        offered = statistics.fmean(
            [sum(player.coops for player in result.players) / 2 for result in results]
        )
        closed = statistics.fmean(
            [sum(player.coops_closed for player in result.players) / 2 for result in results]
        )
        rows.append(
            [
                label,
                num(cell.mean),
                num(cell.minus),
                pct(cell.completion),
                num(offered),
                pct(closed / offered if offered else 0.0),
                pct(cell.negative_share),
            ]
        )
        payload[label] = {"stats": cell.__dict__, "coops": offered, "closed": closed}

    print(f"# Kooperation — {args.games} Partien je Variante\n")
    print(
        table(
            [
                "Variante",
                "Punkte",
                "Minus",
                "Abschluss",
                "Kooperationen/Partie",
                "davon geschlossen",
                "neg. %",
            ],
            rows,
        )
    )
    quote = payload["Kooperation (§11)"]["stats"]["completion"]
    print(
        f"\nGemessene Abschlussquote im Spiel: {pct(quote)}. Ein erfülltes, aber wegen "
        "des Partners offenes Projekt zählt nach §11 voll negativ; der Einzelabschluss "
        "aus Paket B hebt diese Kopplung auf."
    )
    emit(payload, args)


# ------------------------------------------------------------------- Parser


def rules_from(args) -> Rules:
    return Rules(
        players=args.players,
        rounds=args.rounds,
        hand_limit=args.hand_limit,
        repeats=getattr(args, "repeats", "commons"),
        events=not getattr(args, "no_events", False),
    )


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--games", type=int, default=2000, help="Partien je Zelle")
    parser.add_argument("--players", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=6)
    parser.add_argument("--hand-limit", type=int, default=5)
    parser.add_argument("--repeats", choices=REPEAT_POLICIES, default="commons")
    parser.add_argument("--no-events", action="store_true", help="Aktionsstapel ohne Ereignisse")
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--jobs", type=int, default=1, help="Prozesse für parallele Läufe")
    parser.add_argument("--json", help="Ergebnisse zusätzlich als JSON schreiben")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set", help="Zusammensetzung des Bühnensatzes zeigen")
    p_set.add_argument("--repeats", choices=REPEAT_POLICIES, default="commons")
    p_set.set_defaults(func=cmd_set)

    p_tournament = sub.add_parser("tournament", help="Strategien an einem Tisch vergleichen")
    add_common(p_tournament)
    p_tournament.add_argument(
        "--strategies",
        default="open-1-safe,open-2-safe,hoard,random",
        help="kommaseparierte Sitzbelegung (" + ", ".join(sorted(STRATEGIES)) + ")",
    )
    p_tournament.set_defaults(func=cmd_tournament)

    p_variants = sub.add_parser("variants", help="Regelvarianten gegen das Horten messen")
    add_common(p_variants)
    p_variants.add_argument("--variants", help="Teilmenge aus " + ", ".join(RULE_VARIANTS))
    p_variants.set_defaults(func=cmd_variants)

    p_hand = sub.add_parser("handlimit", help="Handlimit-Korridor abtasten")
    add_common(p_hand)
    p_hand.add_argument("--min-limit", type=int, default=2)
    p_hand.add_argument("--max-limit", type=int, default=6)
    p_hand.set_defaults(func=cmd_handlimit)

    p_projects = sub.add_parser("projects", help="Schwierigkeit und Ertrag je Projektkarte")
    add_common(p_projects)
    p_projects.add_argument("--samples", type=int, default=20000, help="Ziehstichproben je Karte")
    p_projects.add_argument("--strategy", default="open-1-safe")
    p_projects.set_defaults(func=cmd_projects)

    p_repeats = sub.add_parser("repeats", help="Policies für die acht Zusatzkopien vergleichen")
    add_common(p_repeats)
    p_repeats.set_defaults(func=cmd_repeats)

    p_coop = sub.add_parser("coop", help="Kooperation nach §11 messen")
    add_common(p_coop)
    p_coop.set_defaults(func=cmd_coop)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
