# Rekonstruktion der Phylo-PDFs

Status: Forschungsnotiz, keine Produktentscheidung.

Diese Notiz rekonstruiert Kartenlisten und Struktur aus den bildbasierten Phylo-PDFs
(nicht im Repository, siehe `README.md`). Die PDFs besitzen keinen Textlayer. Die Ergebnisse
wurden durch Rendering, OCR und visuelle Kontrolle der Seitenübersichten
gewonnen. Schreibweisen und Kartenanzahlen sind belastbar; kleinteilige
Anforderungssymbole einzelner Projektkarten müssen vor einer Regelübernahme
noch einmal direkt am Kartenbild geprüft werden.

## Quellen

- `GSAphylo.pdf`: Genetics Society of America, Process-of-Science-Spiel
- `PHYLOWWESTWISEprintyourown.pdf`: Women in Science and Engineering
- `ingenium_english.pdf`: Ingenium Women in STEM
- `WISErules.pdf`: Regelblatt des Women-in-Science-Modus

Die Rekonstruktion ist nur eine Arbeitsreferenz. Bilder, Logos und bestehendes
Kartendesign werden nicht für unser Produkt übernommen.

## GSA-Kernsatz

Der Regeltext nennt 74 Karten:

- 16 Project Cards
- 58 Resource Cards

Die 58 Resource Cards setzen sich im PDF zusammen aus:

- 17 Species Cards
- 29 Research Technique Cards
- 12 Modifier Cards

Das PDF enthält zusätzlich zwei optionale Mandatory Project Cards. Damit sind
76 spielrelevante Kartenflächen vorhanden, von denen 74 den beschriebenen
Kernsatz bilden.

### Species Cards

| Motiv | Kopien |
|---|---:|
| Frog | 2 |
| Yeast | 2 |
| Zebrafish | 2 |
| Ciliates | 2 |
| Mouse | 2 |
| C. elegans | 2 |
| Fruit Fly | 2 |
| Arabidopsis | 3 |
| Gesamt | 17 |

### Research Technique Cards

| Motiv | Kopien |
|---|---:|
| Sequencing | 8 |
| Molecular Genetics | 5 |
| Genetic Analysis | 3 |
| Imaging | 6 |
| Bioinformatics | 7 |
| Gesamt | 29 |

### Project Cards

| Projekt | Punkte | Aufgabe in Kurzform |
|---|---:|---|
| Cancer Research | 4 | Krebsgenetik an einem Modellorganismus untersuchen |
| Whole Genome Sequencing | 3 | vollständiges Genom sequenzieren |
| Software Development | 3 | Programm zur Analyse genetischer Daten entwickeln |
| Invertebrate Cytogenetic Analysis | 2 | Chromosomen eines Wirbellosen untersuchen |
| Telomere Study | 2 | Telomere eines Einzellers untersuchen |
| Invertebrate Gene Knockout | 4 | Wirkung eines Gen-Knockouts untersuchen |
| Unicellular Transposon Study | 3 | Transposons und mögliche epigenetische Rollen untersuchen |
| Rare Disease Gene Study | 4 | Gen einer seltenen Krankheit identifizieren und untersuchen |
| Vertebrate Embryonic Development Study | 3 | Chromatin und Embryonalentwicklung untersuchen |
| Vertebrate SNP Analysis | 3 | genetische Variation mittels SNP-Array untersuchen |
| Phylogenetic Analysis | 4 | Verwandtschaft durch Sequenzvergleich ableiten |
| Vertebrate CRISPR/Cas Genome Editing | 2 | Gene eines Wirbeltiers verändern |
| Common Garden Experiment | 3 | genetische und Umwelteffekte unterscheiden |
| Plant Transcriptomics | 4 | Genexpression bei Pflanzenabwehr untersuchen |
| Unicellular Genomic Stability Study | 4 | Gene der Genomstabilität untersuchen |
| Invertebrate Hybrid Study | 3 | reproduktive Isolation durch Kreuzung untersuchen |

Die Punktezahlen wurden aus den Kartenbildern rekonstruiert. Die exakten
Kombinationen der Anforderungssymbole sind noch nicht vollständig transkribiert.

### Optionale Mandatory Project Cards

| Karte | Folge bei Nichtabschluss |
|---|---:|
| Lab Preparations | −2 Punkte |
| Increase Sample Size | −2 Punkte |

Beide Karten können nicht kollaborativ abgeschlossen werden. Sie erscheinen im
PDF zusätzlich zu den 16 regulären Projekten.

### Modifier Cards

