/* Rules of the browser game against docs/10-spielregeln.md, version 1.0.
   Run: node --test website/tests/
   The scenario helpers move single cards into a hand so that a rule can be
   checked without playing a whole game; the fuzz tests at the end play
   thousands of complete games and check the card count after every move. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const here = path.dirname(fileURLToPath(import.meta.url));
const site = path.join(here, '..');
const require = createRequire(import.meta.url);

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(site, 'cards.js'), 'utf8'), context);
const ROWS = context.window.CARDS;

const E = require(path.join(site, 'game-engine.js'));
const B = require(path.join(site, 'game-bots.js'));

/* ------------------------------------------------------------ helpers */

const seats = (count) => Array.from({ length: count }, (_, index) => ({ name: `P${index + 1}`, kind: 'human' }));
/** A fresh game in which seat 0 always begins, so the tests stay readable. */
const newTable = (count = 2, seed = 1) => {
  const state = E.newGame({ seats: seats(count), rows: ROWS, seed });
  state.startPlayer = 0;
  state.current = 0;
  state.phase = 'draw';
  state.turn = { draws: 0, started: false, eventPlayed: false, mustStart: false, declined: [] };
  return state;
};

const ZONES = ['projectDeck', 'actionDeck', 'discard', 'consumed'];

/** Moves a copy of the card into a hand, wherever it currently lies. */
function give(state, player, cardId) {
  for (const zone of ZONES) {
    const index = state[zone].findIndex((uid) => state.cards[uid] === cardId);
    if (index >= 0) {
      const [uid] = state[zone].splice(index, 1);
      state.hands[player].push(uid);
      return uid;
    }
  }
  for (let other = 0; other < state.seats.length; other += 1) {
    const index = state.hands[other].findIndex((uid) => state.cards[uid] === cardId);
    if (index >= 0 && other !== player) {
      const [uid] = state.hands[other].splice(index, 1);
      state.hands[player].push(uid);
      return uid;
    }
    if (index >= 0) return state.hands[other][index];
  }
  throw new Error(`card ${cardId} is not available`);
}

/** Empties every hand and puts the game into the action phase of one seat. */
function actionPhase(state, player = 0) {
  for (let seat = 0; seat < state.seats.length; seat += 1) {
    state.consumed.push(...state.hands[seat]);
    state.hands[seat] = [];
  }
  state.current = player;
  state.phase = 'action';
  state.turn = { draws: 2, started: false, eventPlayed: false, mustStart: false, declined: [] };
  return state;
}

const actionsOfType = (state, type) => E.legalActions(state).filter((action) => action.type === type);
const has = (state, type) => actionsOfType(state, type).length > 0;
const uidOf = (state, player, cardId) => state.hands[player].find((uid) => state.cards[uid] === cardId);

/** Starts a project from hand for any seat, bypassing the once-per-turn limit. */
function startProject(state, player, cardId) {
  const uid = give(state, player, cardId);
  const before = state.current;
  state.current = player;
  state.turn.started = false;
  E.apply(state, { type: 'start', uid });
  state.current = before;
  state.turn.started = false;
  return uid;
}

/* ------------------------------------------------------------ the deck */

test('stage set: 16 projects, 46 factors, 12 events (§2)', () => {
  const deck = E.stageDeck(ROWS);
  assert.equal(deck.projects.length, 16);
  assert.equal(deck.actions.length, 58);
  const factors = deck.actions.filter((id) => deck.defs[id].type === 'Projektfaktor');
  const events = deck.actions.filter((id) => deck.defs[id].type === 'Ereignis');
  assert.equal(factors.length, 46);
  assert.equal(events.length, 12);
  assert.equal(deck.projects.length + deck.actions.length, 74);
});

test('the eight duplicated factor motifs follow stage_copies (ADR 0009)', () => {
  const deck = E.stageDeck(ROWS);
  const counts = {};
  for (const id of deck.actions) counts[id] = (counts[id] || 0) + 1;
  const doubled = Object.entries(counts).filter(([, n]) => n === 2).map(([id]) => id).sort();
  assert.deepEqual(doubled, ['KAT-C01', 'KAT-C04', 'KAT-C05', 'KAT-C09', 'KAT-C10', 'KAT-C15', 'KAT-C21', 'KAT-C23']);
});

