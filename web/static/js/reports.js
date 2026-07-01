import { api } from "./api.js";
import { h, clear, formatDate } from "./dom.js";

export async function mount(root, opts = {}) {
  const base = opts.reportUrl || "/reports/weekly";
  clear(root);

  const dateInput = h("input", { type: "date" });
  const out = h("div", {});
  root.append(
    h(
      "div",
      { class: "report-controls" },
      h("div", { class: "field" }, h("label", { text: "Semana (escolha um dia)" }), dateInput),
      h("button", { text: "Ver", onClick: load })
    ),
    out
  );

  async function load() {
    const query = dateInput.value ? "?date=" + dateInput.value : "";
    const data = await api.get(base + query);
    render(data);
  }

  function render(data) {
    clear(out);
    out.append(
      h("p", { class: "sub", text: `Semana: ${fmtFull(data.week_start)} a ${fmtFull(data.week_end)}` })
    );

    const rec = h("ul", { class: "report-list" });
    if (!data.recurring.length) rec.append(h("li", { class: "empty", text: "Nenhuma." }));
    for (const r of data.recurring)
      rec.append(h("li", {}, r.label, h("span", { class: "when", text: formatDate(r.completed_date) })));

    const wl = h("ul", { class: "report-list" });
    if (!data.worklog.length) wl.append(h("li", { class: "empty", text: "Nenhuma." }));
    for (const w of data.worklog)
      wl.append(
        h(
          "li",
          {},
          w.title,
          w.completed_at ? h("span", { class: "when", text: formatDate(w.completed_at) }) : null
        )
      );

    out.append(
      h("div", { class: "report-section" }, h("h3", { text: "Recorrentes concluídas" }), rec),
      h("div", { class: "report-section" }, h("h3", { text: "Tarefas finalizadas" }), wl)
    );
  }

  load();
}

function fmtFull(value) {
  const d = new Date(value + "T00:00:00");
  return d.toLocaleDateString("pt-BR");
}
