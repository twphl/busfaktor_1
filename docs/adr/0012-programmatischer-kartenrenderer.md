# ADR 0012: Programmatischer Kartenrenderer als Produktionsausgabe

- Status: angenommen
- Datum: 2026-08-28
- Ersetzt: ADR 0004
- Berührt: `data/cards.csv`, Kartenlayout, Vorschau- und Druckausgabe

## Kontext

ADR 0004 legte Figma als ausschließliches System für Layout und Typografie
fest. Dieser Produktionspfad ist von der jeweiligen Figma-Umgebung, dem
installierten Plugin und dort verfügbaren Funktionen abhängig. Er erschwert
dadurch automatisierte Prüfungen, reproduzierbare Exporte und stabile
Dateihashes.

Für die weitere Produktion wird ein versionierter Renderer benötigt, der aus
den Repository-Daten prüfbare SVG-Master und eindeutig definierte
Uploaddateien erzeugt. Das schließt die bisherige Figma-Datei als
vorübergehende visuelle Referenz nicht aus, löst sie aber als Autorität für
die Produktionsausgabe ab.

## Entscheidung

### Quelle und Produktionsweg

`data/cards.csv` bleibt die kanonische Quelle für Kartenmotive,
Seltenheiten und Kartendaten. Der programmatische Renderer erzeugt daraus die
Produktionsausgabe. Layoutregeln und Exportparameter werden versioniert im
Repository geführt und automatisiert geprüft.

Figma dient während der Umstellung nur als Übergangs- und Vergleichsreferenz.
Ein Figma-Export ist weder Master noch Voraussetzung für eine druckfähige
Ausgabe. Bei Abweichungen ist die aus den kanonischen Daten und dem
versionierten Renderer erzeugte, erfolgreich geprüfte Ausgabe maßgeblich.

### Geometrie und Exportformat

Der Kartenmaster ist ein selbstenthaltenes SVG mit
`viewBox="0 0 822 1122"`. Das finale Uploadformat ist ein PNG mit folgenden
verbindlichen Eigenschaften:

- exakt 1644 × 2244 Pixel bei 600 dpi
- opakes RGB mit 8 Bit je Kanal und eingebettetem sRGB-Farbprofil
- kein Alphakanal und keine transparente Fläche
- Trim-Rechteck `(72, 72, 1500, 2100)`
- Safe-Rechteck `(132, 132, 1380, 1980)`

Die Rechtecke sind als `(x, y, Breite, Höhe)` in Pixeln angegeben; ihr
Ursprung liegt links oben. Im SVG-Master entsprechen sie wegen der
zweifachen Rasterauflösung den Rechtecken `(36, 36, 750, 1050)` und
`(66, 66, 690, 990)`. Das PNG wird unmittelbar aus dem Master gerendert und
nicht aus einer kleineren Rasterdatei hochskaliert. Abweichende Abmessungen,
stille Skalierung oder Verzerrung sind unzulässig.

### Eigenständiges Trade Dress

Der Renderer verwendet ausschließlich projektspezifische Layouts, Symbole und
Gestaltungselemente sowie dokumentiert lizenzierte Schriften. Assets,
Schriftdateien, Logos, Symbole oder erkennbar kopierte Layoutbestandteile aus
*Magic: The Gathering* werden weder als Eingabe noch als Abhängigkeit oder
Exportbestandteil verwendet. Das schließt insbesondere Beleren-,
Jace-Beleren- und MPlantin-Schriftdateien ein.

### Vorschau- und Druck-Gates

Der Renderer unterscheidet zwei explizite Ausgabemodi:

- **Preview:** darf klar gekennzeichnete Platzhalter und noch nicht
  freigegebene Inhalte sichtbar machen. Preview-Artefakte sind dauerhaft als
  Vorschau markiert und dürfen nicht als Druckdateien ausgegeben werden.
- **Print:** bricht bei fehlenden oder nicht freigegebenen Inhalten,
  Illustrationen oder Rechten sowie bei Geometrie-, Textüberlauf-, Schrift-,
  Farbprofil-, Transparenz- oder Exportfehlern ab. Alle referenzierten Assets
  müssen lokal, eindeutig und per reproduzierbarem Hash bestimmbar sein.

Das Print-Gate umfasst mindestens die bestehende Kartenvalidierung, die
Vollständigkeit der Produktionsfelder, freigegebene Illustrationen und
Nutzungsrechte, vollständige Glyphenabdeckung ohne Font-Fallback, die
Einhaltung von Trim und Safe Area sowie einen technischen Preflight des
finalen PNG. Ein erfolgreicher Preview-Lauf ersetzt keinen erfolgreichen
Print-Lauf.

### Produktionsmengen

Diese Entscheidung ändert keine Kartenanzahlen, Seltenheitsverteilungen,
Boosterzusammenstellungen oder Foilmengen. Insbesondere bleiben die in ADR
0002 festgelegten 612 Standardkarten und 18 Foilkarten unverändert. Der
Renderer bestimmt die technische Ausgabe, nicht die Produktionsmathematik.

## Folgen

- ADR 0004 wird für die Produktionsausgabe abgelöst.
- SVG-Master und Upload-PNG können ohne Figma reproduzierbar gebaut,
  validiert und gehasht werden.
- Die vorhandene Figma-Datei darf zur visuellen Gegenprüfung genutzt werden,
  begründet aber keine abweichenden Produktionswerte.
- Vorschauen bleiben auch bei offenen Freigaben möglich, können jedoch nicht
  versehentlich das Print-Gate umgehen.
- Spätere Änderungen an Mastergeometrie, Uploadabmessungen oder harten
  Produktionszahlen benötigen eine dokumentierte Folgeentscheidung.

## Nicht entschieden

Diese ADR legt weder Kartenrückseite und Duplexausrichtung noch
druckereispezifische PDF/X-, CMYK-, Sonderfarben- oder Foil-Parameter fest.
Solche Parameter werden erst nach Vorlage der verbindlichen Spezifikation des
Produktionsdienstleisters entschieden.
