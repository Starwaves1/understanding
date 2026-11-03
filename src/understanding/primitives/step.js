U.css(`
.steps { list-style: none; padding: 0; }
.steps li { display: flex; gap: 10px; align-items: baseline; margin: 7px 0; animation: pop .35s ease-out both; font-size: 15px; line-height: 1.35; }
.steps .num { flex: none; width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center;
  background: var(--tone, var(--blue)); color: #fff; font-size: 12px; font-weight: 700; transform: translateY(-1px); }
`);
U.register("step", (op, U) => {
  const body = U.card();
  let list = body.lastElementChild;
  if (!list || !list.classList.contains("steps")) list = U.el("ol", "steps", body);
  const li = U.el("li", `tone-${op.tone || "blue"}`, list);
  U.el("span", "num", li, op.n != null ? String(op.n) : String(list.children.length));
  U.el("span", "", li, op.text);
});
