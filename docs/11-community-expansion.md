# Community-Expansion: Karten von Teilnehmenden

Status: Konzept. Die Produktionsvariante ist mit ADR 0019 entschieden
(Variante C, Abschnitt 5); Lizenz, Kuration und Veröffentlichung sind offen.
Bezug: `../CONTRIBUTING.md`, ADR 0009, ADR 0010, ADR 0019,
`09-licensing-and-attribution.md`.

Auf der Konferenz sollen Teilnehmende eigene Karten entwerfen. Aus den
Einreichungen entsteht nach der Konferenz ein Community-Pack. Dieses
Dokument beschreibt Umfang, Ablauf, Kuration, Rechte und die Produktion.

## 1. Grundsatz: getrenntes Pack, eigener Namespace

Das kanonische Set bleibt unberührt. Die 82 Booster-Motive, die
Kollationsmathematik der aktiven Auflage und der Bühnensatz sind gegeneinander
austariert; jede Einmischung von Community-Karten erzwingt eine Neuberechnung
und einen ADR.

Community-Karten laufen deshalb als eigenes Pack:

- eigener ID-Bereich `KAT-X01` bis `KAT-X99`; das Schema erlaubt `X`
  bereits über das Pattern `^KAT-[CUMRBX][0-9]{2}$`
- eigene Datei statt Zeilen in `data/cards.csv`
- keine Seltenheiten, keine Boosterkopien, keine Bühnenkopien
- spielbar als optionale Beimischung zum Aktionsstapel, nicht als Ersatz

## 2. Was Teilnehmende entwerfen dürfen

Freitext gibt es nur für Titel, Flavor Text und Bildidee. Regeltexte werden
nicht frei geschrieben, sondern über vorgegebene Bausteine angekreuzt.
Andernfalls entstehen unspielbare Karten, deren Redaktion nachträglich
teurer ist als der ganze Stand.

| Kartenart | Was die Person entscheidet | Aufwand | Empfehlung |
|---|---|---|---|
| Projektfaktor | Titel, Faktortyp, Flavor, Bildidee | gering | Standardfall am Stand |
| Ereignis | zusätzlich Template E1–E8 und Wirkung | mittel | für Interessierte mit Regelkenntnis |
| Projekt | Anforderungsprofil 2–4, Punktwert = Anzahl, Zielzustand | hoch | nur mit Betreuung |

Ein Projektfaktor ist in unter fünf Minuten vollständig. Er braucht nur
einen Faktortyp aus Team, Daten, Betrieb oder Methode und erfüllt damit
genau eine passende Anforderung. Das ist die richtige Voreinstellung für
Laufkundschaft.

Ereignisse bleiben an die acht Templates aus `10-spielregeln.md`, Abschnitt 13
gebunden. Das Formular listet sie mit je einer Zeile Bedeutung.

Projekte brauchen ein konsistentes Verhältnis von Anforderungen und Punkten:
Der Punktwert entspricht der Zahl der Anforderungssymbole, und ein nicht
abgeschlossenes Projekt kostet unabhängig davon einen Minuspunkt.

## 3. Redaktionelle Leitplanken

Das Muster aus `02-game-design.md` gilt auch für Community-Karten und steht
in Kurzform auf dem Tischaushang:

1. Der Titel benennt den Gegenstand, den Zustand oder den Vorfall.
2. Der Flavor Text dreht ihn durch Einschränkung, Folge oder Timing und
   wiederholt den Titel nicht.
3. Die Bildidee zeigt genau diese Beziehung als beobachtbare Handlung.

Zusätzlich, nach den Grundsätzen in `../CONTRIBUTING.md`:

- Die Satire richtet sich gegen Strukturen, Prozesse und institutionelle
  Absurditäten.
- Keine namentlich genannten Personen, Projekte oder Einrichtungen, auch
  nicht als erkennbare Umschreibung.
- Kein Spott über Berufsanfänger, Hilfskräfte oder marginalisierte Gruppen.

Formatgrenzen für die Lesbarkeit im Kartenformat: Titel höchstens rund 24
Zeichen, Flavor Text höchstens rund 90 Zeichen.

## 4. Ablauf am Stand

**Vorher.** Formulare drucken, Tischaushang aufstellen, drei bis fünf
gedruckte Musterkarten auslegen, Sammelbox beschriften, Stifte bereitlegen.
Eine Person übernimmt die Betreuung und kennt die drei Kartenarten.

**Während.** Kurze Ansprache, Kartenart wählen, Formular ausfüllen,
Einwilligung unterschreiben, Formular in die Box. Realistisch sind fünf
Minuten pro Person, mit Gespräch zehn. Die Betreuung prüft nur zwei Dinge
sofort: Ist die Einwilligung unterschrieben, und ist die Kartenart
eindeutig angekreuzt.

**Danach.** Formulare vollständig einsammeln, durchnummerieren,
fotografieren oder scannen, erst dann transportieren. Ein verlorenes
Formular ist eine verlorene Einwilligung.

## 5. Produktionsvariante: entschieden (C)