| Motiv | Kopien | mechanische Funktion |
|---|---:|---|
| Swap Projects | 1 | Projekte samt Ressourcen zwischen zwei Personen tauschen |
| Lose Funding! | 1 | eine Research Technique aus einem Projekt entfernen |
| Human Error! | 1 | eine Species Card aus einem Projekt entfernen |
| Grant Approved | 2 | als beliebige Research Technique verwenden |
| Resource Donation | 1 | Ressource aus einem fremden Projekt auf die Hand nehmen |
| Join a Society | 2 | oberste drei Ressourcen ansehen und eine behalten |
| Connection Made! | 1 | oberste zwei Projekte ansehen und eines behalten |
| Outreach | 1 | zwei zusätzliche Karten aus einem Nicht-Burn-Stapel ziehen |
| Catalyze Ideas | 1 | oberste zwei Projekte ansehen und eines behalten |
| Fund Research | 1 | zwei zusätzliche Karten aus einem Nicht-Burn-Stapel ziehen |
| Gesamt | 12 | |

Mehrere Sponsor-Karten verwenden somit dieselbe mechanische Funktion mit
anderem Namen und anderer Illustration.

## Tatsächlicher Motivbedarf des GSA-Satzes

Der vollständige 74-Karten-Kernsatz verwendet nur 39 unterschiedliche Motive:

| Funktion | unterschiedliche Motive | physische Karten |
|---|---:|---:|
| Projects | 16 | 16 |
| Species Resources | 8 | 17 |
| Technique Resources | 5 | 29 |
| Modifiers | 10 | 12 |
| Gesamt | 39 | 74 |

Phylo erreicht seine Spielbarkeit also durch häufig wiederholte, einfach
erkennbare Ressourcen. Für einen ersten Test unserer Adaption sind keine 74
unterschiedlichen Illustrationen oder Regeltexte erforderlich.

## WWEST und Ingenium

Die beiden Women-in-Science-Sätze verwenden denselben Grundgedanken in einer
anderen thematischen Ausprägung:

- Portraitkarten ersetzen oder ergänzen Project Cards.
- Discipline Cards sind wiederholte Ressourcen.
- Achievement Cards bilden eine zweite Ressourcenfamilie.
- Modifier Cards erschweren, beschleunigen, schützen oder verändern aktive
  Karten.
- Punkte, Anforderungen und Ressourcensymbole stehen prominent auf der Karte.

Wiederkehrende Modifier-Funktionen sind unter anderem:

- eine zusätzliche Ressource für einen Abschluss verlangen
- eine Ressource abwerfen
- aktive Vorhaben abbrechen
- mehrere Karten ziehen
- eine negative Modifier Card verhindern
- eine Modifier Card als Wildcard-Ressource verwenden
- eine Karte aus dem Burn Pile zurückholen
- Ressourcen nach Abschluss weiterverwenden

Für unsere Adaption sind diese Funktionsmuster nützlicher als die konkreten
Personen- und Disziplinenmotive der PDFs.

## Schlussfolgerung für unsere Adaption

Ein schlanker, PDF-naher Bühnensatz kann mit ungefähr 40 unterschiedlichen
Motiven auskommen:

- 16 Projekte
- 12 bis 16 Projektfaktormotive mit mehreren Kopien
- 10 bis 12 Wendungen

Unser vorhandener Produktplan mit 82 Booster-Motiven erlaubt deutlich mehr
Abwechslung, ohne dass jede Karte einen einzigartigen Effekt benötigt. Die
aktuelle Zuordnung steht in `phylo-panel-revised-cards.csv`; der konsolidierte
Setentwurf steht in `phylo-panel-revised-set.md`.

## Kann das wie ein TCG aussehen?

Ja, als Produkt und Kartenobjekt. Der Spielablauf bleibt allerdings ein
Projekt- und Set-Collection-Spiel, kein Kampf-TCG.

Für eine klare TCG-Wirkung braucht unsere Gestaltung:

- große individuelle Illustration oder Portraitfläche
- vier deutlich erkennbare Projektfaktor-Farben
- Anforderungssymbole in einer festen Kostenleiste
- eigene Rahmen für Projekt, Projektfaktor und Wendung
- sichtbare Seltenheit, Setzeichen und Kartennummer
- kurze Regelbox und optionale Flavor-Zeile
- Foil-Mythics mit ungewöhnlichen, nicht bloß stärkeren Effekten
- konsistente Rückseite und Booster-Trade-Dress

Die Quell-PDFs zeigen bereits, dass Portraits, Farbcodierung, Symbole und
Punktwerte sammelbar wirken können. Unser eigenes Layout sollte diese
Sammelkartenlesbarkeit verstärken und die schulbuchartige Anmutung der
Originalkarten vermeiden.
