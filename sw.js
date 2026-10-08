// Bewaart de telefoonpagina zelf, zodat hij ook zonder internet opent. Alleen
// de pagina en zijn bestanden; de verbinding met de pc gaat er nooit langs.
const CACHE = "veld-proef-1";
const PEERJS = "https://cdn.jsdelivr.net/npm/peerjs@1.5.5/dist/peerjs.min.js";
const BESTANDEN = ["./", "stijl.css", "gedeeld.js", "manifest.webmanifest", "icoon.png", PEERJS];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(BESTANDEN)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((namen) => Promise.all(namen.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
    .then(() => self.clients.claim()));
});

// Eerst wat er bewaard is, en ondertussen een verse versie ophalen voor de
// volgende keer. De pc-pagina hoort er niet bij.
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  const basis = new URL("./", location).pathname;
  const vanHier = url.origin === location.origin && url.pathname.startsWith(basis) && !url.pathname.endsWith("pc.html");
  if (e.request.method !== "GET" || !(vanHier || url.href === PEERJS)) return;
  const sleutel = e.request.mode === "navigate" ? new URL("./", location).href : e.request;
  e.respondWith(caches.open(CACHE).then(async (c) => {
    const oud = await c.match(sleutel, { ignoreSearch: true });
    const vers = fetch(e.request).then((r) => {
      if (r.ok) c.put(sleutel, r.clone());
      return r;
    }).catch(() => oud);
    return oud || vers;
  }));
});
