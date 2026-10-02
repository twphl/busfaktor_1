# ADR 0017: Kartenrückseite als Bandsatz mit Siegel

- Status: angenommen
- Datum: 2026-08-30
- Berührt: Kartenrückseite, `scripts/render_card_back.py`, Trade Dress
- Löst ab: den diagonalen Versalakronym-Entwurf der Rückseitenversionen bis
  0.12.0

## Kontext

Vorder- und Rückseite waren zwei Entwürfe ohne gemeinsame Sprache. Die
Vorderseite ist ein ruhiges Papier-auf-Anthrazit-System mit zurückhaltender
Typografie; die Rückseite war ein Diagonalfeld aus großen Versalakronymen mit
Ottermaskottchen an beiden Rahmenkanten. Außer dem dunklen Träger verband sie
nichts.

Der Schriftgrad war dabei nicht die Ursache. Der diagonale Satz stand bei 30
Einheiten und damit ungefähr auf Höhe des Vorderseitentitels. Laut wurde die
Rückseite durch etwas anderes: Versalien in Bold, über die volle Kartenbreite,
in `line/highlight` bei voller Deckkraft. Weiß auf Schwarz bei 100 Prozent kommt
auf der Vorderseite an keiner Stelle vor, auch im Footer nicht.

Zusätzlich erfüllte die Rückseite ihre eigene Vorgabe aus
`05-figma-design-system.md` nicht: dort waren ein Projektsiegel und vier
Faktorsymbole vorgesehen, gezeichnet wurde keines von beiden.

Vier Richtungen wurden in Produktionsgeometrie gebaut und verglichen
(Dienstsiegel, Sicherheitsdruck, Faktorkompass, gedämpftes Gewebe). Der
Faktorkompass wurde verworfen: Familienfarben auf der Rückseite lesen sich als
Information über die Karte und verletzen damit das Verbot von Pack- und
Seltenheitsinformationen.

## Entscheidung

Die Rückseite ist ein waagerechter Bandsatz des DH-, RSE- und RDM-Vokabulars im
Anthrazitfeld mit einem Siegel in der Mitte. Die Rendererversion steigt auf
`0.13.0`.

**Lautstärke.** Zwei Sätze schließen die Frage: Nichts auf der Rückseite ist
größer als der Footer der Vorderseite, und nichts ist heller als deren
`text/on-dark-muted` (`#A3A098`). Laufsatz und Siegelumschrift stehen beide bei
16 Einheiten und liegen damit zwischen der Markenzeile der Vorderseite (14,3)
und deren Kartenidentität (16,7). Es gibt auf der ganzen Rückseite nur diesen
einen Schriftgrad. `text/on-dark-muted` ist die Antwort, die die Vorderseite auf
die Frage nach der Textlautstärke auf Anthrazit bereits gegeben hat;
`line/recessed` ist dort nur eine Strichfarbe.

**Begrenzung.** Die Zeilen werden vom chamferierten Feld beschnitten, das der
Rahmen umschließt, nie vom Anschnitt. Der schwarze Rand bleibt dadurch ein Rand
und wird nicht zum Anschnitt. Weil nichts mehr die Haarlinie kreuzt, bleibt
diese durchgehend und braucht keine Korridore mehr.

Der Clip liegt dabei um einen Feldabstand **innerhalb** der Rahmenlinie und
läuft parallel zu ihr. Ohne diesen Abstand endete jede Zeile exakt auf der
gezeichneten Haarlinie: Der Schnitt ist gewollt, er darf nur nicht auf der Linie
selbst liegen. Ein gleichmäßiger Versatz verkürzt die Fase um das
`(2 − √2)`-fache des Abstands; bliebe die Fase unverändert, liefe der Clip an
den Ecken schräg zum Rahmen. Feldabstand und Luft über der äußersten Zeile
stammen beide aus der Versalhöhe und stehen deshalb bei je 10 Einheiten
(0,85 mm), sodass der Text ringsum denselben Rand hält. Der Siegelhof liegt mit
0,68 dieses Maßes darunter, weil das Siegel eine gefüllte Marke mit eigenem Rand
ist und keine Kante.

**Endlosigkeit.** Keine Zeile beginnt oder endet im Sichtbaren. Jeder Lauf wird
länger gebaut als das Feld und um eine zeilenweise Phase links davon angesetzt,
sodass der Clip das einzige ist, was je einen Term schneidet.

**Rhythmus.** `y` ist eine Grundlinie, nicht die Zeilenmitte. Über den Anschnitt
entscheidet deshalb die Versaloberkante der äußersten Zeile, nicht deren
Grundlinie. Ein fester Zeilenabstand überlässt diesen Abstand dem Zufall: bei 16
Einheiten landete die äußerste Zeile 0,75 Einheiten unter der Rahmenlinie und
wurde rasiert, bei 17 Einheiten zufällig nicht. Der Rhythmus wird deshalb aus
dem Feld gelöst statt ihm auferlegt — die äußerste Grundlinie wird auf den
benötigten Abstand gesetzt, die Zeilenzahl am Zielabstand gerundet und der
Abstand anschließend so gelöst, dass er diese Position exakt trifft. Unten
ergibt sich derselbe Abstand durch die Halbdrehung.

