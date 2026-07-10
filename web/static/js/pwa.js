// Registro do Service Worker para tornar o site instalavel (PWA).
// Externo porque a CSP (script-src 'self') nao permite script inline.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* registro falhou (ex.: sem HTTPS em dev) -- ignora, site funciona igual */
    });
  });
}
