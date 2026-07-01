// Wrapper de fetch para /api. Envia o cookie de sessao (same-origin) e o
// header X-CSRF-Token nas mutacoes. Redireciona para o login em 401 de sessao.

let CSRF = null;

export function setCsrf(token) {
  CSRF = token;
}

async function request(method, path, body) {
  const opts = { method, headers: {}, credentials: "same-origin" };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (method !== "GET" && CSRF) {
    opts.headers["X-CSRF-Token"] = CSRF;
  }

  const res = await fetch("/api" + path, opts);

  // 401 fora das rotas de auth = sessao expirou -> volta ao login.
  if (res.status === 401 && !path.startsWith("/auth/")) {
    if (location.pathname !== "/login.html") location.href = "/login.html";
    throw new Error("nao autenticado");
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const detail = (data && data.detail) || res.statusText;
    throw Object.assign(new Error(detail), { status: res.status, data });
  }
  return data;
}

export const api = {
  get: (p) => request("GET", p),
  post: (p, b) => request("POST", p, b),
  patch: (p, b) => request("PATCH", p, b),
  del: (p) => request("DELETE", p),
  setCsrf,
};