test('every stage event parses into a supported template', () => {
  const deck = E.stageDeck(ROWS);
  for (const id of new Set(deck.actions)) {
    const def = deck.defs[id];
    if (def.type !== 'Ereignis') continue;
    assert.ok(['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8'].includes(def.spec.template), `${id}: ${def.spec.template}`);
    if (['E6', 'E7'].includes(def.spec.template)) assert.ok(def.spec.families.length > 0, `${id} without factor type`);
  }
});

/* ------------------------------------------------------------ setup and turn */

test('setup: one project and two action cards each, round 1 (§5)', () => {
  const state = newTable(4);
  assert.equal(state.round, 1);
  for (let seat = 0; seat < 4; seat += 1) {
    assert.equal(state.hands[seat].length, 3);
    assert.equal(state.hands[seat].filter((uid) => E.def(state, uid).type === 'Projekt').length, 1);
    assert.equal(state.active[seat].length, 0);
  }
  assert.equal(state.projectDeck.length, 12);
  assert.equal(state.phase, 'draw');
});

test('draw phase: two cards from the three sources (§7)', () => {
  const state = newTable(2);
  assert.deepEqual(E.legalActions(state).map((action) => action.source).sort(), ['action', 'project']);
  E.apply(state, { type: 'draw', source: 'action' });
  assert.equal(state.phase, 'draw');
  E.apply(state, { type: 'draw', source: 'project' });
  assert.equal(state.phase, 'action');
});

test('the top card of the open discard pile is drawable, the one below is not (§7)', () => {
  const state = newTable(2);
  const lower = state.actionDeck.pop();
  const top = state.actionDeck.pop();
  state.discard.push(lower, top);
  const draw = E.legalActions(state).find((action) => action.source === 'discard');
  assert.ok(draw);
  E.apply(state, draw);
  assert.ok(state.hands[0].includes(top));
  assert.ok(!state.hands[0].includes(lower));
  assert.equal(state.discard[state.discard.length - 1], lower);
});

test('empty action deck is refilled from the Verbrauchsstapel (§7)', () => {
  const state = newTable(2);
  state.consumed.push(...state.actionDeck);
  state.actionDeck = [];
  const size = state.consumed.length;
  E.apply(state, { type: 'draw', source: 'action' });
  assert.equal(state.consumed.length, 0);
  assert.equal(state.actionDeck.length, size - 1);
  assert.equal(state.reshuffles, 1);
});

test('without an active project a project must be started (§8.1)', () => {
  const state = newTable(2);
  E.apply(state, { type: 'draw', source: 'action' });
  E.apply(state, { type: 'draw', source: 'action' });
  assert.equal(state.turn.mustStart, true);
  const actions = E.legalActions(state);
  assert.ok(actions.length > 0);
  assert.ok(actions.every((action) => action.type === 'start'), 'only starting is allowed');
  E.apply(state, actions[0]);
  assert.equal(state.active[0].length, 1);
  assert.equal(state.turn.mustStart, false);
});

test('at most one new project and one event per turn (§8.1, §8.3)', () => {
  const state = actionPhase(newTable(2));
  give(state, 0, 'KAT-C02');
  give(state, 0, 'KAT-C11');
  E.apply(state, { type: 'start', uid: uidOf(state, 0, 'KAT-C02') });
  assert.equal(has(state, 'start'), false, 'no second project');

  give(state, 0, 'KAT-C25'); // Sichten
  give(state, 0, 'KAT-U22'); // Rückholen
  state.discard.push(state.actionDeck.pop());
  const event = E.legalActions(state).find((action) => action.type === 'event');
  E.apply(state, event);
  while (state.pending) E.apply(state, E.legalActions(state)[0]);
  assert.equal(has(state, 'event'), false, 'no second event');
});

test('hand limit of five at cleanup, discarded face up in order (§9)', () => {
  const state = actionPhase(newTable(2));
  for (const id of ['KAT-C01', 'KAT-C04', 'KAT-C05', 'KAT-C09', 'KAT-C10', 'KAT-C15', 'KAT-C21']) give(state, 0, id);
  E.apply(state, { type: 'end' });
  assert.equal(state.phase, 'cleanup');
  assert.equal(E.legalActions(state).length, 7);
  const first = state.hands[0][0];
  E.apply(state, { type: 'discard', uid: first });
  assert.equal(state.discard[state.discard.length - 1], first);
  assert.equal(state.phase, 'cleanup');
  E.apply(state, { type: 'discard', uid: state.hands[0][0] });
  assert.equal(state.phase, 'draw', 'turn ends at five cards');
  assert.equal(state.current, 1);
});

