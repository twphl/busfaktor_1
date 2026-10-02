# Redaktionelle Sekundärtags

Verbindlich für die Kartenredaktion. Feld: `editorial_tags` in
`data/cards.csv`.

## Zweck und Abgrenzung

Die vier Faktortypen Team, Daten, Betrieb und Methode ordnen jede Karte nach
Projektressource. Querschnittliche Werte wie Rechte, Teilhabe,
Barrierefreiheit, Provenienz, Pflege und Deutung verschwinden dabei in dieser
Einteilung. Die Sekundärtags machen sie sichtbar und damit prüfbar.

Sie sind ausdrücklich **keine fünfte Spielressource**:

- Sie stehen nicht auf der Karte und werden nicht gerendert.
- Die Simulation liest sie nicht.
- Die Boosterkollation gewichtet sie nicht.
- Sie ändern keine Anforderung, keinen Punktwert und keine Kopienzahl.

Sie sind Redaktions- und Reviewmetadaten: Sie beantworten die Frage, wovon das
Set wie oft erzählt, und decken Lücken auf, statt sie zu schließen.

## Vokabular

Acht Tags, verbindliche Reihenfolge. `access` und `labor` stehen eigenständig,
weil das Set beide Themen tatsächlich trägt und sie sonst unter `care`
beziehungsweise `rights` verschwinden würden.

| Tag | Bedeutung | Nicht gemeint |
|---|---|---|
| `rights` | Lizenz, Urheber- und Persönlichkeitsrecht, Einwilligung, Datenschutz, kulturelle Rechte, Schutzfristen, Takedown | jede Form von Zugang; dafür `access` |
| `access` | Zugang, Auffindbarkeit, Nachnutzbarkeit, offene Schnittstellen, Formatoffenheit, Verfügbarkeit über die Zeit | Barrierefreiheit; dafür `accessibility` |
| `accessibility` | Barrierefreiheit als Anforderung, Prüfung und Ausstattung | allgemeine Benutzbarkeit |
| `participation` | Teilhabe, Mitentscheidung, Aushandlung zwischen Rollen und Einrichtungen, Citizen Science, Vetorechte | reine Teamgröße oder Personalfragen; dafür `labor` |
| `provenance` | Herkunft, Auswahl und Ausschlüsse, Dokumentation, Versionierung, Zitierfähigkeit, Reproduzierbarkeit | inhaltliche Deutung des Materials; dafür `interpretation` |
| `care` | Pflege, Wartung, benannte Zuständigkeit, Weiterbetrieb über das Projektende hinaus, Wiederherstellbarkeit | die Arbeitsbedingungen der pflegenden Person; dafür `labor` |
| `labor` | Arbeitsbedingungen, Stellenumfang, Befristung, Finanzierung von Arbeitszeit, unsichtbare und unbezahlte Arbeit, Anerkennung | die gepflegte Sache selbst; dafür `care` |
| `interpretation` | Forschungsfrage, Quellenkritik, konkurrierende Lesarten, Dissens, Modellierungsentscheidungen, dokumentiertes Nichtwissen | reine Werkzeug- oder Betriebsfragen |

`care` und `labor` treten häufig gemeinsam auf; das ist beabsichtigt. Getrennt
bleiben sie, weil eine Karte über eine unbefristete Stelle etwas anderes sagt
als eine Karte über ein nie geprüftes Backup.

## Vergaberegeln

1. Höchstens drei Tags je Karte, mit `+` getrennt, ohne Wiederholung.
2. Die Reihenfolge folgt der Tabelle oben, nicht einer Gewichtung. Damit
   bleiben Diffs stabil; ein erster Tag bedeutet keine Priorität.
3. Getaggt wird, was Titel, Ziel, Regeltext oder Flavor tatsächlich sagen.
   Ein Thema, das eine Karte nur streifen könnte, wird nicht getaggt.
