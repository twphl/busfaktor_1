/* Busfaktor: 1 — WebRTC Network Layer (PeerJS)
   Verwaltet Online-Räume, Host-Client-Kommunikation, State-Synchronisation
   und Reconnects über WebRTC DataChannels. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.BusfaktorNetwork = api;
})(typeof self !== 'undefined' ? self : this, () => {
  'use strict';

  const PEER_PREFIX = 'bf1-room-';
  const CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

  function generateRoomCode(len = 4) {
    let code = '';
    for (let i = 0; i < len; i += 1) {
      code += CHARS[Math.floor(Math.random() * CHARS.length)];
    }
    return code;
  }

  function normalizeRoomCode(code) {
    return String(code || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
  }

  function getSessionToken(roomId) {
    const key = `bf_token_${roomId}`;
    let token = sessionStorage.getItem(key);
    if (!token) {
      token = 'tok_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      try { sessionStorage.setItem(key, token); } catch (e) { /* private mode */ }
    }
    return token;
  }

  function defaultPeerConfig() {
    if (typeof window !== 'undefined' && window.BUSFAKTOR_PEER_CONFIG) {
      return window.BUSFAKTOR_PEER_CONFIG;
    }
    const isHttps = typeof location !== 'undefined' && location.protocol === 'https:';
    const isLocal = typeof location !== 'undefined' && (location.hostname === 'localhost' || location.hostname === '127.0.0.1');

    // In local dev without https, connect to port 9000 by default
    if (isLocal && !isHttps) {
      return {
        host: location.hostname || 'localhost',
        port: 9000,
        path: '/busfaktor',
        secure: false,
        config: {
          iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
        },
      };
    }

    // In production behind reverse proxy (https://domain/busfaktor)
    return {
      host: typeof location !== 'undefined' ? location.hostname : 'localhost',
      port: isHttps ? 443 : 80,
      path: '/busfaktor',
      secure: isHttps,
      config: {
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      },
    };
  }

  /* ------------------------------------------------------------ HostSession */

  class HostSession {
    constructor({ roomId, hostName, rows, config, onLobbyUpdate, onStateUpdate, onError, onPlayerMessage }) {
      this.roomId = normalizeRoomCode(roomId || generateRoomCode());
      this.hostName = hostName || 'Host';
      this.rows = rows || [];
      this.peerConfig = config || defaultPeerConfig();
      this.onLobbyUpdate = onLobbyUpdate || (() => {});
      this.onStateUpdate = onStateUpdate || (() => {});
      this.onError = onError || (() => {});
      this.onPlayerMessage = onPlayerMessage || (() => {});

      this.peer = null;
      this.game = null;
      this.connections = new Map(); // seatIndex -> DataConnection
      this.tokens = new Map(); // seatIndex -> token
      this.botTimer = null;
      this.reactionTimer = null;

      this.seats = [
        { name: this.hostName, kind: 'human', role: 'human', connected: true },
      ];

      this.initPeer();
    }

    initPeer() {
      const peerId = PEER_PREFIX + this.roomId;
      this.peer = new window.Peer(peerId, this.peerConfig);

      this.peer.on('open', () => {
        this.onLobbyUpdate(this.getLobbyData());
      });

      this.peer.on('connection', (conn) => {
        this.handleIncomingConnection(conn);
      });

      this.peer.on('error', (err) => {
        console.error('[Host] Peer error:', err);
        if (err.type === 'unavailable-id') {
          this.onError(new Error(`Raumcode ${this.roomId} ist bereits vergeben. Bitte wähle einen anderen.`));
        } else {
          this.onError(err);
        }
      });
    }

    handleIncomingConnection(conn) {
      conn.on('data', (msg) => {
        if (!msg || typeof msg !== 'object') return;

        if (msg.type === 'join') {
          this.handleClientJoin(conn, msg);
        } else if (msg.type === 'action') {
          // Look the seat up every time: it shifts when someone leaves the lobby.
          const seat = this.seatOf(conn);
          if (seat !== null) this.handleClientAction(seat, msg.action);
        }
      });

      conn.on('close', () => {
        const seat = this.seatOf(conn);
        if (seat !== null) this.handleClientDisconnect(seat);
      });

      conn.on('error', (err) => {
        console.warn(`[Host] Verbindung zu Sitz ${this.seatOf(conn)} fehlerhaft:`, err);
      });
    }

    seatOf(conn) {
      for (const [seat, candidate] of this.connections) {
        if (candidate === conn) return seat;
      }
      return null;
    }

    handleClientJoin(conn, { name, token }) {
      const E = window.BusfaktorEngine;
      const cleanName = String(name || 'Mitspielende/r').trim().slice(0, 24);

      // Check if this is a reconnecting player
      for (let i = 1; i < this.seats.length; i += 1) {
        if (this.tokens.get(i) === token) {
          // Reconnect!
          this.connections.set(i, conn);
          this.seats[i].connected = true;
          this.seats[i].name = cleanName;
          conn.send({
            type: 'welcome',
            seat: i,
            roomId: this.roomId,
            lobby: this.getLobbyData(),
            started: this.game !== null,
          });

          if (this.game) {
            conn.send({
              type: 'state',
              seat: i,
              state: E.playerView(this.game, i),
            });
          }
          this.broadcastLobby();
          return i;
        }
      }

      // If game has already started, cannot join as a new player
      if (this.game) {
        conn.send({ type: 'error', message: 'Die Partie läuft bereits.' });
        conn.close();
        return null;
      }

      // If room is full (max 4 players)
      if (this.seats.length >= E.RULES.maxPlayers) {
        conn.send({ type: 'error', message: 'Der Raum ist bereits voll (maximal 4 Plätze).' });
        conn.close();
        return null;
      }

      // Assign next seat
      const seat = this.seats.length;
      this.seats.push({ name: cleanName, kind: 'human', role: 'human', connected: true });
      this.connections.set(seat, conn);
      this.tokens.set(seat, token);

      conn.send({
        type: 'welcome',
        seat,
        roomId: this.roomId,
        lobby: this.getLobbyData(),
        started: false,
      });

      this.broadcastLobby();
      return seat;
    }

    handleClientDisconnect(seat) {
      if (this.seats[seat]) {
        this.seats[seat].connected = false;
        this.connections.delete(seat);
        if (!this.game) {
          // In lobby, remove seat if disconnected
          this.seats.splice(seat, 1);
          this.tokens.delete(seat);
          // Re-index remaining connections
          this.shiftSeatsAfter(seat);
          this.reindexSeats();
        }
        this.broadcastLobby();
      }
    }

    // A seat index is a position in this.seats, so every map keyed by it has to
    // move down when a seat in front of it leaves the lobby. Without this the
    // host would authorise actions and send player views for stale seats.
    shiftSeatsAfter(removed) {
      const move = (map) => {
        const next = new Map();
        map.forEach((value, seat) => next.set(seat > removed ? seat - 1 : seat, value));
        return next;
      };
      this.connections = move(this.connections);
      this.tokens = move(this.tokens);
    }

    reindexSeats() {
      // Re-notify all connected clients of their potentially shifted seat
      this.connections.forEach((conn, seat) => {
        if (conn.open) conn.send({ type: 'seat_update', seat, lobby: this.getLobbyData() });
      });
    }

    addBot(botRole = 'umsichtig') {
      const E = window.BusfaktorEngine;
      if (this.game || this.seats.length >= E.RULES.maxPlayers) return false;
      const botNames = ['Rechenzentrum', 'Lenkungskreis', 'Drittmittelstelle', 'Beirat'];
      const used = new Set(this.seats.map((s) => s.name));
      const name = botNames.find((n) => !used.has(n)) || `Bot ${this.seats.length + 1}`;
      this.seats.push({ name, kind: 'bot', role: botRole, connected: true });
      this.broadcastLobby();
      return true;
    }

    removeSeat(seatIndex) {
      if (this.game || seatIndex <= 0 || seatIndex >= this.seats.length) return false;
      const conn = this.connections.get(seatIndex);
      if (conn) conn.close();
      this.seats.splice(seatIndex, 1);
      this.connections.delete(seatIndex);
      this.tokens.delete(seatIndex);
      this.shiftSeatsAfter(seatIndex);
      this.reindexSeats();
      this.broadcastLobby();
      return true;
    }

    getLobbyData() {
      return {
        roomId: this.roomId,
        seats: this.seats.map((s, idx) => ({ ...s, seatIndex: idx })),
      };
    }

    broadcastLobby() {
      const data = this.getLobbyData();
      this.onLobbyUpdate(data);
      const msg = { type: 'lobby', lobby: data };
      this.connections.forEach((conn) => {
        if (conn.open) conn.send(msg);
      });
    }

    startGame() {
      const E = window.BusfaktorEngine;
      if (this.seats.length < E.RULES.minPlayers) {
        throw new Error(`Mindestens ${E.RULES.minPlayers} Plätze erforderlich.`);
      }

      const gameSeats = this.seats.map((s) => (s.kind === 'human' ? { name: s.name, kind: 'human' } : { name: s.name, kind: 'bot', bot: s.role }));
      this.game = E.newGame({ seats: gameSeats, rows: this.rows, seed: (Math.random() * 2 ** 32) >>> 0 });

      this.broadcastState();
      this.checkBotTurn();
    }

    handleClientAction(seat, action) {
      const E = window.BusfaktorEngine;
      if (!this.game || this.game.phase === 'over') return;

      const actor = E.actor(this.game);
      if (actor !== seat) {
        console.warn(`[Host] Aktion von unberechtigtem Sitz ${seat} abgelehnt. Am Zug: ${actor}`);
        return;
      }

      try {
        E.apply(this.game, action);
      } catch (err) {
        console.error(`[Host] Fehler bei Aktion von Sitz ${seat}:`, err);
        const conn = this.connections.get(seat);
        if (conn && conn.open) conn.send({ type: 'action_error', message: err.message });
        return;
      }

      this.broadcastState();
      this.checkBotTurn();
    }

    handleHostAction(action) {
      const E = window.BusfaktorEngine;
      if (!this.game || this.game.phase === 'over') return;
      const actor = E.actor(this.game);
      if (actor !== 0) {
        throw new Error(`Nicht am Zug (aktuell: ${actor})`);
      }
      E.apply(this.game, action);
      this.broadcastState();
      this.checkBotTurn();
    }

    broadcastState() {
      const E = window.BusfaktorEngine;
      // Host local state (Seat 0)
      this.onStateUpdate(E.playerView(this.game, 0), 0);

      // Clients state
      this.connections.forEach((conn, seat) => {
        if (conn.open) {
          conn.send({
            type: 'state',
            seat,
            state: E.playerView(this.game, seat),
          });
        }
      });
    }

    checkBotTurn() {
      const E = window.BusfaktorEngine;
      const B = window.BusfaktorBots;
      clearTimeout(this.botTimer);

      if (!this.game || this.game.phase === 'over') return;

      const actor = E.actor(this.game);
      if (this.seats[actor] && this.seats[actor].kind === 'bot') {
        this.botTimer = setTimeout(() => {
          if (!this.game || this.game.phase === 'over') return;
          const currentActor = E.actor(this.game);
          if (this.seats[currentActor] && this.seats[currentActor].kind === 'bot') {
            const botAction = B.choose(this.game, currentActor);
            E.apply(this.game, botAction);
            this.broadcastState();
            this.checkBotTurn();
          }
        }, 800);
      }
    }

    destroy() {
      clearTimeout(this.botTimer);
      clearTimeout(this.reactionTimer);
      this.connections.forEach((conn) => conn.close());
      this.connections.clear();
      if (this.peer) this.peer.destroy();
    }
  }

  /* ------------------------------------------------------------ ClientSession */

  class ClientSession {
    constructor({ roomId, playerName, config, onWelcome, onLobbyUpdate, onStateUpdate, onError, onDisconnect }) {
      this.roomId = normalizeRoomCode(roomId);
      this.playerName = playerName || 'Mitspielende/r';
      this.peerConfig = config || defaultPeerConfig();
      this.onWelcome = onWelcome || (() => {});
      this.onLobbyUpdate = onLobbyUpdate || (() => {});
      this.onStateUpdate = onStateUpdate || (() => {});
      this.onError = onError || (() => {});
      this.onDisconnect = onDisconnect || (() => {});

      this.peer = null;
      this.conn = null;
      this.mySeat = null;
      this.token = getSessionToken(this.roomId);

      this.initPeer();
    }

    initPeer() {
      this.peer = new window.Peer(this.peerConfig);

      this.peer.on('open', () => {
        this.connectToHost();
      });

      this.peer.on('error', (err) => {
        console.error('[Client] Peer error:', err);
        this.onError(err);
      });
    }

    connectToHost() {
      const hostPeerId = PEER_PREFIX + this.roomId;
      this.conn = this.peer.connect(hostPeerId, { reliable: true });

      this.conn.on('open', () => {
        this.conn.send({
          type: 'join',
          name: this.playerName,
          token: this.token,
        });
      });

      this.conn.on('data', (msg) => {
        if (!msg || typeof msg !== 'object') return;

        switch (msg.type) {
          case 'welcome':
            this.mySeat = msg.seat;
            this.onWelcome({ seat: msg.seat, roomId: msg.roomId, started: msg.started });
            this.onLobbyUpdate(msg.lobby);
            break;
          case 'lobby':
            this.onLobbyUpdate(msg.lobby);
            break;
          case 'seat_update':
            this.mySeat = msg.seat;
            this.onLobbyUpdate(msg.lobby);
            break;
          case 'state':
            this.mySeat = msg.seat;
            this.onStateUpdate(msg.state, msg.seat);
            break;
          case 'action_error':
            this.onError(new Error(msg.message));
            break;
          case 'error':
            this.onError(new Error(msg.message));
            break;
          default:
            break;
        }
      });

      this.conn.on('close', () => {
        this.onDisconnect();
      });

      this.conn.on('error', (err) => {
        this.onError(err);
      });
    }

    sendAction(action) {
      if (this.conn && this.conn.open) {
        this.conn.send({ type: 'action', action });
      } else {
        throw new Error('Keine Verbindung zum Host.');
      }
    }

    destroy() {
      if (this.conn) this.conn.close();
      if (this.peer) this.peer.destroy();
    }
  }

  return {
    generateRoomCode,
    normalizeRoomCode,
    defaultPeerConfig,
    HostSession,
    ClientSession,
  };
});
