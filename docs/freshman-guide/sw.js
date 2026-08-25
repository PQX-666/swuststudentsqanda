const CACHE = "swust-guide-2026-github-v1";
const BASE = "/swuststudentsqanda/";
const CORE = [BASE, BASE + "manifest.webmanifest", BASE + "favicon.svg"];

async function cachePageAndAssets() {
  const cache = await caches.open(CACHE);
  const response = await fetch(BASE, { cache: "reload" });
  if (!response.ok) throw new Error("homepage unavailable");
  await cache.put(BASE, response.clone());
  const html = await response.text();
  const paths = [...html.matchAll(/(?:src|href)=["']([^"']+)["']/g)]
    .map(match => match[1])
    .filter(path => path.startsWith(BASE));
  await Promise.allSettled([...new Set([...CORE.slice(1), ...paths])].map(async path => {
    const asset = await fetch(path, { cache: "reload" });
    if (asset.ok) await cache.put(path, asset);
  }));
}

self.addEventListener("install", event => {
  event.waitUntil(cachePageAndAssets().then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return;

  if (request.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const fresh = await fetch(request);
        const cache = await caches.open(CACHE);
        await cache.put(BASE, fresh.clone());
        return fresh;
      } catch {
        return (await caches.match(BASE)) || Response.error();
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
      const fresh = await fetch(request);
      if (fresh.ok) {
        const cache = await caches.open(CACHE);
        await cache.put(request, fresh.clone());
      }
      return fresh;
    } catch {
      return Response.error();
    }
  })());
});