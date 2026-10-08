// Bewaart de pagina zelf op de telefoon, zodat hij ook zonder internet opent.
// Nooit OneDrive of het inloggen bij Microsoft: die moeten altijd vers.
const CACHE = "proef-1";
const MSAL = "https://cdn.jsdelivr.net/npm/@azure/msal-browser@4.30.0/lib/msal-browser.min.js";
const BESTANDEN = ["./", "manifest.webmanifest", "icoon.png", MSAL];

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
// volgende keer.
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  const vanHier = url.origin === location.origin && url.pathname.startsWith(new URL("./", location).pathname);
  if (e.request.method !== "GET" || !(vanHier || url.href === MSAL)) return;
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
