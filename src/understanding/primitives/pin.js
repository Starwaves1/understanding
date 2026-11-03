U.css(`
.pin-label { position: fixed; padding: 5px 12px 5px 10px; border-radius: 7px; background: #fff;
  border-left: 4px solid var(--tone, var(--green)); box-shadow: 0 6px 20px rgba(0,0,0,.28);
  font-family: var(--hand); font-size: 16px; font-weight: 700; color: var(--ink); white-space: nowrap;
  animation: pop .35s ease-out .25s both; }
.pin-line { stroke: #1d1d1b; stroke-width: 2; stroke-dasharray: 1; animation: draw .3s ease-out both; }
.pin-dot { fill: #fff; stroke: #1d1d1b; stroke-width: 2.5; animation: fade .2s both; }
`);
U.register("pin", (op, U) => {
  const x = U.sx(+op.x), y = U.sy(+op.y);
  const dx = op.dx != null ? U.sx(+op.dx) : 70, dy = op.dy != null ? U.sy(+op.dy) : -60;
  const label = U.el("div", `pin-label tone-${op.tone || "green"}`, U.screenLayer(), op.text);
  U.mark({ x: x - 8, y: y - 8, w: 16, h: 16 });
  const w = label.offsetWidth, h = label.offsetHeight;
  const { x: lx, y: ly } = U.placeLabel(x, y, w, h, dx, dy);
  label.style.left = `${lx}px`;
  label.style.top = `${ly}px`;
  // Leader line ends at the label edge nearest the point.
  const ex = Math.min(Math.max(x, lx), lx + w), ey = Math.min(Math.max(y, ly), ly + h);
  const svg = U.screenSvg();
  U.svg("line", { class: "pin-line", x1: x, y1: y, x2: ex, y2: ey, pathLength: 1 }, svg);
  U.svg("circle", { class: "pin-dot", cx: x, cy: y, r: 5 }, svg);
});
