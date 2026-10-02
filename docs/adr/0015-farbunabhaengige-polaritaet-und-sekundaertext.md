# ADR 0015: Farbunabhängige Polarität und neutraler Sekundärtext

- Status: angenommen
- Datum: 2026-08-30
- Berührt: Farbtoken, Typzeile, Ereignisdarstellung, Vorderseitenrenderer
- Teilweise abgelöst durch: ADR 0018 hinsichtlich jeder sichtbaren
  Polaritätscodierung; der gemeinsame Ereignisakzent und der neutrale
  Sekundärtext bleiben gültig

## Kontext

Der bisherige Entwurf ließ den Farbkanal zwei verschiedene Taxonomien tragen:
Projekte und Projektfaktoren erhielten Familienfarben, Ereignisse dagegen
Polaritätsfarben. Dabei lagen `family/operations` (`#006D63`) und das frühere
`event/positive` (`#2B6F58`) im selben blaugrünen Bereich. In der Fernwirkung
waren Betriebsfaktoren und positive Ereignisse deshalb nicht zuverlässig
getrennt.

Zugleich besaßen das frühere `event/positive` und `event/ambivalent` dieselbe
relative Luminanz von 0,1259. Ihre Polaritäten blieben in Graustufen oder bei
stark reduziertem Farbsehen ununterscheidbar. Da die Vorderseite die
Polarität weder als Wort noch als Form ausgab, war Farbe ihr einziger
sichtbarer Informationsträger.

Der Familienname in der Typzeile stand außerdem in nur 14/18 Einheiten in der
jeweiligen Akzentfarbe. `family/methods` (`#886600`) erreichte auf
`background/paper-raised` rechnerisch nur knapp den AA-Kontrast. Diese digitale
Berechnung ist keine belastbare Aussage über Tonwertzunahme im Vierfarbdruck;
gerade die kleinste farbige Spielinformation blieb daher ein unnötiges
Produktionsrisiko.

## Entscheidung

### Ein Ereignisakzent statt dreier Polaritätsfarben

Alle Ereignisse verwenden unabhängig von ihrer Polarität den gemeinsamen
Akzenttoken `event/base` mit dem Wert `#60457A`. Er kennzeichnet die Kartenart
Ereignis und wird für deren Kartentyp, Strukturelemente, Effektsymbol und die
Kontur des Polaritätsträgers eingesetzt. Die früheren Polaritätsfarben steuern
die Vorderseite nicht mehr; ihre drei Farbtoken werden aus der aktiven
Layoutkonfiguration entfernt.

Familienfarben kennzeichnen weiterhin Projekte und Projektfaktoren. Damit
trägt die Akzentfarbe nur noch eine Taxonomie: entweder die Familie oder die
Kartenart Ereignis.

### Sichtbares typografisches Polaritätszeichen

Direkt nach `EREIGNIS` und vor dem Effektsymbol erhält jedes Ereignis einen
optisch offenen Kreis von 22 × 22 Layout-Einheiten. Seine Kontur ist 1,5
Einheiten breit und verwendet `event/base`; die Innenfläche verwendet
`background/paper-raised`. Im Kreis steht eines von drei typografischen
Zeichen in Noto Sans Bold 15/18 und `text/primary`:

| Datenwert | sichtbares Zeichen |
|---|---|
| `positive` | `+` |
| `negative` | `−` (U+2212) |
| `ambivalent` | `±` |

Zwischen Kreis und 18 Einheiten großem Effektsymbol liegen fünf Einheiten.
Die Polarität wird weder ausgeschrieben noch als Banner, Badge oder
Phosphor-Polaritätsicon dargestellt. Der Ereignis-Identitätsstempel in der
Titelleiste bleibt unverändert und enthält ausschließlich `Lightning`.
Polarität bleibt außerdem als kanonischer Datenwert und als `data-polarity`
am SVG-Träger erhalten; ihre sichtbare Unterscheidung hängt nicht mehr von
Farbe oder Luminanz ab.

### Neutraler Sekundärtext

Alle klein gesetzten Sekundärtexte der Typzeile verwenden `text/primary`:
Domänen- und Familiennamen auf Projekten und Projektfaktoren ebenso wie
Ereignisschlüsselwort und Zielangabe. Familien- und Ereignisfarben bleiben an
den größeren Kartentypen, Symbolen und Strukturelementen sichtbar. Der
Methoden-Goldton `#886600` bleibt unverändert, trägt aber nicht mehr den
14/18-Familiennamen `METHODE`.

## Folgen

- Positive, negative und ambivalente Ereignisse bleiben auch ohne Farbe durch
  unterschiedliche Zeichen unterscheidbar.
- Betriebsfaktoren und positive Ereignisse teilen nicht länger einen nahezu
  gleichfarbigen Sortierhinweis; alle Ereignisse bilden eine gemeinsame
  violette Kartenart.
- Die kleinsten funktionalen Texte besitzen unabhängig von der Akzentpalette
  denselben neutralen Kontrast. Die bestehende Familienpalette muss für diese
  Änderung nicht neu abgestimmt werden.
- Die E1–E8-Effektsymbole und die in ADR 0014 beschlossene Phosphor-Zuordnung
  bleiben unverändert. ADR 0015 löst ADR 0014 nur hinsichtlich der dort
  beschriebenen unsichtbaren Polarität teilweise ab.
- Produktionszahlen, Seltenheiten, Kartenregeln und die Werte in
  `data/cards.csv` ändern sich nicht.
- Renderer-Preview und technischer Proof sind keine farbverbindlichen
  Druckproofs. Die violette Ereignisfarbe, das unveränderte Methodengold und
  die kleinen Zeichen benötigen vor Produktionsfreigabe weiterhin einen
  physischen Andruck.
