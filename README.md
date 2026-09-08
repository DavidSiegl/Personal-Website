# Personal-Website

Statische persönliche Website – HTML, CSS und ein wenig Vanilla-JavaScript, ohne
Build-Schritt und ohne Abhängigkeiten. Lokal ansehen mit `xdg-open index.html`.

    index.html      Startseite: Profil, Kenntnisse, Open Source & Homelab
    lektuere.html   Unterseite: Fachlektüre und Themengraph (generiert, siehe unten)
    graph.js        Kraftlayout für den Themengraph
    styles.css      gemeinsames Stylesheet beider Seiten
    assets/         Profilbild, Favicons
    tools/          Generatoren

## Lektüre-Seite neu erzeugen

`lektuere.html` wird nicht von Hand gepflegt, sondern aus dem Obsidian-Zettelkasten
unter `~/Documents/Zettelkasten` erzeugt. Aufgenommen wird jede Notiz, die auf
`[[Informatik]]` verweist und `#gelesen` oder `#aktuell-lesend` trägt.

    python3 tools/build-lektuere.py

Die thematische Gruppierung steht als `GROUPS` im Skript und ist Handarbeit. Neue
Titel, die dort noch nicht zugeordnet sind, erscheinen auf der Seite unter „Weitere"
und werden zusätzlich auf stderr gemeldet – sie fallen also nicht stillschweigend
unter den Tisch.

## Themengraph

Unter der Bücherliste steht der Teilgraph um `[[Informatik]]`: alle Konzeptnotizen,
die auf die Hauptnode verweisen, plus die Buchnotizen, die ihrerseits auf ein Thema
zeigen. `tools/graph_data.py` liefert ihn als Abschnitt, `build-lektuere.py` setzt
ihn ein – ein eigener Aufruf ist nicht nötig.

Buchnotizen ohne Themenlink bleiben draußen: rund fünfzig davon hängen im Vault nur
am Hub und wären im Bild bedeutungslose Blätter; ihr Platz ist die Bücherliste
darüber. Auf stderr meldet der Generator, was er weggelassen hat – unaufgelöste
Linkziele (`[[PostgreSQL]]` etwa hat noch keine Notiz) und Buchnotizen, deren Links
ins Leere oder auf Autoren zeigen.

Die Daten stehen als JSON im `<script id="graph-data">` der Seite, nicht in einer
eigenen Datei – so funktioniert der Graph auch über `file://`. Ohne JavaScript
bleibt er verborgen; die eingeklappte Notizliste darunter trägt denselben Bestand
und ist zugleich die Bedienung für Tastatur und Screenreader.

Die Kräfte in `graph.js` sind auf rund 50 Knoten eingestellt: `BOUND` hält Notizen
ohne Kanten am Rand statt auf einem weiten Ring, `MIN_D2` und `VMAX` verhindern,
dass die Abstoßung im ersten Tick einzelne Knoten aus dem Bild schleudert.
