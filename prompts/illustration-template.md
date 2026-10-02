# Illustration Prompt Template

Dieses Template erzeugt ausschließlich das Bildmotiv, niemals die vollständige
Karte. Alle Motive verwenden dieselbe Art Direction **Mid-Century Science
Pulp**. Register A und B sind zwei Register dieses Stils, keine getrennten
Stiloptionen.

Der Produktionsprompt besteht immer aus genau drei Teilen:

1. dem unveränderten **Masterprompt** für Art Direction, Format und Grenzen
2. dem automatisch erzeugten **semantischen Kartenkontext** aus Kartentitel und
   Flavor Text
3. einer **Kartenergänzung** aus `visual_motif` für Szene, Register und Maßstab

Der Masterprompt wird nicht pro Karte umformuliert. Titel und Flavor Text
werden nur als Bedeutungsanker angehängt und ausdrücklich von jeder sichtbaren
Typografie ausgeschlossen. Regeltexte werden nicht angehängt.

## Masterprompt

Dieser Block wird für jede Generation unverändert vorangestellt:

```text
Create a horizontal 3:2 source illustration for a coherent series about
contemporary digital humanities research imagined as a vast hand-operated
scientific machine. The final card fills a centered 3:2 window with
xMidYMid-style cropping, so keep the outer 5 percent along every edge as
expendable overscan. The visual language is painted mid-century European science pulp,
approximately 1950s to early 1970s: tactile gouache and oil brushwork, dry
brush edges, selective soft airbrush, and slight misregistration from vintage
offset printing. It is painterly illustration, not photography, polished 3D
concept art, or a historical reconstruction.

Translate invisible digital and institutional processes into physical action:
enamelled control desks, tape drives, punched-card readers, microfilm devices,
file trolleys, cable bundles, projectors, stamp mechanisms, mechanical gauges,
service hatches, and architectural loads. Set them in European institutional
spaces with mineral walls, linoleum, ribbed glass, metal doors, wood veneer,
and visibly retrofitted wiring. Do not use holograms or generic floating user
interfaces.

Use warm paper white and deep print black as the base, with petrol green,
oxide red, sulphur yellow, and cobalt blue as equal functional colours. Let no
more than two functional colours dominate one image. Cyan or warm white may
mark an active process, but success is not represented by a generic golden
glow.

Show a contemporary and diverse institutional cast in simplified present-day
clothing, varied across age, skin tone, gender presentation, body type,
professional role, and hierarchy. Give people competent, serious agency. The
satire targets systems and disproportionate procedures, never identity or an
individual person's presumed incompetence. Avoid caricature, sexualised poses,
and stereotyped assignments of leadership, assistance, or technical work.

Build the image around one observable trigger, one dominant action, one main
apparatus or architectural contradiction, and one visible consequence. The
surreal exaggeration must grow from a real work process through scale, weight,
repetition, congestion, connection, or decay. Keep the decisive action,
expressive faces, and hands in the central safe area with a clear silhouette
and distinct foreground, middle ground, and background. Leave quieter,
low-detail crop space along every edge.

This is the illustration only. Do not create a card frame, title, caption,
icon, rarity mark, logo, watermark, readable document, or legible interface.
Paper, screens, labels, and signs remain blank, abstract, or turned away. Do
not use crowns, thrones, seals, magical portals, or generic cosmic diagrams as
shortcuts for authority, success, rarity, or data.
```

## Kartenergänzung

Die Spalte `visual_motif` enthält ausschließlich die variable Ergänzung. Sie
wird auf Deutsch in fünf kurzen Sätzen oder Satzteilen redigiert:

```text
Szene: [sichtbarer Augenblick, Figuren und konkrete Handlung].
Ort und Apparat: [institutioneller Raum und physische Gegenstände].
Bildspannung: [sichtbare Folge oder Widerspruch].
Inszenierung: [Register A, B oder Mischform; Kamera, Blickfang und Licht].
Maßstab: [Common, Uncommon, Rare oder Mythic; Umfang der Szene].
```

Jede Ergänzung nennt genau eine Hauptaktion und höchstens einen visuellen
Vergleich. Sie wiederholt weder Stil, Palette, Diversitätsvorgaben, Ausschlüsse
noch das horizontale 3:2-Quellformat und den mittigen 3:2-Bildausschnitt aus
dem Masterprompt. Abstrakte Begriffe, Systemdiagramme und bloße Symbolreihen sind
kein Ersatz für eine beobachtbare Handlung.

## Semantischer Kartenkontext

Zwischen Masterprompt und Kartenergänzung fügt der Generator diesen Block ein:

