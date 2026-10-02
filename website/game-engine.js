/* Busfaktor: 1 — rules engine of the browser game (spielen.html).

   Implements docs/10-spielregeln.md, version 1.0, for the 74-card stage set
   (§2). The engine is a state machine and never decides anything itself:
   legalActions(state) lists every move the person who has to decide may make,
   apply(state, action) performs one of them. People choose in spielen.js,
   bots in game-bots.js. The state is plain JSON, so a running game can be
   saved and restored.

   The rules follow scripts/sim/engine.py where the simulator already models
   them; where the simulator decided on a person's behalf (event targets,
   Absicherungen, cooperation), the choice is a legal action here. Card
   properties are derived from data/cards.csv as in scripts/sim/deck.py. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.BusfaktorEngine = api;
})(typeof self !== 'undefined' ? self : this, () => {
  'use strict';

  const RULES = Object.freeze({
    minPlayers: 2, // §1
    maxPlayers: 4,
    rounds: 6, // §15
    handLimit: 5, // §9
    startProjects: 1, // §5.5
    startActions: 2, // §5.5
    drawsPerTurn: 2, // §7
    minusPerActive: 1, // §16: flat, whatever the project is worth
  });

  const FAMILIES = ['team', 'data', 'operations', 'methods'];
  const FAMILY = { team: 'Team', data: 'Daten', operations: 'Betrieb', methods: 'Methode' };
  // "Teamfaktor", "Datenfaktor", ... and "Team-Anforderung", "Daten-Anforderung", ...
  const FAMILY_FACTOR = { team: 'Teamfaktor', data: 'Datenfaktor', operations: 'Betriebsfaktor', methods: 'Methodenfaktor' };
  const FAMILY_REQ = { team: 'Team-Anforderung', data: 'Daten-Anforderung', operations: 'Betriebs-Anforderung', methods: 'Methoden-Anforderung' };
  const KEYWORD = { E1: 'SICHTEN', E2: 'NACHZIEHEN', E3: 'RÜCKHOLEN', E4: 'UMVERTEILEN', E5: 'JOKER', E6: 'MEHRAUFWAND', E7: 'RÜCKSCHLAG', E8: 'ABSICHERUNG' };

  /* ------------------------------------------------------------ card data */

  const FAMILY_PATTERNS = [['team', /\bTeam/], ['data', /\bDaten/], ['operations', /\bBetrieb/], ['methods', /\bMethode/]];
  const NUMERALS = { ein: 1, eine: 1, einen: 1, einem: 1, zwei: 2, drei: 3, vier: 4, 'fünf': 5 };
  const NUMERAL_RE = /(?:^|[^\wäöüß])(ein|eine|einen|einem|zwei|drei|vier|fünf)(?![\wäöüß])/g;

  const familiesIn = (text) => FAMILY_PATTERNS.filter(([, pattern]) => pattern.test(text)).map(([family]) => family);
  const numeralsIn = (text) => [...String(text).matchAll(NUMERAL_RE)].map((match) => NUMERALS[match[1]]);

  // Port of scripts/sim/deck.py parse_event: effect parameters from the rules text.
  function parseEvent(template, text) {
    const families = familiesIn(text);
    const numbers = numeralsIn(text);
    const first = numbers.length ? numbers[0] : 1;
    const spec = { template, families: [], look: 0, take: 0, scope: 'single', chooser: 'actor', counters: '', onlyIfCompletes: false };
    switch (template) {
      case 'E1': return { ...spec, look: first, take: numbers.length > 1 ? numbers[1] : 1 };
      case 'E2': return { ...spec, take: first };
      case 'E3': return { ...spec, take: first };
      case 'E4': return { ...spec, take: first, scope: text.includes('kooperierende') ? 'coop' : 'self' };
      case 'E5': return {
        ...spec,
        families: families.length ? families : FAMILIES.slice(),
        onlyIfCompletes: text.includes('letzte offene Anforderung') || text.includes('genau eine offene Anforderung'),
      };
      case 'E6': return families.length
        ? { ...spec, families }
        : { ...spec, families: FAMILIES.slice(), chooser: 'target' }; // "Diese Person wählt einen Faktortyp"
      case 'E7': return { ...spec, families: families.length ? families : FAMILIES.slice(), scope: text.includes('Jede Person') ? 'all' : 'single' };
      case 'E8': {
        let counters = 'any';
        if (text.includes('Rückschlag')) counters = 'rueckschlag';
        else if (text.includes('Mehraufwand')) counters = 'mehraufwand';
        else if (text.includes('einzelnes Projekt')) counters = 'single';
        return { ...spec, counters };
      }
      default: return spec;
    }
  }

  function cardDef(row) {
    const base = { id: row.card_id, name: row.name, type: row.card_type, rarity: row.rarity, rules: row.rules_text || '', flavor: row.flavor_text || '' };
    if (row.card_type === 'Projekt') {
      return { ...base, requirements: row.requirements ? row.requirements.split('+') : [], points: Number(row.points) || 0, goal: row.project_goal || '' };
    }
    if (row.card_type === 'Projektfaktor') {
      const families = row.factor_family === 'wildcard' ? familiesIn(row.rules_text) : [row.factor_family];
      return { ...base, families };
    }
    return { ...base, polarity: row.polarity, spec: parseEvent(row.effect_template, row.rules_text || '') };
  }

  // Stage set (§2): stage_candidate = true, factors in their stage_copies (ADR 0009).
  function stageDeck(rows) {
    const stage = rows.filter((row) => row.stage_candidate === 'true' && ['Projekt', 'Projektfaktor', 'Ereignis'].includes(row.card_type));
    const defs = {};
    const projects = [];
    const actions = [];
    for (const row of stage) {
      defs[row.card_id] = cardDef(row);
      const copies = row.card_type === 'Projektfaktor' ? Math.max(1, Number(row.stage_copies) || 1) : 1;
      for (let copy = 0; copy < copies; copy += 1) (row.card_type === 'Projekt' ? projects : actions).push(row.card_id);
    }
    return { defs, projects, actions };
  }

  /* ------------------------------------------------------------ random */

  // mulberry32; the state is one uint32 so it survives JSON.
  function random(state) {
    state.rng = (state.rng + 0x6d2b79f5) >>> 0;
    let t = state.rng;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  function shuffle(state, list) {
    for (let i = list.length - 1; i > 0; i -= 1) {
      const j = Math.floor(random(state) * (i + 1));
      [list[i], list[j]] = [list[j], list[i]];
    }
    return list;
  }

  /* ------------------------------------------------------------ helpers */

  const def = (state, uid) => state.defs[state.cards[uid]];
  const nameOf = (state, uid) => `„${def(state, uid).name}“`;
  const seatName = (state, player) => state.seats[player].name;
  const isProject = (state, uid) => def(state, uid).type === 'Projekt';
  const isFactor = (state, uid) => def(state, uid).type === 'Projektfaktor';
  const isEvent = (state, uid) => def(state, uid).type === 'Ereignis';
  const remove = (list, value) => {
    const index = list.indexOf(value);
    if (index < 0) throw new Error(`card ${value} not found`);
    list.splice(index, 1);
  };
  const count = (list) => list.reduce((acc, key) => { acc[key] = (acc[key] || 0) + 1; return acc; }, {});
  const total = (counts) => Object.values(counts).reduce((sum, value) => sum + value, 0);

  function log(state, text, extra = {}) {
    state.logSeq += 1;
    state.log.push({ n: state.logSeq, round: state.round, player: extra.player ?? null, kind: extra.kind || 'move', text });
  }

  function coopOf(state, pid) {
    const project = state.projects[pid];
    return project && project.coop !== null ? state.coops[project.coop] : null;
  }
  const partnerOf = (coop, pid) => (coop.a === pid ? coop.b : coop.a);

  // §10 plus §13 E6: printed requirements and at most one surcharge.
  function requirementCounts(state, pid) {
    const counts = count(def(state, pid).requirements);
    const extra = state.projects[pid].extra;
    if (extra) counts[extra.family] = (counts[extra.family] || 0) + 1;
    return counts;
  }
  // §11: a shared factor fills one requirement of its type at both projects.
  function filledCounts(state, pid) {
    const counts = count(state.projects[pid].filled.map((entry) => entry.family));
    const coop = coopOf(state, pid);
    if (coop && coop.shared) counts[coop.shared.family] = (counts[coop.shared.family] || 0) + 1;
    return counts;
  }
  function openCounts(state, pid) {
    const need = requirementCounts(state, pid);
    const have = filledCounts(state, pid);
    const open = {};
    for (const family of FAMILIES) {
      const value = (need[family] || 0) - (have[family] || 0);
      if (value > 0) open[family] = value;
    }
    return open;
  }
  const isComplete = (state, pid) => total(openCounts(state, pid)) === 0;
  // §11: "an jedem der beiden Projekte höchstens ein Faktor"; surcharges do not count.
  const factorCount = (state, pid) => state.projects[pid].filled.length;

  function activeCoopBetween(state, one, two) {
    return state.coops.some((coop) => !coop.over && ((coop.owners[0] === one && coop.owners[1] === two) || (coop.owners[0] === two && coop.owners[1] === one)));
  }

  function canShare(state, pid, family) {
    const coop = coopOf(state, pid);
    if (!coop || coop.over || coop.shared) return false;
    const partner = partnerOf(coop, pid);
    if (!state.projects[partner]) return false; // partner already completed
    return (openCounts(state, pid)[family] || 0) > 0 && (openCounts(state, partner)[family] || 0) > 0;
  }

  // Every attached factor (including jokers and shared factors), wherever it lies.
  function attachedFactors(state) {
    const result = [];
    for (let player = 0; player < state.seats.length; player += 1) {
      for (const pid of state.active[player]) {
        for (const entry of state.projects[pid].filled) result.push({ uid: entry.uid, family: entry.family, project: pid, shared: false });
      }
    }
    state.coops.forEach((coop, index) => {
      if (coop.shared) {
        const pid = state.projects[coop.a] ? coop.a : coop.b;
        result.push({ uid: coop.shared.uid, family: coop.shared.family, project: pid, shared: true, coop: index });
      }
    });
    return result;
  }
  const controllerOf = (state, uid, fallback) => (state.controller[uid] ?? fallback);
  function ownerOfAttached(state, uid) {
    const found = attachedFactors(state).find((entry) => entry.uid === uid);
    return found ? state.projects[found.project].owner : null;
  }

  /* ------------------------------------------------------------ setup */

  /**
   * seats: [{ name, kind: 'human' | 'bot', bot?: profile }], 2–4 entries.
   * rows: the objects of window.CARDS (data/cards.csv).
   */
  function newGame({ seats, rows, seed = Date.now() }) {
    if (!Array.isArray(seats) || seats.length < RULES.minPlayers || seats.length > RULES.maxPlayers) {
      throw new Error(`2 bis 4 Personen erwartet, erhalten: ${seats && seats.length}`);
    }
    const deck = stageDeck(rows);
    const state = {
      v: 1,
      seed: seed >>> 0,
      rng: seed >>> 0,
      seats: seats.map((seat) => ({ name: seat.name, kind: seat.kind, bot: seat.bot || null })),
      defs: deck.defs,
      cards: [],
      projectDeck: [],
      actionDeck: [],
      discard: [], // §3 offene Ablage, last card on top
      consumed: [], // §3 Verbrauchsstapel, face down
      limbo: [], // cards of an event that is still resolving
      hands: seats.map(() => []),
      active: seats.map(() => []),
      completed: seats.map(() => []),
      projects: {},
      coops: [],
      controller: {},
      round: 1,
      startPlayer: 0,
      current: 0,
      phase: 'draw',
      turn: null,
      turnNo: 0,
      pending: null,
      reshuffles: 0,
      log: [],
      logSeq: 0,
    };
    for (const id of deck.projects) state.projectDeck.push(state.cards.push(id) - 1);
    for (const id of deck.actions) state.actionDeck.push(state.cards.push(id) - 1);
    shuffle(state, state.projectDeck);
    shuffle(state, state.actionDeck);

    // §5.5: one project and two action cards each.
    for (let player = 0; player < seats.length; player += 1) {
      for (let i = 0; i < RULES.startProjects; i += 1) state.hands[player].push(state.projectDeck.pop());
      for (let i = 0; i < RULES.startActions; i += 1) {
        const uid = drawAction(state);
        if (uid !== null) state.hands[player].push(uid);
      }
    }
    // §5.6: random start person.
    state.startPlayer = Math.floor(random(state) * seats.length);
    state.current = state.startPlayer;
    log(state, `Neue Partie mit ${seats.length} Personen. Startperson: ${seatName(state, state.startPlayer)}.`, { kind: 'round' });
    beginTurn(state);
    return state;
  }

  /* ------------------------------------------------------------ piles */

  // §7: an empty action deck is replaced by the shuffled Verbrauchsstapel.
  function drawAction(state) {
    if (!state.actionDeck.length) {
      if (!state.consumed.length) return null;
      state.actionDeck = shuffle(state, state.consumed);
      state.consumed = [];
      state.reshuffles += 1;
      log(state, 'Der Verbrauchsstapel wird gemischt und ist der neue Aktionsstapel.', { kind: 'system' });
    }
    return state.actionDeck.pop();
  }

  function drawSources(state) {
    const sources = [];
    if (state.projectDeck.length) sources.push('project');
    if (state.actionDeck.length || state.consumed.length) sources.push('action');
    if (state.discard.length) sources.push('discard');
    return sources;
  }

  function consume(state, uid) {
    delete state.controller[uid];
    state.consumed.push(uid);
  }
  function fromLimbo(state, uid) {
    remove(state.limbo, uid);
    return uid;
  }

  /* ------------------------------------------------------------ turn flow */

  function beginTurn(state) {
    state.turnNo += 1;
    state.phase = 'draw';
    state.turn = { draws: 0, started: false, eventPlayed: false, mustStart: false, declined: [] };
    log(state, `Runde ${state.round} · Am Zug: ${seatName(state, state.current)}`, { kind: 'turn', player: state.current });
    if (!drawSources(state).length) enterActions(state);
  }

  function enterActions(state) {
    state.phase = 'action';
    const me = state.current;
    // §8.1: without an active project, a project from the hand must be started.
    state.turn.mustStart = !state.active[me].length && state.hands[me].some((uid) => isProject(state, uid));
  }

  function endTurn(state) {
    const next = (state.current + 1) % state.seats.length;
    if (next === state.startPlayer) {
      if (state.round >= RULES.rounds) {
        finish(state);
        return;
      }
      state.round += 1;
    }
    state.current = next;
    beginTurn(state);
  }

  function finish(state) {
    state.phase = 'over';
    state.pending = null;
    state.turn = null;
    const result = scores(state);
    const names = result.winners.map((player) => seatName(state, player)).join(' und ');
    log(state, `Partie beendet nach ${RULES.rounds} Runden. ${result.winners.length > 1 ? 'Geteilter Sieg' : 'Sieg'}: ${names}.`, { kind: 'round' });
  }

  /* ------------------------------------------------------------ legal actions */

  function actor(state) {
    if (state.phase === 'over') return null;
    return state.pending ? state.pending.player : state.current;
  }

  function legalActions(state) {
    if (state.phase === 'over') return [];
    if (state.pending) return pendingActions(state, state.pending);
    const me = state.current;
    if (state.phase === 'draw') return drawSources(state).map((source) => ({ type: 'draw', source }));
    if (state.phase === 'cleanup') return state.hands[me].map((uid) => ({ type: 'discard', uid }));

    const hand = state.hands[me];
    if (state.turn.mustStart) return hand.filter((uid) => isProject(state, uid)).map((uid) => ({ type: 'start', uid }));
    const actions = [];
    if (!state.turn.started) {
      for (const uid of hand) if (isProject(state, uid)) actions.push({ type: 'start', uid });
    }
    for (const uid of hand) {
      if (isFactor(state, uid)) actions.push(...attachments(state, me, uid, def(state, uid).families));
    }
    if (!state.turn.eventPlayed) {
      for (const uid of hand) if (isEvent(state, uid)) actions.push(...eventPlays(state, me, uid));
    }
    actions.push(...coopOffers(state, me));
    actions.push({ type: 'end' });
    return actions;
  }

  // §8.2 / §11: a factor goes to an own active project with a matching open
  // requirement, or between two cooperating projects that both need its type.
  function attachments(state, me, uid, families) {
    const actions = [];
    for (const pid of state.active[me]) {
      const open = openCounts(state, pid);
      for (const family of families) {
        if (!open[family]) continue;
        actions.push({ type: 'attach', uid, project: pid, family });
        if (canShare(state, pid, family) && !state.turn.declined.includes(`share:${uid}:${pid}:${family}`)) {
          actions.push({ type: 'attach', uid, project: pid, family, shared: true });
        }
      }
    }
    return actions;
  }

  function eventPlays(state, me, uid) {
    const spec = def(state, uid).spec;
    const plays = [];
    switch (spec.template) {
      case 'E1':
      case 'E2':
        return [{ type: 'event', uid }];
      case 'E3':
        for (const card of state.discard) if (isFactor(state, card)) plays.push({ type: 'event', uid, card });
        return plays;
      case 'E4':
        // A shared factor is not moved by Umverteilen (see website/README.md).
        for (const from of state.active[me]) {
          for (const entry of state.projects[from].filled) {
            for (const to of state.active[me]) {
              if (to !== from && openCounts(state, to)[entry.family]) plays.push({ type: 'event', uid, card: entry.uid, from, project: to });
            }
          }
        }
        return plays;
      case 'E5':
        for (const pid of state.active[me]) {
          const open = openCounts(state, pid);
          if (spec.onlyIfCompletes && total(open) !== 1) continue;
          for (const family of spec.families) {
            if (!open[family]) continue;
            plays.push({ type: 'event', uid, project: pid, family });
            if (canShare(state, pid, family) && !state.turn.declined.includes(`share:${uid}:${pid}:${family}`)) {
              plays.push({ type: 'event', uid, project: pid, family, shared: true });
            }
          }
        }
        return plays;
      case 'E6':
        // §13 E6: at most one surcharge per project, only on another person's project.
        for (let other = 0; other < state.seats.length; other += 1) {
          if (other === me) continue;
          for (const pid of state.active[other]) {
            if (state.projects[pid].extra) continue;
            plays.push(spec.chooser === 'target' ? { type: 'event', uid, project: pid } : { type: 'event', uid, project: pid, family: spec.families[0] });
          }
        }
        return plays;
      case 'E7':
        if (spec.scope === 'all') return [{ type: 'event', uid }];
        for (const entry of attachedFactors(state)) {
          if (spec.families.includes(entry.family)) plays.push({ type: 'event', uid, card: entry.uid });
        }
        return plays;
      default:
        return []; // E8 only as a reaction (§12)
    }
  }

  // §8.4 / §11: conditions for a cooperation between two active projects.
  function coopOffers(state, me) {
    const eligible = (pid) => state.projects[pid].coop === null && factorCount(state, pid) <= 1;
    const offers = [];
    const mine = state.active[me].filter(eligible);
    for (let other = 0; other < state.seats.length; other += 1) {
      if (other === me || activeCoopBetween(state, me, other)) continue;
      for (const project of mine) {
        for (const partner of state.active[other].filter(eligible)) {
          if (!state.turn.declined.includes(`coop:${project}:${partner}`)) offers.push({ type: 'coop', project, partner });
        }
      }
    }
    return offers;
  }

  function pendingActions(state, pending) {
    const player = pending.player;
    switch (pending.type) {
      case 'react':
        return [
          ...state.hands[player].filter((uid) => counterMatches(state, uid, pending.play)).map((uid) => ({ type: 'react', uid })),
          { type: 'pass' },
        ];
      case 'coop':
      case 'share':
        return [{ type: 'accept' }, { type: 'decline' }];
      case 'family':
        return FAMILIES.map((family) => ({ type: 'family', family }));
      case 'return':
        return controlledAttached(state, player).map((uid) => ({ type: 'return', uid }));
      case 'e1': {
        const actions = [];
        for (const keep of pending.seen) {
          const rest = pending.seen.filter((uid) => uid !== keep);
          for (const order of permutations(rest)) actions.push({ type: 'e1', keep, rest: order });
        }
        return actions;
      }
      default:
        throw new Error(`unknown pending decision: ${pending.type}`);
    }
  }

  function permutations(list) {
    if (list.length <= 1) return [list.slice()];
    return list.flatMap((item, index) => permutations([...list.slice(0, index), ...list.slice(index + 1)]).map((rest) => [item, ...rest]));
  }

  function controlledAttached(state, player) {
    return attachedFactors(state).filter((entry) => controllerOf(state, entry.uid, state.projects[entry.project].owner) === player).map((entry) => entry.uid);
  }

  /* ------------------------------------------------------------ apply */

  const canonical = (action) => JSON.stringify(Object.keys(action).sort().reduce((acc, key) => { acc[key] = action[key]; return acc; }, {}));
  const sameAction = (a, b) => canonical(a) === canonical(b);

  function isLegal(state, action) {
    return legalActions(state).some((candidate) => sameAction(candidate, action));
  }

  function apply(state, action) {
    if (!isLegal(state, action)) throw new Error(`Unzulässiger Zug: ${JSON.stringify(action)}`);
    if (state.pending) {
      resolvePending(state, action);
    } else if (state.phase === 'draw') {
      draw(state, action.source);
    } else if (state.phase === 'cleanup') {
      discardCard(state, action.uid);
    } else {
      actionPhase(state, action);
    }
    return state;
  }

  function draw(state, source) {
    const me = state.current;
    let uid;
    if (source === 'project') {
      uid = state.projectDeck.pop();
      log(state, `${seatName(state, me)}: Karte vom Projektstapel gezogen.`, { player: me });
    } else if (source === 'discard') {
      uid = state.discard.pop();
      log(state, `${seatName(state, me)}: ${nameOf(state, uid)} von der offenen Ablage genommen.`, { player: me });
    } else {
      uid = drawAction(state);
      log(state, `${seatName(state, me)}: Karte vom Aktionsstapel gezogen.`, { player: me });
    }
    state.hands[me].push(uid);
    state.turn.draws += 1;
    if (state.turn.draws >= RULES.drawsPerTurn || !drawSources(state).length) enterActions(state);
  }

  function discardCard(state, uid) {
    const me = state.current;
    remove(state.hands[me], uid);
    state.discard.push(uid);
    log(state, `${seatName(state, me)}: ${nameOf(state, uid)} auf die offene Ablage gelegt.`, { player: me });
    if (state.hands[me].length <= RULES.handLimit) endTurn(state);
  }

  function actionPhase(state, action) {
    const me = state.current;
    switch (action.type) {
      case 'start': {
        remove(state.hands[me], action.uid);
        state.active[me].push(action.uid);
        state.projects[action.uid] = { owner: me, filled: [], extra: null, coop: null };
        state.turn.started = true;
        state.turn.mustStart = false;
        log(state, `${seatName(state, me)}: Projekt ${nameOf(state, action.uid)} begonnen (${def(state, action.uid).points} Punkte).`, { player: me });
        return;
      }
      case 'attach':
        if (action.shared) {
          askShare(state, me, action);
          return;
        }
        attach(state, me, action);
        return;
      case 'event':
        if (action.shared) {
          askShare(state, me, action);
          return;
        }
        playEvent(state, me, action);
        return;
      case 'coop': {
        const partnerOwner = state.projects[action.partner].owner;
        state.pending = { type: 'coop', player: partnerOwner, by: me, offer: action };
        log(state, `${seatName(state, me)}: Kooperation mit ${seatName(state, partnerOwner)} angeboten – ${nameOf(state, action.project)} mit ${nameOf(state, action.partner)}.`, { player: me });
        return;
      }
      case 'end':
        state.phase = 'cleanup';
        if (state.hands[me].length <= RULES.handLimit) endTurn(state);
        return;
      default:
        throw new Error(`unknown action: ${action.type}`);
    }
  }

  // §11: both people agree to share a factor.
  function askShare(state, me, action) {
    const coop = coopOf(state, action.project);
    const partner = partnerOf(coop, action.project);
    state.pending = { type: 'share', player: state.projects[partner].owner, by: me, proposal: action };
    log(state, `${seatName(state, me)}: ${nameOf(state, action.uid)} als gemeinsamen Faktor (${FAMILY[action.family]}) zwischen ${nameOf(state, action.project)} und ${nameOf(state, partner)} vorgeschlagen.`, { player: me });
  }

  function attach(state, me, action) {
    remove(state.hands[me], action.uid);
    placeFactor(state, me, action);
    const where = action.shared
      ? `als gemeinsamer Faktor zwischen ${nameOf(state, action.project)} und ${nameOf(state, partnerOf(coopOf(state, action.project), action.project))}`
      : `an ${nameOf(state, action.project)}`;
    log(state, `${seatName(state, me)}: ${nameOf(state, action.uid)} ${where} angelegt (${FAMILY[action.family]}).`, { player: me });
    resolveCompletions(state);
  }

  function placeFactor(state, me, action) {
    state.controller[action.uid] = me;
    if (action.shared) coopOf(state, action.project).shared = { uid: action.uid, family: action.family };
    else state.projects[action.project].filled.push({ uid: action.uid, family: action.family });
  }

  /* ------------------------------------------------------------ events */

  function describeTarget(state, action) {
    const spec = def(state, action.uid).spec;
    switch (spec.template) {
      case 'E3': return ` – holt ${nameOf(state, action.card)} aus der offenen Ablage`;
      case 'E4': return ` – verschiebt ${nameOf(state, action.card)} von ${nameOf(state, action.from)} nach ${nameOf(state, action.project)}`;
      case 'E5': return ` – an ${nameOf(state, action.project)} als ${FAMILY_FACTOR[action.family]}`;
      case 'E6': return ` – gegen ${nameOf(state, action.project)} von ${seatName(state, state.projects[action.project].owner)}`;
      case 'E7':
        if (spec.scope === 'all') return ' – jede Person nimmt einen eigenen angelegten Faktor zurück';
        return ` – gegen ${nameOf(state, action.card)} an ${nameOf(state, attachedFactors(state).find((entry) => entry.uid === action.card).project)}`;
      default: return '';
    }
  }

  // §12: show, name targets, open the reaction window, resolve, consume.
  function playEvent(state, me, action) {
    const card = def(state, action.uid);
    remove(state.hands[me], action.uid);
    state.limbo.push(action.uid);
    state.turn.eventPlayed = true;
    log(state, `${seatName(state, me)}: Ereignis ${nameOf(state, action.uid)} gespielt${describeTarget(state, action)}.`, { player: me, kind: 'event' });

    if (card.polarity === 'negative') {
      const queue = reactionQueue(state, me, action);
      if (queue.length) {
        state.pending = { type: 'react', player: queue[0], queue: queue.slice(1), by: me, play: action };
        return;
      }
    }
    resolveEvent(state, me, action);
  }

  function victimOf(state, action) {
    const spec = def(state, action.uid).spec;
    if (spec.template === 'E6') return state.projects[action.project].owner;
    if (spec.template === 'E7' && spec.scope !== 'all') {
      return controllerOf(state, action.card, ownerOfAttached(state, action.card));
    }
    return null;
  }

  // §12: the affected person first, then everyone else from the left of the
  // active person. Only people holding a matching Absicherung are asked.
  function reactionQueue(state, me, action) {
    const victim = victimOf(state, action);
    const order = [];
    if (victim !== null && victim !== me) order.push(victim);
    for (let step = 1; step < state.seats.length; step += 1) {
      const player = (me + step) % state.seats.length;
      if (!order.includes(player)) order.push(player);
    }
    return order.filter((player) => state.hands[player].some((uid) => counterMatches(state, uid, action)));
  }

  function counterMatches(state, uid, play) {
    if (!isEvent(state, uid)) return false;
    const spec = def(state, uid).spec;
    if (spec.template !== 'E8') return false;
    const target = def(state, play.uid).spec;
    if (spec.counters === 'rueckschlag') return target.template === 'E7';
    if (spec.counters === 'mehraufwand') return target.template === 'E6';
    if (spec.counters === 'single') return target.scope !== 'all';
    return true;
  }

  function resolveEvent(state, me, action) {
    const spec = def(state, action.uid).spec;
    const who = seatName(state, me);
    switch (spec.template) {
      case 'E1': { // Sichten
        const seen = [];
        for (let i = 0; i < spec.look; i += 1) {
          const uid = drawAction(state);
          if (uid === null) break;
          seen.push(uid);
          state.limbo.push(uid);
        }
        if (!seen.length) {
          log(state, 'Keine Karte mehr im Aktionsstapel.', { kind: 'system' });
          consume(state, fromLimbo(state, action.uid));
          return;
        }
        state.pending = { type: 'e1', player: me, seen, event: action.uid };
        return;
      }
      case 'E2': { // Nachziehen: set revealed events aside, they are not reshuffled
        const found = [];
        const aside = [];
        while (found.length < spec.take) {
          const uid = drawAction(state);
          if (uid === null) break;
          if (isFactor(state, uid)) {
            found.push(uid);
            state.hands[me].push(uid);
          } else {
            aside.push(uid);
            state.limbo.push(uid);
          }
        }
        const parts = [found.length ? `${found.map((uid) => nameOf(state, uid)).join(', ')} auf die Hand` : 'kein Faktor gefunden'];
        if (aside.length) parts.push(`${aside.map((uid) => nameOf(state, uid)).join(', ')} verbraucht`);
        log(state, `${who}: aufgedeckt – ${parts.join('; ')}.`, { player: me });
        for (const uid of aside) consume(state, fromLimbo(state, uid));
        consume(state, fromLimbo(state, action.uid));
        return;
      }
      case 'E3': // Rückholen: any factor of the open discard pile
        remove(state.discard, action.card);
        state.hands[me].push(action.card);
        consume(state, fromLimbo(state, action.uid));
        return;
      case 'E4': { // Umverteilen: the controller and the chosen type stay
        const from = state.projects[action.from];
        const entry = from.filled.find((item) => item.uid === action.card);
        from.filled.splice(from.filled.indexOf(entry), 1);
        state.projects[action.project].filled.push(entry);
        consume(state, fromLimbo(state, action.uid));
        resolveCompletions(state);
        return;
      }
      case 'E5': // Joker: counts as a factor of the chosen type while attached
        fromLimbo(state, action.uid);
        placeFactor(state, me, action);
        resolveCompletions(state);
        return;
      case 'E6': // Mehraufwand
        if (spec.chooser === 'target') {
          state.pending = { type: 'family', player: state.projects[action.project].owner, by: me, project: action.project, event: action.uid };
          return;
        }
        addSurcharge(state, action.project, fromLimbo(state, action.uid), action.family);
        return;
      case 'E7':
        if (spec.scope === 'all') {
          const queue = [];
          for (let step = 0; step < state.seats.length; step += 1) queue.push((me + step) % state.seats.length);
          continueReturns(state, queue, action.uid);
          return;
        }
        returnFactor(state, action.card);
        consume(state, fromLimbo(state, action.uid));
        return;
      default:
        consume(state, fromLimbo(state, action.uid));
    }
  }

  function addSurcharge(state, pid, uid, family) {
    state.projects[pid].extra = { uid, family };
    log(state, `${nameOf(state, pid)} braucht zusätzlich eine ${FAMILY_REQ[family]}.`, { player: state.projects[pid].owner });
  }

  // §13 E7: back to the hand of the controlling person; sharing ends.
  function returnFactor(state, uid) {
    const entry = attachedFactors(state).find((item) => item.uid === uid);
    const owner = state.projects[entry.project].owner;
    if (entry.shared) {
      state.coops[entry.coop].shared = null;
    } else {
      const project = state.projects[entry.project];
      project.filled.splice(project.filled.findIndex((item) => item.uid === uid), 1);
    }
    const controller = controllerOf(state, uid, owner);
    delete state.controller[uid];
    state.hands[controller].push(uid);
    log(state, `${seatName(state, controller)}: ${nameOf(state, uid)} zurück auf die Hand bekommen${entry.shared ? ', die gemeinsame Nutzung endet' : ''}.`, { player: controller });
  }

  // "Jede Person nimmt einen von ihr kontrollierten angelegten Projektfaktor
  // auf die Hand zurück": people with a single option do not need to decide.
  function continueReturns(state, queue, event) {
    while (queue.length) {
      const player = queue.shift();
      const options = controlledAttached(state, player);
      if (!options.length) continue;
      if (options.length === 1) {
        returnFactor(state, options[0]);
        continue;
      }
      state.pending = { type: 'return', player, queue, event };
      return;
    }
    state.pending = null;
    consume(state, fromLimbo(state, event));
  }

  /* ------------------------------------------------------------ decisions */

  function resolvePending(state, action) {
    const pending = state.pending;
    const me = pending.player;
    switch (pending.type) {
      case 'react': {
        if (action.type === 'pass') {
          if (pending.queue.length) {
            state.pending = { ...pending, player: pending.queue[0], queue: pending.queue.slice(1) };
          } else {
            state.pending = null;
            resolveEvent(state, pending.by, pending.play);
          }
          return;
        }
        // §12: Absicherung and the negative event are both consumed.
        remove(state.hands[me], action.uid);
        consume(state, action.uid);
        consume(state, fromLimbo(state, pending.play.uid));
        state.pending = null;
        log(state, `${seatName(state, me)}: Absicherung ${nameOf(state, action.uid)} gespielt – ${nameOf(state, pending.play.uid)} wirkt nicht.`, { player: me, kind: 'event' });
        return;
      }
      case 'coop': {
        const offer = pending.offer;
        state.pending = null;
        if (action.type === 'decline') {
          state.turn.declined.push(`coop:${offer.project}:${offer.partner}`);
          log(state, `${seatName(state, me)}: Kooperation abgelehnt.`, { player: me });
          return;
        }
        const index = state.coops.push({ a: offer.project, b: offer.partner, owners: [pending.by, me], shared: null, closed: [], over: false }) - 1;
        state.projects[offer.project].coop = index;
        state.projects[offer.partner].coop = index;
        log(state, `${seatName(state, me)}: Kooperation angenommen – ${nameOf(state, offer.project)} und ${nameOf(state, offer.partner)} kooperieren.`, { player: me, kind: 'event' });
        return;
      }
      case 'share': {
        const proposal = pending.proposal;
        state.pending = null;
        if (action.type === 'decline') {
          state.turn.declined.push(`share:${proposal.uid}:${proposal.project}:${proposal.family}`);
          log(state, `${seatName(state, me)}: gemeinsame Nutzung abgelehnt.`, { player: me });
          return;
        }
        log(state, `${seatName(state, me)}: gemeinsamer Nutzung zugestimmt.`, { player: me });
        if (proposal.type === 'attach') attach(state, pending.by, proposal);
        else playEvent(state, pending.by, proposal);
        return;
      }
      case 'family':
        state.pending = null;
        log(state, `${seatName(state, me)}: ${FAMILY[action.family]} gewählt.`, { player: me });
        addSurcharge(state, pending.project, fromLimbo(state, pending.event), action.family);
        return;
      case 'return':
        returnFactor(state, action.uid);
        continueReturns(state, pending.queue.slice(), pending.event);
        return;
      case 'e1': {
        // The kept card goes to the hand; the rest under the action deck,
        // `rest` in the order in which they will be drawn.
        for (const uid of pending.seen) remove(state.limbo, uid);
        state.hands[me].push(action.keep);
        state.actionDeck = [...action.rest].reverse().concat(state.actionDeck);
        state.pending = null;
        log(state, `${seatName(state, me)}: eine von ${pending.seen.length} Karten auf die Hand genommen${action.rest.length ? ', die übrigen kommen unter den Aktionsstapel' : ''}.`, { player: me });
        consume(state, fromLimbo(state, pending.event));
        return;
      }
      default:
        throw new Error(`unknown pending decision: ${pending.type}`);
    }
  }

  /* ------------------------------------------------------------ completion */

  // §10 / §17: fulfilled projects close at once, the active person's first.
  function resolveCompletions(state) {
    let changed = true;
    while (changed) {
      changed = false;
      for (let step = 0; step < state.seats.length; step += 1) {
        const player = (state.current + step) % state.seats.length;
        for (const pid of state.active[player].slice()) {
          if (state.projects[pid] && isComplete(state, pid)) {
            closeProject(state, pid);
            changed = true;
          }
        }
      }
    }
  }

  function closeProject(state, pid) {
    const project = state.projects[pid];
    const owner = project.owner;
    remove(state.active[owner], pid);
    state.completed[owner].push(pid);
    for (const entry of project.filled) consume(state, entry.uid);
    if (project.extra) consume(state, project.extra.uid);
    const coop = coopOf(state, pid);
    delete state.projects[pid];
    if (coop) {
      coop.closed.push(pid);
      // §11: the shared factor stays while the partner project still needs it.
      if (coop.closed.length === 2) {
        if (coop.shared) consume(state, coop.shared.uid);
        coop.shared = null;
        coop.over = true;
      }
    }
    log(state, `${seatName(state, owner)}: Projekt ${nameOf(state, pid)} abgeschlossen (+${def(state, pid).points}).`, { player: owner, kind: 'complete' });
  }

  /* ------------------------------------------------------------ scoring */

  // §16: completed points minus one per active, unfinished project.
  function scores(state) {
    const rows = state.seats.map((seat, player) => {
      const plus = state.completed[player].reduce((sum, uid) => sum + def(state, uid).points, 0);
      const unfinished = state.active[player].length;
      const minus = unfinished * RULES.minusPerActive;
      return { player, name: seat.name, plus, minus, total: plus - minus, completed: state.completed[player].length, unfinished };
    });
    let top = rows.slice();
    const best = Math.max(...top.map((row) => row.total));
    top = top.filter((row) => row.total === best);
    if (top.length > 1) {
      const most = Math.max(...top.map((row) => row.completed));
      top = top.filter((row) => row.completed === most);
    }
    if (top.length > 1) {
      const least = Math.min(...top.map((row) => row.unfinished));
      top = top.filter((row) => row.unfinished === least);
    }
    return { rows, winners: top.map((row) => row.player) };
  }

  /* ------------------------------------------------------------ descriptions */

  // One German line per legal action, for buttons.
  function describe(state, action) {
    const p = state.pending;
    switch (action.type) {
      case 'draw':
        if (action.source === 'project') return `Vom Projektstapel ziehen (${state.projectDeck.length})`;
        if (action.source === 'action') return `Vom Aktionsstapel ziehen (${state.actionDeck.length || state.consumed.length})`;
        return `${nameOf(state, state.discard[state.discard.length - 1])} von der offenen Ablage nehmen`;
      case 'start': return `${nameOf(state, action.uid)} beginnen`;
      case 'attach':
        if (action.shared) return `Gemeinsam mit ${nameOf(state, partnerOf(coopOf(state, action.project), action.project))} nutzen · ${FAMILY[action.family]}`;
        return `An ${nameOf(state, action.project)} anlegen · ${FAMILY[action.family]}`;
      case 'event': {
        const spec = def(state, action.uid).spec;
        switch (spec.template) {
          case 'E3': return `${nameOf(state, action.card)} aus der Ablage holen`;
          case 'E4': return `${nameOf(state, action.card)} von ${nameOf(state, action.from)} nach ${nameOf(state, action.project)} verschieben`;
          case 'E5':
            if (action.shared) return `Als gemeinsamen Faktor mit ${nameOf(state, partnerOf(coopOf(state, action.project), action.project))} anlegen · ${FAMILY[action.family]}`;
            return `An ${nameOf(state, action.project)} anlegen · ${FAMILY[action.family]}`;
          case 'E6': {
            const target = `${nameOf(state, action.project)} von ${seatName(state, state.projects[action.project].owner)}`;
            return action.family ? `An ${target} legen · +1 ${FAMILY[action.family]}` : `An ${target} legen`;
          }
          case 'E7': {
            if (spec.scope === 'all') return `${nameOf(state, action.uid)} ausspielen`;
            const entry = attachedFactors(state).find((item) => item.uid === action.card);
            const owner = seatName(state, controllerOf(state, action.card, state.projects[entry.project].owner));
            return `${nameOf(state, action.card)} an ${nameOf(state, entry.project)} zurück zu ${owner}`;
          }
          default: return `${nameOf(state, action.uid)} ausspielen`;
        }
      }
      case 'coop': return `${nameOf(state, action.project)} mit ${nameOf(state, action.partner)} von ${seatName(state, state.projects[action.partner].owner)}`;
      case 'end': return 'Zug beenden';
      case 'discard': return `${nameOf(state, action.uid)} abwerfen`;
      case 'react': return `${nameOf(state, action.uid)} spielen`;
      case 'pass': return 'Nicht reagieren';
      case 'accept': return p && p.type === 'share' ? 'Gemeinsam nutzen' : 'Kooperation annehmen';
      case 'decline': return 'Ablehnen';
      case 'family': return FAMILY[action.family];
      case 'return': return `${nameOf(state, action.uid)} zurücknehmen`;
      case 'e1': return `${nameOf(state, action.keep)} nehmen`;
      default: return action.type;
    }
  }

  /* ------------------------------------------------------------ checks */

  // Every physical card lies in exactly one place. Used by the tests.
  function checkInvariants(state) {
    const seen = new Map();
    const note = (uid, where) => {
      if (seen.has(uid)) throw new Error(`card ${uid} (${state.cards[uid]}) in ${seen.get(uid)} and ${where}`);
      seen.set(uid, where);
    };
    state.projectDeck.forEach((uid) => note(uid, 'projectDeck'));
    state.actionDeck.forEach((uid) => note(uid, 'actionDeck'));
    state.discard.forEach((uid) => note(uid, 'discard'));
    state.consumed.forEach((uid) => note(uid, 'consumed'));
    state.limbo.forEach((uid) => note(uid, 'limbo'));
    state.hands.forEach((hand, player) => hand.forEach((uid) => note(uid, `hand ${player}`)));
    state.completed.forEach((list, player) => list.forEach((uid) => note(uid, `completed ${player}`)));
    for (const [pid, project] of Object.entries(state.projects)) {
      note(Number(pid), `active ${project.owner}`);
      if (!state.active[project.owner].includes(Number(pid))) throw new Error(`project ${pid} missing from active list`);
      project.filled.forEach((entry) => note(entry.uid, `project ${pid}`));
      if (project.extra) note(project.extra.uid, `surcharge ${pid}`);
      const open = requirementCounts(state, Number(pid));
      const have = filledCounts(state, Number(pid));
      for (const family of FAMILIES) {
        if ((have[family] || 0) > (open[family] || 0)) throw new Error(`project ${pid} overfilled with ${family}`);
      }
    }
    state.coops.forEach((coop, index) => { if (coop.shared) note(coop.shared.uid, `shared ${index}`); });
    if (seen.size !== state.cards.length) throw new Error(`${state.cards.length - seen.size} cards lost`);
    if (state.projectDeck.some((uid) => !isProject(state, uid))) throw new Error('non-project in project deck');
    return true;
  }

  /* ------------------------------------------------------------ player view */

  // Safe subset of state for network transmission to one specific seat.
  // Masks hidden card identities (other hands, draw decks, consumed pile)
  // while preserving array lengths so that UI counters and legalActions work.
  function playerView(state, seatIndex) {
    if (seatIndex < 0 || seatIndex >= state.seats.length) {
      throw new Error(`Ungültiger Sitz: ${seatIndex}`);
    }
    const view = {
      ...state,
      seed: null,
      rng: null,
      projectDeck: state.projectDeck.map(() => null),
      actionDeck: state.actionDeck.map(() => null),
      consumed: state.consumed.map(() => null),
      limbo: state.limbo.map((uid) => {
        if (state.pending && state.pending.type === 'e1' && state.pending.player === seatIndex) {
          return uid;
        }
        return null;
      }),
      hands: state.hands.map((hand, index) => (index === seatIndex ? hand.slice() : hand.map(() => null))),
    };

    if (state.pending) {
      if (state.pending.type === 'e1') {
        view.pending = {
          ...state.pending,
          seen: state.pending.player === seatIndex ? state.pending.seen.slice() : state.pending.seen.map(() => null),
        };
      } else {
        view.pending = { ...state.pending };
      }
    }

    return view;
  }

  return {
    RULES,
    FAMILIES,
    FAMILY,
    FAMILY_FACTOR,
    FAMILY_REQ,
    KEYWORD,
    parseEvent,
    stageDeck,
    newGame,
    legalActions,
    isLegal,
    apply,
    actor,
    describe,
    scores,
    checkInvariants,
    playerView,
    // read helpers for the page and the bots
    def,
    openCounts,
    requirementCounts,
    isComplete,
    factorCount,
    coopOf,
    partnerOf,
    attachedFactors,
    controllerOf,
    drawSources,
  };
});