4. Ein leeres Feld ist ein zulässiges Ergebnis. Karten ohne Querschnittsbezug
   bleiben ungetaggt, statt einen Tag mitzunehmen.
5. Regel 3 und 4 sind die eigentliche Leistung des Felds: Eine Lücke in der
   Abdeckung ist ein Befund für die Redaktion, kein Fehler in den Daten.

Geprüft wird das in `scripts/validate_cards.py`: Vokabular, Reihenfolge,
Eindeutigkeit, Höchstzahl und die Bedingung, dass jeder Tag mindestens eine
Karte trägt. Der Validator gibt die Verteilung bei jedem Lauf aus.

## Abdeckung

Die Tabelle zählt Motive; `scripts/validate_cards.py` gibt die aktuelle
Verteilung bei jedem Lauf aus.

| Tag | Motive | IDs |
|---|---|---|
| `rights` | 4 | `U10`, `R05`, `R11`, `M08` |
| `access` | 8 | `C02`, `U09`, `U10`, `R05`, `R16`, `R17`, `R18`, `M08` |
| `accessibility` | 1 | `C20` |
| `participation` | 7 | `C04`, `U03`, `U06`, `U08`, `R03`, `R11`, `M03` |
| `provenance` | 30 | `C08`, `C11`, `C12`, `C18`, `C22`, `C26`, `U05`, `U07`, `U09`, `U16`, `U17`, `U20`, `U22`, `U24`, `R03`, `R04`, `R07`, `R08`, `R10`, `R12`, `R13`, `R14`, `R15`, `R17`, `R18`, `M01`, `M02`, `M04`, `M05`, `M09` |
| `care` | 30 | `C01`, `C06`, `C07`, `C15`, `C16`, `C17`, `C18`, `C19`, `U01`, `U05`, `U11`, `U12`, `U13`, `U14`, `U15`, `U21`, `U22`, `U23`, `U24`, `U26`, `R01`, `R02`, `R06`, `R09`, `R12`, `R16`, `R18`, `M01`, `M04`, `M07` |
| `labor` | 16 | `C01`, `C03`, `C04`, `C05`, `C06`, `C07`, `U01`, `U02`, `U04`, `U21`, `U27`, `R01`, `R02`, `R09`, `M03`, `M07` |
| `interpretation` | 23 | `C10`, `C11`, `C14`, `C23`, `C24`, `C25`, `C28`, `U03`, `U08`, `U16`, `U17`, `U18`, `U19`, `U20`, `U23`, `U25`, `R04`, `R07`, `R08`, `R10`, `R11`, `R13`, `M05` |

Ohne Tag bleiben fünf Motive: `C09`, `C13`, `C21`, `C27` und `M06`. Sie
erzählen von Datenmodellierung, Rechenausstattung und einer gelungenen Demo,
ohne einen Querschnittswert zu berühren.

### Was die Verteilung zeigt

- `rights` trägt vier Motive, darunter keine einzige Common: Datenschutz,
  Persönlichkeitsrechte, sensible Bestände, kulturelle Rechte,
  Datensouveränität und Takedown kommen im Set praktisch nicht vor. `C13`
  („Spalte: Bemerkung“) enthält Personen und Orte in einem Freitextfeld und
  wäre der nächstliegende Ort für eine redaktionelle Anpassung; getaggt wird
  die Karte erst, wenn ihr Text das Thema auch benennt.
- `accessibility` hängt an einer einzigen Karte, `C20`, die
  Barrierefreiheit zudem als aufgeschobenes Spezialmodul zeigt.
- `participation` liegt bei sieben Motiven, von denen nur `C04` eine Common
  ist. Mitentscheidung erscheint damit fast nur in selteneren Karten.
- `care`, `provenance`, `interpretation` und `labor` decken das Set breit ab.
  Das entspricht dem Gegenstand des Spiels und ist kein Korrekturbedarf.

Die Tabelle ist ein Redaktionsstand, keine Zielvorgabe; maßgeblich sind die
Zahlen im Validatorlauf.
