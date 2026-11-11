// Service worker mínimo: torna o app instalável e mostra uma página offline.
// Não faz cache de dados nem de páginas autenticadas — são dados financeiros,
// e servir uma cópia antiga ou de outro usuário seria pior que mostrar erro.
const CACHE = "moneyflow-offline-v1";
const OFFLINE_URL = "/assets/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.add(OFFLINE_URL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Só intercepta navegações; tudo o mais (API do Dash, assets) vai direto à rede.
  if (event.request.mode !== "navigate") return;
  event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE_URL)));
});
