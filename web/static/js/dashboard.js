import { api } from "./api.js";
import { h, clear } from "./dom.js";

const NS = "http://www.w3.org/2000/svg";
const DONE_COLOR = "var(--primary)";
const OPEN_COLOR = "var(--surface-container-high)";

// Todas as agregações vêm do backend (/dashboard), já separadas em dois grupos
// comparáveis. O frontend só desenha as pizzas.
export async function mount(root, opts = {}) {
  const dashUrl = opts.dashUrl || "/dashboard";
  const data = await api.get(dashUrl);

  clear(root);
  root.append(
    groupRow("Tarefas Recorrentes Diárias", data.recurring),
    groupRow("Tarefas Pontuais", data.pontual)
  );
}

function groupRow(title, g) {
  return h(
    "section",
    { class: "dash-group" },
    h("h2", { class: "dash-group-title", text: title }),
    h(
      "div",
      { class: "metrics" },
      pieCard("Dia", g.day.done, g.day.open),
      pieCard("Semana", g.week.done, g.week.open),
      pieCard("Mês", g.month.done, g.month.open)
    )
  );
}

function pieCard(title, done, open) {
  const total = done + open;
  const frac = total ? done / total : 0;
  const pct = Math.round(frac * 100);

  return h(
    "div",
    { class: "metric" },
    h("h3", { text: title }),
    buildPie(frac),
    h(
      "div",
      { class: "pie-caption" },
      h("span", { class: "pie-pct", text: pct + "%" }),
      h("span", { text: " concluídas" })
    ),
    h(
      "div",
      { class: "pie-legend" },
      legendItem("Concluídas", done, DONE_COLOR),
      legendItem("Em aberto", open, OPEN_COLOR)
    )
  );
}

function legendItem(label, count, color) {
  const swatch = h("span", { class: "swatch" });
  swatch.style.background = color;
  return h("span", { class: "item" }, swatch, `${label}: ${count}`);
}

function buildPie(frac) {
  const size = 140;
  const r = 60;
  const c = size / 2;

  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "pie-svg");
  svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `${Math.round(frac * 100)}% concluídas`);

  if (frac <= 0) svg.appendChild(circle(c, r, OPEN_COLOR));
  else if (frac >= 1) svg.appendChild(circle(c, r, DONE_COLOR));
  else {
    svg.appendChild(slice(c, r, 0, frac, DONE_COLOR));
    svg.appendChild(slice(c, r, frac, 1, OPEN_COLOR));
  }
  return svg;
}

function circle(c, r, color) {
  const el = document.createElementNS(NS, "circle");
  el.setAttribute("cx", String(c));
  el.setAttribute("cy", String(c));
  el.setAttribute("r", String(r));
  el.style.fill = color;
  return el;
}

function slice(c, r, f0, f1, color) {
  const a0 = 2 * Math.PI * f0;
  const a1 = 2 * Math.PI * f1;
  const x0 = c + r * Math.sin(a0);
  const y0 = c - r * Math.cos(a0);
  const x1 = c + r * Math.sin(a1);
  const y1 = c - r * Math.cos(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;

  const el = document.createElementNS(NS, "path");
  el.setAttribute("d", `M ${c} ${c} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`);
  el.style.fill = color;
  return el;
}
