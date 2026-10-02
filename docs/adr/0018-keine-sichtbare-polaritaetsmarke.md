# ADR 0018: Keine sichtbare Polaritätsmarke

- Status: angenommen
- Datum: 2026-08-30
- Berührt: Typzeile, Polaritätsdarstellung, Vorderseitenrenderer, Regelhinweis
- Löst ab: ADR 0016 vollständig und ADR 0015 hinsichtlich der sichtbaren
  Polaritätscodierung

## Kontext

ADR 0015 führte für positive, negative und ambivalente Ereignisse die Zeichen
`+`, `−` und `±` ein. ADR 0016 entfernte deren Kreis, ließ aber eine
freistehende violette Marke und einen festen 18-Einheiten-Slot in der Typzeile
bestehen. Auch ohne Träger bildet diese Marke eine zusätzliche visuelle
Kategorie neben Kartentyp, Effektsymbol und Ereignisschlüsselwort.

Die Polarität wird nur für das Reaktionsfenster von Absicherungen mechanisch
benötigt. Im aktuellen Set sind alle und ausschließlich die Ereignisse mit den
sichtbaren Schlüsselwörtern `MEHRAUFWAND` (E6) und `RÜCKSCHLAG` (E7) negativ.
Damit ist die relevante Eigenschaft bereits ohne eine weitere Marke eindeutig
auf der Karte erkennbar. Positive und ambivalente Ereignisse benötigen keine
eigene sichtbare Unterscheidung.

## Entscheidung

Die Vorderseite zeigt keine Polaritätsmarke. Das gilt gleichermaßen für `+`,
`−` und `±`. Der Renderer erzeugt weder Zeichen, Wort, Icon, Träger noch einen
dafür reservierten leeren Slot.

Direkt fünf Einheiten nach `EREIGNIS` beginnt das 18 Einheiten große
Effektsymbol. Darauf folgen wie bisher das E1–E8-Schlüsselwort und eine
gegebenenfalls vorhandene Zielangabe.

Das kanonische Feld `polarity` bleibt in `data/cards.csv`, Validierung und
Simulation erhalten. Im SVG wird sein Wert ausschließlich als nicht sichtbares
Attribut `data-polarity` am Wurzelelement geführt. Der Validator sichert ab,
dass genau E6 und E7 negativ sind; die Spielregeln benennen diese beiden
Schlüsselwörter ausdrücklich als negative Ereignisse.

Der maschinenlesbare Vertrag steigt auf Layoutversion `1.24.0` und
Rendererversion `0.28.0`.

## Folgen

- Die Ereignis-Typzeile enthält nur noch Kartentyp, Effektsymbol,
  Schlüsselwort und gegebenenfalls Zielangabe.
- Gegenüber ADR 0016 gewinnt der Sekundärtext 23 Einheiten Breite. Beim engsten
  Ereignis `KAT-U17` verbleiben rund 106,997 Einheiten bis zur rechten
  Textgrenze.
- Negative Ereignisse bleiben über `MEHRAUFWAND` und `RÜCKSCHLAG` sichtbar und
  damit ohne verborgene Information absicherbar.
- Positive und ambivalente Werte bleiben für Datenpflege und Simulation
  erhalten, erscheinen aber nicht als eigene Markierung auf der Karte.
- Produktionszahlen, Seltenheiten, Kartenmotive und Illustrationen ändern sich
  nicht.
