# Busfaktor: 1 — Signaling-Server (VPS)

Dieser Dienst vermittelt den Verbindungsaufbau (WebRTC-Handshake) zwischen Mitspielenden von *Busfaktor: 1*.
Sobald die Verbindung steht, läuft die Partie direkt über verschlüsselte WebRTC-DataChannels von Browser zu Browser.

---

## 1. Schnelle Inbetriebnahme mit Docker

```bash
cd server
docker compose up -d
```

Der Server lauscht auf Port `9000` unter dem Pfad `/busfaktor`.

---

## 2. Betrieb direkt mit Node.js & systemd

### Installation
```bash
cd server
npm install
node server.js
```

### Als systemd-Dienst einrichten
Erstelle `/etc/systemd/system/busfaktor-peer.service`:

```ini
[Unit]
Description=Busfaktor: 1 PeerJS Signaling Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/busfaktor/server
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=5
Environment=PORT=9000
Environment=PEER_PATH=/busfaktor

[Install]
WantedBy=multi-user.target
```

Aktivieren und starten:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now busfaktor-peer
```

---

## 3. Reverse Proxy (Nginx / Caddy) mit SSL

Da Browser WebRTC in sicheren Kontexten (`https://`) erwarten, muss der Signaling-Server über HTTPS/WSS erreichbar sein.

### Nginx
```nginx
location /busfaktor {
    proxy_pass http://127.0.0.1:9000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Caddy
```caddy
example.com {
    handle /busfaktor* {
        reverse_proxy 127.0.0.1:9000
    }
}
```

---

## 4. Für restriktive Netze (eduroam / BBAW): STUN / TURN

Öffentliche STUN-Server (z. B. Google `stun:stun.l.google.com:19302`) lösen NAT für ca. 85 % der Verbindungen auf. In manchen Instituts- und Konferenznetzen mit symmetrischem NAT wird ein TURN-Relay benötigt.

Auf Debian/Ubuntu lässt sich `coturn` installieren:
```bash
sudo apt update && sudo apt install coturn
```
Konfiguriere `/etc/turnserver.conf` mit Nutzername und Passwort und trage die Adresse in die Client-Konfiguration ein (`website/network.js`).
