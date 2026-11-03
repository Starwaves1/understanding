// Grid-placed boxes with arrows. Layout is recomputed on every node/edge so the
// diagram grows smoothly as ops stream in.
U.css(`
.diagram { position: relative; }
.diagram svg.edges { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; color: #6f6a60; }
.diagram svg.edges path { fill: none; stroke: currentColor; stroke-width: 1.8; stroke-dasharray: 1; animation: draw .45s ease-out both; }
.diagram .elabel { position: absolute; transform: translate(-50%, -50%); font-size: 11.5px; color: var(--muted);
  background: var(--paper); padding: 0 4px; white-space: nowrap; animation: fade .4s both; }
.dnode { position: absolute; transform: translate(-50%, -50%); text-align: center; animation: pop .35s ease-out both; }
.dnode .sub { font-size: 11px; color: var(--muted); margin-bottom: 3px; white-space: nowrap; }
.dnode .box { display: inline-block; min-width: 54px; max-width: 150px; padding: 8px 12px; border-radius: 8px;
  border: 1.8px solid var(--tone); background: var(--tone-bg); font-family: var(--hand); font-size: 16px; font-weight: 700;
  line-height: 1.15; color: var(--ink); }
`);

(() => {
  const ROW_H = 84, PAD_TOP = 44;

  function get(U, id) {
    U.state.diagrams ||= {};
    id = id || U.state.lastDiagram || "d";
    if (!U.state.diagrams[id]) {
      const el = U.el("div", "diagram", U.card());
      const edges = U.svg("svg", { class: "edges" }, el);
      edges.innerHTML = `<defs><marker id="ah-${id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor" style="animation:none;stroke:none"/></marker></defs>`;
      U.state.diagrams[id] = { id, el, edgesSvg: edges, nodes: {}, edges: [] };
    }
    U.state.lastDiagram = id;
    return U.state.diagrams[id];
  }

  function layout(D) {
    const nodes = Object.values(D.nodes);
    const cols = Math.max(1, ...nodes.map((n) => n.col + 1));
    const rows = Math.max(1, ...nodes.map((n) => n.row + 1));
    const w = D.el.clientWidth || 390;
    D.el.style.height = `${rows * ROW_H + 8}px`;
    for (const n of nodes) {
      n.cx = ((n.col + 0.5) * w) / cols;
      n.cy = n.row * ROW_H + PAD_TOP;
      n.el.style.left = `${n.cx}px`;
      n.el.style.top = `${n.cy}px`;
    }
    for (const e of D.edges) route(D, e);
  }

  // Anchor on the box edge facing the other node.
  function anchor(n, toward) {
    const r = n.el.querySelector(".box");
    const hw = r.offsetWidth / 2 + 3, hh = r.offsetHeight / 2 + 3;
    const boxCy = n.cy + (n.el.offsetHeight - r.offsetHeight) / 2;
    const dx = toward.cx - n.cx, dy = toward.cy - n.cy;
    if (Math.abs(dx) * hh >= Math.abs(dy) * hw) return [n.cx + Math.sign(dx) * hw, boxCy];
    return [n.cx, boxCy + Math.sign(dy) * hh];
  }

  function route(D, e) {
    const a = D.nodes[e.from], b = D.nodes[e.to];
    if (!a || !b) return;
    const [x1, y1] = anchor(a, b), [x2, y2] = anchor(b, a);
    const horiz = Math.abs(x2 - x1) > Math.abs(y2 - y1);
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
    const d = horiz ? `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}` : `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
    e.path.setAttribute("d", d);
    if (e.label) {
      // Beside the line, not on it: above horizontal edges, right of vertical ones.
      e.label.style.left = `${horiz ? mx : mx + 6}px`;
      e.label.style.top = `${horiz ? my - 10 : my}px`;
      e.label.style.transform = horiz ? "translate(-50%, -50%)" : "translate(0, -50%)";
    }
  }

  U.register("diagram", (op, U) => get(U, op.id));

  U.register("node", (op, U) => {
    const D = get(U, op.d);
    const old = D.nodes[op.id];
    if (old) old.el.remove();
    const el = U.el("div", `dnode tone-${op.tone || "blue"}`, D.el);
    if (op.sub) U.el("div", "sub", el, op.sub);
    U.el("div", "box", el, op.label ?? op.id);
    D.nodes[op.id] = { el, col: +op.col || 0, row: +op.row || 0 };
    layout(D);
  });

  U.register("edge", (op, U) => {
    const D = get(U, op.d);
    const path = U.svg("path", { "marker-end": `url(#ah-${D.id})`, pathLength: 1 }, D.edgesSvg);
    const e = { from: op.from, to: op.to, path };
    if (op.label) e.label = U.el("div", "elabel", D.el, op.label);
    D.edges.push(e);
    layout(D);
  });
})();
