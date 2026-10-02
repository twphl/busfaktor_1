# Projektgeschichte und verworfene Äste

## Ausgangspunkt

Das Projekt entstand aus einem DH-/RSE-Katastrophen-Bingo mit Motiven wie
`Backup nie getestet`, `Excel als Datenbank`, `KI hat das vorgeschlagen` und
der Live-Demo auf Eduroam. Der Ton war von Beginn an trocken und
wiedererkennbar; Ziel des Humors sind Strukturen und Prozesse.

## Vom Bingo zum Sammelkartenobjekt

Aus dem Bingo entstand die Idee eines hochwertigen Konferenzobjekts mit
Boosterverteilung, Seltenheiten und Foils. Die Kleinstauflage wurde auf 612
Standard- und 18 Foilkarten optimiert, manuell kollationiert und verpackt.

## Untersuchte Regelwerksäste

### Multiplayer-Singleton

Der erste ausgearbeitete Hauptpfad verwendete vier persönliche 40-Karten-Decks,
Projektleitungen, Kapazitäten und einen Kampf-/Stabilitätsablauf. Er hätte in
der verfügbaren Zeit ein vollständiges neues TCG mit vielen individuellen
Mechaniken benötigt und wurde durch ADR 0006 abgelöst.

### Arcmage

Arcmage bot ein attraktives klassisches TCG-Gefühl und offene Kartenlisten,
verlangte aber zu viele Kartenarten, Werte, Einheiten und Balancearbeit für die
erste Auflage.

### Dvorak

Dvorak war sehr erreichbar, wirkte für das gewünschte Sammelobjekt und die
fachliche Projektmetapher jedoch zu generisch.

## Entscheidung für die Phylo-Fassung

Die Process-of-Science-Regeln von Phylo bilden Forschungsarbeit direkt als
Projekte, Anforderungen, Ressourcen und Kooperation ab. Die Referenz-PDFs
zeigen außerdem, dass ein vollständiges Spiel mit 16 Projekten und einem
gemeinsamen 58-Karten-Aktionsstapel auskommt.

Das Projekt übernimmt diesen Grundgedanken als eigenständige Adaption:

- Projekt statt Projektleitung
- Projektfaktor statt Ressource
- Team, Daten, Betrieb und Methode statt Organismen und Forschungstechniken
- Ereignisse als begrenzte Interaktion
- eigene deutsche Texte, Symbole, Illustrationen und Gestaltung

## Ergebnis der Panelrunden

Drei getrennte Fachperspektiven—DH/RSE, Comedy/Sensitivity und Game
Design—prüften die 82er-Liste und den ursprünglichen 148-Einträge-Ideenpool.
Das Ergebnis ist:

- 16 Projekte
- 38 Projektfaktoren
- 28 Ereignisse auf acht Effekt-Templates
- acht gezielte Motiv-Ersetzungen für fachliche Breite
- Booster mit garantiert 2 Projekten, 7 Faktoren und 3 Ereignissen
- zwei identische 74-Karten-Bühnensätze *(seit ADR 0019 nur noch einer)*

Der Panelentwurf wurde am 5. August 2026 in die kanonische
`../data/cards.csv` und den typbewussten Booster-Collator übernommen.

## Reduzierte Auflage, September 2026

Die Kostenschätzung für 612 Standardkarten lag über dem Budget. ADR 0019 senkt
den Standardauftrag auf 234 Karten: ein Bühnensatz statt zwei, 13 Booster statt
36, zwölf Blanko-Karten statt 50 Reservekarten. Der Foilauftrag bleibt bei 18
Karten, von denen nur 8 in den Umlauf gehen — mehr hätte Mythics häufiger
gemacht als Rares und ADR 0013 verletzt.

Bei der Gelegenheit wanderten die Kopienzahlen aus `../data/cards.csv` in
Auflagenprofile unter `../data/print_runs/`. Die Spalte `booster_copies` war
dort redundant (eine reine Funktion von `rarity`) und auflagenspezifisch; seither
wird sie aus der Packstruktur abgeleitet. Der 612er-Plan bleibt dadurch
ausführbar.

## Weiterhin gültige Produktentscheidungen

- neun Mythic-Motive ausschließlich als Foil
- Illustration und Kartenlayout strikt getrennt; das Layout setzt der
  Renderer (ADR 0012)
- Mid-Century Science Pulp als einheitlicher Illustrationsstil
- keine übernommenen Logos, Layouts oder Trade Dress