**Siegel.** In der Kartenmitte steht ein Siegel aus Umschrift, zwei Otterköpfen
und einer Teilungslinie. Die Punktsymmetrie verlangt eine Figur ohne Oben —
gelöst wie bei einer Bildkarte im Kartenspiel: ein Kopf je Hälfte, an einer
Teilungslinie gegeneinander gestellt. Im Siegel sitzt der Kopf auf Papier und
trägt deshalb `background/paper-raised` und `text/primary` statt Creme auf
Schwarz.

**Umschrift.** Sie lautet `BUSFAKTOR: 1 · DH · RSE · RDM` und ist eine eigene
Liste, nicht das Feldvokabular. Der erste Entwurf zog sie aus denselben
`PATTERN_TERMS` wie der Hintergrund; ein Siegel, das wiederholt, was ringsum
schon steht, sagt nichts. Die Umschrift benennt stattdessen die ausstellende
Instanz, also das Spiel und seine drei Felder — Information, die sonst nirgends
auf der Karte steht.

Ausgeschrieben können die Felder dort nicht stehen. Der Ring wird über 180 Grad
gezeichnet und per Halbdrehung wiederholt, die Umschrift muss also innerhalb
einer halben Umdrehung vollständig sein. Das sind bei 16 Einheiten rund 37
Zeichen. „Digital Humanities · Research Software Engineering · Research Data
Management“ kostet 80 und verlangt entweder 0,6 mm Schriftgrad — halb so groß
wie das Kleinste, was die Vorderseite druckt — oder ein Siegel von 63 mm
Durchmesser auf einer 63 mm breiten Karte. Die deutsche Kurzform kostet 60
Zeichen und immer noch 48 mm Siegel.

Der erste Begriff der Umschrift steht mittig auf zwölf Uhr, wie die Legende auf
einer Münze. Begänne der Lauf dort, stünde am oberen Rand das Ende der zweiten
Kopie, und das Auge träfe die Umschrift mitten im Satz — die Reihenfolge läse
sich dann falsch.

Die Anpassung der Laufweite an den halben Ring ist deshalb zugleich die Prüfung:
Weicht sie zu weit von 1 ab, passt die Umschrift nicht in diesen Ring, und der
Renderer bricht mit dieser Diagnose ab, statt eine unleserliche oder
auseinanderklaffende Fassung zu setzen.

**Punktsymmetrie.** Alles, was ein Oben hat — die Laufzeilen, die Köpfe, die
Ringlettern, die Eckornamente — wird einmal oberhalb der Mitte gezeichnet und
per Halbdrehung wiederholt. Die konzentrischen Formen des Siegels sind für sich
punktsymmetrisch und werden einmal gezeichnet.

## Folgen

- Vorder- und Rückseite teilen jetzt Träger, Rahmengeometrie, Textfarbe und
  Schriftregister. Der Bruch aus dem Ausgangszustand ist geschlossen.
- Die vier Faktorsymbole aus `05-figma-design-system.md` bleiben **offen**. Der
  Bandsatz führt sie nicht; sie waren in den verworfenen Varianten A bis C
  enthalten. Diese Vorgabe ist damit weiterhin unerfüllt und in
  `06-open-questions.md` zu führen.
- Fünf Vertragstests der Rückseite beschrieben die Diagonale und wurden ersetzt.
  Neu geprüft werden: dass keine Laufzeile im Sichtbaren beginnt oder endet, dass
  die äußerste Zeile nicht angeschnitten wird, dass die Zeilen im Anthrazit
  gehalten sind, dass die Rahmenlinie außer an den Ecken durchgehend ist, dass
  das Siegel mittig sitzt und genau zwei Köpfe trägt, und dass der Laufsatz das
  Footer-Register der Vorderseite nicht überschreitet.
- Die Rasterprüfung auf Punktsymmetrie bleibt bestehen und gilt unverändert.
- Der Otterkopf ist weiterhin ein eingebettetes PNG und steht im Siegel bei rund
  7,3 mm Kopfbreite, das Siegel selbst bei rund 22 mm Durchmesser. Für die
  Produktion ist eine Vektorfassung nötig, sonst geht die Feinzeichnung im
  Offset verloren.
- Die Umschrift steht bei rund 1,36 mm Schriftgrad, also etwa 0,97 mm
  Versalhöhe. Sie ist druckbar, aber wie die übrige Typografie erst nach
  physischem Andruck freigegeben.
- Die drei Felder erscheinen auf der Rückseite nur abgekürzt. Wer sie
  ausgeschrieben braucht, braucht dafür einen anderen Träger als den Siegelring
  — Regelblatt, Boosterbanderole oder Verpackung.
- Produktionszahlen, Seltenheiten, Spielmechanik und `data/cards.csv` ändern
  sich nicht.
