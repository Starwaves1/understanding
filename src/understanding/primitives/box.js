U.css(`
.hl-box { fill: rgba(240,180,41,.10); stroke: var(--accent); stroke-width: 3; rx: 8; stroke-dasharray: 1;
  animation: draw .5s ease-out both; filter: drop-shadow(0 0 6px rgba(240,180,41,.6)); }
.hl-mark { position: fixed; border-radius: 4px; background: rgba(255, 196, 0, .38); mix-blend-mode: multiply;
  transform-origin: left center; animation: swipe .35s ease-out both; }
@keyframes swipe { from { transform: scaleX(0); } }
.hl-label { position: fixed; padding: 3px 10px; border-radius: 6px; background: var(--accent); color: #2b2a27;
  font-family: var(--hand); font-weight: 700; font-size: 15px; white-space: nowrap; animation: pop .3s ease-out .3s both; }
`);
U.register("box", (op, U) => {
  // Quoted text snaps to the real OCR'd lines: a marker swipe per line.
  const lines = op.quote ? U.findQuote(op.quote) : null;
  let top;
  if (lines) {
    lines.forEach((r, i) => {
      const m = U.el("div", "hl-mark", U.screenLayer());
      Object.assign(m.style, { left: `${r.x - 3}px`, top: `${r.y - 2}px`, width: `${r.w + 6}px`, height: `${r.h + 4}px`, animationDelay: `${i * 0.12}s` });
      U.mark(r);
    });
    const last = lines[lines.length - 1];
    top = { x: lines[0].x, y: lines[0].y, endX: last.x + last.w, endY: last.y + last.h / 2 };
  } else {
    if (op.x == null) return console.warn("box: quote not found on screen", op.quote);
    const x = U.sx(+op.x), y = U.sy(+op.y), w = U.sx(+op.w), h = U.sy(+op.h);
    U.mark({ x, y, w, h });
    U.svg("rect", { class: "hl-box", x: x - 4, y: y - 4, width: w + 8, height: h + 8, pathLength: 1 }, U.screenSvg());
    top = { x: x - 4, y: y - 4 };
  }
  if (op.text) {
    const l = U.el("div", "hl-label", U.screenLayer(), op.text);
    // Quoted text: label just right of where the highlight ends (covers no text
    // on that line). Regions: label above the box.
    const r = top.endX != null
      ? U.placeLabel(top.endX, top.endY, l.offsetWidth, l.offsetHeight, 14, 0)
      : U.placeLabel(top.x, top.y - l.offsetHeight / 2 - 8, l.offsetWidth, l.offsetHeight, 0, 0);
    l.style.left = `${r.x}px`;
    l.style.top = `${r.y}px`;
  }
});