| Variante | Vorlauf | Am Stand | Sichtbarkeit | Risiko |
|---|---|---|---|---|
| A Nur Formular, Druck später | Formulare kopieren | gering | Ergebnis erst nach der Konferenz | keines |
| B Blanko-Karten sofort bespielbar | eigenes Blanko-Design und Druckposition | mittel | sofort, die Karte liegt in der laufenden Partie | Druckentscheidung vor Freigabe nötig |
| C Beides | wie B | höher | sofort und dauerhaft | doppelte Erfassung, Zuordnung Karte zu Formular |

**Entschieden ist C** (ADR 0019): Formular *und* zwölf bespielbare
Blanko-Karten. A bleibt die Grundlage, weil nur das Formular die Einwilligung
und die vollständigen Felder trägt; B kommt mit sechs Blanko-Motiven hinzu,
gerendert über `make cards-blank`.

Die zwölf Karten sind sechs Motive à zwei: vier Projektfaktoren (je
Faktortyp), ein Ereignis, ein Projekt. Sie haben einen eigenen Posten im
Standardauftrag.

Zwölf Karten decken die Aktion nicht ab, sie zeigen sie: Sie reichen für
Musterkarten am Tisch und die ersten Einreichungen, die sofort mitgespielt
werden. Der Regelfall bleibt das Formular.

Bei C muss jede Blanko-Karte dieselbe Nummer tragen wie das zugehörige
Formular, sonst ist die Zuordnung nach der Konferenz nicht mehr herstellbar.
`render_blank_cards.py` sieht noch kein Nummernfeld vor (siehe Abschnitt 9).

## 6. Kuration nach der Konferenz

1. **Eingang.** Jedes Formular erhält eine laufende Nummer und wird
   digitalisiert.
2. **Rechteprüfung.** Ohne unterschriebene Einwilligung wird eine Karte
   nicht aufgenommen. Rückfrage nur, wenn eine Kontaktadresse vorliegt.
3. **Redaktionsprüfung.** Leitplanken aus Abschnitt 3, Formatgrenzen,
   Dopplungen gegen die kanonischen 82 Motive.
4. **Mechanikprüfung.** Faktortyp vorhanden, Template zulässig,
   Anforderungen und Punkte konsistent.
5. **Aufnahme.** ID aus dem `KAT-X`-Bereich vergeben, Zeile anlegen,
   Validierung laufen lassen.
6. **Layout und Veröffentlichung.** Erst nach Klärung der Lizenzlage.

Abgelehnte Einreichungen werden nicht öffentlich kommentiert. Alle
Einreichenden mit Namensfreigabe erscheinen in einer gemeinsamen
Credit-Liste, unabhängig davon, ob ihre Karte aufgenommen wurde. Das ist
die fairere Lösung und vermeidet eine sichtbare Ablehnungsliste.

## 7. Datenmodell (Vorschlag, noch nicht implementiert)

- `data/community_cards.csv` mit derselben Kopfzeile wie `data/cards.csv`
- zusätzliche Felder `contributor`, `contributor_credit`, `consent_date`,
  `source_form_id`
- `scripts/validate_cards.py` prüft die Datei mit gelockerten Regeln: keine
  Seltenheits- und Kopienarithmetik, aber ID-Muster, Faktortyp und
  Template-Zulässigkeit
- `scripts/collate_boosters.py` bleibt unverändert und liest die Datei nicht

Damit bleibt die Zusicherung erhalten, dass `data/cards.csv` genau die 82
kanonischen Motive enthält und nichts sonst.

## 8. Rechte und Einwilligung

Der Einwilligungstext auf dem Formular ist der kritische Teil der ganzen
Aktion. Er muss eine Nutzung abdecken, deren Lizenz noch nicht feststeht: Das
Repository steht unter CC BY-SA 4.0 (`09-licensing-and-attribution.md`), die
Lizenz der Community-Kartendaten ist dagegen offen.

Zwei Wege sind möglich:

- **Weit gefasste Einwilligung.** Nicht-exklusiv, unentgeltlich, räumlich
  und zeitlich unbeschränkt, einschließlich Bearbeitung, Druck und
  Veröffentlichung unter einer später festgelegten offenen Lizenz. So
  formuliert es das beiliegende Formular.
- **Lizenz vorher festlegen.** Sauberer, aber setzt eine Entscheidung vor
  der Konferenz voraus.

Weiter gilt: Erhoben werden nur Name und optional eine E-Mail-Adresse, beide
ausschließlich für Credit und Rückfragen. Die Namensnennung ist eine eigene
Ankreuzoption; ohne sie läuft die Karte anonym. Fotos werden nicht benötigt.

## 9. Offene Punkte

- Nummernfeld im Blanko-Layout (Voraussetzung für C)
- Lizenz der Community-Kartendaten
- Ob das Pack gedruckt oder nur digital veröffentlicht wird
- Wer die Kuration übernimmt und bis wann

## 10. Material

- `community/einreichungsformular.html` — zwei Formulare je A4-Bogen,
  zum Ausdrucken oder als PDF speichern
- `community/tischaushang.html` — A4-Aushang für den Tisch mit
  Kartenarten, Templates und Leitplanken
