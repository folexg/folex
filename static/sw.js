const CACHE = "download-v1";
const SHELL = ["/", "/privacy", "/terms", "/manifest.json", "/static/style.css", "/static/icon-192.png", "/static/icon-512.png", "/favicon.ico"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => {})))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(k => Promise.all(k.filter(n => n !== CACHE && n !== "shared-files").map(n => caches.delete(n)))).then(() => self.clients.claim()));
});
async function share(req) {
  let dest = "/";
  try {
    const f = await req.formData();
    const vids = f.getAll("videos").filter(x => x && x.size);
    if (vids.length) {
      await caches.delete("shared-files");
      const c = await caches.open("shared-files");
      let i = 0;
      for (const v of vids) {
        await c.put("/shared/" + (i++), new Response(v, { headers: { "Content-Type": v.type || "video/mp4", "X-Name": encodeURIComponent(v.name || "video.mp4") } }));
      }
      dest = "/?shared=1#whatsapp";
    } else {
      const m = ((f.get("url") || "") + " " + (f.get("text") || "")).match(/https?:\/\/\S+/);
      if (m) dest = "/?url=" + encodeURIComponent(m[0]);
    }
  } catch (e) {}
  return Response.redirect(new URL(dest, self.location.origin).href, 303);
}
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (u.origin !== location.origin) return;
  if (r.method === "POST" && u.pathname === "/share-target") { e.respondWith(share(r)); return; }
  if (r.method !== "GET" || u.pathname.startsWith("/api/")) return;
  e.respondWith(
    fetch(r).then(res => {
      if (res.status === 200) { const cp = res.clone(); caches.open(CACHE).then(c => c.put(r, cp)); }
      return res;
    }).catch(() => caches.match(r).then(m => m || (r.mode === "navigate" ? caches.match("/") : Response.error())))
  );
});
