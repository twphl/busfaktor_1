# ADR 0012: Produktname „Busfaktor: 1“

- Status: angenommen
- Datum: 2026-08-28
- Ändert: offene Frage „eigener endgültiger Produktname“ aus
  `06-open-questions.md`; `README.md`, `docs/01-decisions.md`,
  `docs/10-spielregeln.md`

## Kontext

Das Projekt lief unter dem Arbeitstitel `DH-Katastrophen: Projektspiel`, einem
Rest aus der Bingo-Vorstufe. Der Titel benennt eine Materialsammlung, kein
Produkt: „Katastrophen“ verspricht Einzelunfälle, während das Spiel seit
ADR 0006 strukturelle Projektbedingungen behandelt, und „Projektspiel“ ist eine
Gattungsbeschreibung ohne Wiedererkennung. Als Konferenzobjekt braucht das Set
einen Namen, der auf Banderole und Boosterfront ohne Erklärung trägt.

## Entscheidung

Das Produkt heißt:

> **Busfaktor: 1**
> Ein Sammelkartenspiel über DH-, RDM- und RSE-Projekte

`Busfaktor` ist ein etablierter Fachbegriff aus der Softwareentwicklung und
benennt genau den Gegenstand des Spiels: Projekte, die an einzelnen Personen,
einzelnen Servern und inoffiziellen Zuständigkeiten hängen. Der Witz richtet
sich damit gegen eine Struktur, nicht gegen eine Person, und erfüllt das
Humorprinzip aus `00-project-brief.md`. Die Schreibung mit Doppelpunkt liest
sich als Messwert auf einem Formular und trifft das Verwaltungsregister von
`Projekt` und `Projektfaktor`.

Der Untertitel nennt `Sammelkartenspiel`, nicht `Trading Card Game`:
mechanisch ist das Spiel nach ADR 0006 ein Projekt- und Set-Collection-Spiel,
und „kein neu entwickeltes Kampf-TCG“ steht als Nicht-Ziel im Brief. Gesammelt,
geöffnet und getauscht wird trotzdem, der Begriff bleibt also zutreffend.

## Verworfene Alternativen

- **`… Ein DH-, RDM-, RSE-Trading Card Game`.** Die aufgeschobenen Bindestriche
  binden an `Trading` statt an das Gesamtkompositum und lesen sich als
  „DH-Trading, RDM-Trading, RSE-Trading Card Game“. Die korrekte Durchkopplung
  `DH-, RDM- und RSE-Trading-Card-Game` ist unlesbar. Die gewählte Fassung
  bindet die Kürzel stattdessen an `Projekte`, wo die Konstruktion aufgeht.
- **Untertitel ganz ohne Akronyme.** Verständlich außerhalb der Fachcommunity,
  verliert aber die sofortige Selbstzuordnung am Konferenzstand, die den
  Untertitel überhaupt rechtfertigt.
- **`Busfaktor` allein.** Ohne die `1` bleibt es ein neutraler Fachbegriff; die
  Zahl macht daraus einen Befund.

## Folgen

- Die Kartennamen-Kollision mit `KAT-U21 – Busfaktor: 1` (`data/cards.csv`) ist
  gewollt: Das Set trägt den Namen einer seiner Karten. Damit wird U21 zur
  Titelkarte. Die pauschale Panel-Empfehlung „kein Unfallmoment“ wird nach der
  dokumentierten Tonentscheidung vom 2026-08-31 nicht übernommen: Der echte
  Bus und der Beinahe-Unfall bleiben als schwarzhumorige Literalisation der
  Fachmetapher erhalten; Schlüsselbund und blockierter Betrieb richten die
  Pointe auf die institutionelle Ein-Personen-Abhängigkeit
  (`review/kat-u21-abnahme-2026-08-31.md`).
- Die Markenrecherche bleibt offen. `Busfaktor` ist ein generischer Fachbegriff
  und damit der günstigste Ausgangsfall, ersetzt die Prüfung aber nicht.
- Kartenpräfix `KAT-`, Repository-Name und Figma-Dateiname bleiben unverändert.
  Sie sind interne Bezeichner ohne Produktaußenwirkung; eine Umbenennung würde
  alle 82 Datensätze, die Tests und das Plugin-Mapping berühren, ohne etwas zu
  gewinnen.
- `docs/research/` und `__scrap/` bleiben unverändert. Beide sind Herkunfts-
  und Panelstand, kein normativer Text.