```text
Semantic context for image selection only. Do not depict or reproduce any of
the following words as typography, labels, captions, signage, or interface
text.
Card title: "[NAME]"
Flavor text: "[FLAVOR TEXT]"
Make the relationship between title and flavor text visually clear through
physical objects, action, and consequence.
```

Der Block hilft dem Bildmodell, das `visual_motif` im Sinn der fertigen Karte
zu lesen. Die englische Negativanweisung steht unmittelbar vor den deutschen
Kartentexten, damit sie nicht als Aufforderung zur Schriftgenerierung wirken.

Beispiel für `KAT-C03`:

```text
Szene: Zwei Forschende versuchen an einem Arbeitstisch eine Entscheidung zu
protokollieren, während aus einem pneumatischen Postschacht immer neue
ungelesene Umschläge auf die Arbeitsfläche rutschen. Ort und Apparat: enger
Sitzungsraum mit Rohrpost, Aktenwagen und einem überlasteten Tischprojektor.
Bildspannung: Die fertige Entscheidungsvorlage verschwindet unter der
wachsenden Post. Inszenierung: Register A, leichte Aufsicht, die Hände am
letzten freien Stück Tisch im harten Projektorlicht. Maßstab: Common, zwei
Figuren und ein Raum.
```

Der vollständige Produktionsprompt ist die unveränderte Verkettung:

```text
[MASTERPROMPT]

[SEMANTISCHER KARTENKONTEXT]

[visual_motif DER KARTE]
```

## Registermodule

Das Register folgt der Szene und dem Flavor Text, nicht Kartenart oder
Seltenheit. Für Mischszenen dürfen beide Module kombiniert werden, solange die
gemalte Machart und Palette einheitlich bleiben.

### Register A – Desaster

Für Katastrophe, Überlastung, Kontrollverlust und institutionellen Druck:

```text
strong chiaroscuro, expressive but non-caricatured reactions, looming analog
machinery, compressed space, banal procedural failure staged with dramatic
scientific-horror tension, slightly aged magazine reproduction
```

### Register B – Heroisch-utopisch

Für gelingende, monumentale oder absurd heroische Forschung:

```text
heroic wide perspective, airbrushed technical and architectural depth,
optimistic retro-futurist research environment, luminous gradients and bold scale,
institutional ambition presented as cosmic scientific spectacle
```

## Intensitätsmodule

Die Intensität folgt der Seltenheitsstufe, nicht der Szene. Es gibt ein Modul
je Raritätsstufe, damit für jede Karte eindeutig feststeht, welches gilt.

Die Intensität regelt ausschließlich den **Umfang** der Szene, nicht ihre
Dramatik. Eine klar lesbare, dramatische Hauptszene ist laut Leitplanken für
alle Karten verbindlich; ein Common ist kleiner, nicht langweiliger. Die
Module dürfen weder Palette noch Materialität verändern.

### Common – alltäglich

```text
intimate everyday scale, one or two figures, a single ordinary room or desk,
mundane incident kept limited in scope rather than escalated, tight framing
with shallow depth
```

### Uncommon – strukturell

```text
structural scale, a small group and the apparatus around them, institutional
context visible beyond the immediate room, moderate escalation
```

### Rare – institutionelle Eskalation

```text
large institutional or technical scale, figures dwarfed by the systems around
them, an entire facility or organisational apparatus in view, pronounced
escalation
```

### Mythic – monumental

```text
monumental scale, improbable singular event, vast architectural or cosmic
depth, maximum spectacle while keeping the central action readable
```

## Serienkonsistenz

- dieselbe gemalte Materialität und Grundpalette in beiden Registern
- keine Stilwechsel nach Seltenheit oder Kartenart; die Seltenheit steuert
  ausschließlich die Intensität
- wiederkehrende Apparate, Räume und Farbtemperaturen über das Set
- Spiegelmotive mit identischer Perspektive und Figurenanordnung erzeugen
- zeitgenössische Vielfalt nicht durch historische Rollenklischees ersetzen

## Negativregeln

- keine KI-generierte Schrift als Inhalt
- keine vollständigen Karten, Rahmen, Icons oder Seltenheitszeichen
- keine vier oder sechs Finger als Fokusfehler
- keine identischen Gesichter im Set
- keine ausschließlich weißen, jungen oder männlichen technischen Teams
- keine sexualisierten Posen
- keine stereotype Zuordnung von Assistenz, Leitung oder Technik
- keine geschützten Logos, Fraktionszeichen oder erkennbares Trade Dress
