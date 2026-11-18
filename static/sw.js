const CACHE = "download-v2";
const SHELL = ["/", "/privacy", "/terms", "/manifest.json", "/static/style.css", "/static/icon-192.png", "/static/icon-512.png", "/favicon.ico"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => {})))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(k => Promise.all(k.filter(n => n !== CACHE).map(n => caches.delete(n)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (u.origin !== location.origin || r.method !== "GET" || u.pathname.startsWith("/api/")) return;
  e.respondWith(
    fetch(r).then(res => {
      if (res.status === 200) { const cp = res.clone(); caches.open(CACHE).then(c => c.put(r, cp)); }
      return res;
    }).catch(() => caches.match(r).then(m => m || (r.mode === "navigate" ? caches.match("/") : Response.error())))
  );
});
