/* Browser service workers require JavaScript. The Python build injects the complete asset list. */
const CACHE = __CACHE__;
const ASSETS = __ASSETS__;
const PREFIX = __PREFIX__;
const BASE = __BASE__;
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS.map(url => new Request(url, {cache: 'reload'})))));
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      // Only remove this application's previous releases, including its former Workbox cache.
      if (name !== CACHE && (name.startsWith(PREFIX) || (name.startsWith('workbox-precache-') && name.includes(self.registration.scope)))) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(event.request, {ignoreSearch: true});
    if (cached) return cached;
    if (event.request.mode === 'navigate') return await cache.match(BASE + 'index.html') || fetch(event.request);
    return fetch(event.request);
  })());
});
