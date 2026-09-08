"""Der Themengraph aus dem Obsidian-Zettelkasten, als Abschnitt fuer lektuere.html.

Abgebildet wird der Teilgraph um [[Informatik]]: alle Konzeptnotizen, die auf die
Hauptnode verweisen, plus die Buchnotizen, die ihrerseits auf ein Thema zeigen.
Buchnotizen ohne Themenlink bleiben aussen vor - sie haengen im Vault nur am Hub
und waeren im Bild 50 bedeutungslose Blaetter; ihr Platz ist die Bücherliste.

Kein eigenes Skript: build-lektuere.py ruft section() auf und setzt das Ergebnis
in die Seite. Direkter Aufruf gibt nur die Kennzahlen aus.

    python3 tools/graph_data.py
"""
import html, json, pathlib, re, sys

VAULT = pathlib.Path.home() / "Documents/Zettelkasten"

# [[Ziel|Anzeige]] und [[Ziel#Abschnitt]] zeigen beide auf "Ziel".
LINK = re.compile(r'\[\[([^\]\|#]+)')

# Organisatorische Hubs, an denen alles haengt: als Kante ohne Aussage.
HUBS = {"Informatik", "Lektüre", "Literatur"}

# Anzeigenamen. Der Vault disambiguiert Notizen im Dateinamen ("Go
# (Programmiersprache)" neben dem Brettspiel), im Graphen stoert der Zusatz.
LABELS = {
    "Go (Programmiersprache)": "Go",
    "C (Programmiersprache)": "C",
    "Internet Protocol (IP)": "IP",
    "Privilegienstufen (OS)": "Privilegienstufen",
    "Continuous Delivery with Docker and Jenkins - Rafal Leszko":
        "Continuous Delivery with Docker and Jenkins",
}

# Bildanhaenge sind im Vault Linkziele wie jedes andere, aber keine Notizen.
ATTACHMENT = re.compile(r'\.(png|jpe?g|gif|webp|svg|pdf)$', re.I)


def read_vault():
    notes = {}
    for p in sorted(VAULT.glob("*.md")):
        try:
            notes[p.stem] = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as err:
            print(f"uebersprungen: {p.name}: {err}", file=sys.stderr)
    if not notes:
        sys.exit(f"keine Notizen unter {VAULT} gefunden")
    return notes


def body(txt):
    """Notiztext ohne YAML-Frontmatter - dort stehen Links nur als Metadaten."""
    if txt.startswith("---"):
        end = txt.find("\n---", 3)
        if end >= 0:
            return txt[end + 4:]
    return txt


def build(notes):
    bodies = {k: body(t) for k, t in notes.items()}
    informatik = {k for k, b in bodies.items() if "[[Informatik]]" in b}
    # Buchnotizen legt das Book-Search-Plugin an; totalPage haben nur sie.
    books = {k for k in informatik
             if notes[k].startswith("---") and "totalPage" in notes[k]}
    concepts = informatik - books

    def targets(key):
        return {t.strip() for t in LINK.findall(bodies[key])} - HUBS - {key}

    bridges = {k for k in books if targets(k) & concepts}
    nodes = concepts | bridges

    edges = sorted({(k, t) for k in nodes for t in targets(k) if t in nodes})

    unresolved = sorted({t for k in nodes for t in targets(k)
                         if t not in notes and not ATTACHMENT.search(t)})
    if unresolved:
        print(f"unaufgeloeste Linkziele (nicht im Graphen): {unresolved}",
              file=sys.stderr)

    dropped = sorted(k for k in books - bridges if targets(k) - set(notes) or
                     targets(k) & set(notes))
    if dropped:
        print(f"Buchnotizen mit Links, aber ohne Themenbezug: {dropped}",
              file=sys.stderr)

    label = {k: LABELS.get(k, k) for k in nodes}
    for a, b in ((a, b) for a in nodes for b in nodes
                 if a < b and label[a] == label[b]):
        print(f"Anzeigename '{label[a]}' doppelt: {a} / {b} - nutze Dateinamen",
              file=sys.stderr)
        label[a], label[b] = a, b

    return nodes, edges, label, bridges


