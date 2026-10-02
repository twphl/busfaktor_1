# ADR 0016: Freistehende Polaritätsmarke

- Status: abgelöst
- Datum: 2026-08-30
- Berührt: Typzeile, Polaritätsdarstellung, Vorderseitenrenderer
- Löst teilweise ab: ADR 0015 hinsichtlich Trägergeometrie, Zeichengröße und
  Zeichenfarbe
- Abgelöst durch: ADR 0018; auf der Vorderseite erscheint keine
  Polaritätsmarke mehr

## Kontext

ADR 0015 trennte die Polarität vom Farbkanal, führte für `+`, `−` und `±` aber
einen konturierten 22-Einheiten-Kreis ein. Dieser Träger erzeugte innerhalb der
ohnehin kompakten Typzeile eine zusätzliche Badge-Form. Eine Verkleinerung des
Kreises wäre druckseitig keine robuste Lösung: Kontur, Innenraum und Glyphe
rückten enger zusammen und reagierten empfindlicher auf Tonwertzunahme und
Passerschwankungen.

Die drei Polaritäten benötigen keine eigene Trägerform. Ihre konventionellen
Zeichen bleiben in Graustufen und bei reduziertem Farbsehen unterscheidbar.
Eine gemeinsame violette Zeichenfarbe kann sie zugleich ruhiger in die
Ereignis-Typzeile integrieren, ohne erneut polaritätsabhängige Farben
einzuführen.

## Entscheidung

Der Polaritätskreis aus ADR 0015 entfällt vollständig. Der Renderer zeichnet
weder Kontur noch Füllfläche oder einen anderen Träger.

Der maschinenlesbare Vertrag wird dafür auf Layoutversion `1.20.0` und
Rendererversion `0.24.0` angehoben.

Direkt nach `EREIGNIS` steht die Polaritätsmarke frei in einem festen
18-Einheiten-Slot. Sie verwendet Noto Sans Bold 18/22 und den gemeinsamen
Ereigniston `event/base` (`#60457A`). Die Zuordnung bleibt:

| Datenwert | sichtbares Zeichen |
|---|---|
| `positive` | `+` |
| `negative` | `−` (U+2212) |
| `ambivalent` | `±` |

Nach dem Slot liegen fünf Einheiten Abstand vor dem 18 Einheiten großen
Effektsymbol. Ereignisschlüsselwort und Zielangabe bleiben in neutralem
`text/primary`. Alle drei Polaritätsmarken besitzen dieselbe Farbe; ihre
Semantik bleibt deshalb glyphenbasiert und farbunabhängig.

Der gemeinsame Ereignisakzent `event/base`, der neutrale Sekundärtext und das
unveränderte Methodengold aus ADR 0015 bleiben beschlossen. ADR 0016 ersetzt
nur dessen Kreisgeometrie sowie Größe und Farbe des Polaritätszeichens.

## Folgen

- Die Polaritätsmarke fügt sich als Teil der violetten Ereignissignatur in die
  Typzeile ein, ohne eine zusätzliche Badge- oder Trägerform einzuführen.
- Gegenüber dem 22-Einheiten-Kreis gewinnt die nachfolgende Sekundärzeile vier
  Einheiten Breite. Beim engsten Ereignis `KAT-U17` verbleiben rund 83,997
  Einheiten bis zur rechten Textgrenze.
- Die Polarität bleibt durch `+`, `−` und `±` formbasiert unterscheidbar. Die
  gemeinsame violette Farbe ist kein Träger der Polaritätssemantik.
- Die produktive Strichstärkenskala benötigt keine Kontur für die
  Polaritätsdarstellung.
- Produktionszahlen, Seltenheiten, Spielmechanik und die Werte in
  `data/cards.csv` ändern sich nicht.
- Renderer-Preview und technischer Proof bleiben nicht farbverbindlich. Größe,
  Farbe und Laufweite der freistehenden Zeichen benötigen vor der
  Produktionsfreigabe weiterhin einen physischen Andruck.
