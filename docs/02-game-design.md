# Spielsystem: Projektspiel

Für eine Partie ist `10-spielregeln.md` maßgeblich. Diese Übersicht erklärt
das System kompakt und begründet einzelne Designentscheidungen; die
Grundlagen stehen in ADR 0006 und ADR 0010.

## Spielidee

Zwei bis vier Personen bearbeiten Forschungs- und Infrastrukturprojekte. Ein
Projekt wird abgeschlossen, indem die geforderten Projektfaktoren aus Team,
Daten, Betrieb und Methode angelegt werden. Ereignisse helfen, stören oder
verändern laufende Projekte. Die höchste Punktzahl gewinnt.

Es gibt keinen Kampf, keine Lebenspunkte und keine Eliminierung.

## Bühnensatz

Ein vollständiger Satz enthält 74 Karten:

- 16 Projekte
- 46 Projektfaktoren
- 12 Ereignisse

Für das Spiel werden zwei gemeinsame Nachziehstapel gebildet:

1. Projektstapel mit 16 Projekten
2. Aktionsstapel mit 46 Projektfaktoren und 12 Ereignissen

Dazu kommen eine offene Ablage und ein verdeckter Verbrauchsstapel.

## Kartenarten

### Projekt

Ein konkreter Forschungs- oder Infrastrukturauftrag. Jedes Projekt zeigt:

- zwei bis vier Anforderungssymbole
- dieselbe Zahl als Punktwert
- einen überprüfbaren Zielzustand
- eine kurze satirische Flavor-Zeile

Ein ausgespieltes Projekt ist eine Verpflichtung. Wird es nicht abgeschlossen,
zählt es am Spielende 1 Minuspunkt, unabhängig von seinem Punktwert (ADR 0010).

### Projektfaktor

Projektfaktoren gehören einem von vier Faktortypen an und erfüllen eine
passende Anforderung eines Projekts:

- **Team** — Personalzeit, Kooperation, Wissen und Zuständigkeit
- **Daten** — Korpora, Metadaten, Standards und Datenzugang
- **Betrieb** — Systeme, Speicher, Deployment und Wartung
- **Methode** — Verfahren, Auswertung, Automatisierung und Modellierung

Eine Wildcard nennt gemäß Kartentext mehrere mögliche Faktortypen; sie ist kein
fünfter Faktortyp.

`Projektfaktor` ist ein neutraler Begriff. Auch ein Workaround oder ein
ungetestetes Backup kann Teil der Projektwirklichkeit sein, ohne als gute
Ressource bezeichnet zu werden. Das Regelblatt erklärt diese Deutung
ausdrücklich für Spielende (`10-spielregeln.md` §4).

### Ereignis

Ein einmaliger Effekt. Die 28 Motive verwenden nur acht Grundtemplates:

1. Karten sichten
2. Karten nachziehen
3. Faktor zurückholen
4. Faktoren umverteilen
5. als Joker anlegen
6. Mehraufwand hinzufügen
7. Faktor zurückgeben
8. negatives Ereignis verhindern

## Redaktionelles Muster: Anker, Drehung, Bildbeweis

Titel, Flavor Text und Illustration bilden eine gemeinsame Aussage in drei
Schritten:

1. **Anker — Titel:** benennt den konkreten Gegenstand, Zustand oder Vorfall.
   Der Titel muss ohne den Flavor Text erkennen lassen, worum es auf der Karte
   geht.
2. **Drehung — Flavor Text:** ergänzt Einschränkung, Konsequenz, Zeitpunkt oder
   ironischen Widerspruch. Er darf den Hauptgegenstand nicht erst neu
   einführen und soll den Titel nicht bloß wiederholen.
3. **Bildbeweis — Illustration:** macht die Beziehung zwischen Anker und
   Drehung durch eine beobachtbare Handlung und sichtbare Folge verständlich.
   Sie führt keine dritte, für die Pointe notwendige Prämisse ein.

Die Kartenarten setzen das Muster unterschiedlich ein:

- **Projekt:** Der Titel benennt den erreichten Zielzustand. Der Flavor Text
  belegt oder relativiert ihn, ohne den erfolgreichen Abschluss zu verneinen.
- **Projektfaktor:** Der Titel benennt Ressource, Praxis oder Bedingung. Der
  Flavor Text legt deren institutionellen Widerspruch offen.
- **Ereignis:** Der Titel benennt den Vorfall. Der Flavor Text liefert Ursache,
  Folge oder Timing des Vorfalls.

Redaktionsprüfung je Karte:

- Ist der Hauptgegenstand bereits im Titel vorhanden?
- Liefert der Flavor Text einen zweiten Gedanken statt einer Wiederholung?
- Sind Titel und Flavor Text ohne zusätzliches Hintergrundwissen verbunden?
- Zeigt das `visual_motif` genau diese Verbindung?
- Bleibt die Pointe verständlich, obwohl die Illustration keine lesbare
  Typografie enthält?

## Spielaufbau

1. Projekt- und Aktionsstapel getrennt mischen.
2. Offenen Abwurf- und verdeckten Verbrauchsstapel bereithalten.
3. Jede Person erhält ein Projekt und zwei Karten vom Aktionsstapel.
4. Startperson bestimmen.

## Zugablauf

### 1. Zwei Karten ziehen

