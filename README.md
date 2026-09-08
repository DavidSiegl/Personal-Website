# Personal-Website

Statische persönliche Website – reines HTML und CSS, ohne Build-Schritt und ohne
Abhängigkeiten. Lokal ansehen mit `xdg-open index.html`.

    index.html      Startseite: Profil, Kenntnisse, Open Source & Homelab
    lektuere.html   Unterseite: gelesene IT-Fachlektüre (generiert, siehe unten)
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

## Profilbild

`assets/profile.jpg` ist ein quadratischer Ausschnitt des Originals `assets/Ich.jpg`;
der ffmpeg-Befehl dafür steht in `assets/README.md`. Original und Lebenslauf-PDF sind
über `.gitignore` vom Repo ausgenommen.
