/* Busfaktor: 1 — computer opponents of the browser game.

   Port of scripts/sim/strategies.py. The simulator's engine also chose event
   targets, Absicherungen and cooperations on the bots' behalf
   (engine.Game._build_play, try_counter, offer_cooperation); those heuristics
   live here, because in the browser engine every choice is a legal action.
   choose(state, player) always returns one of legalActions(state). */
(function (root, factory) {
  const api = factory(root.BusfaktorEngine || (typeof require === 'function' ? require('./game-engine.js') : null));
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.BusfaktorBots = api;
})(typeof self !== 'undefined' ? self : this, (E) => {
  'use strict';

  // Profiles after the simulator's strategies: open-1-safe (the best open
  // line in scripts/README.md), hoard, and coop.
  const PROFILES = {
    umsichtig: { label: 'Umsichtig', hint: 'ein Projekt nach dem anderen', maxActive: 1, slack: 1, prefer: 'cheap', hoard: false, coop: false },
    abwartend: { label: 'Abwartend', hint: 'beginnt erst, wenn es gleich fertig wird', maxActive: 1, slack: 1, prefer: 'cheap', hoard: true, coop: false },
    kooperativ: { label: 'Kooperativ', hint: 'zwei Projekte zugleich, bietet Kooperationen an', maxActive: 2, slack: 1, prefer: 'cheap', hoard: false, coop: true },
  };

  const def = (state, uid) => E.def(state, uid);
  const isFactor = (state, uid) => def(state, uid).type === 'Projektfaktor';
  const isProject = (state, uid) => def(state, uid).type === 'Projekt';
  const sum = (counts) => Object.values(counts).reduce((acc, value) => acc + value, 0);
  const addCounts = (target, source) => { for (const [key, value] of Object.entries(source)) target[key] = (target[key] || 0) + value; return target; };
  const countList = (list) => list.reduce((acc, key) => { acc[key] = (acc[key] || 0) + 1; return acc; }, {});

  /* ------------------------------------------------------------ planning */

  const handFactors = (state, player) => state.hands[player].filter((uid) => isFactor(state, uid));
  const handProjects = (state, player) => state.hands[player].filter((uid) => isProject(state, uid));

  function activeNeeds(state, player) {
    const need = {};
    for (const pid of state.active[player]) addCounts(need, E.openCounts(state, pid));
    return need;
  }

  // deck.can_satisfy: single-type factors first, wildcards by backtracking.
  function canSatisfy(requirements, factors, state) {
    const need = { ...requirements };
    const flexible = [];
    for (const uid of factors) {
      const families = def(state, uid).families;
      if (families.length === 1) {
        if (need[families[0]] > 0) need[families[0]] -= 1;
      } else flexible.push(families);
    }
    const assign = (index) => {
      if (Object.values(need).every((value) => value <= 0)) return true;
      if (index >= flexible.length) return false;
      for (const family of flexible[index]) {
        if (need[family] > 0) {
          need[family] -= 1;
          if (assign(index + 1)) return true;
          need[family] += 1;
        }
      }
      return assign(index + 1);
    };
    return assign(0);
  }

  const canCompleteNow = (state, player, pid) => canSatisfy(countList(def(state, pid).requirements), handFactors(state, player), state);

  function spareFactors(state, player) {
    const need = activeNeeds(state, player);
    const spare = [];
    const sorted = handFactors(state, player).slice().sort((a, b) => def(state, a).families.length - def(state, b).families.length);
    for (const uid of sorted) {
      const family = def(state, uid).families.find((item) => need[item] > 0);
      if (family) need[family] -= 1;
      else spare.push(uid);
    }
    return spare;
  }

  function missingFor(state, player, pid) {
    const need = countList(def(state, pid).requirements);
    for (const uid of spareFactors(state, player)) {
      const family = def(state, uid).families.find((item) => need[item] > 0);
      if (family) need[family] -= 1;
    }
    return sum(need);
  }

  function rankProjects(state, player, profile, projects) {
    const key = (uid) => [canCompleteNow(state, player, uid) ? 0 : 1, profile.prefer === 'cheap' ? def(state, uid).points : -def(state, uid).points, uid];
    return projects.slice().sort((a, b) => {
      const ka = key(a);
      const kb = key(b);
      for (let i = 0; i < ka.length; i += 1) if (ka[i] !== kb[i]) return ka[i] - kb[i];
      return 0;
    });
  }

  function plannedProject(state, player, profile) {
    const projects = handProjects(state, player);
    return projects.length ? rankProjects(state, player, profile, projects)[0] : null;
  }

  function planNeeds(state, player, profile) {
    const need = activeNeeds(state, player);
    const planned = plannedProject(state, player, profile);
    if (planned !== null) addCounts(need, countList(def(state, planned).requirements));
    return need;
  }

  function cardValue(state, player, profile, uid) {
    const card = def(state, uid);
    if (card.type === 'Projektfaktor') {
      const need = planNeeds(state, player, profile);
      const hit = Math.max(0, ...card.families.map((family) => need[family] || 0));
      return (hit > 0 ? 10 : 3) + (card.families.length > 1 ? 0.5 : 0);
    }
    if (card.type === 'Projekt') return plannedProject(state, player, profile) === uid ? 10.5 : 2;
    return card.spec.template === 'E8' ? 6 : 5;
  }

  function wantsProjectCard(state, player, profile) {
    const inHand = handProjects(state, player).length;
    const pipeline = state.active[player].length + inHand;
    if (profile.hoard) return pipeline === 0;
    if (pipeline === 0) return true;
    if (inHand || state.round >= E.RULES.rounds) return false;
    if (state.active[player].length < profile.maxActive && spareFactors(state, player).length >= 2) return true;
    return state.active[player].every((pid) => sum(E.openCounts(state, pid)) <= 1);
  }

  /* ------------------------------------------------------------ phases */

  function chooseSource(state, player, profile, actions) {
    const sources = actions.map((action) => action.source);
    if (sources.includes('discard')) {
      const top = state.discard[state.discard.length - 1];
      if (isFactor(state, top)) {
        const need = planNeeds(state, player, profile);
        if (def(state, top).families.some((family) => need[family] > 0)) return 'discard';
      }
    }
    if (sources.includes('project') && wantsProjectCard(state, player, profile)) return 'project';
    if (sources.includes('action')) return 'action';
    return sources[0];
  }

  function chooseStart(state, player, profile) {
    const projects = handProjects(state, player);
    if (!projects.length) return null;
    const ranked = rankProjects(state, player, profile, projects);
    const finishable = ranked.find((uid) => canCompleteNow(state, player, uid));
    if (finishable !== undefined) return finishable;
    // A start without a chance to finish only brings a minus point.
    if (profile.hoard || state.round === E.RULES.rounds) return null;
    if (state.active[player].length >= profile.maxActive) return null;
    const slack = Math.max(0, Math.min(profile.slack, E.RULES.rounds - state.round - 1));
    return ranked.find((uid) => missingFor(state, player, uid) <= slack) ?? null;
  }

  function chooseAttach(state, attaches) {
    const key = (action) => {
      const openAfter = sum(E.openCounts(state, action.project)) - 1;
      return [openAfter === 0 ? 0 : 1, openAfter, -def(state, action.project).points, def(state, action.uid).families.length > 1 ? 1 : 0, action.uid, action.shared ? 0 : 1];
    };
    return attaches.slice().sort((a, b) => {
      const ka = key(a);
      const kb = key(b);
      for (let i = 0; i < ka.length; i += 1) if (ka[i] !== kb[i]) return ka[i] - kb[i];
      return 0;
    })[0];
  }

  // engine.Game._build_play: a value per play; played from 1.0 upwards.
  function eventValue(state, player, profile, action) {
    const spec = def(state, action.uid).spec;
    const own = (pid) => state.projects[pid].owner === player;
    switch (spec.template) {
      case 'E1': return 1.0;
      case 'E2': return 1.5;
      case 'E3': {
        const need = planNeeds(state, player, profile);
        const useful = def(state, action.card).families.some((family) => need[family] > 0);
        // prefer the topmost useful factor, as the simulator does
        return (useful ? 2.0 : 0.5) + state.discard.indexOf(action.card) / 1000;
      }
      case 'E4': {
        const open = E.openCounts(state, action.project);
        return sum(open) === 1 ? 3.0 : 0;
      }
      case 'E5': {
        const completes = sum(E.openCounts(state, action.project)) === 1;
        return (completes ? 3.0 : 1.2) + (action.shared ? 0.1 : 0);
      }
      case 'E6': {
        const pid = action.project;
        return 1.0 + E.factorCount(state, pid) / Math.max(1, def(state, pid).points);
      }
      case 'E7': {
        if (spec.scope === 'all') {
          // hits everyone: only worth it when others lose more than we do
          const lost = (who) => E.attachedFactors(state).some((entry) => E.controllerOf(state, entry.uid, state.projects[entry.project].owner) === who);
          const others = state.seats.some((_, who) => who !== player && lost(who));
          return others && !lost(player) ? 1.5 : 0;
        }
        const entry = E.attachedFactors(state).find((item) => item.uid === action.card);
        if (own(entry.project) || E.controllerOf(state, entry.uid, player) === player) return 0;
        const coop = E.coopOf(state, entry.project);
        if (coop && coop.owners.includes(player)) return 0;
        return 1.0 + def(state, entry.project).points / 4 + E.factorCount(state, entry.project) / 4;
      }
      default: return 0;
    }
  }

  function bestEvent(state, player, profile, events) {
    let best = null;
    let bestValue = -Infinity;
    for (const action of events) {
      const value = eventValue(state, player, profile, action);
      if (value > bestValue) { best = action; bestValue = value; }
    }
    return bestValue >= 1.0 ? best : null;
  }

  // A cooperation only helps when both projects need a common factor type.
  function overlap(state, one, two) {
    const a = E.openCounts(state, one);
    const b = E.openCounts(state, two);
    return Object.keys(a).some((family) => b[family] > 0);
  }

  function chooseDiscard(state, player, profile) {
    let worst = null;
    let worstKey = null;
    for (const uid of state.hands[player]) {
      const key = [cardValue(state, player, profile, uid), uid];
      if (!worstKey || key[0] < worstKey[0] || (key[0] === worstKey[0] && key[1] < worstKey[1])) { worst = uid; worstKey = key; }
    }
    return worst;
  }

  /* ------------------------------------------------------------ entry */

  function profileOf(state, player) {
    return PROFILES[state.seats[player].bot] || PROFILES.umsichtig;
  }

  function choose(state, player) {
    const actions = E.legalActions(state);
    if (!actions.length) throw new Error('no legal action');
    const profile = profileOf(state, player);
    const find = (type) => actions.find((action) => action.type === type);
    const pending = state.pending;

    if (pending) {
      switch (pending.type) {
        case 'react': return find('react') || find('pass'); // engine.try_counter: always
        case 'coop': return overlap(state, pending.offer.project, pending.offer.partner) ? find('accept') : find('decline');
        case 'share': return find('accept');
        case 'family': { // engine._victim_choice: the type the hand covers best
          const supply = {};
          for (const uid of handFactors(state, player)) for (const family of def(state, uid).families) supply[family] = (supply[family] || 0) + 1;
          return actions.slice().sort((a, b) => (supply[b.family] || 0) - (supply[a.family] || 0) || (a.family < b.family ? 1 : -1))[0];
        }
        case 'return': { // engine._return_worst_factor: from the cheapest project
          const where = (uid) => E.attachedFactors(state).find((entry) => entry.uid === uid).project;
          return actions.slice().sort((a, b) => def(state, where(a.uid)).points - def(state, where(b.uid)).points)[0];
        }
        case 'e1': {
          const keep = pending.seen.slice().sort((a, b) => cardValue(state, player, profile, b) - cardValue(state, player, profile, a))[0];
          return actions.find((action) => action.keep === keep);
        }
        default: return actions[0];
      }
    }

    if (state.phase === 'draw') {
      const source = chooseSource(state, player, profile, actions);
      return actions.find((action) => action.source === source);
    }
    if (state.phase === 'cleanup') {
      const uid = chooseDiscard(state, player, profile);
      return actions.find((action) => action.uid === uid);
    }

    // Action phase, in the simulator's order: start, attach, event, cooperation.
    if (state.turn.mustStart) {
      const uid = rankProjects(state, player, profile, handProjects(state, player))[0];
      return actions.find((action) => action.uid === uid);
    }
    if (!state.turn.started) {
      const uid = chooseStart(state, player, profile);
      if (uid !== null) return actions.find((action) => action.type === 'start' && action.uid === uid);
    }
    const attaches = actions.filter((action) => action.type === 'attach');
    if (attaches.length) return chooseAttach(state, attaches);
    const event = bestEvent(state, player, profile, actions.filter((action) => action.type === 'event'));
    if (event) return event;
    if (profile.coop) {
      const offer = actions.find((action) => action.type === 'coop' && overlap(state, action.project, action.partner));
      if (offer) return offer;
    }
    return find('end');
  }

  return { PROFILES, choose };
});