Die aktive Person zieht insgesamt zwei Karten. Vor dem Aufdecken wird jeweils
gewählt zwischen:

- Projektstapel
- Aktionsstapel
- oberster Karte der offenen Ablage

### 2. Aktionen ausführen

In sinnvoller Reihenfolge darf die aktive Person:

- ein Projekt auslegen
- Projektfaktoren passend an eigene Projekte anlegen
- höchstens ein Ereignis spielen
- eine Kooperation anbieten
- erfüllte Projekte abschließen

Das Auslegen ist die einzige Pflichthandlung: Wer kein aktives Projekt vor sich
liegen hat, muss eines beginnen, sobald eines auf der Hand ist. Ohne diese Regel
lohnt es sich, Projekte bis zum letzten Zug zurückzuhalten und erst auszulegen,
wenn sie sofort abschließbar sind — Minuspunkte lassen sich dann vollständig
vermeiden, und auf der Bühne passiert drei Runden lang sichtbar nichts.

### 3. Aufräumen

Das Handkartenlimit beträgt fünf. Überzählige Karten werden offen
abgeworfen. Simulationsgestützt bestätigt (ADR 0010): Das Limit wirkt über
den getesteten Bereich (3–6) kaum auf das Spielergebnis, weil passende
Faktoren bereits in der Aktionsphase angelegt werden.

## Anlegen, Abwerfen und Verbrauchen

| Vorgang | Ziel |
|---|---|
| Projektfaktor anlegen | bleibt sichtbar am Projekt |
| Karte aus der Hand abwerfen | offen auf die Ablage |
| Faktoren eines abgeschlossenen Projekts verbrauchen | verdeckt auf den Verbrauchsstapel |
| Ereignis ausspielen | nach dem Effekt auf den Verbrauchsstapel |

Nur die oberste Karte der offenen Ablage darf normal gezogen werden.
Wenn der Aktionsstapel leer ist, wird der Verbrauchsstapel neu gemischt.

## Projektabschluss

Sobald alle Anforderungen erfüllt sind:

1. Projekt in den eigenen Punktebereich legen.
2. Angelegte Faktoren verdeckt verbrauchen.
3. Punktwert am Spielende positiv zählen.

Doppelte Symbole erfordern zwei unterschiedliche physische Faktoren desselben
Faktortyps.

## Kooperation

Zwei Personen können freiwillig jeweils ein aktives Projekt verbinden. Benötigen
beide Projekte denselben Faktortyp, kann ein passender Faktor für beide Projekte
zählen. Gewertet werden beide Projekte getrennt, und jedes wird einzeln
abgeschlossen, sobald es erfüllt ist. Ein gemeinsamer Abschluss machte
Kooperation in der Simulation unwirtschaftlich (ADR 0010).

Es gelten:

- höchstens eine aktive Kooperation pro Personenpaar
- Kooperation nur, solange an jedem beteiligten Projekt höchstens ein Faktor
  liegt
- beide Personen müssen zustimmen

## Spielende und Wertung

Gewertet wird nach sechs vollständigen Runden:

- abgeschlossene Projekte: Punkte positiv, in Höhe des Punktwerts
- aktive, unvollendete Projekte: 1 Minuspunkt je Projekt, unabhängig vom
  Punktwert (ADR 0010)
- höchste Summe gewinnt

Es gibt keine frühe Eliminierung.

## Verhältnis zu den Boostern

Jedes Booster enthält 2 Projekte, 7 Projektfaktoren und 3 Ereignisse. Ein Pack
allein ist nicht spielbar. Mehrere Packs können zu einem gemeinsamen Pool
zusammengelegt werden; für die Bühne wird der kuratierte 74er-Satz verwendet.

## Seltenheit

Common, Uncommon, Rare und Mythic bezeichnen Druckmenge und Sammelwert, nicht
Spielstärke (ADR 0013). Eine Karte ist nicht deshalb stärker, weil sie seltener
gedruckt wird — und ausdrücklich auch nicht schwächer.

Für Karten mit demselben Effekt-Template gilt der Nicht-Dominanz-Test: Die
Situationen, in denen die eine Karte wirkt, dürfen keine Teilmenge der
Situationen der anderen sein, solange beide dasselbe kosten. Eine engere Karte
braucht dafür an anderer Stelle eine eigene Wirkungsachse — Reichweite,
Verbleib nach dem Projektabschluss, Kooperation oder Kosten. Eine größere Zahl
derselben Handlung ist keine solche Achse; deshalb nennen Mythics feste
Anzahlen statt „bis zu".

Foil-Mythics gehören nicht zum Bühnensatz. Sie sind in frei zusammengestellten
Partien zugelassen, und genau dafür gilt der Test: Wer mehr Booster öffnet,
soll keine stärkeren Karten bekommen, sondern andere.

## Offene Designfragen

- Startkarten je Personenzahl (zwei bis vier)
- offener Abwurf versus vereinfachter Einzelstapel
- genaue Parameter der acht Ereignis-Templates

Das Handlimit eignet sich nicht als Stellschraube gegen das Zurückhalten von
Projekten: Es greift erst am Zugende, während in der Aktionsphase Handlimit
plus zwei Karten zur Verfügung stehen. Die Simulation dazu beschreibt
`scripts/README.md`.
