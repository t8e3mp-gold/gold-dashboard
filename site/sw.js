"use strict";
// Offline support: app shell is cached; data is network-first with the last good copy as fallback.
const C = "gd-v1", SHELL = ["./", "index.html", "app.js", "style.css"];
const key = u => { const x = new URL(u); x.search = ""; return x.toString(); };
self.addEventListener("install", e => e.waitUntil(caches.open(C).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const r = e.request; if (r.method !== "GET" || new URL(r.url).origin !== location.origin) return;
  e.respondWith((async () => {
    const c = await caches.open(C);
    try {
      const n = await fetch(r, {cache: "no-store"});
      if (n.ok) c.put(key(r.url), n.clone());
      return n;
    } catch (err) {
      const hit = await c.match(key(r.url));
      if (!hit) return new Response("offline", {status: 503});
      const h = new Headers(hit.headers); h.set("x-sw-cache", "1");
      return new Response(await hit.blob(), {status: 200, headers: h});
    }
  })());
});
