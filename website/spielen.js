/* Browser game: setup, table, handover between people and the pacing of the
   bots. The rules live in game-engine.js, the bots in game-bots.js; this file
   only shows the state and turns clicks into legal actions. */
(() => {
  'use strict';
  const E = window.BusfaktorEngine;
  const B = window.BusfaktorBots;
  const ROWS = window.CARDS || [];
  const ICONS = (window.CARD_RENDERER_DATA || {}).icons || {};
  const STORE_KEY = 'busfaktor-spiel-v1';
  const PREFS_KEY = 'busfaktor-spiel-einstellungen';
  const BOT_NAMES = ['Rechenzentrum', 'Lenkungskreis', 'Drittmittelstelle', 'Beirat'];
  const ROLES = [['human', 'Person'], ['umsichtig', 'Bot · umsichtig'], ['abwartend', 'Bot · abwartend'], ['kooperativ', 'Bot · kooperativ']];
  const EFFECT_ICON = { E1: 'inspect', E2: 'draw', E3: 'retrieve', E4: 'redistribute', E5: 'joker', E6: 'extra_effort', E7: 'negative', E8: 'safeguard' };
  const TYPE_ORDER = { Projekt: 0, Projektfaktor: 1, Ereignis: 2 };

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const store = {
    get(key) { try { return JSON.parse(localStorage.getItem(key)); } catch (error) { return null; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (error) { /* private mode */ } },
    drop(key) { try { localStorage.removeItem(key); } catch (error) { /* private mode */ } },
  };

  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (value === null || value === undefined || value === false) continue;
      if (key === 'class') el.className = value;
      else if (key === 'text') el.textContent = value;
      else if (key === 'style') el.style.cssText = value;
      else if (key.startsWith('on')) el.addEventListener(key.slice(2), value);
      else el.setAttribute(key, value === true ? '' : value);
    }
    for (const child of children.flat(Infinity)) {
      if (child === null || child === undefined || child === false) continue;
      el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return el;
  }

  const SVG = 'http://www.w3.org/2000/svg';
  function icon(name, cls = 'gi') {
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('viewBox', '0 0 256 256');
    svg.setAttribute('class', cls);
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('fill', 'currentColor');
    const build = (parent, node) => {
      const el = document.createElementNS(SVG, node.tag);
      for (const [key, value] of Object.entries(node.attrs || {})) el.setAttribute(key, value);
      (node.children || []).forEach((child) => build(el, child));
      parent.append(el);
    };
    ((ICONS[name] || {}).children || []).forEach((child) => build(svg, child));
    return svg;
  }

  /* ------------------------------------------------------------ state */

  let game = null;
  let viewer = null; // seat whose hand is shown; null while the device is handed over
  let handoverFor = null;
  let selected = null; // uid of the selected hand card
  let filterKey = null; // board target that matched several actions
  let coopOpen = false;
  let e1Choice = null; // { keep, swap } while choosing from "Sichten"
  let botTimer = null;
  let resultShown = false;
  let lastSeen = {}; // seat -> log number the person last saw
  const known = {}; // seat -> Set of hand cards already shown
  const fresh = {}; // seat -> Set of cards new since the person's last move
  const prefs = { fast: false, ...(store.get(PREFS_KEY) || {}) };

  // Online multiplayer state
  let onlineSession = null;
  let onlineRole = null; // 'host' | 'client'
  let onlineMySeat = null;
  let onlineRoomCode = null;

  const card = (uid) => E.def(game, uid);
  const seatName = (player) => game.seats[player].name;
  const quoted = (uid) => `„${card(uid).name}“`;
  const humans = () => game.seats.map((seat, index) => index).filter((index) => game.seats[index].kind === 'human');
  const isBot = (player) => game.seats[player].kind === 'bot';

  function save() {
    if (onlineSession) return; // Online games are managed by the host session
    if (game && game.phase !== 'over') store.set(STORE_KEY, { game, lastSeen });
    else store.drop(STORE_KEY);
  }

  /* ------------------------------------------------------------ setup */

  let mode = 'solo';
  let seats = [];

  const presets = {
    solo: () => [
      { name: 'Du', role: 'human' },
      { name: BOT_NAMES[0], role: 'umsichtig' },
      { name: BOT_NAMES[1], role: 'kooperativ' },
    ],
    table: () => [
      { name: 'Person 1', role: 'human' },
      { name: 'Person 2', role: 'human' },
    ],
  };

  function setMode(next) {
    mode = next;
    document.querySelectorAll('.mode-switch [data-mode]').forEach((button) => button.setAttribute('aria-checked', String(button.dataset.mode === next)));
    if (next === 'online') {
      $('#local-setup').hidden = true;
      $('#online-setup').hidden = false;
      initHostRoom();
    } else {
      $('#local-setup').hidden = false;
      $('#online-setup').hidden = true;
      if (onlineSession) {
        onlineSession.destroy();
        onlineSession = null;
        onlineRole = null;
        onlineMySeat = null;
      }
      seats = presets[next]();
      renderSeats();
    }
  }

  function defaultName(index, role) {
    if (role !== 'human') {
      const used = new Set(seats.map((seat) => seat.name));
      return BOT_NAMES.find((name) => !used.has(name)) || `Bot ${index + 1}`;
    }
    return mode === 'solo' && index === 0 ? 'Du' : `Person ${index + 1}`;
  }

  function renderSeats() {
    const list = $('#seats');
    list.replaceChildren(...seats.map((seat, index) => h('li', { class: 'seat-row' },
      h('span', { class: 'seat-no', 'aria-hidden': 'true', text: String(index + 1).padStart(2, '0') }),
      h('input', {
        class: 'seat-name', type: 'text', value: seat.name, maxlength: 24, autocomplete: 'off',
        'aria-label': `Name auf Platz ${index + 1}`,
        oninput: (event) => { seat.name = event.target.value; },
      }),
      h('select', {
        class: 'seat-role', 'aria-label': `Wer spielt auf Platz ${index + 1}`,
        onchange: (event) => {
          const wasBot = seat.role !== 'human';
          seat.role = event.target.value;
          const isBotNow = seat.role !== 'human';
          if (wasBot !== isBotNow) seat.name = defaultName(index, seat.role);
          renderSeats();
        },
      }, ROLES.map(([value, label]) => h('option', { value, selected: seat.role === value }, label))),
      h('button', {
        class: 'seat-remove', type: 'button', 'aria-label': `Platz ${index + 1} entfernen`,
        disabled: seats.length <= E.RULES.minPlayers,
        onclick: () => { seats.splice(index, 1); renderSeats(); },
      }, '×'),
    )));
    $('#add-seat').disabled = seats.length >= E.RULES.maxPlayers;
    const noHuman = !seats.some((seat) => seat.role === 'human');
    $('#start-game').disabled = noHuman;
    $('#seat-note').textContent = noHuman ? 'Mindestens ein Platz braucht eine Person.' : 'Zwei bis vier Plätze, mindestens einer mit einer Person';
    $('#seat-note').classList.toggle('is-warning', noHuman);
  }

  function seatsForGame(list) {
    const used = new Set();
    return list.map((seat, index) => {
      let name = String(seat.name || '').trim() || defaultName(index, seat.role);
      const base = name;
      for (let n = 2; used.has(name); n += 1) name = `${base} ${n}`;
      used.add(name);
      return seat.role === 'human' ? { name, kind: 'human' } : { name, kind: 'bot', bot: seat.role };
    });
  }

  function renderResume() {
    if (onlineSession) { $('#resume').hidden = true; return; }
    const saved = store.get(STORE_KEY);
    const ok = saved && saved.game && saved.game.v === 1 && saved.game.phase !== 'over';
    $('#resume').hidden = !ok;
    if (ok) {
      const names = saved.game.seats.map((seat) => seat.name).join(', ');
      $('#resume-meta').textContent = `Runde ${saved.game.round} von ${E.RULES.rounds} · ${names}`;
    }
  }

  /* ------------------------------------------------------------ online setup */

  function initHostRoom() {
    if (onlineSession) onlineSession.destroy();
    const code = window.BusfaktorNetwork ? window.BusfaktorNetwork.generateRoomCode() : 'TEST';
    $('#display-room-code').textContent = code;
    const hostName = $('#host-name').value.trim() || 'Du';

    onlineRole = 'host';
    onlineMySeat = 0;
    onlineRoomCode = code;

    if (!window.BusfaktorNetwork) return;

    $('#start-online-game').disabled = true;
    showHostStatus('Verbinde mit dem Signaling-Server …', false);

    onlineSession = new window.BusfaktorNetwork.HostSession({
      roomId: code,
      hostName,
      rows: ROWS,
      onLobbyUpdate: (lobby) => {
        showHostStatus(`Raum ${lobby.roomId} ist offen. Gib den Code oder den Link weiter.`, false);
        renderOnlineLobby(lobby);
      },
      onStateUpdate: handleOnlineStateUpdate,
      onError: (err) => {
        // Without a reachable signaling server nobody can join this code.
        $('#start-online-game').disabled = true;
        showHostStatus(`Kein Raum: ${err.message} Ohne erreichbaren Signaling-Server funktioniert der Code nicht.`, true);
      },
    });
  }

  function renderOnlineLobby(lobby) {
    const list = $('#online-seats');
    list.replaceChildren(...lobby.seats.map((seat, index) => {
      const isHostSeat = index === 0;
      const isBotSeat = seat.kind === 'bot';
      let roleLabel = 'Person';
      if (isHostSeat) roleLabel = 'Host (Du)';
      else if (isBotSeat) roleLabel = (B.PROFILES[seat.role] || {}).label || 'Bot';

      return h('li', { class: 'seat-row online-seat-row' },
        h('span', { class: 'seat-no', 'aria-hidden': 'true', text: String(index + 1).padStart(2, '0') }),
        h('strong', { class: 'seat-name-label', text: seat.name }),
        h('span', { class: `seat-status-badge ${seat.connected ? 'is-connected' : 'is-waiting'}`, text: roleLabel }),
        !isHostSeat ? h('button', {
          class: 'seat-remove', type: 'button', 'aria-label': `Platz ${index + 1} entfernen`,
          onclick: () => onlineSession.removeSeat(index),
        }, '×') : h('span', {})
      );
    }));

    $('#online-seat-count').textContent = lobby.seats.length;
    $('#start-online-game').disabled = lobby.seats.length < E.RULES.minPlayers;
    $('#online-add-bot').disabled = lobby.seats.length >= E.RULES.maxPlayers;
    $('#online-seat-note').textContent = lobby.seats.length < E.RULES.minPlayers
      ? 'Mindestens 2 Plätze (Personen oder Bots) erforderlich.'
      : 'Bereit zum Starten.';
  }

  function joinOnlineRoom() {
    const code = window.BusfaktorNetwork ? window.BusfaktorNetwork.normalizeRoomCode($('#join-code').value) : '';
    const name = $('#join-name').value.trim() || 'Person';
    if (!code) {
      showJoinStatus('Bitte gib einen Raumcode ein.', true);
      return;
    }
    showJoinStatus(`Verbinde mit Raum ${code}...`, false);
    if (onlineSession) onlineSession.destroy();

    onlineRole = 'client';
    onlineRoomCode = code;

    onlineSession = new window.BusfaktorNetwork.ClientSession({
      roomId: code,
      playerName: name,
      onWelcome: ({ seat, roomId }) => {
        onlineMySeat = seat;
        showJoinStatus(`Verbunden als „${name}“ auf Platz ${seat + 1}. Warte auf Spielstart durch den Host...`, false);
      },
      onLobbyUpdate: (lobby) => {
        if (!game) {
          const names = lobby.seats.map((s) => s.name).join(', ');
          showJoinStatus(`Im Raum (${lobby.seats.length}/4): ${names}. Warte auf Spielstart...`, false);
        }
      },
      onStateUpdate: handleOnlineStateUpdate,
      onError: (err) => {
        showJoinStatus(`Fehler: ${err.message}`, true);
      },
      onDisconnect: () => {
        showJoinStatus('Verbindung zum Host getrennt.', true);
      },
    });
  }

  function showStatus(selector, text, isError) {
    const box = $(selector);
    if (!box) return;
    box.hidden = false;
    box.className = `online-status-msg ${isError ? 'is-error' : ''}`;
    box.textContent = text;
  }
  const showJoinStatus = (text, isError) => showStatus('#join-status', text, isError);
  const showHostStatus = (text, isError) => showStatus('#host-status', text, isError);

  function handleOnlineStateUpdate(state, seat) {
    game = state;
    viewer = seat;
    onlineMySeat = seat;
    if ($('#play').hidden) {
      $('#play-intro').hidden = true;
      $('#setup').hidden = true;
      $('#play').hidden = false;
      document.body.classList.add('is-playing');
      $('#online-bar-info').hidden = false;
      $('#online-bar-text').textContent = `Raum ${onlineRoomCode} · Platz ${seat + 1} (${game.seats[seat].name})`;
      window.scrollTo(0, 0);
    }
    advance();
  }

  function startGame(gameSeats) {
    game = E.newGame({ seats: gameSeats, rows: ROWS, seed: (Math.random() * 2 ** 32) >>> 0 });
    lastSeen = {};
    enterTable();
  }

  function enterTable() {
    lastZones = null;
    viewer = null;
    selected = null;
    filterKey = null;
    coopOpen = false;
    e1Choice = null;
    resultShown = game.phase === 'over';
    for (const key of Object.keys(known)) delete known[key];
    for (const key of Object.keys(fresh)) delete fresh[key];
    $('#play-intro').hidden = true;
    $('#setup').hidden = true;
    $('#play').hidden = false;
    document.body.classList.add('is-playing');
    window.scrollTo(0, 0);
    advance();
  }

  function leaveTable() {
    clearTimeout(botTimer);
    if (onlineSession) {
      onlineSession.destroy();
      onlineSession = null;
      onlineRole = null;
      onlineMySeat = null;
      $('#online-bar-info').hidden = true;
    }
    game = null;
    viewer = null;
    lastZones = null;
    $('#handover').hidden = true;
    $('#play').hidden = true;
    document.body.classList.remove('is-playing');
    hidePeek();
    $('#play-intro').hidden = false;
    $('#setup').hidden = false;
    renderResume();
    window.scrollTo(0, 0);
  }

  /* ------------------------------------------------------------ flow */

  function advance() {
    clearTimeout(botTimer);
    if (!onlineSession) save();
    if (game.phase === 'over') {
      if (viewer === null) viewer = onlineSession ? onlineMySeat : humans()[0];
      $('#handover').hidden = true;
      render();
      if (!resultShown) {
        resultShown = true;
        showResult();
      }
      return;
    }

    if (onlineSession) {
      $('#handover').hidden = true;
      viewer = onlineMySeat;
      render();
      return;
    }

    const who = E.actor(game);
    if (isBot(who)) {
      if (viewer === null && humans().length === 1) viewer = humans()[0];
      render();
      botTimer = setTimeout(botStep, botDelay());
      return;
    }
    if (who !== viewer && humans().length > 1) {
      showHandover(who);
      return;
    }
    viewer = who;
    render();
  }

  function botDelay() {
    const last = game.log[game.log.length - 1];
    if (prefs.fast) return 160;
    return last && ['event', 'complete'].includes(last.kind) ? 1300 : 650;
  }

  function botStep() {
    if (!game || game.phase === 'over') return;
    const who = E.actor(game);
    if (!isBot(who)) return;
    E.apply(game, B.choose(game, who));
    advance();
  }

  function perform(action) {
    if (viewer !== null) fresh[viewer] = new Set();
    if (onlineSession) {
      try {
        if (onlineRole === 'client') {
          onlineSession.sendAction(action);
        } else if (onlineRole === 'host') {
          onlineSession.handleHostAction(action);
        }
      } catch (error) {
        console.error(error);
        $('#prompt').prepend(h('p', { class: 'prompt-error', text: `Das ging nicht: ${error.message}` }));
        return;
      }
      selected = null;
      filterKey = null;
      coopOpen = false;
      e1Choice = null;
      return;
    }

    try {
      E.apply(game, action);
    } catch (error) {
      console.error(error);
      $('#prompt').prepend(h('p', { class: 'prompt-error', text: `Das ging nicht: ${error.message}` }));
      return;
    }
    selected = null;
    filterKey = null;
    coopOpen = false;
    e1Choice = null;
    advance();
  }

  /* ------------------------------------------------------------ handover */

  function handoverReason(who) {
    const pending = game.pending;
    if (!pending || pending.player !== who) return `Runde ${game.round}: Du bist am Zug.`;
    const by = pending.by !== undefined ? seatName(pending.by) : '';
    switch (pending.type) {
      case 'react': return `${by} spielt ${quoted(pending.play.uid)}. Du kannst mit einer Absicherung reagieren.`;
      case 'coop': return `${by} bietet dir eine Kooperation an.`;
      case 'share': return `${by} möchte einen Faktor gemeinsam mit dir nutzen.`;
      case 'family': return `${quoted(pending.event)} liegt an deinem Projekt ${quoted(pending.project)}. Du wählst den zusätzlichen Faktortyp.`;
      case 'return': return `${quoted(pending.event)}: Du nimmst einen deiner angelegten Faktoren zurück.`;
      default: return `Eine Entscheidung wartet auf dich.`;
    }
  }

  function showHandover(who) {
    viewer = null;
    handoverFor = who;
    selected = null;
    filterKey = null;
    coopOpen = false;
    render();
    $('#handover-name').textContent = seatName(who);
    $('#handover-reason').textContent = handoverReason(who);
    const since = lastSeen[who] ?? 0;
    const news = game.log.filter((entry) => entry.n > since && entry.kind !== 'turn').slice(-10);
    $('#handover-news-box').hidden = !news.length || since === 0;
    $('#handover-news').replaceChildren(...news.map((entry) => h('li', { class: `log-${entry.kind}`, text: entry.text })));
    $('#handover-go').textContent = `Ich bin ${seatName(who)} · Karten zeigen`;
    $('#handover').hidden = false;
    $('#handover-go').focus();
  }

  /* ------------------------------------------------------------ actions and targets */

  function myActions() {
    if (!game || game.phase === 'over' || viewer === null) return [];
    const who = E.actor(game);
    if (who !== viewer || isBot(who)) return [];
    return E.legalActions(game);
  }

  // Actions that the board may offer as click targets right now.
  function candidates() {
    const actions = myActions();
    if (!actions.length) return [];
    if (game.pending || game.phase === 'draw') return actions;
    if (selected !== null) return actions.filter((action) => action.uid === selected);
    return [];
  }

  function targetKey(action) {
    switch (action.type) {
      case 'draw': return `pile:${action.source}`;
      case 'start': return 'zone:start';
      case 'attach': return `project:${action.project}`;
      case 'return': return `factor:${action.uid}`;
      case 'event': {
        const spec = card(action.uid).spec;
        if (spec.template === 'E3') return 'pile:discard';
        if (spec.template === 'E4') return `factor:${action.card}`;
        if (spec.template === 'E5' || spec.template === 'E6') return `project:${action.project}`;
        if (spec.template === 'E7' && spec.scope !== 'all') return `factor:${action.card}`;
        return null;
      }
      default: return null;
    }
  }

  function onTarget(key) {
    const matches = candidates().filter((action) => targetKey(action) === key);
    if (matches.length === 1) {
      perform(matches[0]);
    } else if (matches.length > 1) {
      filterKey = key;
      renderPrompt();
      markTargets();
      $('#prompt').focus({ preventScroll: true });
    }
  }

  function select(uid) {
    selected = selected === uid ? null : uid;
    filterKey = null;
    coopOpen = false;
    render();
  }

  /* ------------------------------------------------------------ card faces */

  // The rendered cards, as on paper. Their print is too small to read at table
  // size, so every face carries its name below and a large preview on hover.
  function cardImage(c, sizes) {
    return h('img', {
      src: `assets/cards-sm/${c.id}.webp`,
      srcset: `assets/cards-sm/${c.id}.webp 360w, assets/cards/${c.id}.webp 750w`,
      sizes, alt: '', width: 360, height: 504, draggable: 'false',
    });
  }

  function eventHint(spec) {
    const types = (families) => families.map((family) => E.FAMILY[family]).join(' oder ');
    switch (spec.template) {
      case 'E1': return `${spec.look} Karten ansehen, ${spec.take} nehmen`;
      case 'E2': return `Aufdecken bis ${spec.take} Faktoren`;
      case 'E3': return 'Faktor aus der Ablage holen';
      case 'E4': return 'Faktor zwischen eigenen Projekten verschieben';
      case 'E5': return spec.families.length === 4 ? 'Erfüllt einen Typ deiner Wahl' : `Erfüllt ${types(spec.families)}`;
      case 'E6': return spec.chooser === 'target' ? 'Fremdes Projekt: +1 Anforderung, Ziel wählt' : `Fremdes Projekt: +1 ${E.FAMILY[spec.families[0]]}`;
      case 'E7': return spec.scope === 'all' ? 'Alle nehmen einen Faktor zurück' : `${types(spec.families)}faktor zurück auf die Hand`;
      case 'E8': return spec.counters === 'rueckschlag' ? 'Reaktion: verhindert einen Rückschlag' : 'Reaktion auf ein negatives Ereignis';
      default: return '';
    }
  }

  function requirementIcons(requirements, extra) {
    return h('span', { class: 'req-icons', 'aria-label': requirements.map((family) => E.FAMILY[family]).join(', ') },
      requirements.map((family) => h('span', { class: `req-dot fam-${family}` }, icon(family))),
      extra ? h('span', { class: `req-dot fam-${extra} is-extra` }, icon(extra)) : null);
  }

  // Words with a hyphen stay whole ("Die Live-Demo / funktioniert", never
  // "Die Live- / Demo funktioniert"), and a closing "…" stays with its word.
  const nameNodes = (text) => text.replace(/ …$/, '\u00a0…').split(/(\S*[^\s-]-[^\s-]\S*)/).filter(Boolean)
    .map((part) => (/[^\s-]-[^\s-]/.test(part) ? h('span', { class: 'nobr', text: part }) : part));

  function cardLabel(uid) {
    const c = card(uid);
    if (c.type === 'Projekt') return `${c.name}, Projekt, ${c.points} Punkte, braucht ${c.requirements.map((family) => E.FAMILY[family]).join(', ')}`;
    if (c.type === 'Projektfaktor') return `${c.name}, Projektfaktor ${c.families.map((family) => E.FAMILY[family]).join(' oder ')}`;
    return `${c.name}, Ereignis ${E.KEYWORD[c.spec.template].toLowerCase()}: ${eventHint(c.spec)}`;
  }

  // One line under the name: what the card is, in the card colours.
  function cardMeta(c) {
    if (c.type === 'Projekt') return [requirementIcons(c.requirements), h('span', { text: `${c.points} P` })];
    if (c.type === 'Projektfaktor') {
      return [h('span', { class: 'req-icons' }, c.families.map((family) => h('span', { class: `req-dot fam-${family}` }, icon(family)))),
        h('span', { text: c.families.length > 1 ? 'Wildcard' : E.FAMILY[c.families[0]] })];
    }
    return [h('span', { class: `req-icons` }, h('span', { class: `req-dot is-event is-${c.polarity}` }, icon(EFFECT_ICON[c.spec.template]))),
      h('span', { text: E.KEYWORD[c.spec.template] })];
  }

  function cardFace(uid, { tag = 'button', extraClass = '', sizes = '140px', caption = true } = {}) {
    const c = card(uid);
    return h(tag, {
      class: `gc gc-${c.type === 'Projekt' ? 'project' : c.type === 'Projektfaktor' ? 'factor' : 'event'} ${extraClass}`.trim(),
      type: tag === 'button' ? 'button' : null, 'data-uid': uid, 'data-card': c.id, 'aria-label': tag === 'button' ? cardLabel(uid) : null,
    },
    h('span', { class: 'gc-face' }, cardImage(c, sizes)),
    caption ? h('span', { class: 'gc-cap', 'aria-hidden': tag === 'button' ? 'true' : null },
      h('span', { class: 'gc-name' }, nameNodes(c.name)),
      h('span', { class: 'gc-meta' }, cardMeta(c))) : null);
  }

  /* ------------------------------------------------------------ projects */

  function slotLayout(pid) {
    const project = game.projects[pid];
    const coop = E.coopOf(game, pid);
    const slots = card(pid).requirements.map((family) => ({ family, extra: false }));
    if (project.extra) slots.push({ family: project.extra.family, extra: true });
    const pool = project.filled.map((entry) => ({ ...entry, shared: false }));
    if (coop && coop.shared) pool.push({ ...coop.shared, shared: true });
    // Filled factors first in the printed slots, the surcharge slot last.
    for (const slot of slots) {
      const index = pool.findIndex((entry) => entry.family === slot.family);
      if (index >= 0) slot.fill = pool.splice(index, 1)[0];
    }
    return slots;
  }

  function slotItem(slot) {
    const cls = `slot fam-${slot.family}${slot.fill ? ' is-filled' : ''}${slot.extra ? ' is-extra' : ''}`;
    if (!slot.fill) {
      return h('li', { class: cls },
        h('span', { class: 'slot-body' }, icon(slot.family), h('span', { class: 'slot-text', text: slot.extra ? `${E.FAMILY[slot.family]} · Mehraufwand` : `${E.FAMILY[slot.family]} offen` })));
    }
    const c = card(slot.fill.uid);
    const tags = [];
    if (slot.fill.shared) tags.push('gemeinsam');
    if (c.type === 'Ereignis') tags.push('Joker');
    else if (c.families.length > 1) tags.push('Wildcard');
    const owner = E.controllerOf(game, slot.fill.uid, null);
    return h('li', { class: cls },
      h('button', {
        class: 'slot-body', type: 'button', 'data-target': `factor:${slot.fill.uid}`, 'data-inspect': slot.fill.uid, 'data-card': c.id,
        'aria-label': `${c.name}, erfüllt ${E.FAMILY[slot.family]}${tags.length ? `, ${tags.join(', ')}` : ''}${owner !== null ? `, kontrolliert von ${seatName(owner)}` : ''}`,
      },
      icon(slot.family),
      h('span', { class: 'slot-text' }, nameNodes(c.name)),
      tags.length ? h('span', { class: 'slot-tag', text: tags.join(' · ') }) : null));
  }

  // The other seats show a project compactly: its requirements as colour chips,
  // the attached cards behind them on hover (peek) or tap (card detail).
  function slotChip(slot) {
    const cls = `chip fam-${slot.family}${slot.fill ? ' is-filled' : ''}${slot.extra ? ' is-extra' : ''}${slot.fill && slot.fill.shared ? ' is-shared' : ''}`;
    if (!slot.fill) {
      return h('li', { class: cls },
        h('span', { class: 'chip-body', role: 'img', 'aria-label': `${E.FAMILY[slot.family]} offen${slot.extra ? ', Mehraufwand' : ''}` }, icon(slot.family)));
    }
    const c = card(slot.fill.uid);
    return h('li', { class: cls },
      h('button', {
        class: 'chip-body', type: 'button', 'data-target': `factor:${slot.fill.uid}`, 'data-inspect': slot.fill.uid, 'data-card': c.id,
        'aria-label': `${c.name}, erfüllt ${E.FAMILY[slot.family]}${slot.fill.shared ? ', gemeinsam' : ''}`,
      }, icon(slot.family)));
  }

  function projectPanel(pid, { sizes = '112px', compact = false } = {}) {
    const c = card(pid);
    const project = game.projects[pid];
    const coop = E.coopOf(game, pid);
    const open = E.openCounts(game, pid);
    const openTotal = Object.values(open).reduce((sum, value) => sum + value, 0);
    const extra = project.extra ? card(project.extra.uid) : null;
    let coopText = '';
    if (coop) {
      const partner = E.partnerOf(coop, pid);
      const partnerOwner = coop.owners[coop.a === pid ? 1 : 0];
      coopText = `Kooperation mit ${seatName(partnerOwner)}: ${card(partner).name}${game.projects[partner] ? '' : ' (abgeschlossen)'}`;
    }
    let state;
    if (compact) {
      state = h('ul', { class: 'chips' }, slotLayout(pid).map(slotChip),
        extra ? h('li', { class: 'chip is-event' }, h('button', {
          class: 'chip-body', type: 'button', 'data-inspect': project.extra.uid, 'data-extra': project.extra.uid, 'data-card': extra.id,
          'aria-label': `Mehraufwand: ${extra.name}`,
        }, icon('extra_effort'))) : null,
        coop ? h('li', { class: 'chip is-coop' }, h('span', { class: 'chip-body', role: 'img', 'aria-label': coopText, title: coopText }, icon('cooperation'))) : null);
    } else {
      state = [h('ul', { class: 'slots' }, slotLayout(pid).map(slotItem)),
        extra ? h('button', { class: 'proj-note is-extra', type: 'button', 'data-inspect': project.extra.uid, 'data-extra': project.extra.uid, 'data-card': extra.id },
          icon('extra_effort'), h('span', { text: `Mehraufwand: ${extra.name}` })) : null,
        coop ? h('p', { class: 'proj-note is-coop', title: coopText }, icon('cooperation'), h('span', { text: coopText })) : null];
    }
    return h('div', { class: `proj${coop ? ' is-coop' : ''}${compact ? ' is-compact' : ''}`, 'data-pid': pid },
      h('button', {
        class: 'proj-head', type: 'button', 'data-target': `project:${pid}`, 'data-inspect': pid, 'data-card': c.id,
        'aria-label': `${c.name}, ${c.points} Punkte, noch ${openTotal} offen`,
      }, cardImage(c, sizes)),
      h('div', { class: 'proj-body' },
        h('p', { class: 'proj-name' }, nameNodes(c.name)),
        h('p', { class: 'proj-meta' }, h('b', { text: `${c.points} P` }), ` · ${openTotal} offen`),
        state));
  }


  // Typographic minus, so "Stand −1" matches the rest of the table.
  const signed = (value) => (value < 0 ? `\u2212${Math.abs(value)}` : String(value));

  const standing = (player) => {
    const plus = game.completed[player].reduce((sum, uid) => sum + card(uid).points, 0);
    return { plus, minus: game.active[player].length * E.RULES.minusPerActive, done: game.completed[player].length };
  };

  function completedLine(player) {
    const list = game.completed[player];
    if (!list.length) return 'Noch kein Projekt abgeschlossen.';
    return `Abgeschlossen: ${list.map((uid) => `${card(uid).name} (${card(uid).points})`).join(' · ')}`;
  }

  /* ------------------------------------------------------------ render */

  function render() {
    if (!game) return;
    if (selected !== null && (viewer === null || !game.hands[viewer].includes(selected))) {
      selected = null;
      filterKey = null;
    }
    const moves = planFlights();
    renderBar();
    renderOpponents();
    renderPiles();
    renderMine();
    renderHand();
    renderPrompt();
    renderLog();
    markTargets();
    fitNames($('#play'));
    fitTable();
    fitRows();
    squeezeHand();
    keepLanding();
    launchFlights(moves);
    refreshPeek();
    if (viewer !== null) lastSeen[viewer] = game.logSeq;
    const last = game.log[game.log.length - 1];
    if (last && $('#announce').dataset.n !== String(last.n)) {
      $('#announce').dataset.n = String(last.n);
      $('#announce').textContent = last.text;
    }
  }

  function renderBar() {
    $('#round').textContent = game.round;
    $('#rounds').textContent = E.RULES.rounds;
    document.querySelectorAll('#phases li').forEach((item) => {
      const current = game.phase === item.dataset.phase;
      item.classList.toggle('is-current', current);
      if (current) item.setAttribute('aria-current', 'step');
      else item.removeAttribute('aria-current');
    });
    let label = game.phase === 'over' ? 'Partie beendet' : `Am Zug: ${seatName(game.current)}`;
    if (game.pending && game.pending.player !== game.current) label += ` · Entscheidung: ${seatName(game.pending.player)}`;
    $('#turn-label').textContent = label;
    $('#fast-bots').checked = prefs.fast;
  }

  function seatOrder() {
    const base = viewer ?? handoverFor ?? 0;
    const order = [];
    for (let step = 1; step < game.seats.length; step += 1) order.push((base + step) % game.seats.length);
    return viewer === null ? [base, ...order] : order;
  }

  function renderOpponents() {
    const box = $('#opponents');
    box.replaceChildren(...seatOrder().map((player) => {
      const seat = game.seats[player];
      const s = standing(player);
      const profile = seat.kind === 'bot' ? (B.PROFILES[seat.bot] || {}).label : null;
      const acting = game.phase !== 'over' && E.actor(game) === player;
      const handSize = game.hands[player].length;
      return h('article', { class: `opp${game.current === player && game.phase !== 'over' ? ' is-current' : ''}${acting ? ' is-acting' : ''}`, 'aria-label': seat.name, 'data-seat': player },
        h('header', { class: 'opp-head' },
          h('div', { class: 'opp-who' },
            h('strong', { class: 'opp-name', text: seat.name }),
            h('span', { class: 'opp-kind', text: profile ? `Bot · ${profile.toLowerCase()}` : 'Person' })),
          h('div', { class: 'opp-line' },
            h('span', { class: 'opp-hand', 'aria-hidden': 'true' },
              Array.from({ length: Math.min(handSize, 9) }, () => h('span', { class: 'opp-back' }))),
            h('p', { class: 'opp-stats' },
              h('span', {}, 'Hand ', h('b', { text: handSize })),
              h('span', {}, 'Punkte ', h('b', { text: s.plus })),
              h('span', {}, 'Offen ', h('b', { text: s.minus ? `−${s.minus}` : '0' })),
              // Closed projects by name on hover; the count is also where they fly to.
              h('span', { class: 'opp-done', title: completedLine(player) }, 'Fertig ', h('b', { text: s.done }))))),
        game.active[player].length
          ? h('div', { class: 'proj-row' }, game.active[player].map((pid) => projectPanel(pid, { sizes: '64px', compact: true })))
          : h('p', { class: 'empty-note', text: 'Kein aktives Projekt.' }));
    }));
  }

  function renderPiles() {
    const top = game.discard[game.discard.length - 1];
    const pile = (source, label, count, note) => h('button', { class: 'pile', type: 'button', 'data-target': `pile:${source}`, 'aria-label': `${label.replace('\u00ad', '')}, ${count} Karten` },
      h('span', { class: 'pile-stack' }, h('img', { src: 'assets/cards-sm/back.webp', alt: '', width: 360, height: 504 })),
      h('span', { class: 'pile-label', text: label }),
      h('span', { class: 'pile-count', text: note || `${count} Karten` }));
    const refill = !game.actionDeck.length && game.consumed.length;
    $('#piles').replaceChildren(
      pile('project', 'Projekt\u00adstapel', game.projectDeck.length, game.projectDeck.length ? '' : 'leer'),
      pile('action', 'Aktions\u00adstapel', game.actionDeck.length, refill ? 'wird neu gemischt' : ''),
      h('div', { class: 'pile pile-discard' },
        top === undefined
          ? h('button', { class: 'pile-empty', type: 'button', 'data-target': 'pile:discard', text: 'leer' })
          : h('button', { class: 'pile-top', type: 'button', 'data-target': 'pile:discard', 'data-inspect': top, 'data-card': card(top).id, 'aria-label': `Offene Ablage, oben ${card(top).name}` }, cardFace(top, { tag: 'span', sizes: '64px', caption: false })),
        h('span', { class: 'pile-label', text: 'Offene Ablage' }),
        game.discard.length
          ? h('button', { class: 'pile-count link-button', type: 'button', onclick: openDiscard, text: `${game.discard.length} ansehen` })
          : h('span', { class: 'pile-count', text: '0 Karten' })),
      h('div', { class: 'pile pile-consumed', 'aria-label': `Verbrauchsstapel, ${game.consumed.length} Karten` },
        h('span', { class: 'pile-stack' }, h('img', { src: 'assets/cards-sm/back.webp', alt: '', width: 360, height: 504 })),
        h('span', { class: 'pile-label', text: 'Verbrauchs\u00adstapel' }),
        h('span', { class: 'pile-count', text: `${game.consumed.length} Karten` })));
  }

  function renderMine() {
    const player = viewer ?? handoverFor;
    const box = $('#my-projects');
    if (viewer === null) {
      $('#my-title').textContent = 'Projekte';
      $('#my-meta').textContent = '';
      box.replaceChildren();
      $('#my-completed').textContent = '';
      return;
    }
    const s = standing(player);
    $('#my-title').textContent = humans().length > 1 ? `Deine Projekte · ${seatName(player)}` : 'Deine Projekte';
    $('#my-meta').textContent = `Punkte ${s.plus} · Offen ${s.minus ? `−${s.minus}` : '0'} · Stand ${signed(s.plus - s.minus)}`;
    const panels = game.active[player].map((pid) => projectPanel(pid));
    const canStart = candidates().some((action) => action.type === 'start');
    if (canStart) panels.push(h('button', { class: 'proj-start', type: 'button', 'data-target': 'zone:start' }, icon('project'), h('span', { text: 'Projekt hier beginnen' })));
    if (!panels.length) panels.push(h('p', { class: 'empty-note', text: 'Noch kein aktives Projekt. Jedes aktive Projekt zählt am Ende −1, bis es fertig ist.' }));
    box.replaceChildren(...panels);
    $('#my-completed').textContent = completedLine(player);
    $('#my-completed').hidden = !game.completed[player].length;
  }

  function renderHand() {
    const box = $('#hand');
    if (viewer === null) {
      $('#hand-meta').textContent = '';
      box.replaceChildren(h('p', { class: 'empty-note', text: 'Verdeckt, bis das Gerät übergeben ist.' }));
      return;
    }
    const hand = game.hands[viewer];
    const seen = known[viewer] || new Set(hand);
    fresh[viewer] = fresh[viewer] || new Set();
    // Fresh cards keep their mark until the next move; they fly in only once.
    const arriving = new Set(hand.filter((uid) => !seen.has(uid)));
    for (const uid of arriving) fresh[viewer].add(uid);
    known[viewer] = new Set(hand);
    const over = hand.length - E.RULES.handLimit;
    $('#hand-meta').textContent = `${hand.length} Karten · Limit ${E.RULES.handLimit}${over > 0 ? ` · ${over} zu viel` : ''}`;
    const actions = myActions();
    const playable = new Set(actions.filter((action) => ['start', 'attach', 'event', 'discard'].includes(action.type)).map((action) => action.uid));
    // Only while choosing what to play do the other cards step back.
    box.classList.toggle('is-choosing', game.phase === 'action' && !game.pending && actions.length > 0);
    const sorted = hand.slice().sort((a, b) => TYPE_ORDER[card(a).type] - TYPE_ORDER[card(b).type] || card(a).name.localeCompare(card(b).name, 'de'));
    box.replaceChildren(...(sorted.length ? sorted.map((uid) => {
      const face = cardFace(uid, {
        extraClass: [selected === uid ? 'is-selected' : '', playable.has(uid) ? 'is-playable' : '', fresh[viewer].has(uid) ? 'is-new' : '', arriving.has(uid) ? 'is-arriving' : ''].join(' '),
      });
      face.setAttribute('aria-pressed', String(selected === uid));
      return face;
    }) : [h('p', { class: 'empty-note', text: 'Keine Karten auf der Hand.' })]));
  }

  // A long hand overlaps instead of wrapping, like cards held in one hand.
  // Phones scroll the hand sideways instead (see style.css).
  function squeezeHand() {
    const box = $('#hand');
    const faces = box.querySelectorAll('.gc');
    box.style.removeProperty('--squeeze');
    if (faces.length < 2 || getComputedStyle(box).flexWrap !== 'wrap') return;
    const gap = parseFloat(getComputedStyle(box).columnGap) || 0;
    const width = faces[0].offsetWidth;
    const need = faces.length * width + (faces.length - 1) * gap;
    const room = box.clientWidth;
    if (need > room) box.style.setProperty('--squeeze', `${Math.ceil((need - room) / (faces.length - 1))}px`);
  }

  function renderLog() {
    const entries = game.log.slice(-150).reverse();
    $('#log').replaceChildren(...entries.map((entry) => h('li', { class: `log-${entry.kind}`, text: entry.text })));
  }

  function markTargets() {
    document.querySelectorAll('#play .is-target').forEach((el) => el.classList.remove('is-target'));
    document.querySelectorAll('#play .has-target').forEach((el) => el.classList.remove('has-target'));
    const keys = new Set(candidates().map(targetKey).filter(Boolean));
    if (filterKey) keys.clear();
    document.querySelectorAll('#play [data-target]').forEach((el) => {
      if (!keys.has(el.dataset.target)) return;
      el.classList.add('is-target');
      const panel = el.closest('.proj, .pile');
      if (panel) panel.classList.add('has-target');
    });
  }

  /* ------------------------------------------------------------ prompt */

  const title = (text) => h('h3', { class: 'prompt-title', text });
  const para = (text, cls = 'prompt-text') => h('p', { class: cls, text });
  const choice = (action, primary = false) => h('button', {
    class: `move${primary ? ' is-primary' : ''}`, type: 'button', onclick: () => perform(action),
  }, E.describe(game, action));
  const choices = (actions, primaryType) => h('div', { class: 'moves' }, actions.map((action) => choice(action, action.type === primaryType)));

  function renderPrompt() {
    const box = $('#prompt');
    const parts = [];
    if (game.phase === 'over') {
      const result = E.scores(game);
      parts.push(title('Partie beendet'),
        para(`${result.winners.length > 1 ? 'Geteilter Sieg' : 'Sieg'}: ${result.winners.map(seatName).join(' und ')}.`),
        h('div', { class: 'moves' },
          h('button', { class: 'move is-primary', type: 'button', onclick: showResult, text: 'Ergebnis ansehen' }),
          h('button', { class: 'move', type: 'button', onclick: newSetup, text: 'Neue Partie einrichten' })));
    } else if (viewer !== null) {
      const who = E.actor(game);
      if (isBot(who)) parts.push(...botStatus(who));
      else if (who === viewer) parts.push(...decision());
      else if (onlineSession) {
        const last = game.log[game.log.length - 1];
        const pending = game.pending;
        const heading = pending && pending.player === who ? `Entscheidung: ${seatName(who)}` : `Am Zug: ${seatName(who)}`;
        parts.push(title(heading), para(last ? last.text : '', 'prompt-text is-live'),
          h('p', { class: 'prompt-hint', text: 'Karten ansehen geht jederzeit: Klick auf eine Karte oder ein Projekt.' }));
      }
    }
    if (selected !== null && viewer !== null) parts.push(selectionBlock(selected));
    box.replaceChildren(...parts);
    fitNames(box);
  }

  // A name whose longest word is wider than its box is hyphenated instead of
  // overflowing (Erschließungsstandard on a phone); the rest stay whole.
  function fitNames(root) {
    root.querySelectorAll('.gc-name, .proj-name, .slot-text').forEach((el) => {
      el.classList.remove('is-long');
      if (el.scrollWidth > el.clientWidth + 1) el.classList.add('is-long');
    });
  }

  function botStatus(who) {
    const pending = game.pending;
    const last = game.log[game.log.length - 1];
    const heading = pending && pending.player === who && pending.player !== game.current ? `Entscheidung: ${seatName(who)}` : `Am Zug: ${seatName(who)}`;
    return [title(heading), para(last ? last.text : '', 'prompt-text is-live'),
      h('p', { class: 'prompt-hint', text: 'Karten ansehen geht jederzeit: Klick auf eine Karte oder ein Projekt.' })];
  }

  function familiesInCommon(one, two) {
    const a = E.openCounts(game, one);
    const b = E.openCounts(game, two);
    return E.FAMILIES.filter((family) => a[family] && b[family]).map((family) => E.FAMILY[family]);
  }

  function decision() {
    const actions = myActions();
    const pending = game.pending;
    const find = (type) => actions.filter((action) => action.type === type);
    if (pending) {
      const by = pending.by !== undefined ? seatName(pending.by) : '';
      switch (pending.type) {
        case 'react': {
          const play = pending.play;
          return [title('Absicherung spielen?'),
            para(`${by} spielt ${quoted(play.uid)}. ${card(play.uid).rules}`),
            para('Eine Absicherung verhindert den Effekt; beide Ereignisse werden verbraucht (§12).', 'prompt-hint'),
            choices(actions, 'react')];
        }
        case 'coop': {
          const offer = pending.offer;
          const common = familiesInCommon(offer.project, offer.partner);
          return [title('Kooperation angeboten'),
            para(`${by} möchte ${quoted(offer.project)} mit deinem Projekt ${quoted(offer.partner)} verbinden. ${common.length ? `Beide brauchen noch: ${common.join(', ')}.` : 'Die beiden Projekte brauchen gerade keinen gemeinsamen Faktortyp.'}`),
            para('Ein gemeinsamer Faktor erfüllt an beiden Projekten je eine Anforderung. Jedes Projekt schließt für sich ab; Punkte bekommt jede Person nur für das eigene (§11).', 'prompt-hint'),
            choices(actions, 'accept')];
        }
        case 'share': {
          const proposal = pending.proposal;
          return [title('Gemeinsamer Faktor?'),
            para(`${by} möchte ${quoted(proposal.uid)} als ${E.FAMILY_FACTOR[proposal.family]} zwischen ${quoted(proposal.project)} und deinem Projekt legen. Er erfüllt dann auch bei dir eine ${E.FAMILY_REQ[proposal.family]}.`),
            choices(actions, 'accept')];
        }
        case 'family':
          return [title('Mehraufwand: Faktortyp wählen'),
            para(`${by} legt ${quoted(pending.event)} an dein Projekt ${quoted(pending.project)}. Du wählst, welche Anforderung dazukommt.`),
            h('div', { class: 'moves is-families' }, actions.map((action) => h('button', {
              class: `move move-family fam-${action.family}`, type: 'button', onclick: () => perform(action),
            }, icon(action.family), E.FAMILY[action.family])))];
        case 'return':
          return [title('Faktor zurücknehmen'),
            para(`${quoted(pending.event)}: Nimm einen von dir kontrollierten, angelegten Faktor auf die Hand zurück.`),
            choices(actions)];
        case 'e1':
          return e1Decision(actions);
        default:
          return [choices(actions)];
      }
    }

    if (game.phase === 'draw') {
      const left = E.RULES.drawsPerTurn - game.turn.draws;
      return [title('Karten ziehen'),
        para(`Noch ${left} von ${E.RULES.drawsPerTurn}. Vom Projektstapel, vom Aktionsstapel oder die oberste Karte der offenen Ablage.`),
        choices(actions)];
    }

    if (game.phase === 'cleanup') {
      const over = game.hands[viewer].length - E.RULES.handLimit;
      return [title('Hand aufräumen'),
        para(`Wirf noch ${over} ${over === 1 ? 'Karte' : 'Karten'} ab. Sie kommen offen auf die Ablage, die zuletzt abgeworfene liegt oben.`),
        para('Karte in der Hand anklicken oder hier wählen.', 'prompt-hint'),
        choices(find('discard'))];
    }

    // Action phase
    if (game.turn.mustStart) {
      return [title('Projekt beginnen'),
        para('Vor dir liegt kein aktives Projekt. Beginne eines von deiner Hand (§8.1).'),
        choices(find('start'))];
    }
    const parts = [title('Aktionen')];
    parts.push(para(selected === null ? 'Wähle eine Handkarte: anlegen, beginnen oder ausspielen. Markierte Karten sind gerade spielbar.' : 'Wähle ein markiertes Ziel oder eine der Möglichkeiten unten.'));
    parts.push(h('ul', { class: 'turn-checks' },
      h('li', { class: game.turn.started ? 'is-done' : '' }, game.turn.started ? 'Projekt begonnen' : 'Ein Projekt beginnen (höchstens eins)'),
      h('li', { class: game.turn.eventPlayed ? 'is-done' : '' }, game.turn.eventPlayed ? 'Ereignis gespielt' : 'Ein Ereignis spielen (höchstens eins)'),
      h('li', {}, 'Passende Faktoren anlegen (beliebig viele)')));
    const offers = find('coop');
    const buttons = [];
    if (offers.length) {
      buttons.push(h('button', { class: 'move', type: 'button', 'data-toggle': 'coop', 'aria-expanded': String(coopOpen), onclick: () => { coopOpen = !coopOpen; renderPrompt(); } },
        coopOpen ? 'Kooperation anbieten ▴' : 'Kooperation anbieten …'));
      if (coopOpen) {
        buttons.push(h('div', { class: 'moves is-nested' }, offers.map((offer) => {
          const common = familiesInCommon(offer.project, offer.partner);
          return h('button', { class: 'move', type: 'button', onclick: () => perform(offer) },
            E.describe(game, offer), h('small', { text: common.length ? `gemeinsam offen: ${common.join(', ')}` : 'kein gemeinsamer Faktortyp offen' }));
        })));
      }
    }
    buttons.push(choice({ type: 'end' }, selected === null));
    parts.push(h('div', { class: 'moves' }, buttons));
    return parts;
  }

  function e1Decision(actions) {
    const pending = game.pending;
    if (!e1Choice || !pending.seen.includes(e1Choice.keep)) e1Choice = { keep: pending.seen[0], swap: false };
    const rest = pending.seen.filter((uid) => uid !== e1Choice.keep);
    const order = e1Choice.swap ? rest.slice().reverse() : rest;
    const action = actions.find((candidate) => candidate.keep === e1Choice.keep && candidate.rest.join() === order.join());
    return [title(`${quoted(pending.event)}: eine Karte nehmen`),
      para('Die übrigen kommen unter den Aktionsstapel, in der Reihenfolge unten.'),
      h('div', { class: 'e1-cards' }, pending.seen.map((uid) => {
        const face = cardFace(uid, { extraClass: uid === e1Choice.keep ? 'is-selected' : '', sizes: '92px' });
        face.setAttribute('aria-pressed', String(uid === e1Choice.keep));
        face.addEventListener('click', () => { e1Choice = { keep: uid, swap: false }; renderPrompt(); });
        return face;
      })),
      order.length ? h('p', { class: 'prompt-hint' }, `Unter den Stapel: ${order.map((uid) => card(uid).name).join(', dann ')}`,
        order.length > 1 ? h('button', { class: 'link-button', type: 'button', onclick: () => { e1Choice.swap = !e1Choice.swap; renderPrompt(); } }, 'Reihenfolge tauschen') : null) : null,
      h('div', { class: 'moves' }, h('button', { class: 'move is-primary', type: 'button', onclick: () => perform(action) }, `${quoted(e1Choice.keep)} nehmen`))];
  }

  function unplayableReason(uid) {
    const c = card(uid);
    if (game.phase !== 'action' || game.pending || E.actor(game) !== viewer) return null;
    if (c.type === 'Projekt') return game.turn.started ? 'In diesem Zug wurde schon ein Projekt begonnen.' : null;
    if (c.type === 'Projektfaktor') return 'Keines deiner aktiven Projekte hat eine passende offene Anforderung.';
    if (c.spec.template === 'E8') return 'Absicherungen spielst du nur als Reaktion auf ein passendes Ereignis.';
    if (game.turn.eventPlayed) return 'In diesem Zug wurde schon ein Ereignis gespielt.';
    return 'Gerade gibt es kein zulässiges Ziel.';
  }

  function selectionBlock(uid) {
    const c = card(uid);
    let actions = candidates().filter((action) => action.uid === uid && !['react'].includes(action.type));
    if (filterKey) actions = actions.filter((action) => targetKey(action) === filterKey);
    const parts = [h('div', { class: 'prompt-card' },
      h('button', { class: 'prompt-art', type: 'button', onclick: () => openCard(uid), 'aria-label': `${c.name} groß ansehen` },
        cardImage(c, '112px')),
      h('div', { class: 'prompt-card-copy' },
        h('p', { class: 'prompt-card-name' }, nameNodes(c.name)),
        h('p', { class: 'prompt-card-rule', text: c.rules })))];
    if (actions.length) {
      parts.push(h('div', { class: 'moves' }, actions.map((action) => choice(action, actions.length === 1))));
    } else {
      const reason = unplayableReason(uid);
      if (reason) parts.push(para(reason, 'prompt-hint'));
    }
    parts.push(filterKey
      ? h('button', { class: 'link-button', type: 'button', onclick: () => { filterKey = null; render(); }, text: 'Alle Möglichkeiten zeigen' })
      : h('button', { class: 'link-button', type: 'button', onclick: () => select(uid), text: 'Auswahl aufheben' }));
    return h('div', { class: 'prompt-selection' }, parts);
  }

  /* ------------------------------------------------------------ peek */

  // Large preview of the card under the mouse. On touch a tap selects the
  // card instead, and the side panel shows it with its rules text.
  const peek = h('div', { class: 'peek', 'aria-hidden': 'true' }, h('img', { alt: '', width: 750, height: 1050 }));
  document.body.append(peek);
  let peekFor = null;
  let peekTimer = null;
  let pointer = null;
  const peekable = (target) => (target instanceof Element ? target.closest('#play [data-card]') : null);

  function placePeek(el) {
    const rect = el.getBoundingClientRect();
    const width = Math.round(Math.min(300, (window.innerHeight - 40) * 5 / 7));
    const height = Math.round(width * 1.4);
    const gap = 16;
    const edge = 10;
    let left = rect.left + rect.width / 2 - width / 2;
    let top = rect.top - height - gap;
    if (top < edge) {
      // No room above: beside the card, else below it.
      top = rect.top + rect.height / 2 - height / 2;
      if (rect.right + gap + width <= window.innerWidth - edge) left = rect.right + gap;
      else if (rect.left - gap - width >= edge) left = rect.left - gap - width;
      else top = rect.bottom + gap;
    }
    peek.style.width = `${width}px`;
    peek.style.left = `${Math.max(edge, Math.min(left, window.innerWidth - width - edge))}px`;
    peek.style.top = `${Math.max(edge, Math.min(top, window.innerHeight - height - edge))}px`;
  }

  function showPeek() {
    if (!peekFor || !peekFor.isConnected) return;
    placePeek(peekFor);
    peek.classList.add('is-open');
  }

  function hidePeek() {
    clearTimeout(peekTimer);
    peekFor = null;
    peek.classList.remove('is-open');
  }

  function peekAt(el) {
    const open = peek.classList.contains('is-open');
    hidePeek();
    if (!el) return;
    peekFor = el;
    peek.firstChild.setAttribute('src', `assets/cards/${el.dataset.card}.webp`);
    // Moving along the hand keeps the preview open; a first hover waits a moment.
    if (open) showPeek();
    else peekTimer = setTimeout(showPeek, 280);
  }

  // After a re-render the hovered element is new; keep the preview if the same
  // card is still under the mouse.
  function refreshPeek() {
    if (!peekFor || peekFor.isConnected) return;
    const id = peekFor.dataset.card;
    const under = pointer ? peekable(document.elementFromPoint(pointer.x, pointer.y)) : null;
    if (!under || under.dataset.card !== id) {
      hidePeek();
      return;
    }
    peekFor = under;
    if (peek.classList.contains('is-open')) placePeek(under);
  }

  document.addEventListener('pointermove', (event) => {
    if (event.pointerType !== 'mouse') return;
    pointer = { x: event.clientX, y: event.clientY };
    const el = peekable(event.target);
    if (el !== peekFor) peekAt(el);
  }, { passive: true });
  document.addEventListener('pointerdown', hidePeek, { passive: true });
  document.documentElement.addEventListener('mouseleave', hidePeek);
  window.addEventListener('scroll', hidePeek, { passive: true });

  /* ------------------------------------------------------------ card flights */

  // Each render compares where every card lies with the render before and
  // flies the cards that moved: drawn, started, attached, played, discarded,
  // closed. Decks, the consumed pile and other hands show the back, so a card
  // that turns public flips on its way.
  const stillMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const flightLayer = h('div', { class: 'flights', 'aria-hidden': 'true' });
  document.body.append(flightLayer);
  let lastZones = null;
  let lastViewer = null;
  const landing = new Map(); // uid -> zone, while the card is in the air

  function cardZones(state) {
    const zones = new Map();
    // Masked cards (online: other hands, decks) are null and stay unknown.
    const put = (uid, zone) => { if (typeof uid === 'number') zones.set(uid, zone); };
    state.projectDeck.forEach((uid) => put(uid, { kind: 'deck', pile: 'project' }));
    state.actionDeck.forEach((uid) => put(uid, { kind: 'deck', pile: 'action' }));
    state.discard.forEach((uid) => put(uid, { kind: 'discard' }));
    state.consumed.forEach((uid) => put(uid, { kind: 'consumed' }));
    state.hands.forEach((hand, player) => hand.forEach((uid) => put(uid, { kind: 'hand', player })));
    state.completed.forEach((list, player) => list.forEach((uid) => put(uid, { kind: 'completed', player })));
    for (const [pid, project] of Object.entries(state.projects)) {
      put(Number(pid), { kind: 'project', player: project.owner });
      project.filled.forEach((entry) => put(entry.uid, { kind: 'factor', player: project.owner, project: Number(pid) }));
      if (project.extra) put(project.extra.uid, { kind: 'extra', player: project.owner, project: Number(pid) });
    }
    state.coops.forEach((coop, index) => { if (coop.shared) put(coop.shared.uid, { kind: 'factor', player: null, project: `coop${index}` }); });
    return zones;
  }

  const zoneKey = (zone) => [zone.kind, zone.player ?? '', zone.pile ?? '', zone.project ?? ''].join(':');
  const faceUp = (zone) => !['deck', 'consumed'].includes(zone.kind) && !(zone.kind === 'hand' && zone.player !== viewer);
  const seatEl = (player) => $(`#opponents .opp[data-seat="${player}"]`);

  function anchorEl(uid, zone) {
    switch (zone.kind) {
      case 'deck': return $(`#piles .pile[data-target="pile:${zone.pile}"] img`);
      case 'consumed': return $('#piles .pile-consumed img');
      case 'discard': return $('#piles .pile-discard > button');
      case 'hand': return zone.player === viewer ? $(`#hand .gc[data-uid="${uid}"] .gc-face`) : seatEl(zone.player)?.querySelector('.opp-hand');
      case 'project': return $(`#play .proj[data-pid="${uid}"] .proj-head`);
      case 'factor': return $(`#play [data-target="factor:${uid}"]`);
      case 'extra': return $(`#play [data-extra="${uid}"]`);
      case 'completed': return zone.player === viewer ? $('#my-completed') : seatEl(zone.player)?.querySelector('.opp-done');
      default: return null;
    }
  }

  // Where a card came from when the last render did not know it (a masked hand
  // online, a card from "Sichten").
  function guessSource(zone) {
    if (zone.kind === 'hand' && zone.player === viewer) return { kind: 'deck', pile: 'action' };
    if (['project', 'factor', 'extra'].includes(zone.kind) && typeof zone.player === 'number' && zone.player !== viewer) return { kind: 'hand', player: zone.player };
    return null;
  }

  // Before the table is rebuilt: which cards move, and where they start.
  function planFlights() {
    const zones = cardZones(game);
    const moves = [];
    if (lastZones && viewer !== null && viewer === lastViewer && !stillMotion.matches) {
      for (const [uid, to] of zones) {
        let from = lastZones.get(uid);
        if (from && zoneKey(from) === zoneKey(to)) continue;
        if (!from) from = guessSource(to);
        // Reshuffling the consumed pile into the deck is not a move worth watching.
        if (!from || (['deck', 'consumed'].includes(from.kind) && ['deck', 'consumed'].includes(to.kind))) continue;
        const el = anchorEl(uid, from);
        if (el) moves.push({ uid, from, to, rect: el.getBoundingClientRect() });
      }
    }
    lastZones = zones;
    lastViewer = viewer;
    return moves.slice(0, 10);
  }

  // Card-shaped anchors are met exactly; text (a requirement, a list) gets a
  // small card that fades as it arrives.
  function cardBox(rect) {
    if (rect.width && Math.abs(rect.width / rect.height - 5 / 7) < 0.1) return { ...rect.toJSON(), exact: true };
    const width = 56;
    return { left: rect.left + rect.width / 2 - width / 2, top: rect.top + rect.height / 2 - width * 0.7, width, exact: false };
  }

  function flyCard(c, fromRect, toRect, { fromFace, toFace, duration, delay }) {
    const a = cardBox(fromRect);
    const b = cardBox(toRect);
    const flight = h('div', { class: 'flight' },
      h('div', { class: 'flight-card' },
        h('img', { class: 'flight-face', src: `assets/cards-sm/${c.id}.webp`, alt: '' }),
        h('img', { class: 'flight-back', src: 'assets/cards-sm/back.webp', alt: '' })));
    flight.style.cssText = `left:${b.left}px;top:${b.top}px;width:${b.width}px`;
    flightLayer.append(flight);
    const timing = { duration, delay, easing: 'cubic-bezier(.22,.8,.24,1)', fill: 'both' };
    const move = flight.animate([
      { transform: `translate(${a.left - b.left}px,${a.top - b.top}px) scale(${a.width / b.width})` },
      { transform: 'none' },
    ], timing);
    const turn = (face) => `rotateY(${face ? 0 : 180}deg)`;
    if (fromFace !== toFace) flight.firstChild.animate([{ transform: turn(fromFace) }, { transform: turn(toFace) }], timing);
    else flight.firstChild.style.transform = turn(toFace);
    if (!b.exact) flight.animate([{ opacity: 1, offset: 0.65 }, { opacity: 0 }], { duration, delay, fill: 'both' });
    return move.finished.catch(() => {}).then(() => flight.remove());
  }

  function scoreFloat(rect, points, delay) {
    const tag = h('div', { class: 'score-float', text: `+${points}` });
    tag.style.cssText = `left:${rect.left + rect.width / 2}px;top:${rect.top + rect.height / 2}px`;
    flightLayer.append(tag);
    tag.animate([
      { transform: 'translate(-50%,-20%) scale(.7)', opacity: 0 },
      { transform: 'translate(-50%,-60%) scale(1)', opacity: 1, offset: 0.2 },
      { transform: 'translate(-50%,-60%) scale(1)', opacity: 1, offset: 0.55 },
      { transform: 'translate(-50%,-150%) scale(1)', opacity: 0 },
    ], { duration: 1500, delay, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'both' }).finished.catch(() => {}).then(() => tag.remove());
  }

  // After the table is rebuilt: fly every move to its new place.
  function launchFlights(moves) {
    const duration = prefs.fast ? 240 : 520;
    moves.forEach((move, index) => {
      const target = anchorEl(move.uid, move.to);
      if (!target || !target.getClientRects().length) return;
      const c = card(move.uid);
      const delay = index * (prefs.fast ? 30 : 70);
      // The card itself waits under the flight; piles, other hands and lists do not.
      const own = !['deck', 'consumed', 'completed'].includes(move.to.kind) && faceUp(move.to);
      if (own) {
        target.classList.add('is-landing');
        target.closest('.gc')?.classList.remove('is-arriving');
        landing.set(move.uid, move.to);
      }
      if (move.from.kind === 'project' && move.to.kind === 'completed') scoreFloat(move.rect, c.points, delay + duration * 0.5);
      flyCard(c, move.rect, target.getBoundingClientRect(), { fromFace: faceUp(move.from), toFace: faceUp(move.to), duration, delay }).then(() => {
        if (!own) return;
        landing.delete(move.uid);
        const now = anchorEl(move.uid, move.to);
        if (now) {
          now.classList.remove('is-landing');
          now.classList.add('has-landed');
        }
      });
    });
  }

  // A render during a flight rebuilds its target; keep that hidden too.
  function keepLanding() {
    for (const [uid, zone] of landing) anchorEl(uid, zone)?.classList.add('is-landing');
  }

  /* ------------------------------------------------------------ fit */

  // On wide screens the table is exactly as high as the window below the site
  // header, so the page does not scroll. A board that runs longer is scaled
  // down, to 80 % at most; only then does the board itself scroll. Phones keep
  // the long, scrolling table.
  const wideTable = window.matchMedia('(min-width: 901px)');
  function fitTable() {
    const header = $('.site-header');
    if (header) document.documentElement.style.setProperty('--header-h', `${header.offsetHeight}px`);
    const board = $('.play-board');
    const fit = $('#board-fit');
    fit.style.zoom = '';
    if (!wideTable.matches || $('#play').hidden) return;
    const room = board.clientHeight;
    let height = fit.getBoundingClientRect().height;
    let zoom = 1;
    for (let pass = 0; pass < 4 && height > room + 0.5 && zoom > 0.8; pass += 1) {
      zoom = Math.max(0.8, zoom * (room / height) - 0.004);
      fit.style.zoom = zoom.toFixed(3);
      height = fit.getBoundingClientRect().height;
    }
  }

  // A row of projects wider than the board is scaled down to fit, to 70 % at
  // most, and scrolls sideways only beyond that.
  function fitRows() {
    document.querySelectorAll('#board-fit .proj-row').forEach((row) => {
      row.style.zoom = '';
      row.classList.remove('is-scrolling');
      if (!wideTable.matches || row.scrollWidth <= row.clientWidth + 1) return;
      row.style.zoom = Math.max(0.7, row.clientWidth / row.scrollWidth - 0.004).toFixed(3);
      if (row.scrollWidth > row.clientWidth + 1) row.classList.add('is-scrolling');
    });
  }

  /* ------------------------------------------------------------ dialogs */

  function openCard(uid) {
    hidePeek();
    const c = card(uid);
    const dialog = $('#card-detail');
    $('#detail-image').src = `assets/cards/${c.id}.webp`;
    $('#detail-image').alt = c.name;
    const extra = c.type === 'Projekt' ? ` · ${c.points} Punkte` : '';
    $('#detail-meta').textContent = `${c.id} · ${c.type}${extra}`;
    $('#detail-title').textContent = c.name;
    $('#detail-rule').textContent = c.type === 'Projekt' && c.goal ? `${c.goal} ${c.rules}` : c.rules;
    $('#detail-flavor').textContent = c.flavor;
    $('#detail-flavor').hidden = !c.flavor;
    $('#detail-collection').href = `karten.html#${c.id}`;
    if (!dialog.open) dialog.showModal();
  }

  function openDiscard() {
    const grid = $('#discard-grid');
    grid.replaceChildren(...game.discard.slice().reverse().map((uid) => {
      const face = cardFace(uid, { sizes: '120px' });
      face.addEventListener('click', () => { $('#discard-view').close(); openCard(uid); });
      return face;
    }));
    $('#discard-view').showModal();
    fitNames(grid);
  }

  function showResult() {
    const result = E.scores(game);
    const rows = result.rows.slice().sort((a, b) => b.total - a.total || b.completed - a.completed || a.unfinished - b.unfinished);
    $('#result-title').textContent = `${result.winners.length > 1 ? 'Geteilter Sieg' : 'Sieg'}: ${result.winners.map(seatName).join(' und ')}`;
    let place = 0;
    let previous = null;
    $('#result-rows').replaceChildren(...rows.map((row, index) => {
      const key = `${row.total}/${row.completed}/${row.unfinished}`;
      if (key !== previous) place = index + 1;
      previous = key;
      return h('tr', { class: result.winners.includes(row.player) ? 'is-winner' : '' },
        h('td', { text: `${place}.` }),
        h('th', { scope: 'row', text: row.name }),
        h('td', { text: `${row.completed} · +${row.plus}` }),
        h('td', { text: row.unfinished ? `${row.unfinished} · −${row.minus}` : '0' }),
        h('td', { class: 'result-total', text: signed(row.total) }));
    }));
    const dialog = $('#result');
    if (!dialog.open) dialog.showModal();
  }

  function newSetup() {
    $('#result').close();
    leaveTable();
  }

  /* ------------------------------------------------------------ wiring */

  document.querySelectorAll('.mode-switch [data-mode]').forEach((button) => button.addEventListener('click', () => setMode(button.dataset.mode)));
  $('#add-seat').addEventListener('click', () => {
    if (seats.length >= E.RULES.maxPlayers) return;
    const role = mode === 'solo' ? 'umsichtig' : 'human';
    seats.push({ name: '', role });
    seats[seats.length - 1].name = defaultName(seats.length - 1, role);
    renderSeats();
  });
  $('#start-game').addEventListener('click', () => {
    const gameSeats = seatsForGame(seats);
    if (!gameSeats.some((seat) => seat.kind === 'human')) return;
    store.set(PREFS_KEY, { ...prefs, mode, seats });
    startGame(gameSeats);
  });
  $('#resume-game').addEventListener('click', () => {
    const saved = store.get(STORE_KEY);
    if (!saved || !saved.game) { renderResume(); return; }
    game = saved.game;
    lastSeen = saved.lastSeen || {};
    enterTable();
  });
  $('#resume-drop').addEventListener('click', () => { store.drop(STORE_KEY); renderResume(); });
  $('#quit-game').addEventListener('click', () => {
    if (game.phase !== 'over' && !window.confirm('Partie beenden? Sie wird nicht gespeichert.')) return;
    store.drop(STORE_KEY);
    leaveTable();
  });
  $('#rematch').addEventListener('click', () => {
    const seatsAgain = game.seats.map((seat) => ({ ...seat }));
    $('#result').close();
    startGame(seatsAgain);
  });
  $('#new-setup').addEventListener('click', newSetup);
  window.addEventListener('resize', () => {
    if (!game) return;
    fitTable();
    fitRows();
    squeezeHand();
  });
  $('#fast-bots').addEventListener('change', (event) => {
    prefs.fast = event.target.checked;
    store.set(PREFS_KEY, { ...(store.get(PREFS_KEY) || {}), fast: prefs.fast });
  });
  $('#handover-go').addEventListener('click', () => {
    $('#handover').hidden = true;
    viewer = handoverFor;
    render();
    $('#prompt').focus({ preventScroll: true });
  });

  $('#play').addEventListener('click', (event) => {
    if (!game) return;
    const handCard = event.target.closest('#hand .gc');
    if (handCard) {
      select(Number(handCard.dataset.uid));
      return;
    }
    let el = event.target.closest('[data-target], [data-inspect]');
    if (!el) {
      const panel = event.target.closest('.proj');
      if (panel) el = panel.querySelector('.proj-head');
    }
    if (!el || !$('#play').contains(el)) return;
    if (el.dataset.target && el.classList.contains('is-target')) {
      onTarget(el.dataset.target);
      return;
    }
    if (el.dataset.inspect !== undefined) openCard(Number(el.dataset.inspect));
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !game || document.querySelector('dialog[open]')) return;
    if (selected !== null || filterKey) {
      selected = null;
      filterKey = null;
      render();
    }
  });

  document.querySelectorAll('dialog').forEach((dialog) => {
    dialog.querySelectorAll('[data-close]').forEach((button) => button.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
  });

  /* Online multiplayer wiring */
  $('#tab-create-room').addEventListener('click', () => {
    $('#tab-create-room').classList.add('is-active');
    $('#tab-create-room').setAttribute('aria-selected', 'true');
    $('#tab-join-room').classList.remove('is-active');
    $('#tab-join-room').setAttribute('aria-selected', 'false');
    $('#panel-create-room').hidden = false;
    $('#panel-join-room').hidden = true;
    if (!onlineSession || onlineRole !== 'host') initHostRoom();
  });

  $('#tab-join-room').addEventListener('click', () => {
    $('#tab-join-room').classList.add('is-active');
    $('#tab-join-room').setAttribute('aria-selected', 'true');
    $('#tab-create-room').classList.remove('is-active');
    $('#tab-create-room').setAttribute('aria-selected', 'false');
    $('#panel-join-room').hidden = false;
    $('#panel-create-room').hidden = true;
    if (onlineSession && onlineRole === 'host') {
      onlineSession.destroy();
      onlineSession = null;
      onlineRole = null;
    }
  });

  $('#copy-room-link').addEventListener('click', () => {
    const code = $('#display-room-code').textContent;
    const url = new URL(location.href);
    url.searchParams.set('raum', code);
    navigator.clipboard.writeText(url.toString()).then(() => {
      const btn = $('#copy-room-link');
      const old = btn.textContent;
      btn.textContent = 'Kopiert!';
      setTimeout(() => { btn.textContent = old; }, 2000);
    }).catch(() => {
      prompt('Link kopieren:', url.toString());
    });
  });

  $('#host-name').addEventListener('input', (e) => {
    if (onlineSession && onlineRole === 'host') {
      onlineSession.hostName = e.target.value.trim() || 'Du';
      onlineSession.seats[0].name = onlineSession.hostName;
      onlineSession.broadcastLobby();
    }
  });

  $('#online-add-bot').addEventListener('click', () => {
    if (onlineSession && onlineRole === 'host') {
      onlineSession.addBot('umsichtig');
    }
  });

  $('#start-online-game').addEventListener('click', () => {
    if (onlineSession && onlineRole === 'host') {
      try {
        onlineSession.startGame();
      } catch (err) {
        alert(err.message);
      }
    }
  });

  $('#btn-join-room').addEventListener('click', joinOnlineRoom);
  $('#join-code').addEventListener('keydown', (e) => { if (e.key === 'Enter') joinOnlineRoom(); });

  const urlParams = new URLSearchParams(location.search);
  const roomParam = urlParams.get('raum') || urlParams.get('room');
  if (roomParam) {
    setMode('online');
    $('#tab-join-room').click();
    $('#join-code').value = roomParam.toUpperCase();
    $('#join-name').focus();
  } else {
    const saved = store.get(PREFS_KEY);
    if (saved && saved.mode && Array.isArray(saved.seats) && saved.seats.length >= E.RULES.minPlayers) {
      mode = saved.mode;
      seats = saved.seats.map((seat) => ({ name: String(seat.name || ''), role: ROLES.some(([value]) => value === seat.role) ? seat.role : 'human' }));
      document.querySelectorAll('.mode-switch [data-mode]').forEach((button) => button.setAttribute('aria-checked', String(button.dataset.mode === mode)));
      renderSeats();
    } else {
      setMode('solo');
    }
  }
  renderResume();
})();