/* ------------------------------------------------------------ factors and projects */

test('two identical symbols need two physical factors (§3, §10)', () => {
  const state = actionPhase(newTable(2));
  const project = startProject(state, 0, 'KAT-R03'); // team+team+data
  const first = give(state, 0, 'KAT-C01'); // Team
  E.apply(state, { type: 'attach', uid: first, project, family: 'team' });
  assert.equal(E.openCounts(state, project).team, 1, 'one team requirement is still open');
  const second = give(state, 0, 'KAT-C04'); // another team factor
  assert.ok(E.legalActions(state).some((action) => action.type === 'attach' && action.uid === second && action.family === 'team'));
  E.apply(state, { type: 'attach', uid: second, project, family: 'team' });
  assert.equal(E.openCounts(state, project).team, undefined);
});

test('a factor only goes to an open requirement of its own type (§8.2)', () => {
  const state = actionPhase(newTable(2));
  const project = startProject(state, 0, 'KAT-C11'); // data+methods
  const team = give(state, 0, 'KAT-C01');
  assert.equal(E.legalActions(state).some((action) => action.type === 'attach' && action.uid === team), false);
  const wildcard = give(state, 0, 'KAT-U25'); // data or methods
  const families = E.legalActions(state)
    .filter((action) => action.type === 'attach' && action.uid === wildcard)
    .map((action) => action.family).sort();
  assert.deepEqual(families, ['data', 'methods'], 'the wildcard offers both of its types');
});

test('a fulfilled project closes at once and scores (§10, §16)', () => {
  const state = actionPhase(newTable(2));
  const project = startProject(state, 0, 'KAT-C02'); // team+operations, 2 points
  const team = give(state, 0, 'KAT-C01');
  const operations = give(state, 0, 'KAT-C15');
  E.apply(state, { type: 'attach', uid: team, project, family: 'team' });
  E.apply(state, { type: 'attach', uid: operations, project, family: 'operations' });
  assert.equal(state.active[0].length, 0);
  assert.deepEqual(state.completed[0], [project]);
  assert.ok(state.consumed.includes(team) && state.consumed.includes(operations), 'factors are consumed');
  assert.equal(E.scores(state).rows[0].plus, 2);
});

/* ------------------------------------------------------------ events */

test('Mehraufwand adds a requirement, at most one per project (§13 E6)', () => {
  const state = actionPhase(newTable(2));
  const project = startProject(state, 1, 'KAT-C11');
  state.current = 0;
  const event = give(state, 0, 'KAT-C03'); // 47 Mails, extra team requirement
  const play = E.legalActions(state).find((action) => action.type === 'event' && action.uid === event);
  assert.ok(play);
  E.apply(state, play);
  assert.equal(E.openCounts(state, project).team, 1);
  assert.equal(E.requirementCounts(state, project).team, 1);
  state.turn.eventPlayed = false;
  const again = give(state, 0, 'KAT-U02'); // the other Mehraufwand of the stage set
  assert.equal(E.legalActions(state).some((action) => action.type === 'event' && action.uid === again), false, 'no second surcharge');
});

test('the target of "Eine Kleinigkeit noch" picks the factor type (§13 E6)', () => {
  const state = actionPhase(newTable(2));
  const project = startProject(state, 1, 'KAT-C11');
  state.current = 0;
  const event = give(state, 0, 'KAT-U02');
  E.apply(state, E.legalActions(state).find((action) => action.type === 'event' && action.uid === event));
  assert.equal(state.pending.type, 'family');
  assert.equal(state.pending.player, 1, 'the affected person decides');
  E.apply(state, { type: 'family', family: 'operations' });
  assert.equal(E.openCounts(state, project).operations, 1);
});

