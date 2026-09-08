#!/usr/bin/env python3
"""Erzeugt lektuere.html im Projektwurzelverzeichnis aus dem Obsidian-Zettelkasten.

Aufgenommen wird jede Notiz, die auf [[Informatik]] verweist und #gelesen trägt.
Die Gruppierung in GROUPS ist Handarbeit: Titel, die dort fehlen, landen sichtbar
unter "Weitere" und werden auf stderr gemeldet, statt still zu verschwinden.

    python3 tools/build-lektuere.py
"""
import html, pathlib, re, sys
from datetime import date

VAULT = pathlib.Path.home() / "Documents/Zettelkasten"
OUT = pathlib.Path(__file__).resolve().parent.parent / "lektuere.html"

GROUPS = [
    ("Handwerk & Programmierung",
     "Wie man Code schreibt, der ein Jahr später noch lesbar ist – und wie man die Werkzeuge beherrscht, mit denen man ihn schreibt.",
     ["The C Programming Language", "The Practice of Programming", "The Pragmatic Programmer",
      "Think Like a Programmer", "The Art of Clean Code", "Learning Go", "Practical Vim",
      "Mastering Regular Expressions", "Classic Shell Scripting", "Fluent Python",
      "A Philosophy of Software Design"]),
    ("Grundlagen & Systeme",
     "Was unter der Abstraktion liegt: vom Logikgatter bis zum laufenden Linux-System.",
     ["Code", "How Computers Really Work", "How Linux Works", "Algorithms to Live By"]),
    ("DevOps, Container & Delivery",
     "Der Kern meiner täglichen Arbeit: Systeme reproduzierbar bauen, ausrollen und betreiben.",
     ["Docker Up and Running", "Kubernetes Up and Running", "The Book of Kubernetes",
      "Infrastructure as Code 1", "Building CICD Systems Using Tekton",
      "Continuous Delivery with Docker and Jenkins - Rafal Leszko", "Go for DevOps",
      "DevOps for the Desperate", "Fundamentals of DevOps and Software Delivery"]),
    ("Daten, Datenbanken & Statistik",
     "Vom Speicherlayout einer Datenbank bis zu den Modellen, die auf den Daten rechnen.",
     ["Designing Data-intensive Applications", "Mastering PostgreSQL 15",
      "Data Pipelines Pocket Reference", "Data Science for Business",
      "Python Data Science Essentials", "Statistics for Data Scientists",
      "Practical Statistics for Data Scientists", "An Introduction to Statistical Learning"]),
    ("Kultur & Kritik",
     "Die Softwarewelt als Gegenstand: ihre Biografien, ihre Ideologien, ihre ökonomischen Fehlentwicklungen.",
     ["Just for Fun", "Hackers & Painters", "The Innovators", "Steve Jobs", "Source Code",
      "Enshittification"]),
]

# Google-Books-Metadaten kommen teils mit kaputtem Escaping oder Autorennamen im Titel.
TITLE_FIX = {
    "Continuous Delivery with Docker and Jenkins - Rafal Leszko": "Continuous Delivery with Docker and Jenkins",
    "Infrastructure as Code 1": "Infrastructure as Code",
}
AUTHOR_FIX = {"Bri Bruce, Of, Andrew Bruce": "Peter Bruce, Andrew Bruce"}

# Diese Notiz traegt #aktuell-lesend, verweist aber auf [[Literatur]] statt auf
# [[Informatik]] - vermutlich ein Versehen im Vault. Bis die Notiz korrigiert ist,
# wird sie hier namentlich aufgenommen.
CURRENT_EXTRA = {"A Philosophy of Software Design"}


def clean(s):
    return re.sub(r'\s+', ' ', s.replace('\\"', '').replace('\\', '').strip(' "\',')).strip()


def load():
    books = []
    for p in VAULT.glob("*.md"):
        txt = p.read_text(encoding="utf-8")
        if not txt.startswith("---"):
            continue
        end = txt.find("\n---", 3)
        if end < 0:
            continue
        body = txt[end + 4:]
        informatik = "[[Informatik]]" in body or p.stem in CURRENT_EXTRA
        reading = "#aktuell-lesend" in body
        if not informatik or not (reading or "#gelesen" in body):
            continue
        fm = {}
        for line in txt[3:end].splitlines():
            m = re.match(r'^([A-Za-z0-9_]+):\s*(.*)$', line)
            if m:
                fm[m.group(1)] = clean(m.group(2))
        books.append({
            "key": p.stem,
            "reading": reading,
            "title": TITLE_FIX.get(p.stem, clean(fm.get("title") or p.stem)),
            "subtitle": clean(fm.get("subtitle", "")),
            "authors": AUTHOR_FIX.get(fm.get("authors", ""), fm.get("authors") or fm.get("author", "")).replace(",", ", "),
            "publisher": clean(fm.get("publisher", "")),
            "year": (fm.get("publishDate") or "")[:4],
            "pages": fm.get("totalPage") or "",
        })
    return books


