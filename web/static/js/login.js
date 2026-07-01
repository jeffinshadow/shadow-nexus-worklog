import { api } from "./api.js";

const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const formLogin = document.getElementById("form-login");
const formRegister = document.getElementById("form-register");

function select(which) {
  const login = which === "login";
  tabLogin.setAttribute("aria-selected", login ? "true" : "false");
  tabRegister.setAttribute("aria-selected", login ? "false" : "true");
  formLogin.classList.toggle("hidden", !login);
  formRegister.classList.toggle("hidden", login);
}

tabLogin.addEventListener("click", () => select("login"));
tabRegister.addEventListener("click", () => select("register"));

formLogin.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const err = document.getElementById("login-error");
  err.textContent = "";
  try {
    await api.post("/auth/login", {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    });
    location.href = "/index.html";
  } catch (e) {
    err.textContent = e.message || "Falha no login.";
  }
});

formRegister.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const err = document.getElementById("reg-error");
  err.textContent = "";
  try {
    await api.post("/auth/register", {
      email: document.getElementById("reg-email").value,
      password: document.getElementById("reg-password").value,
    });
    select("login");
    document.getElementById("login-error").textContent = "Conta criada. Faça login.";
    document.getElementById("login-email").value = document.getElementById("reg-email").value;
  } catch (e) {
    err.textContent = e.message || "Falha no cadastro.";
  }
});
