const CACHE_NAME = "tuhin-image-lab-v3";

const FILES_TO_CACHE = [
    "/",
    "/static/manifest.json",
    "/static/icon-192.png",
    "/static/icon-512.png"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(FILES_TO_CACHE))
            .catch(error => {
                console.error("Cache install failed:", error);
            })
    );

    self.skipWaiting();
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            )
        )
    );

    self.clients.claim();
});

self.addEventListener("fetch", event => {
    if (event.request.method !== "GET") {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then(response => {
                return response;
            })
            .catch(() => {
                return caches.match(event.request)
                    .then(cachedResponse => {
                        return cachedResponse || caches.match("/");
                    });
            })
    );
});
