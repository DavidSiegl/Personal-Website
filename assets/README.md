# assets

`profile.jpg` — Profilbild für die Startseite: quadratischer Ausschnitt aus dem Original
`Ich.jpg` (2667×4000), skaliert auf 800×800 und ohne EXIF-Daten.

Neu erzeugen nach demselben Zuschnitt (aus dem Projektwurzelverzeichnis):

    ffmpeg -y -i assets/Ich.jpg -map_metadata -1 \
      -vf "crop=2667:2667:0:100,scale=800:800:flags=lanczos" -q:v 3 assets/profile.jpg

Fehlt `profile.jpg`, zeigt die Seite den Initialen-Kreis „DS“ — das `<img>` entfernt sich
bei einem Ladefehler selbst, es bricht also nichts.