test('Rückschlag returns the factor to its controlling person (§13 E7)', () => {
  const state = actionPhase(newTable(2));
  const project = startProject(state, 1, 'KAT-C11');
  const factor = give(state, 1, 'KAT-C09'); // data
  state.current = 1;
  E.apply(state, { type: 'attach', uid: factor, project, family: 'data' });
  state.current = 0;
  state.turn.eventPlayed = false;
  const event = give(state, 0, 'KAT-C08'); // UTF-8, beinahe
  const play = E.legalActions(state).find((action) => action.type === 'event' && action.uid === event && action.card === factor);
  assert.ok(play);
  E.apply(state, play);
  assert.ok(state.hands[1].includes(factor), 'back to the controlling person');
  assert.equal(E.openCounts(state, project).data, 1);
});

test('an Absicherung stops the negative event, both are consumed (§12)', () => {
  const state = actionPhase(newTable(2));
  const project = startProject(state, 1, 'KAT-C11');
  const factor = give(state, 1, 'KAT-C09');
  state.current = 1;
  E.apply(state, { type: 'attach', uid: factor, project, family: 'data' });
  state.current = 0;
  state.turn.eventPlayed = false;
  const guard = give(state, 1, 'KAT-R06'); // Getestete Wiederherstellung
  const event = give(state, 0, 'KAT-C08');
  E.apply(state, E.legalActions(state).find((action) => action.type === 'event' && action.uid === event));
  assert.equal(state.pending.type, 'react');
  assert.equal(state.pending.player, 1);
  E.apply(state, { type: 'react', uid: guard });
  assert.equal(state.pending, null);
  assert.ok(state.consumed.includes(guard) && state.consumed.includes(event));
  assert.ok(!state.hands[1].includes(factor), 'the factor stays attached');
});

test('an Absicherung is never played in one’s own turn (§12)', () => {
  const state = actionPhase(newTable(2));
  give(state, 0, 'KAT-R06');
  assert.equal(has(state, 'event'), false);
});

test('Sichten looks at three cards and puts the rest back under the deck (§13 E1)', () => {
  const state = actionPhase(newTable(2));
  const event = give(state, 0, 'KAT-C25');
  const deckSize = state.actionDeck.length;
  E.apply(state, { type: 'event', uid: event });
  assert.equal(state.pending.type, 'e1');
  assert.equal(state.pending.seen.length, 3);
  const [keep, ...rest] = state.pending.seen;
  E.apply(state, { type: 'e1', keep, rest });
  assert.ok(state.hands[0].includes(keep));
  assert.equal(state.actionDeck.length, deckSize - 3 + 2);
  assert.equal(state.actionDeck[1], rest[0], 'the rest lies at the bottom in the chosen order');
  assert.equal(state.actionDeck[0], rest[1]);
  assert.ok(state.consumed.includes(event));
});

test('Nachziehen finds factors, revealed events are consumed (§13 E2)', () => {
  const state = actionPhase(newTable(2));
  const event = give(state, 0, 'KAT-U26');
  E.apply(state, { type: 'event', uid: event });
  assert.equal(state.hands[0].filter((uid) => E.def(state, uid).type === 'Projektfaktor').length, 2);
  assert.ok(state.hands[0].every((uid) => E.def(state, uid).type !== 'Ereignis'));
});

test('Sicherheitsvorfall: everyone gives one controlled factor back (§13 E7)', () => {
  const state = actionPhase(newTable(3));
  const projects = [0, 1, 2].map((seat) => {
    const project = startProject(state, seat, ['KAT-R03', 'KAT-C11', 'KAT-C18'][seat]);
    const factor = give(state, seat, ['KAT-C01', 'KAT-C09', 'KAT-C15'][seat]);
    const family = ['team', 'data', 'operations'][seat];
    state.current = seat;
    E.apply(state, { type: 'attach', uid: factor, project, family });
    return { project, factor };
  });
  state.current = 0;
  state.turn.eventPlayed = false;
  const event = give(state, 0, 'KAT-R16');
  E.apply(state, { type: 'event', uid: event });
  // every seat had exactly one option, so nothing is left to decide
  assert.equal(state.pending, null);
  for (let seat = 0; seat < 3; seat += 1) assert.ok(state.hands[seat].includes(projects[seat].factor), `seat ${seat}`);
});

/* ------------------------------------------------------------ cooperation */

