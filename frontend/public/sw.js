/* Gaboshop : reçoit les alertes (Web Push) même quand le site est fermé.
   Ce fichier ne garde rien en cache : chaque ouverture montre toujours la dernière version du site. */

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'Gaboshop', body: event.data ? event.data.text() : '' };
  }
  const title = data.title || 'Gaboshop';
  const options = {
    body: data.body || '',
    icon: data.icon || '/icon-192.png',
    badge: data.badge || '/icon-192.png',
    lang: 'fr',
    vibrate: [120, 60, 120],
    data: { url: data.url || '/notifications', id: data.id || null },
  };
  if (data.tag) {
    options.tag = data.tag;
    options.renotify = true;
  }
  event.waitUntil((async () => {
    await self.registration.showNotification(title, options);
    // Les pages ouvertes mettent leur cloche à jour tout de suite.
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    windows.forEach((client) => client.postMessage({ type: 'gaboshop-push', id: data.id || null }));
  })());
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL((event.notification.data && event.notification.data.url) || '/notifications', self.location.origin);
  const path = target.pathname + target.search + target.hash;
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const open = windows.find((client) => new URL(client.url).origin === self.location.origin);
    if (open) {
      await open.focus();
      open.postMessage({ type: 'gaboshop-open', path });
      return;
    }
    await self.clients.openWindow(path);
  })());
});
