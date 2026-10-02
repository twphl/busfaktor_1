#!/usr/bin/env node
/* Busfaktor: 1 — Signaling-Server für WebRTC (PeerJS)
   Vermittelt den initialen Verbindungsaufbau (SDP-Offers & ICE-Kandidaten)
   zwischen den Browsern. Nach dem Handshake läuft der gesamte Spielverkehr
   direkt von Browser zu Browser via WebRTC DataChannel. */

const { PeerServer } = require('peer');

const PORT = parseInt(process.env.PORT || '9000', 10);
const PATH = process.env.PEER_PATH || '/busfaktor';

const server = PeerServer({
  port: PORT,
  path: PATH,
  // Off: the client connects to a known room id (PEER_PREFIX + Raumcode) and
  // never lists peers. Discovery would let anyone enumerate the open rooms.
  allow_discovery: false,
  proxied: true, // Für Betrieb hinter Nginx/Caddy Reverse Proxy
});

console.log(`[Busfaktor: 1] Peer-Server läuft auf Port ${PORT}, Pfad: ${PATH}`);

server.on('connection', (client) => {
  console.log(`[Connect] Peer verbunden: ${client.getId()}`);
});

server.on('disconnect', (client) => {
  console.log(`[Disconnect] Peer getrennt: ${client.getId()}`);
});

server.on('error', (err) => {
  console.error('[Error] Peer-Server Fehler:', err);
});