test('cooperation: shared factor fills a requirement in both projects (§11)', () => {
  const state = actionPhase(newTable(2));
  const mine = startProject(state, 0, 'KAT-C02'); // team+operations
  const theirs = startProject(state, 1, 'KAT-R03'); // team+team+data
  state.current = 0;
  const offer = E.legalActions(state).find((action) => action.type === 'coop');
  assert.ok(offer);
  E.apply(state, offer);
  assert.equal(state.pending.type, 'coop');
  assert.equal(state.pending.player, 1);
  E.apply(state, { type: 'accept' });

  const factor = give(state, 0, 'KAT-C01'); // team
  const shared = E.legalActions(state).find((action) => action.type === 'attach' && action.uid === factor && action.shared);
  assert.ok(shared, 'sharing is offered');
  E.apply(state, shared);
  assert.equal(state.pending.type, 'share');
  assert.equal(state.pending.player, 1, 'the partner agrees');
  E.apply(state, { type: 'accept' });
  assert.equal(E.openCounts(state, mine).team, undefined);
  assert.equal(E.openCounts(state, theirs).team, 1, 'one of the two team requirements is covered');
});

test('cooperating projects close individually, the shared factor stays (§11)', () => {
  const state = actionPhase(newTable(2));
  const mine = startProject(state, 0, 'KAT-C02');
  const theirs = startProject(state, 1, 'KAT-R03');
  state.current = 0;
  E.apply(state, E.legalActions(state).find((action) => action.type === 'coop'));
  E.apply(state, { type: 'accept' });
  const sharedFactor = give(state, 0, 'KAT-C01');
  E.apply(state, E.legalActions(state).find((action) => action.type === 'attach' && action.uid === sharedFactor && action.shared));
  E.apply(state, { type: 'accept' });

  const operations = give(state, 0, 'KAT-C15');
  E.apply(state, { type: 'attach', uid: operations, project: mine, family: 'operations' });
  assert.deepEqual(state.completed[0], [mine], 'my project closes on its own');
  assert.ok(!state.consumed.includes(sharedFactor), 'the shared factor stays for the partner');
  assert.equal(E.openCounts(state, theirs).team, 1);

  state.current = 1;
  const team = give(state, 1, 'KAT-C04');
  const data = give(state, 1, 'KAT-C09');
  E.apply(state, { type: 'attach', uid: team, project: theirs, family: 'team' });
  E.apply(state, { type: 'attach', uid: data, project: theirs, family: 'data' });
  assert.deepEqual(state.completed[1], [theirs]);
  assert.ok(state.consumed.includes(sharedFactor), 'consumed once both are done');
  assert.equal(state.coops[0].over, true);
});

test('cooperation needs consent and at most one factor per project (§11)', () => {
  const state = actionPhase(newTable(2));
  const mine = startProject(state, 0, 'KAT-R03');
  startProject(state, 1, 'KAT-C11');
  const one = give(state, 0, 'KAT-C01');
  const two = give(state, 0, 'KAT-C04');
  state.current = 0;
  E.apply(state, { type: 'attach', uid: one, project: mine, family: 'team' });
  assert.ok(has(state, 'coop'), 'one factor is still allowed');
  E.apply(state, { type: 'attach', uid: two, project: mine, family: 'team' });
  assert.equal(has(state, 'coop'), false, 'two factors are too many');
});

test('a declined cooperation is not offered again in the same turn (§8.4)', () => {
  const state = actionPhase(newTable(2));
  startProject(state, 0, 'KAT-C02');
  startProject(state, 1, 'KAT-R03');
  state.current = 0;
  E.apply(state, E.legalActions(state).find((action) => action.type === 'coop'));
  E.apply(state, { type: 'decline' });
  assert.equal(has(state, 'coop'), false);
});

/* ------------------------------------------------------------ scoring */

test('scoring: minus one per unfinished project, tie-breaks (§16)', () => {
  const state = actionPhase(newTable(3));
  startProject(state, 0, 'KAT-R11'); // 4 points, stays open
  state.completed[0].push(give(state, 0, 'KAT-C02')); // 2
  state.hands[0] = [];
  state.completed[1].push(give(state, 1, 'KAT-C11')); // 2
  state.hands[1] = [];
  startProject(state, 2, 'KAT-C18');
  const result = E.scores(state);
  assert.deepEqual(result.rows.map((row) => row.total), [1, 2, -1]);
  assert.deepEqual(result.winners, [1]);
});

