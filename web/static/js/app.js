import { api } from "./api.js";
import * as board from "./board.js";
import * as dashboard from "./dashboard.js";
import * as reports from "./reports.js";
import * as admin from "./admin.js";

const VIEWS = {
  board: { el: "view-board", mount: (el) => board.mount(el) },
  reports: { el: "view-reports", mount: (el) => reports.mount(el) },
  dashboard: { el: "view-dashboard", mount: (el) => dashboard.mount(el) },
  admin: { el: "view-admin", mount: (el) => admin.mount(el) },
};

let me = null;

function initTheme() {
  const saved = localStorage.getItem("theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  document.getElementById("btn-theme").addEventListener("click", () => {
    const current =
      document.documentElement.getAttribute("data-theme") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  });
}

function switchView(name) {
  for (const [key, v] of Object.entries(VIEWS)) {
    document.getElementById(v.el).classList.toggle("hidden", key !== name);
  }
  for (const tab of document.querySelectorAll("#tabs button")) {
    tab.setAttribute("aria-selected", tab.dataset.view === name ? "true" : "false");
  }
  const view = VIEWS[name];
  view.mount(document.getElementById(view.el)).catch(() => {
    document.getElementById(view.el).textContent = "Erro ao carregar.";
  });
}

function setupApp() {
  if (me.role === "admin") document.getElementById("tab-admin").classList.remove("hidden");

  for (const tab of document.querySelectorAll("#tabs button")) {
    tab.addEventListener("click", () => switchView(tab.dataset.view));
  }

  document.getElementById("btn-logout").addEventListener("click", async () => {
    try {
      await api.post("/auth/logout");
    } catch (e) {
      /* ignora */
    }
    location.href = "/login.html";
  });

  switchView("board");
}

function showChangePassword() {
  document.getElementById("tabs").classList.add("hidden");
  document.getElementById("view-board").classList.add("hidden");
  const view = document.getElementById("view-change-password");
  view.classList.remove("hidden");

  document.getElementById("form-change-password").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = document.getElementById("cp-error");
    err.textContent = "";
    try {
      await api.post("/auth/change-password", {
        current_password: document.getElementById("cp-current").value,
        new_password: document.getElementById("cp-new").value,
      });
      location.reload();
    } catch (e) {
      err.textContent = e.message || "Erro ao trocar a senha.";
    }
  });
}

async function boot() {
  initTheme();
  try {
    me = await api.get("/auth/me");
  } catch (e) {
    location.href = "/login.html";
    return;
  }
  api.setCsrf(me.csrf_token);
  document.getElementById("who").textContent =
    me.email + (me.role === "admin" ? " · admin" : "");

  if (me.must_change_password) showChangePassword();
  else setupApp();
}

boot();
