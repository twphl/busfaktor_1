// Test suite for playerView() in game-engine.js
const fs = require('fs');
const path = require('path');
const assert = require('assert');

// Load cards data and engine
const cardsFile = path.resolve(__dirname, '../cards.js');
const engineFile = path.resolve(__dirname, '../game-engine.js');

// Mock window for cards.js
global.window = {};
require(cardsFile);
const E = require(engineFile);

const ROWS = global.window.CARDS;
assert(ROWS && ROWS.length > 0, 'CARDS should be loaded');

console.log('Testing playerView()...');

// 1. Setup a game
const seats = [
  { name: 'Alice', kind: 'human' },
  { name: 'Bob', kind: 'human' },
  { name: 'Carol', kind: 'human' },
];

const state = E.newGame({ seats, rows: ROWS, seed: 12345 });
assert.strictEqual(state.hands.length, 3);

// 2. Test playerView for Seat 0
const view0 = E.playerView(state, 0);

// Check that state wasn't mutated
assert(state.seed !== null);
assert(state.rng !== null);
assert(state.projectDeck.every((uid) => typeof uid === 'number'));
assert(state.actionDeck.every((uid) => typeof uid === 'number'));

// Check that view0 has nullified secrets
assert.strictEqual(view0.seed, null);
assert.strictEqual(view0.rng, null);
assert.strictEqual(view0.projectDeck.length, state.projectDeck.length);
assert(view0.projectDeck.every((x) => x === null), 'projectDeck must be nulls');
assert.strictEqual(view0.actionDeck.length, state.actionDeck.length);
assert(view0.actionDeck.every((x) => x === null), 'actionDeck must be nulls');
assert.strictEqual(view0.consumed.length, state.consumed.length);
assert(view0.consumed.every((x) => x === null), 'consumed must be nulls');

// Check hands
assert.deepStrictEqual(view0.hands[0], state.hands[0], 'own hand must be intact');
assert.strictEqual(view0.hands[1].length, state.hands[1].length);
assert(view0.hands[1].every((x) => x === null), 'opponent hand 1 must be nulls');
assert.strictEqual(view0.hands[2].length, state.hands[2].length);
assert(view0.hands[2].every((x) => x === null), 'opponent hand 2 must be nulls');

// 3. Test legalActions on view0 when seat 0 is active
if (E.actor(state) === 0) {
  const actionsReal = E.legalActions(state);
  const actionsView = E.legalActions(view0);
  assert.deepStrictEqual(actionsView, actionsReal, 'legalActions(view) must match legalActions(state) for active player');
}

// 4. Test E1 pending masking
state.pending = {
  type: 'e1',
  player: 1, // Bob is deciding
  seen: [42, 43, 44],
  event: 10,
};

const viewBob = E.playerView(state, 1);
const viewAlice = E.playerView(state, 0);

assert.deepStrictEqual(viewBob.pending.seen, [42, 43, 44], 'Bob (the chooser) should see the cards');
assert.deepStrictEqual(viewAlice.pending.seen, [null, null, null], 'Alice must not see the cards');

// 5. Test invalid seat index
assert.throws(() => E.playerView(state, -1), /Ungültiger Sitz/);
assert.throws(() => E.playerView(state, 3), /Ungültiger Sitz/);

console.log('✓ All playerView tests passed successfully.');
