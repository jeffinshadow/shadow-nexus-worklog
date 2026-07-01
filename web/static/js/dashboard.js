import { api } from "./api.js";
import { h, clear } from "./dom.js";

export async function mount(root, opts = {}) {
  const url = opts.dashUrl || "/dashboard";
  const data = await api.get(url);
  clear(root);
  root.append(
    h(
      "div",
      { class: "metrics" },
      metric("Diárias de hoje", data.today),
      metric("Semana atual", data.week),
      metric("Mês corrente", data.month)
    )
  );
}

function metric(title, m) {
  const pct = m.total ? Math.round((100 * m.done) / m.total) : 0;
  const fill = h("span", {});
  fill.style.width = pct + "%";
  return h(
    "div",
    { class: "metric" },
    h("h3", { text: title }),
    h("div", { class: "value" }, String(m.done), h("small", { text: ` / ${m.total}  (${pct}%)` })),
    h("div", { class: "bar" }, fill)
  );
}
