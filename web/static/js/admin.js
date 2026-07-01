import { api } from "./api.js";
import { h, clear } from "./dom.js";
import * as board from "./board.js";
import * as dashboard from "./dashboard.js";
import * as reports from "./reports.js";

const SUBVIEWS = [
  { key: "board", label: "Board" },
  { key: "dashboard", label: "Dashboard" },
  { key: "reports", label: "Relatórios" },
];

export async function mount(root) {
  clear(root);
  const users = await api.get("/admin/users");
  if (!users.length) {
    root.append(h("p", { class: "empty", text: "Nenhum usuário." }));
    return;
  }

  const select = h(
    "select",
    {},
    ...users.map((u) => h("option", { value: u.id }, `${u.email}${u.role === "admin" ? " (admin)" : ""}`))
  );

  let active = "board";
  const subtabs = h(
    "div",
    { class: "auth-tabs" },
    ...SUBVIEWS.map((s) =>
      h("button", {
        text: s.label,
        "aria-selected": s.key === active ? "true" : "false",
        onClick: () => {
          active = s.key;
          for (const b of subtabs.children)
            b.setAttribute("aria-selected", b.textContent === s.label ? "true" : "false");
          renderCurrent();
        },
      })
    )
  );

  const content = h("div", {});
  root.append(
    h(
      "div",
      { class: "admin-bar" },
      h("div", { class: "field" }, h("label", { text: "Usuário" }), select)
    ),
    subtabs,
    h("p", { class: "readonly-note", text: "Visão somente leitura." }),
    content
  );

  function renderCurrent() {
    const uid = select.value;
    if (active === "board")
      board.mount(content, { readOnly: true, boardUrl: `/admin/users/${uid}/board` });
    else if (active === "dashboard")
      dashboard.mount(content, { dashUrl: `/admin/users/${uid}/dashboard` });
    else reports.mount(content, { reportUrl: `/admin/users/${uid}/reports/weekly` });
  }

  select.addEventListener("change", renderCurrent);
  renderCurrent();
}