def components(nodes, edges):
    adj = {k: set() for k in nodes}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    seen, out = set(), []
    for start in sorted(nodes):
        if start in seen:
            continue
        stack, group = [start], set()
        while stack:
            n = stack.pop()
            if n in group:
                continue
            group.add(n)
            stack.extend(adj[n] - group)
        seen |= group
        out.append(group)
    return sorted(out, key=len, reverse=True)


def render_list(data):
    """Textfassung des Graphen - Fallback ohne JavaScript und zugleich die
    Bedienoberflaeche fuer Tastatur und Screenreader."""
    by_id = {n["id"]: n for n in data["nodes"]}
    items = []
    for n in sorted(data["nodes"], key=lambda n: (-len(n["out"]) - len(n["in"]), n["label"])):
        # Wechselseitige Verweise stehen in beiden Richtungen, in der Textfassung
        # gibt es aber nur eine Nachbarschaft: dict.fromkeys haelt die Reihenfolge.
        refs = [f'<a href="#z-{by_id[t]["slug"]}">{html.escape(by_id[t]["label"])}</a>'
                for t in dict.fromkeys(n["out"] + n["in"])]
        kind = "Buch" if n["kind"] == "buch" else "Thema"
        items.append(
            f'''            <li class="zettel" id="z-{n["slug"]}">
              <button class="zettel__name" type="button" data-node="{html.escape(n["id"], quote=True)}">
                {html.escape(n["label"])}
              </button>
              <span class="zettel__kind">{kind}</span>
              <span class="zettel__refs">{" · ".join(refs) or "keine Verweise"}</span>
            </li>''')
    return "\n".join(items)




def collect():
    """Graphdaten aus dem Vault. Meldet auf stderr, was ausgelassen wurde."""
    notes = read_vault()
    nodes, edges, label, bridges = build(notes)

    out_links = {k: [] for k in nodes}
    in_links = {k: [] for k in nodes}
    for a, b in edges:
        out_links[a].append(b)
        in_links[b].append(a)

    slugs = {}
    for k in nodes:
        slugs.setdefault(slug(k), []).append(k)
    for s, keys in sorted(slugs.items()):
        if len(keys) > 1:
            print(f"Slug '{s}' doppelt: {keys} - Sprungmarken kollidieren",
                  file=sys.stderr)

    data = {"nodes": [{
        "id": k,
        "label": label[k],
        "slug": slug(k),
        "kind": "buch" if k in bridges else "thema",
        "out": sorted(out_links[k], key=lambda t: label[t]),
        "in": sorted(in_links[k], key=lambda t: label[t]),
    } for k in sorted(nodes, key=lambda k: label[k])]}
    return data, edges, components(nodes, edges)


def slug(name):
    s = (name.lower().replace("ä", "ae").replace("ö", "oe")
         .replace("ü", "ue").replace("ß", "ss"))
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-')


def section():
    """Der Graph-Kasten als HTML-Abschnitt, fertig zum Einsetzen in die Seite."""
    data, _edges, _groups = collect()

    # Die Daten stehen inline im Dokument, nicht in einer eigenen Datei: so
    # funktioniert der Graph auch, wenn die Seite über file:// geöffnet wird.
    return f'''      <section class="graph-block">
        <h2>Themengraph</h2>

        <div class="graph" hidden>
          <div class="graph__stage">
            <canvas class="graph__canvas" role="img"
                    aria-label="Interaktiver Graph der Informatik-Notizen. Derselbe Inhalt steht darunter als Liste."></canvas>
            <div class="graph__legend">
              <span class="graph__key graph__key--thema">Thema</span>
              <span class="graph__key graph__key--buch">Buch</span>
            </div>
            <button class="graph__reset" type="button">Ansicht zurücksetzen</button>
            <p class="graph__usage">Knoten ziehen · Fläche schieben · Strg + Scrollen zoomt</p>
            <aside class="graph__panel" aria-live="polite" hidden></aside>
          </div>
        </div>

        <details class="zettel-fallback">
          <summary>Alle {len(data["nodes"])} Notizen als Liste</summary>
          <ol class="zettel-list">
{render_list(data)}
          </ol>
        </details>

        <script id="graph-data" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>
      </section>'''


if __name__ == "__main__":
    _data, _edges, _groups = collect()
    print(f"{len(_data['nodes'])} Knoten, {len(_edges)} Kanten, "
          f"{len(_groups)} Komponenten, größte {len(_groups[0])}")
