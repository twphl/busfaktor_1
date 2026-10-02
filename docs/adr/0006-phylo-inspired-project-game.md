# ADR 0006: Phylo-inspiriertes Projektkartenspiel

- Status: angenommen
- Datum: 2026-08-05
- Ersetzt: ADR 0001

> **Nachtrag 2026-08-28:** Die hier eingeführte Kartenart `Wendung` heißt seit
> ADR 0011 `Ereignis`. Mechanik, Zahlen und Templates bleiben unverändert; nur
> der Produktbegriff wurde ersetzt. Dieser ADR behält den Wortlaut vom
> 2026-08-05.

## Kontext

Der kompakte Multiplayer-Singleton-Entwurf hätte innerhalb der verbleibenden
Produktionszeit ein neues Kampf-, Kosten- und Deckbausystem sowie 82
individuelle Mechaniken benötigt. Die untersuchten Process-of-Science-Varianten
von Phylo bieten dagegen einen bereits erprobten Kern aus Projekten,
Anforderungen, Ressourcen und Kooperation.

## Entscheidung

Das Produkt wird als eigenständige, Phylo-inspirierte Projektspiel-Fassung
weiterentwickelt:

- Projekte werden durch Kombinationen aus Team, Daten, Betrieb und Methode
  abgeschlossen.
- Projektfaktoren erfüllen diese Anforderungen.
- Wendungen verändern Projekte, Faktoren oder den Kartenfluss.
- Der Bühnensatz verwendet gemeinsame Projekt- und Aktionsstapel statt
  persönlicher Kampfdecks.
- Das Spiel erhält eigene deutsche Regeltexte, Terminologie, Ikonografie und
  eigenes Trade Dress.

Die Begriffe Projekt, Projektfaktor und Wendung sind Produktbegriffe. `Phylo`
bleibt Herkunfts- und Arbeitsbegriff, nicht automatisch der endgültige
Produktname.

## Folgen

- ADR 0001 und die Projektleitungsdaten sind abgelöst.
- Der 82er-Boosterpool wird auf 16 Projekte, 38 Projektfaktoren und 28
  Wendungen abgebildet.
- Ein Booster enthält garantiert 2 Projekte, 7 Projektfaktoren und 3
  Wendungen.
- Für den Prototyp genügen acht wiederverwendbare Wendungs-Templates.
- Lizenz, Version und Attribution der adaptierten Regelstruktur sind vor einer
  Veröffentlichung ein Freigabegate.