def render_book(b):
    meta = " · ".join(x for x in (
        re.sub(r'\s+', ' ', b["authors"]).strip(", "),
        b["publisher"],
        f'{b["pages"]} Seiten' if b["pages"] else "",
    ) if x)
    sub = f'<span class="book__sub">{html.escape(b["subtitle"])}</span>' if b["subtitle"] else ""
    return f'''        <li class="book">
          <span class="book__year">{html.escape(b["year"] or "—")}</span>
          <span class="book__body">
            <span class="book__title">{html.escape(b["title"])}</span>
            {sub}
            <span class="book__meta">{html.escape(meta)}</span>
          </span>
        </li>'''


def main():
    books = {b["key"]: b for b in load()}
    placed = {k for _, _, keys in GROUPS for k in keys}
    rest = sorted(set(books) - placed)
    if rest:
        print(f"Nicht zugeordnet (landen unter 'Weitere'): {rest}", file=sys.stderr)

    total_pages = sum(int(b["pages"]) for b in books.values() if b["pages"])
    years = sorted(b["year"] for b in books.values() if b["year"])

    sections = []
    for name, lede, keys in GROUPS + ([("Weitere", "Zuletzt hinzugekommen.", rest)] if rest else []):
        items = [books[k] for k in keys if k in books]
        if not items:
            continue
        items.sort(key=lambda b: (b["year"], b["title"]))
        sections.append(f'''      <section class="shelf">
        <h2>{html.escape(name)} <span class="shelf__count">{len(items)}</span></h2>
        <p class="shelf__lede">{html.escape(lede)}</p>
        <ol class="books">
{chr(10).join(render_book(b) for b in items)}
        </ol>
      </section>''')

    page = f'''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lektüre — David Siegl</title>
  <meta name="description" content="IT-Fachlektüre als Fundament der Arbeit: alle gelesenen Informatik-Titel aus dem Zettelkasten von David Siegl.">
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="assets/favicon.png" sizes="96x96" type="image/png">
  <link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <a class="skip-link" href="#regal">Zur Bücherliste springen</a>

  <nav class="topbar" aria-label="Hauptnavigation">
    <a class="topbar__home" href="index.html">David Siegl</a>
    <a class="topbar__here" href="lektuere.html" aria-current="page">Lektüre</a>
  </nav>

  <header class="pagehead">
    <p class="eyebrow">Aus dem Zettelkasten</p>
    <h1>Lektüre</h1>
    <p class="bio">
      Vieles an meiner Arbeit lässt sich nicht zusammensuchen. Wer eine Datenbank betreibt, muss
      verstehen, warum es ein Write-Ahead-Log gibt; wer Deployments automatisiert, sollte wissen,
      welches Problem Continuous Delivery ursprünglich gelöst hat. Dieses Verständnis kommt aus
      Büchern, die ein Thema von Grund auf entwickeln – nicht aus der Dokumentation der jeweils
      aktuellen API-Version.
    </p>
    <p class="bio">
      Gelesenes landet bei mir in einem Zettelkasten: jeder Titel eine Notiz, verknüpft mit den
      Themen, auf die er einzahlt, und mit den Autoren, die ihn geschrieben haben. Was hier steht,
      ist genau dieser Bestand — alle Notizen, die auf die Hauptnode <code>Informatik</code>
      verweisen – abgeschlossene ebenso wie gerade laufende Lektüre.
    </p>

    <dl class="stats">
      <div><dt>Titel</dt><dd>{len(books)}</dd></div>
      <div><dt>Seiten</dt><dd>{total_pages:,}</dd></div>
      <div><dt>Zeitraum</dt><dd>{years[0]}–{years[-1]}</dd></div>
      <div><dt>Themenfelder</dt><dd>{len(GROUPS)}</dd></div>
    </dl>
  </header>

  <main id="regal">
{chr(10).join(sections)}
  </main>

  <footer class="footer">
    <p>© <span id="year">{date.today().year}</span> David Siegl</p>
    <p class="footer__links">
      <a href="index.html">Startseite</a>
      <a href="https://github.com/DavidSiegl" target="_blank" rel="noopener noreferrer">GitHub</a>
      <a href="mailto:david.siegl95@gmail.com">E-Mail</a>
    </p>
  </footer>

  <script>document.getElementById('year').textContent = new Date().getFullYear();</script>
</body>
</html>
'''.replace(f"{total_pages:,}", f"{total_pages:,}".replace(",", "."))

    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT}: {len(books)} Titel, {total_pages} Seiten, {len(sections)} Abschnitte")


if __name__ == "__main__":
    main()