test('a tie is decided by more completed projects (§16)', () => {
  const state = actionPhase(newTable(2));
  state.completed[0].push(give(state, 0, 'KAT-C02'), give(state, 0, 'KAT-C11')); // 2 + 2
  state.completed[1].push(give(state, 1, 'KAT-R11')); // 4
  state.hands = [[], []];
  const result = E.scores(state);
  assert.deepEqual(result.rows.map((row) => row.total), [4, 4]);
  assert.deepEqual(result.winners, [0]);
});

test('a game ends after six full rounds', () => {
  const state = newTable(3, 42);
  let guard = 0;
  while (state.phase !== 'over') {
    E.apply(state, B.choose(state, E.actor(state)));
    assert.ok((guard += 1) < 4000, 'game does not end');
  }
  assert.equal(state.round, E.RULES.rounds);
  assert.equal(E.legalActions(state).length, 0);
  assert.equal(E.actor(state), null);
});

/* ------------------------------------------------------------ network view */

test('playerView masks other hands, both decks and the random seed', () => {
  const state = newTable(3, 7);
  const view = E.playerView(state, 1);
  assert.deepEqual(view.hands[1], state.hands[1], 'own hand stays readable');
  assert.ok(view.hands[0].every((uid) => uid === null));
  assert.ok(view.hands[2].every((uid) => uid === null));
  assert.equal(view.hands[0].length, state.hands[0].length, 'counts stay right');
  assert.ok(view.projectDeck.every((uid) => uid === null));
  assert.ok(view.actionDeck.every((uid) => uid === null));
  assert.equal(view.actionDeck.length, state.actionDeck.length);
  assert.equal(view.rng, null);
  assert.equal(view.seed, null);
  assert.equal(view.discard.length, state.discard.length);
});

test('playerView hides the Sichten cards from everyone else', () => {
  const state = actionPhase(newTable(2));
  const event = give(state, 0, 'KAT-C25');
  E.apply(state, { type: 'event', uid: event });
  assert.equal(state.pending.type, 'e1');
  assert.ok(E.playerView(state, 0).pending.seen.every((uid) => uid !== null), 'the acting person sees them');
  assert.ok(E.playerView(state, 1).pending.seen.every((uid) => uid === null), 'the others do not');
});

test('playerView rejects a seat that does not exist', () => {
  const state = newTable(2);
  assert.throws(() => E.playerView(state, 2), /Ungültiger Sitz/);
});

/* ------------------------------------------------------------ fuzz */

test('1200 games of random legal moves keep all 74 cards', () => {
  for (let game = 0; game < 1200; game += 1) {
    const count = 2 + (game % 3);
    const state = E.newGame({ seats: seats(count), rows: ROWS, seed: game * 7919 + 1 });
    let seed = game + 1;
    const random = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
    let steps = 0;
    while (state.phase !== 'over') {
      const actions = E.legalActions(state);
      assert.ok(actions.length > 0, 'someone must always be able to act');
      let action = actions[Math.floor(random() * actions.length)];
      // keep turns from ending immediately, so more rules are exercised
      if (action.type === 'end' && actions.length > 1 && random() < 0.8) action = actions[Math.floor(random() * (actions.length - 1))];
      E.apply(state, action);
      E.checkInvariants(state);
      assert.ok((steps += 1) < 5000, 'game does not end');
    }
    assert.equal(state.cards.length, 74);
  }
});

test('600 bot games run through without an illegal move', () => {
  const profiles = ['umsichtig', 'abwartend', 'kooperativ'];
  for (let game = 0; game < 600; game += 1) {
    const count = 2 + (game % 3);
    const table = Array.from({ length: count }, (_, index) => ({ name: `B${index}`, kind: 'bot', bot: profiles[(game + index) % profiles.length] }));
    const state = E.newGame({ seats: table, rows: ROWS, seed: game + 1 });
    while (state.phase !== 'over') {
      const who = E.actor(state);
      const action = B.choose(state, who);
      assert.ok(E.isLegal(state, action), `illegal bot move: ${JSON.stringify(action)}`);
      E.apply(state, action);
    }
    E.checkInvariants(state);
    const result = E.scores(state);
    assert.equal(result.winners.length > 0, true);
  }
});
