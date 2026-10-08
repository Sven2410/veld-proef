// Bewaart de telefoonpagina zelf, zodat hij ook zonder internet opent. Alleen
// de pagina en zijn bestanden; de verbinding met de pc gaat er nooit langs.
const CACHE = "veld-proef-3";
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

// Eerst vers van internet, zodat een nieuwe versie in één keer binnenkomt.
// Geen internet, of na 3 seconden nog niets, dan wat er bewaard is (en de
// verse versie gaat dan in de bewaarde kopie voor de volgende keer). Eerst
// was het andersom, en dan zag je een nieuwe versie pas de tweede keer.
// PeerJS heeft een vast versienummer en verandert nooit: meteen bewaard.
// De pc-pagina hoort er niet bij.
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  const basis = new URL("./", location).pathname;
  const vanHier = url.origin === location.origin && url.pathname.startsWith(basis) && !url.pathname.endsWith("pc.html");
  if (e.request.method !== "GET" || !(vanHier || url.href === PEERJS)) return;
  const sleutel = e.request.mode === "navigate" ? new URL("./", location).href : e.request;
  e.respondWith(caches.open(CACHE).then(async (c) => {
    const oud = await c.match(sleutel, { ignoreSearch: true });
    if (oud && url.href === PEERJS) return oud;
    const vers = fetch(e.request).then((r) => {
      if (r.ok) c.put(sleutel, r.clone());
      return r;
    });
    if (!oud) return vers;
    const traag = new Promise((ok) => setTimeout(() => ok(oud), 3000));
    return Promise.race([vers.catch(() => oud), traag]);
  }));
});
