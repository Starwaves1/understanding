U.css(`
.illus svg { width: 100%; height: auto; display: block; overflow: visible; }
.illus .cap { text-align: center; font-size: 12.5px; color: var(--muted); margin-top: 4px; }
.illus .stroke { stroke-dasharray: 1; animation: draw .6s ease-out both; }
.illus .filled { animation: fade .5s ease-out both; }
.illus text { font-family: var(--hand); fill: var(--ink); }
`);
U.register("svg", (op, U) => {
  const wrap = U.el("div", "illus", U.card());
  const vbW = +(String(op.viewBox || "").split(/[\s,]+/)[2] || 0);
  if (vbW >= 500) U.cardEl.classList.add("wide"); // wide drawings get a wide card
  const svg = U.svg("svg", { viewBox: op.viewBox || "0 0 400 240" }, wrap);
  svg.innerHTML = String(op.markup || "").replace(/<script[\s\S]*?<\/script>/gi, "").replace(/\son\w+=/gi, " data-x=");
  let i = 0;
  for (const el of svg.querySelectorAll("path,line,polyline,polygon,rect,circle,ellipse,text")) {
    const delay = `${(i++ * 0.08).toFixed(2)}s`;
    if (el.tagName !== "text" && el.getAttribute("stroke") && el.getAttribute("stroke") !== "none") {
      el.setAttribute("pathLength", "1");
      el.classList.add("stroke");
    }
    if (el.tagName === "text" || (el.getAttribute("fill") && el.getAttribute("fill") !== "none")) el.classList.add("filled");
    el.style.animationDelay = delay;
  }
  if (op.caption) U.el("div", "cap", wrap, op.caption);
});
