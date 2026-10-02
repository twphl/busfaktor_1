#!/usr/bin/env python3
"""Kartendaten laden und die beiden Nachziehstapel des Bühnensatzes bauen.

`data/cards.csv` ist die kanonische Quelle. Alle spielrelevanten Eigenschaften
werden aus den Datenfeldern und dem `rules_text` abgeleitet, damit eine
Kartenänderung nicht zusätzlich hier gepflegt werden muss.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS_CSV = ROOT / "data" / "cards.csv"

FAMILIES = ("team", "data", "operations", "methods")

# Bezeichnungen der Faktortypen, wie sie in den deutschen Regeltexten
# vorkommen ("Teamfaktor", "Team-Anforderung", "Daten- oder Methodenfaktor", ...).
_FAMILY_PATTERNS = (
    ("team", re.compile(r"\bTeam")),
    ("data", re.compile(r"\bDaten")),
    ("operations", re.compile(r"\bBetrieb")),
    ("methods", re.compile(r"\bMethode")),
)
_NUMERALS = {
    "ein": 1,
    "eine": 1,
    "einen": 1,
    "einem": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
}
_NUMERAL_RE = re.compile(r"\b(" + "|".join(_NUMERALS) + r")\b")

# Der Bühnensatz enthält 46 Projektfaktoren, die Kartenliste aber nur 38
# Motive. Die gedruckte Auswahl steht in data/cards.csv (stage_copies,
# ADR 0009); die Policies unten machen alternative Auswahlen simulierbar.
STAGE_FACTOR_SLOTS = 46
REPEAT_POLICIES = ("commons", "requirements", "none")
SUPPORTED_TEMPLATES = {"E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"}


@dataclass(frozen=True)
class EventSpec:
    """Aus `rules_text` abgeleitete Parameter eines Ereignisses."""

    template: str
    families: tuple[str, ...] = ()
    look: int = 0
    take: int = 0
    scope: str = "single"  # single | all | self | coop
    chooser: str = "actor"  # actor | target
    counters: str = ""  # E8: rueckschlag | mehraufwand | single | any
    only_if_completes: bool = False


@dataclass(frozen=True)
class CardDef:
    """Ein Kartenmotiv, unabhängig von der Zahl gedruckter Exemplare."""

    card_id: str
    name: str
    card_type: str  # Projekt | Projektfaktor | Ereignis
    rarity: str
    families: tuple[str, ...] = ()  # erfüllbare Faktortypen eines Faktors
    requirements: tuple[str, ...] = ()  # Anforderungen eines Projekts
    points: int = 0
    polarity: str = ""
    event: EventSpec | None = None

    @property
    def is_project(self) -> bool:
        return self.card_type == "Projekt"

    @property
    def is_factor(self) -> bool:
        return self.card_type == "Projektfaktor"

    @property
    def is_event(self) -> bool:
        return self.card_type == "Ereignis"

    @property
    def is_wildcard(self) -> bool:
        return self.is_factor and len(self.families) > 1


@dataclass(frozen=True)
class Card:
    """Ein physisches Exemplar. `uid` unterscheidet doppelte Motive."""

    uid: int
    defn: CardDef

    @property
    def card_id(self) -> str:
        return self.defn.card_id

    @property
    def name(self) -> str:
        return self.defn.name

    def __repr__(self) -> str:  # pragma: no cover - nur für Debugging
        return f"<{self.defn.card_id} {self.defn.name} #{self.uid}>"


@dataclass
class StageSet:
    """Der 74-Karten-Bühnensatz, aufgeteilt in seine zwei Stapel."""

    projects: list[Card]
    actions: list[Card]
    repeated_ids: tuple[str, ...] = ()
    unsupported: tuple[str, ...] = ()

    @property
    def factors(self) -> list[Card]:
        return [card for card in self.actions if card.defn.is_factor]

    @property
    def events(self) -> list[Card]:
        return [card for card in self.actions if card.defn.is_event]

    def family_counts(self) -> Counter[str]:
        counts: Counter[str] = Counter()
        for card in self.factors:
            key = card.defn.families[0] if len(card.defn.families) == 1 else "wildcard"
            counts[key] += 1
        return counts


def _families_in(text: str) -> tuple[str, ...]:
    return tuple(family for family, pattern in _FAMILY_PATTERNS if pattern.search(text))


def _numerals_in(text: str) -> list[int]:
    return [_NUMERALS[match] for match in _NUMERAL_RE.findall(text)]


def parse_event(template: str, rules_text: str) -> EventSpec:
    """Leitet die Effektparameter eines Ereignisses aus ihrem Regeltext ab."""

    families = _families_in(rules_text)
    numbers = _numerals_in(rules_text)
    first = numbers[0] if numbers else 1

    if template == "E1":  # Sichten
        look = first
        take = numbers[1] if len(numbers) > 1 else 1
        return EventSpec(template, look=look, take=take)
    if template == "E2":  # Nachziehen
        return EventSpec(template, take=first)
    if template == "E3":  # Rückholen aus der offenen Ablage
        return EventSpec(template, take=first)
    if template == "E4":  # Umverteilen
        scope = "coop" if "kooperierende" in rules_text else "self"
        return EventSpec(template, take=first, scope=scope)
    if template == "E5":  # Joker
        options = families or FAMILIES
        return EventSpec(
            template,
            families=tuple(options),
            only_if_completes=(
                "letzte offene Anforderung" in rules_text
                or "genau eine offene Anforderung" in rules_text
            ),
        )
    if template == "E6":  # Mehraufwand
        if families:
            return EventSpec(template, families=families)
        # "Diese Person wählt einen Faktortyp" — das Ziel wählt selbst.
        return EventSpec(template, families=FAMILIES, chooser="target")
    if template == "E7":  # Rückschlag
        scope = "all" if "Jede Person" in rules_text else "single"
        return EventSpec(template, families=families or FAMILIES, scope=scope)
    if template == "E8":  # Absicherung
        if "Rückschlag" in rules_text:
            counters = "rueckschlag"
        elif "Mehraufwand" in rules_text:
            counters = "mehraufwand"
        elif "einzelnes Projekt" in rules_text:
            counters = "single"
        else:
            counters = "any"
        return EventSpec(template, counters=counters)
    return EventSpec(template)


def _card_def(row: dict[str, str]) -> CardDef:
    card_type = row["card_type"]
    if card_type == "Projekt":
        requirements = tuple(row["requirements"].split("+")) if row["requirements"] else ()
        return CardDef(
            card_id=row["card_id"],
            name=row["name"],
            card_type=card_type,
            rarity=row["rarity"],
            requirements=requirements,
            points=int(row["points"]),
        )
    if card_type == "Projektfaktor":
        family = row["factor_family"]
        families = _families_in(row["rules_text"]) if family == "wildcard" else (family,)
        return CardDef(
            card_id=row["card_id"],
            name=row["name"],
            card_type=card_type,
            rarity=row["rarity"],
            families=families,
        )
    return CardDef(
        card_id=row["card_id"],
        name=row["name"],
        card_type=card_type,
        rarity=row["rarity"],
        polarity=row["polarity"],
        event=parse_event(row["effect_template"], row["rules_text"]),
    )


@lru_cache(maxsize=1)
def load_cards(path: str | None = None) -> tuple[CardDef, ...]:
    """Alle spielbaren Motive aus `data/cards.csv`."""

    csv_path = Path(path) if path else CARDS_CSV
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return tuple(
        _card_def(row)
        for row in rows
        if row["card_type"] in {"Projekt", "Projektfaktor", "Ereignis"}
    )


def plan_repeats(factors: list[CardDef], projects: list[CardDef], policy: str) -> list[str]:
    """Wählt die acht doppelt gedruckten Faktormotive des Bühnensatzes."""

    if policy == "none":
        return []
    missing = STAGE_FACTOR_SLOTS - len(factors)
    if missing <= 0:
        return []

    basics = [card for card in factors if not card.is_wildcard]
    if policy == "commons":
        per_family = {family: missing // len(FAMILIES) for family in FAMILIES}
        for index in range(missing % len(FAMILIES)):
            per_family[FAMILIES[index]] += 1
    elif policy == "requirements":
        # Verteilung an den Anforderungen der 16 Projekte ausrichten (ADR 0009).
        demand = Counter(req for project in projects for req in project.requirements)
        have = Counter(card.families[0] for card in basics)
        total = sum(have.values()) + missing
        share = {family: total * demand[family] / sum(demand.values()) for family in FAMILIES}
        target = {family: max(have[family], int(share[family])) for family in FAMILIES}
        while sum(target.values()) < sum(have.values()) + missing:
            family = max(FAMILIES, key=lambda f: share[f] - target[f])
            target[family] += 1
        while sum(target.values()) > sum(have.values()) + missing:
            family = min(
                (f for f in FAMILIES if target[f] > have[f]),
                key=lambda f: share[f] - target[f],
            )
            target[family] -= 1
        per_family = {family: target[family] - have[family] for family in FAMILIES}
    else:
        raise ValueError(f"unknown repeat policy: {policy}")

    repeats: list[str] = []
    for family in FAMILIES:
        pool = [card for card in basics if card.families[0] == family]
        # Commons zuerst: sie werden ohnehin neunfach gedruckt.
        pool.sort(key=lambda card: (card.rarity != "common", card.card_id))
        for index in range(per_family[family]):
            repeats.append(pool[index % len(pool)].card_id)
    return repeats


@lru_cache(maxsize=8)
def build_stage_set(repeats: str = "commons", stage_only: bool = True) -> StageSet:
    """Baut Projekt- und Aktionsstapel aus den Bühnenkarten.

    `stage_only` beschränkt auf `stage_candidate = true` (16/38/12). Ohne die
    Beschränkung entsteht ein Pool aus allen 82 spielbaren Motiven.
    """

    with CARDS_CSV.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["card_type"] != "Spielerhilfe"]
    if stage_only:
        rows = [row for row in rows if row["stage_candidate"] == "true"]
    defs = [_card_def(row) for row in rows]

    projects = [card for card in defs if card.is_project]
    factors = [card for card in defs if card.is_factor]
    events = [card for card in defs if card.is_event]

    by_id = {card.card_id: card for card in defs}
    repeated = plan_repeats(factors, projects, repeats)

    uid = 0
    project_cards: list[Card] = []
    for card in projects:
        project_cards.append(Card(uid, card))
        uid += 1
    action_cards: list[Card] = []
    for card in factors + events:
        action_cards.append(Card(uid, card))
        uid += 1
    for card_id in repeated:
        action_cards.append(Card(uid, by_id[card_id]))
        uid += 1

    unsupported = tuple(
        sorted(
            {
                card.card_id
                for card in events
                if card.event is not None and card.event.template not in SUPPORTED_TEMPLATES
            }
        )
    )
    return StageSet(project_cards, action_cards, tuple(repeated), unsupported)


def can_satisfy(requirements: Counter[str] | dict[str, int], cards: list[Card]) -> bool:
    """Prüft, ob eine Kartenmenge einen Anforderungs-Multiset abdeckt.

    Wildcards werden erst nach den eindeutigen Faktoren zugeteilt; bei zwei
    Optionen pro Wildcard genügt Backtracking über die Restnachfrage.
    """

    need = Counter({family: count for family, count in requirements.items() if count > 0})
    if not need:
        return True
    flexible: list[tuple[str, ...]] = []
    for card in cards:
        families = card.defn.families
        if len(families) == 1:
            family = families[0]
            if need.get(family, 0) > 0:
                need[family] -= 1
                if need[family] == 0:
                    del need[family]
        elif families:
            flexible.append(families)
    return _assign_wildcards(need, flexible, 0)


def _assign_wildcards(need: Counter[str], flexible: list[tuple[str, ...]], index: int) -> bool:
    if not need:
        return True
    if index >= len(flexible):
        return False
    for family in flexible[index]:
        if need.get(family, 0) > 0:
            need[family] -= 1
            if need[family] == 0:
                del need[family]
            if _assign_wildcards(need, flexible, index + 1):
                return True
            need[family] += 1
    return _assign_wildcards(need, flexible, index + 1)


def draw_cost(requirements: tuple[str, ...], deck: list[Card], rng) -> int:
    """Erwartungswert-Stichprobe: Aktionskarten bis ein Projekt erfüllbar ist."""

    order = list(deck)
    rng.shuffle(order)
    held: list[Card] = []
    need = Counter(requirements)
    for count, card in enumerate(order, start=1):
        if not card.defn.is_factor:
            continue
        held.append(card)
        if can_satisfy(need, held):
            return count
    return len(order)
