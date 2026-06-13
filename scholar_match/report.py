"""Render matches into a single self-contained HTML file you open in a browser.

Reads matches_explained.json if present (richer), else matches.json. The data
is embedded directly in the HTML, so the file works offline with no server.

Two views: a searchable list, and a force-directed network graph (vanilla JS /
SVG, no external libraries — runs offline).
"""

from __future__ import annotations

import json

from . import config

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>scholar-match · UW-Madison AI/stats</title>
<style>
  :root {{ --bg:#0f1115; --card:#1a1d24; --line:#2a2e38; --txt:#e7e9ee;
           --muted:#9aa3b2; --accent:#c5050c; --bar:#3b82f6; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
          background:var(--bg); color:var(--txt); }}
  header {{ padding:24px 20px 8px; border-bottom:1px solid var(--line); }}
  h1 {{ margin:0 0 4px; font-size:22px; }}
  .sub {{ color:var(--muted); font-size:13px; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:16px 20px 60px; }}
  .tabs {{ display:flex; gap:8px; margin:16px 0 0; }}
  .tab {{ padding:7px 14px; border-radius:8px; border:1px solid var(--line);
          background:var(--card); color:var(--muted); cursor:pointer; }}
  .tab.active {{ color:var(--txt); border-color:var(--bar); }}
  #q {{ width:100%; padding:10px 12px; margin:16px 0; border-radius:8px;
        border:1px solid var(--line); background:var(--card); color:var(--txt); }}
  .author {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
             padding:16px; margin:14px 0; }}
  .author > h2 {{ margin:0 0 2px; font-size:18px; }}
  .chips {{ display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 12px; }}
  .chip {{ font-size:12px; background:#23272f; border:1px solid var(--line);
           padding:2px 8px; border-radius:999px; color:var(--muted); }}
  .match {{ border-top:1px solid var(--line); padding:12px 0; }}
  .match:last-child {{ padding-bottom:0; }}
  .mhead {{ display:flex; align-items:center; gap:10px; }}
  .mname {{ font-weight:600; }}
  .barwrap {{ flex:1; height:6px; background:#23272f; border-radius:3px; overflow:hidden; }}
  .bar {{ height:100%; background:var(--bar); }}
  .score {{ font-variant-numeric:tabular-nums; color:var(--muted); font-size:13px;
            min-width:42px; text-align:right; }}
  .exp {{ margin:8px 0 0; font-size:14px; }}
  .exp .lbl {{ color:var(--muted); }}
  a {{ color:#8ab4ff; text-decoration:none; }}
  .empty {{ color:var(--muted); font-style:italic; }}
  #graphwrap {{ display:none; }}
  #graph {{ width:100%; height:620px; background:var(--card);
            border:1px solid var(--line); border-radius:12px; touch-action:none; }}
  #graph text {{ fill:var(--txt); font-size:11px; pointer-events:none; }}
  #graph line {{ stroke:var(--line); }}
  #graph circle {{ cursor:grab; }}
  .ghint {{ color:var(--muted); font-size:12px; margin:8px 2px; }}
</style>
</head>
<body>
<header>
  <div class="wrap" style="padding-bottom:0;">
    <h1>scholar-match</h1>
    <div class="sub">UW-Madison · AI / ML / statistics · {n} scholars matched</div>
    <div class="tabs">
      <div class="tab active" id="tab-list">List</div>
      <div class="tab" id="tab-graph">Graph</div>
    </div>
  </div>
</header>
<div class="wrap">
  <div id="listwrap">
    <input id="q" placeholder="Filter by name or research area…" autocomplete="off">
    <div id="list"></div>
  </div>
  <div id="graphwrap">
    <div class="ghint">Drag nodes to rearrange · node size = number of AI papers ·
      edge = a top match (thicker = closer) · click a node to open OpenAlex.</div>
    <svg id="graph" viewBox="0 0 960 620" preserveAspectRatio="xMidYMid meet"></svg>
  </div>
</div>
<script>
const DATA = {data};

function esc(s) {{
  return String(s).replace(/[&<>"]/g, c =>
    ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
}}
function authorLink(id, name) {{
  return id ? `<a href="${{esc(id)}}" target="_blank" rel="noopener">${{esc(name)}}</a>`
            : esc(name);
}}

/* ---------- List view ---------- */
function matchHTML(m) {{
  const pct = Math.max(0, Math.min(100, Math.round((m.similarity || 0) * 100)));
  let exp = '';
  if (m.explanation) {{
    const e = m.explanation;
    const themes = (e.shared_themes || []).map(esc).join(', ');
    exp = `<div class="exp">
      ${{themes ? `<span class="lbl">Shared:</span> ${{themes}}<br>` : ''}}
      ${{e.summary ? `${{esc(e.summary)}}<br>` : ''}}
      ${{e.collaboration_idea ? `<span class="lbl">Idea:</span> ${{esc(e.collaboration_idea)}}` : ''}}
    </div>`;
  }}
  return `<div class="match">
    <div class="mhead">
      <span class="mname">${{authorLink(m.author_id, m.name)}}</span>
      <span class="barwrap"><span class="bar" style="width:${{pct}}%"></span></span>
      <span class="score">${{(m.similarity ?? 0).toFixed(2)}}</span>
    </div>${{exp}}
  </div>`;
}}
function authorHTML(a) {{
  const chips = (a.top_concepts || []).map(c => `<span class="chip">${{esc(c)}}</span>`).join('');
  const matches = (a.matches || []).map(matchHTML).join('') ||
    '<div class="empty">No matches.</div>';
  return `<div class="author"><h2>${{authorLink(a.author_id, a.name)}}</h2>
    <div class="chips">${{chips}}</div>${{matches}}</div>`;
}}
const listEl = document.getElementById('list');
const q = document.getElementById('q');
function renderList(filter) {{
  const f = (filter || '').toLowerCase();
  const rows = DATA.filter(a => !f ||
    (a.name + ' ' + (a.top_concepts || []).join(' ')).toLowerCase().includes(f));
  listEl.innerHTML = rows.map(authorHTML).join('') ||
    '<div class="empty">Nothing matches that filter.</div>';
}}
q.addEventListener('input', () => renderList(q.value));
renderList('');

/* ---------- Graph view (vanilla force-directed SVG) ---------- */
const W = 960, H = 620;
const svg = document.getElementById('graph');
const SVGNS = 'http://www.w3.org/2000/svg';
let graphBuilt = false;

function hue(s) {{ let h = 0; for (const c of (s || '')) h = (h * 31 + c.charCodeAt(0)) % 360; return h; }}

function buildGraph() {{
  const nodes = DATA.map(a => ({{
    id: a.author_id, name: a.name, n: a.n_works || 1,
    c: (a.top_concepts || [])[0] || '',
    x: W / 2 + (Math.random() - 0.5) * 200,
    y: H / 2 + (Math.random() - 0.5) * 200, vx: 0, vy: 0, fixed: false,
  }}));
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  const seen = new Set(), edges = [];
  for (const a of DATA) for (const m of (a.matches || [])) {{
    if (!idx.has(m.author_id) || !idx.has(a.author_id)) continue;
    const key = [a.author_id, m.author_id].sort().join('|');
    if (seen.has(key)) continue; seen.add(key);
    edges.push({{ s: idx.get(a.author_id), t: idx.get(m.author_id), w: m.similarity || 0 }});
  }}

  const lineEls = edges.map(e => {{
    const ln = document.createElementNS(SVGNS, 'line');
    ln.setAttribute('stroke-width', (0.5 + 3 * e.w).toFixed(2));
    ln.setAttribute('stroke-opacity', (0.25 + 0.5 * e.w).toFixed(2));
    svg.appendChild(ln); return ln;
  }});
  const groupEls = nodes.map(nd => {{
    const g = document.createElementNS(SVGNS, 'g');
    const r = 5 + Math.sqrt(nd.n) * 2;
    const ci = document.createElementNS(SVGNS, 'circle');
    ci.setAttribute('r', r);
    ci.setAttribute('fill', `hsl(${{hue(nd.c)}},60%,55%)`);
    ci.setAttribute('stroke', '#0f1115'); ci.setAttribute('stroke-width', '1.5');
    const tx = document.createElementNS(SVGNS, 'text');
    tx.setAttribute('x', r + 3); tx.setAttribute('y', 4); tx.textContent = nd.name;
    const title = document.createElementNS(SVGNS, 'title');
    title.textContent = `${{nd.name}} · ${{nd.n}} papers · ${{nd.c}}`;
    g.appendChild(ci); g.appendChild(tx); g.appendChild(title);
    g.style.cursor = 'grab';
    svg.appendChild(g);
    g.addEventListener('mousedown', ev => startDrag(ev, nd));
    g.addEventListener('click', () => {{ if (nd.id) window.open(nd.id, '_blank'); }});
    return g;
  }});

  // Force simulation
  let alpha = 1;
  function tick() {{
    for (let i = 0; i < nodes.length; i++) {{
      for (let j = i + 1; j < nodes.length; j++) {{
        const a = nodes[i], b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy || 0.01;
        const rep = 2200 / d2, d = Math.sqrt(d2);
        const fx = (dx / d) * rep, fy = (dy / d) * rep;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      }}
    }}
    for (const e of edges) {{
      const a = nodes[e.s], b = nodes[e.t];
      let dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const k = (d - 90) * 0.02 * (0.4 + e.w);
      const fx = (dx / d) * k, fy = (dy / d) * k;
      a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
    }}
    for (const nd of nodes) {{
      nd.vx += (W / 2 - nd.x) * 0.002;   // gravity to center
      nd.vy += (H / 2 - nd.y) * 0.002;
      if (!nd.fixed) {{
        nd.x += nd.vx * alpha; nd.y += nd.vy * alpha;
        nd.x = Math.max(20, Math.min(W - 20, nd.x));
        nd.y = Math.max(20, Math.min(H - 20, nd.y));
      }}
      nd.vx *= 0.85; nd.vy *= 0.85;
    }}
    edges.forEach((e, i) => {{
      const a = nodes[e.s], b = nodes[e.t];
      lineEls[i].setAttribute('x1', a.x); lineEls[i].setAttribute('y1', a.y);
      lineEls[i].setAttribute('x2', b.x); lineEls[i].setAttribute('y2', b.y);
    }});
    groupEls.forEach((g, i) =>
      g.setAttribute('transform', `translate(${{nodes[i].x}},${{nodes[i].y}})`));
    alpha *= 0.985;
    if (alpha > 0.02) requestAnimationFrame(tick);
  }}
  tick();

  // Drag
  let dragNode = null;
  function pt(ev) {{
    const r = svg.getBoundingClientRect();
    return {{ x: (ev.clientX - r.left) / r.width * W, y: (ev.clientY - r.top) / r.height * H }};
  }}
  function startDrag(ev, nd) {{ ev.preventDefault(); dragNode = nd; nd.fixed = true; alpha = Math.max(alpha, 0.3); tick(); }}
  window.addEventListener('mousemove', ev => {{
    if (!dragNode) return;
    const p = pt(ev); dragNode.x = p.x; dragNode.y = p.y; dragNode.vx = dragNode.vy = 0;
  }});
  window.addEventListener('mouseup', () => {{ if (dragNode) {{ dragNode.fixed = false; dragNode = null; }} }});
  graphBuilt = true;
}}

/* ---------- Tabs ---------- */
const tabList = document.getElementById('tab-list'), tabGraph = document.getElementById('tab-graph');
const listWrap = document.getElementById('listwrap'), graphWrap = document.getElementById('graphwrap');
tabList.onclick = () => {{
  tabList.classList.add('active'); tabGraph.classList.remove('active');
  listWrap.style.display = ''; graphWrap.style.display = 'none';
}};
tabGraph.onclick = () => {{
  tabGraph.classList.add('active'); tabList.classList.remove('active');
  listWrap.style.display = 'none'; graphWrap.style.display = '';
  if (!graphBuilt) buildGraph();
}};
</script>
</body>
</html>
"""


def build_report(path=config.DATA_DIR / "report.html") -> str:
    """Generate report.html from the best available matches file."""
    if config.EXPLAINED_PATH.exists():
        records = json.loads(config.EXPLAINED_PATH.read_text())
    elif config.MATCHES_PATH.exists():
        records = json.loads(config.MATCHES_PATH.read_text())
    else:
        raise FileNotFoundError(
            "No matches found. Run `match` (and optionally `explain`) first."
        )

    html = _TEMPLATE.format(
        n=len(records),
        data=json.dumps(records, ensure_ascii=False),
    )
    path.write_text(html)
    print(f"Wrote report ({len(records)} scholars) -> {path}")
    print(f"Open it with:  open {path}")
    return str(path)
