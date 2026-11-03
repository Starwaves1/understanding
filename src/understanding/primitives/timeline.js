U.css(`
.timeline { display: flex; position: relative; padding: 26px 4px 4px; }
.timeline::before { content: ""; position: absolute; left: 8px; right: 8px; top: 33px; height: 2px; background: #d9d3c4; }
.timeline .ev { flex: 1; position: relative; text-align: center; animation: pop .35s ease-out both; }
.timeline .ev::before { content: ""; display: block; width: 14px; height: 14px; border-radius: 50%; margin: 0 auto 6px;
  background: var(--tone, var(--blue)); box-shadow: 0 0 0 3px var(--paper); position: relative; }
.timeline .t { position: absolute; top: -24px; left: 0; right: 0; font-family: var(--hand); font-weight: 700; font-size: 14px; }
.timeline .lbl { font-size: 12.5px; line-height: 1.25; color: var(--ink); padding: 0 3px; }
`);
U.register("event", (op, U) => {
  const body = U.card();
  let tl = body.lastElementChild;
  if (!tl || !tl.classList.contains("timeline")) tl = U.el("div", "timeline", body);
  const ev = U.el("div", `ev tone-${op.tone || "blue"}`, tl);
  U.el("div", "t", ev, op.t);
  U.el("div", "lbl", ev, op.label);
});
