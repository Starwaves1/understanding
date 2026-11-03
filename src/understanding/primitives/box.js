U.css(`
.hl-box { fill: rgba(240,180,41,.10); stroke: var(--accent); stroke-width: 3; rx: 8; stroke-dasharray: 1;
  animation: draw .5s ease-out both; filter: drop-shadow(0 0 6px rgba(240,180,41,.6)); }
.hl-label { position: fixed; padding: 3px 10px; border-radius: 6px; background: var(--accent); color: #2b2a27;
  font-family: var(--hand); font-weight: 700; font-size: 15px; white-space: nowrap; animation: pop .3s ease-out .3s both; }
`);
U.register("box", (op, U) => {
  const x = U.sx(+op.x), y = U.sy(+op.y), w = U.sx(+op.w), h = U.sy(+op.h);
  U.mark({ x, y, w, h });
  U.svg("rect", { class: "hl-box", x: x - 4, y: y - 4, width: w + 8, height: h + 8, pathLength: 1 }, U.screenSvg());
  if (op.text) {
    const l = U.el("div", "hl-label", U.screenLayer(), op.text);
    const [lx, ly] = U.clampBox(x - 4, y - l.offsetHeight - 10, l.offsetWidth, l.offsetHeight);
    l.style.left = `${lx}px`;
    l.style.top = `${ly}px`;
  }
});
