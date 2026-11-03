U.css(`
.note { padding: 10px 14px; border-radius: 10px; background: var(--tone-bg, #fff6dc);
  border-left: 4px solid var(--tone, var(--accent)); font-family: var(--hand); font-size: 17px; line-height: 1.3; }
`);
U.register("note", (op, U) => {
  U.el("div", `note tone-${op.tone || "orange"}`, U.card(), op.text);
});
