# Lizenz- und Abgrenzungsnotizen

Dieses Dokument ist keine Rechtsberatung.

## Regelwerk: Phylo-Lizenz

Was die Quellen sind und warum sie als „Process of Science"-Familie
zusammengehören, steht ausführlich in
[`docs/inspiration/README.md`](inspiration/README.md); hier nur die
lizenzrechtliche Auswertung.

Die aktuelle Fassung adaptiert die Grundstruktur des PHYLO Process of Science
Game. Primärquellen für die Regelanalyse waren `GSAphylo.pdf`,
`PHYLOWWESTWISEprintyourown.pdf`, `WISErules.pdf` und `ingenium_english.pdf`
(nicht im Repository, die Decks sind auf
[phylogame.org/decks](https://phylogame.org/decks/) verzeichnet; siehe
`docs/inspiration/phylo-pdf-reconstruction.md` für die Rekonstruktion).
Übernommen wird aus diesen Quellen ausschließlich die abstrakte Mechanik-Kategorie
(Projekt/Ressource/Modifier als Spielprinzip); Text, Kartennamen, Illustrationen
und Rahmen sind eigenständig, siehe „Eigenständige Umsetzung" unten.

Recherchiert am 2026-09-08 auf der offiziellen Lizenzseite
[phylogame.org/licenses](https://phylogame.org/licenses/):

- **Card Fronts / Card Backs** (CC BY-NC-ND 4.0): betrifft die Karten
  dieses Projekts nicht — Karten, Renderer und Druckdateien enthalten keine
  Phylo-Bilder und keine Phylo-Kartenrückseite. Keynote (Folie 2) und
  Website-Startseite zeigen zur Herkunft der Mechanik drei unveränderte
  Beispielkarten mit Namensnennung, nicht kommerziell und ausdrücklich
  ausgenommen von CC BY-SA: GSA/PHYLO „Lose Funding!“ (Art: Maki Naro),
  WWEST/WISE „Rosalind Franklin“ (Art: Ping Zhu), Ingenium „Jocelyn Bell
  Burnell“ (nineSixteen Creative Inc.). Quelle der Dateien:
  `keynote-neustart/assets/inspiration/`.
- **Game Mechanics**: Creative Commons Attribution-ShareAlike 4.0
  International. Eigene Bearbeitungen der übernommenen Mechanik dürfen laut
  Lizenztext eine eigene Lizenz erhalten; die Kernregeln selbst bleiben unter
  CC BY-SA.
- **Pflicht-Credit** für das „process of science"-Spiel (GSA-Deck oder
  WISE-Deck, auf der Lizenzseite ausdrücklich als Bucket [2] zusammen
  genannt), wörtlich von der Lizenzseite:
  „Sydney Ang, Genevieve Leduc-Robert, Lu Li, and Sam MacKinnon."
  Hinweis zur Schreibweise: Der GSA-Blogbeitrag [„Playing a game with basic
  research"](https://genestogenomes.org/playing-a-game-with-basic-research/)
  schreibt den Vornamen „Sidney" statt „Sydney". Für die Attribution wird die
  exakte Formulierung der Lizenzseite verwendet, weil sie dort wörtlich
  verlangt wird.
- Kontakt für Rückfragen zur Lizenz: Dave Ng, db@mail.ubc.ca (auf der
  Lizenzseite genannt, u. a. für Anpassungen der Card-Back-Lizenz).
- **Ingenium- und WWEST/WISE-Deck-Seiten separat geprüft**
  ([ingenium-women-in-stem](https://phylogame.org/decks/ingenium-women-in-stem/),
  [wwest-women-in-science-and-engineering-deck](https://phylogame.org/decks/wwest-women-in-science-and-engineering-deck/)):
  Beide nennen dort nur **Bild-/Grafik-Credits** unter CC BY-NC-ND 4.0
  (Ingenium: nineSixteen Creative Inc.; WWEST/WISE: Ping Zhu, Simon Gurr) —
  das betrifft uns nicht, da keine Phylo-Illustrationen verwendet werden.
  Eine eigene Mechanik-Lizenz nennt keine der beiden Seiten; die Ingenium-Seite
  beschreibt ihre Mechanik selbst nur als „similar to the WWEST WISE Deck".
  Die Zuordnung von Ingenium zum „process of science"-Bucket [2] ist damit
  eine nachvollziehbare Ableitung aus dieser Beschreibung und aus ADR 0006
  (adaptiert wurde die Projekt/Ressource/Modifier-Mechanik, nicht der andere
  Phylo-Mechanik-Typ „ecosystem building" aus Bucket [1]), aber kein
  wörtliches Zitat von der Ingenium-Seite selbst.

**Umsetzung:** Die Credit-Zeile steht in `10-spielregeln.md` §19. Es handelt
sich nicht um Rechtsberatung, sondern um dokumentierte Recherche zum Stand
2026-09-08.

## Eigenständige Umsetzung

Unabhängig von der Lizenzprüfung werden nicht übernommen:

- Phylo-Logo oder andere geschützte Logos
- Quellillustrationen und konkrete Figuren
- Kartenrahmen, Rückseiten, Symbole oder Trade Dress
- exakte Kartentexte und konkrete Projektnamen der Referenzsets

Das Produkt verwendet eigene deutsche Begriffe, Motive, Regeltexte,
semantische Iconzuordnungen, Illustrationen und Gestaltung. Allgemeine
Basisglyphen dürfen aus dokumentierten offenen Bibliotheken stammen.

## Bildstil

Der Illustrationsstil „Mid-Century Science Pulp" (ADR 0008) bezeichnet eine
Epoche und gemalte Machart (ca. 1950er bis frühe 1970er Jahre), keine konkrete
geschützte Einzelquelle und kein:e benannte:r Illustrator:in als Vorlage.
Stilrichtungen und Epochenbeschreibungen sind nicht urheberrechtsfähig, anders
als konkrete Werke; es besteht daher kein Attributionsbedarf für den
Bildstil selbst. Das interne Moodboard bleibt Referenzmaterial und
kein Produktionsinput (siehe unten).

## Icons

Der renderer-native Iconkatalog verwendet `@phosphor-icons/core` 2.1.1 im
Gewicht Bold. Die 22 benötigten Grundglyphen, drei daraus abgeleitete
Komposit-SVGs und die Zuordnung der 22 Produktbegriffe liegen unter
`data/assets/icons/`. Die Quelle ist das versionierte npm-Paket; ein Laufzeit-
oder Netzwerkimport findet nicht statt.

Phosphor Icons steht unter der MIT-Lizenz. Der unveränderte Lizenztext liegt
unter `data/assets/icons/phosphor/LICENSE.phosphor.txt`; das maschinenlesbare
`data/assets/icons/manifest.json` dokumentiert Paket, Version, Gewicht, Quelle
und jede semantische Zuordnung. Die Komposite Projektfaktor,
Boosterbanderole und Wildcard-Wahl verwenden ausschließlich diese
lizenzierten Grundglyphen. Siehe ADR 0014.

## Illustrationen

Alle 82 Kartenillustrationen sind von der Redaktion selbst mit ChatGPT
(OpenAI-Bilderzeugung) erstellt worden. Für diese Veröffentlichung als
kostenloser Konferenzgag genügt dazu ein allgemeiner Hinweis statt eines
vollständigen Registers pro Karte: KI-generierte Illustrationen, erstellt vom
Redaktionsteam mit ChatGPT, Nutzung im Rahmen der OpenAI-Nutzungsbedingungen.
Ein Register mit Erstellungsdatum, Prompt-/Briefingversion, Bearbeitung,
Nutzungsrechten und Credit-Zeile je Karten-ID bleibt für eine spätere Auflage
sinnvoll. Die Illustrationen stehen wie alle eigenen Inhalte unter
CC BY-SA 4.0 (siehe unten).

Stilproben und Moodboards sind interne Referenz und kein druckfertiges Asset.
Sie liegen nicht im Repository und dürfen nicht als Produktionsinput verwendet
werden.

## Repository und Produkt

Die Phylo-Prüfung ist abgeschlossen (siehe oben). Entschieden am 2026-09-08:
Alle eigenen Inhalte (Regeln, Kartendaten, Illustrationen, Gestaltung,
Dokumentation, Renderer-, Website- und Präsentationscode) erscheinen
einheitlich unter **Creative Commons Attribution-ShareAlike 4.0
International (CC BY-SA 4.0)** — konsistent mit der Mechanik-Lizenz von
Phylo selbst, die eine eigene Lizenz für Bearbeitungen ausdrücklich erlaubt
(siehe oben). Die Phylo-Pflicht-Credit (§19 im Regelblatt) bleibt davon
unberührt und gilt zusätzlich.

Das Regelheft trägt die kompakte Attribution (§19); der Lizenztext steht in
`LICENSE` im Wurzelverzeichnis.
