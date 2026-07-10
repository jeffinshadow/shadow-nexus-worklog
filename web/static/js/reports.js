import { api } from "./api.js";
import { h, clear } from "./dom.js";

// Tela de EXTRACAO de relatorio: escolhe o periodo e exporta um PDF com as
// atividades por dia. Admin passa opts.exportBase apontando para o usuario alvo.
export async function mount(root, opts = {}) {
  const base = opts.exportBase || "/reports/export";
  clear(root);

  const iso = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const today = new Date();
  const weekAgo = new Date();
  weekAgo.setDate(today.getDate() - 6);

  const startInput = h("input", { type: "date", value: iso(weekAgo) });
  const endInput = h("input", { type: "date", value: iso(today) });
  const err = h("div", { class: "error-text" });
  const btn = h("button", { text: "Exportar PDF", onClick: run });

  root.append(
    h(
      "div",
      { class: "report-section" },
      h("h3", { text: "Exportar relatório" }),
      h("p", {
        class: "sub",
        text: "Escolha o período e baixe um PDF com as atividades por dia (recorrentes concluídas/não concluídas e pontuais concluídas).",
      }),
      h(
        "div",
        { class: "report-controls" },
        h("div", { class: "field" }, h("label", { text: "Início" }), startInput),
        h("div", { class: "field" }, h("label", { text: "Fim" }), endInput),
        btn
      ),
      err
    )
  );

  async function run() {
    err.textContent = "";
    const start = startInput.value;
    const end = endInput.value;
    if (!start || !end) {
      err.textContent = "Preencha início e fim.";
      return;
    }
    if (start > end) {
      err.textContent = "O início não pode ser depois do fim.";
      return;
    }

    const label = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Gerando...";
    try {
      await api.download(`${base}?start=${start}&end=${end}`);
    } catch (e) {
      err.textContent = e.message || "Falha ao exportar.";
    } finally {
      btn.disabled = false;
      btn.textContent = label;
    }
  }
}
