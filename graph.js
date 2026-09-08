/* Kraftgerichteter Graph der Zettelkasten-Notizen.
 *
 * Bewusst ohne Bibliothek: bei rund 50 Knoten kostet die naive O(n^2)-Abstossung
 * weniger als das Laden von d3, und die Seite bleibt abhaengigkeitsfrei. Das
 * Markup funktioniert ohne dieses Skript - die Liste unter dem Graphen traegt
 * denselben Inhalt, deshalb ist <section class="graph"> im HTML hidden und wird
 * erst hier eingeblendet.
 */
(function () {
  'use strict';

  var raw = document.getElementById('graph-data');
  var stage = document.querySelector('.graph');
  var canvas = document.querySelector('.graph__canvas');
  if (!raw || !stage || !canvas || !canvas.getContext) return;

  var ctx = canvas.getContext('2d');
  var panel = document.querySelector('.graph__panel');
  var data;
  try {
    data = JSON.parse(raw.textContent);
  } catch (err) {
    console.error('Graphdaten unlesbar:', err);
    return;
  }
  if (!data.nodes || !data.nodes.length) return;

  var REPULSION = 5200;   // Ladung je Knotenpaar
  var SPRING = 0.035;     // Federhaerte der Kanten
  var REST = 78;          // Ruhelaenge einer Kante in Weltkoordinaten
  var GRAVITY = 0.012;    // Zug zur Mitte, haelt Komponenten beisammen
  var DAMPING = 0.86;
  var MIN_D2 = 100;       // Abstossung unterhalb 10px deckeln
  var VMAX = 25;          // Schrittweite je Tick begrenzen
  var BOUND = 300;        // weiche Wand: dahinter zieht es scharf nach innen
  var WALL = 0.12;
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)');

  var byId = {};
  var nodes = data.nodes.map(function (n, i) {
    // Deterministische Spirale mit goldenem Winkel: gleiche Daten, gleiches
    // Layout bei jedem Aufruf, und keine zwei Knoten starten aufeinander.
    var a = i * 2.399;
    var rad = 40 + 150 * Math.sqrt(i / data.nodes.length);
    var node = {
      id: n.id, label: n.label, slug: n.slug, kind: n.kind,
      out: n.out, into: n['in'],
      degree: n.out.length + n['in'].length,
      x: Math.cos(a) * rad,
      y: Math.sin(a) * rad,
      vx: 0, vy: 0, fixed: false
    };
    node.r = 5 + 2.3 * Math.sqrt(node.degree);
    byId[node.id] = node;
    return node;
  });

  var links = [];
  nodes.forEach(function (n) {
    n.out.forEach(function (t) {
      if (byId[t]) links.push({ source: n, target: byId[t] });
    });
  });

  var neighbours = {};
  nodes.forEach(function (n) { neighbours[n.id] = {}; });
  links.forEach(function (l) {
    neighbours[l.source.id][l.target.id] = true;
    neighbours[l.target.id][l.source.id] = true;
  });

  var view = { scale: 1, x: 0, y: 0 };
  var width = 0, height = 0;
  var alpha = 1, running = false;
  var selected = null, hovered = null, dragging = null, panning = null;
  var refit = true;       // nach Aufbau und Reset einmal automatisch rahmen

  function theme() {
    var s = getComputedStyle(document.body);
    return {
      accent: s.getPropertyValue('--accent').trim() || '#2f6f5e',
      text: s.getPropertyValue('--text').trim() || '#17181c',
      muted: s.getPropertyValue('--text-muted').trim() || '#5c6070',
      border: s.getPropertyValue('--border').trim() || '#e2e2dc',
      surface: s.getPropertyValue('--bg-elevated').trim() || '#ffffff',
      font: s.getPropertyValue('--font').trim() || 'system-ui, sans-serif'
    };
  }
  var colors = theme();

  function resize() {
    var box = canvas.getBoundingClientRect();
    if (!box.width || !box.height) return;
    var dpr = window.devicePixelRatio || 1;
    width = box.width;
    height = box.height;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (!selected && !running) fit();
    draw();
  }

  function tick() {
    var i, j, a, b, dx, dy, d2, d, f;

    for (i = 0; i < nodes.length; i++) {
      for (j = i + 1; j < nodes.length; j++) {
        a = nodes[i];
        b = nodes[j];
        dx = b.x - a.x;
        dy = b.y - a.y;
        // Ohne Untergrenze wird REPULSION/d2 bei fast deckungsgleichen Knoten
        // beliebig gross und schleudert sie aus dem Bild.
        d2 = Math.max(dx * dx + dy * dy, MIN_D2);
        d = Math.sqrt(d2);
        // Nahfeld zusaetzlich haerten, sonst ueberdecken sich die Beschriftungen.
        f = (REPULSION / d2 + Math.max(0, a.r + b.r + 16 - d) * 0.6) * alpha / d;
        a.vx -= dx * f; a.vy -= dy * f;
        b.vx += dx * f; b.vy += dy * f;
      }
    }

    for (i = 0; i < links.length; i++) {
      a = links[i].source;
      b = links[i].target;
      dx = b.x - a.x;
      dy = b.y - a.y;
      d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      f = (d - REST) * SPRING * alpha / d;
      a.vx += dx * f; a.vy += dy * f;
      b.vx -= dx * f; b.vy -= dy * f;
    }

    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      if (a.fixed) { a.vx = a.vy = 0; continue; }
      a.vx -= a.x * GRAVITY * alpha;
      a.vy -= a.y * GRAVITY * alpha;
      // Knoten ohne Kanten spueren nur Abstossung und Schwerkraft und kaemen
      // sonst auf einem weiten Ring zur Ruhe. Die Wand haelt sie am Rand.
      var rad = Math.sqrt(a.x * a.x + a.y * a.y);
      if (rad > BOUND) {
        f = (rad - BOUND) * WALL * alpha / rad;
        a.vx -= a.x * f;
        a.vy -= a.y * f;
      }
      a.vx *= DAMPING;
      a.vy *= DAMPING;
      var speed = Math.sqrt(a.vx * a.vx + a.vy * a.vy);
      if (speed > VMAX) { a.vx *= VMAX / speed; a.vy *= VMAX / speed; }
      a.x += a.vx;
      a.y += a.vy;
    }
  }

  function fit() {
    if (!width || !nodes.length) return;
    var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    nodes.forEach(function (n) {
      x0 = Math.min(x0, n.x); x1 = Math.max(x1, n.x);
      y0 = Math.min(y0, n.y); y1 = Math.max(y1, n.y);
    });
    // Rand fuer Knotenradius und die Beschriftung darunter.
    var pad = 46;
    view.scale = Math.max(0.4, Math.min(1.4,
      Math.min((width - pad * 2) / Math.max(x1 - x0, 1),
               (height - pad * 2) / Math.max(y1 - y0, 1))));
    view.x = -(x0 + x1) / 2 * view.scale;
    view.y = -(y0 + y1) / 2 * view.scale;
  }

  function toScreen(n) {
    return {
      x: n.x * view.scale + view.x + width / 2,
      y: n.y * view.scale + view.y + height / 2
    };
  }

  function toWorld(px, py) {
    return {
      x: (px - width / 2 - view.x) / view.scale,
      y: (py - height / 2 - view.y) / view.scale
    };
  }

  function draw() {
    if (!width) return;
    var focus = hovered || selected;
    ctx.clearRect(0, 0, width, height);

    links.forEach(function (l) {
      var lit = focus && (l.source === focus || l.target === focus);
      var s = toScreen(l.source), t = toScreen(l.target);
      ctx.strokeStyle = lit ? colors.accent : colors.border;
      ctx.globalAlpha = focus ? (lit ? 0.95 : 0.25) : 0.8;
      ctx.lineWidth = lit ? 1.8 : 1;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    });

    nodes.forEach(function (n) {
      var lit = !focus || n === focus || neighbours[focus.id][n.id];
      var p = toScreen(n);
      var r = n.r * Math.max(0.7, Math.min(view.scale, 1.6));
      ctx.globalAlpha = lit ? 1 : 0.28;

      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      // Buecher hohl, Themen gefuellt - dieselbe Unterscheidung wie in der Legende.
      if (n.kind === 'buch') {
        ctx.fillStyle = colors.surface;
        ctx.fill();
        ctx.strokeStyle = colors.accent;
        ctx.lineWidth = 2;
        ctx.stroke();
      } else {
        ctx.fillStyle = n === selected ? colors.accent : colors.muted;
        ctx.fill();
      }
      if (n === selected) {
        ctx.strokeStyle = colors.accent;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 4, 0, Math.PI * 2);
        ctx.stroke();
      }

      var size = Math.max(10, Math.min(12 * view.scale, 15));
      ctx.font = (n === focus ? '600 ' : '') + size + 'px ' + colors.font;
      ctx.fillStyle = n === focus ? colors.text : colors.muted;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(n.label, p.x, p.y + r + 4);
    });
    ctx.globalAlpha = 1;
  }

  function run() {
    if (running) return;
    running = true;
    if (calm.matches) {
      // Ohne Animation: bis zur Ruhelage rechnen und einmal zeichnen.
      while (alpha > 0.02) { tick(); alpha *= 0.94; }
      running = false;
      if (refit) { fit(); refit = false; }
      draw();
      return;
    }
    (function frame() {
      tick();
      alpha *= 0.985;
      if (alpha > 0.02 || dragging) { draw(); requestAnimationFrame(frame); }
      else { running = false; if (refit) { fit(); refit = false; } draw(); }
    }());
  }

  function reheat(to) {
    alpha = Math.max(alpha, to || 0.35);
    run();
  }

  function nodeAt(px, py) {
    var w = toWorld(px, py), hit = null, best = Infinity;
    nodes.forEach(function (n) {
      var dx = n.x - w.x, dy = n.y - w.y, d = Math.sqrt(dx * dx + dy * dy);
      var reach = Math.max(n.r + 6, 14 / view.scale);
      if (d < reach && d < best) { best = d; hit = n; }
    });
    return hit;
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderPanel(n) {
    if (!n) {
      panel.hidden = true;
      panel.innerHTML = '';
      return;
    }
    panel.hidden = false;
    function list(ids) {
      if (!ids.length) return '<span class="graph__none">—</span>';
      return ids.map(function (id) {
        return '<button type="button" class="graph__ref" data-node="' +
          esc(byId[id].id) + '">' + esc(byId[id].label) + '</button>';
      }).join('');
    }
    panel.innerHTML =
      '<h3 class="graph__title">' + esc(n.label) + '</h3>' +
      '<p class="graph__kind">' + (n.kind === 'buch' ? 'Buchnotiz' : 'Themennotiz') +
      ' · ' + n.degree + (n.degree === 1 ? ' Verweis' : ' Verweise') + '</p>' +
      '<h4 class="graph__sub">Verweist auf</h4><p class="graph__refs">' + list(n.out) + '</p>' +
      '<h4 class="graph__sub">Referenziert von</h4><p class="graph__refs">' + list(n.into) + '</p>';
  }

  function select(n) {
    selected = n;
    renderPanel(n);
    document.querySelectorAll('.zettel').forEach(function (li) {
      li.classList.toggle('zettel--on', !!n && li.id === 'z-' + n.slug);
    });
    draw();
  }

  canvas.addEventListener('pointerdown', function (ev) {
    var box = canvas.getBoundingClientRect();
    var px = ev.clientX - box.left, py = ev.clientY - box.top;
    var hit = nodeAt(px, py);
    canvas.setPointerCapture(ev.pointerId);
    if (hit) {
      dragging = hit;
      hit.fixed = true;
      select(hit);
      reheat(0.3);
    } else {
      panning = { x: px - view.x, y: py - view.y, fromX: px, fromY: py };
    }
  });

  canvas.addEventListener('pointermove', function (ev) {
    var box = canvas.getBoundingClientRect();
    var px = ev.clientX - box.left, py = ev.clientY - box.top;
    if (dragging) {
      var w = toWorld(px, py);
      dragging.x = w.x;
      dragging.y = w.y;
      if (calm.matches) {
        // alpha ist hier laengst abgeklungen; ohne Anhebung bliebe der Rest
        // des Graphen beim Ziehen regungslos.
        var rest = alpha;
        alpha = 0.25;
        tick();
        alpha = rest;
        draw();
      }
      return;
    }
    if (panning) {
      view.x = px - panning.x;
      view.y = py - panning.y;
      draw();
      return;
    }
    var hit = nodeAt(px, py);
    canvas.style.cursor = hit ? 'pointer' : 'grab';
    if (hit !== hovered) { hovered = hit; draw(); }
  });

  function endPointer(ev) {
    if (dragging) { dragging.fixed = false; dragging = null; reheat(0.2); }
    if (panning && ev && ev.clientX !== undefined) {
      var box = canvas.getBoundingClientRect();
      var moved = Math.abs(ev.clientX - box.left - panning.fromX) +
                  Math.abs(ev.clientY - box.top - panning.fromY);
      // Tippen statt Schieben: die Auswahl aufheben und die Karte schliessen.
      if (moved < 5) select(null);
    }
    panning = null;
  }
  canvas.addEventListener('pointerup', endPointer);
  canvas.addEventListener('pointercancel', endPointer);
  canvas.addEventListener('pointerleave', function () {
    if (hovered) { hovered = null; draw(); }
  });

  canvas.addEventListener('wheel', function (ev) {
    // Ohne Modifier scrollt die Seite weiter - der Graph steht mitten im
    // Textfluss und darf das Rad nicht fuer sich beanspruchen.
    if (!ev.ctrlKey && !ev.metaKey) return;
    ev.preventDefault();
    var box = canvas.getBoundingClientRect();
    var px = ev.clientX - box.left, py = ev.clientY - box.top;
    var before = toWorld(px, py);
    view.scale = Math.min(3, Math.max(0.4, view.scale * (ev.deltaY < 0 ? 1.12 : 0.89)));
    var after = toWorld(px, py);
    // Punkt unter dem Zeiger festhalten, sonst wandert die Ansicht beim Zoomen.
    view.x += (after.x - before.x) * view.scale;
    view.y += (after.y - before.y) * view.scale;
    draw();
  }, { passive: false });

  document.querySelector('.graph__reset').addEventListener('click', function () {
    nodes.forEach(function (n) { n.fixed = false; });
    select(null);
    refit = true;
    reheat(0.6);
  });

  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-node]');
    if (!btn) return;
    var n = byId[btn.getAttribute('data-node')];
    if (!n) return;
    ev.preventDefault();
    select(n);
    // Gewaehlten Knoten in die Mitte holen, er kann weit ausserhalb liegen.
    view.x = -n.x * view.scale;
    view.y = -n.y * view.scale;
    draw();
    stage.scrollIntoView({ behavior: calm.matches ? 'auto' : 'smooth', block: 'center' });
  });

  if (window.ResizeObserver) new ResizeObserver(resize).observe(canvas);
  else window.addEventListener('resize', resize);
  if (window.matchMedia) {
    var dark = window.matchMedia('(prefers-color-scheme: dark)');
    var repaint = function () { colors = theme(); draw(); };
    if (dark.addEventListener) dark.addEventListener('change', repaint);
  }

  stage.hidden = false;
  resize();
  run();
}());
