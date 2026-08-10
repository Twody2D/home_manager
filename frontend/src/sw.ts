/// <reference lib="webworker" />
import { createHandlerBoundToURL, precacheAndRoute } from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";

declare const self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: (string | { revision: string | null; url: string })[];
};

// Injected by vite-plugin-pwa's injectManifest build step with the app
// shell's hashed asset list — this is the offline-install behavior carried
// over from the previous generateSW setup.
precacheAndRoute(self.__WB_MANIFEST);

// Same intent as the old generateSW navigateFallbackDenylist: offline page
// reloads fall back to the cached app shell, but API calls must always hit
// the network so they get a real (or a real failed) response.
registerRoute(
  new NavigationRoute(createHandlerBoundToURL("/index.html"), {
    denylist: [/^\/api\//],
  }),
);

self.addEventListener("push", (event: PushEvent) => {
  let title = "Home Manager";
  let body = "";
  let url = "/";

  if (event.data) {
    try {
      const payload = event.data.json() as { title?: string; body?: string; url?: string };
      title = payload.title ?? title;
      body = payload.body ?? body;
      url = payload.url ?? url;
    } catch {
      body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url },
    }),
  );
});

self.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();
  const url = (event.notification.data as { url?: string } | undefined)?.url ?? "/";

  event.waitUntil(
    (async () => {
      const clientsList = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      const existing = clientsList.find((c) => "focus" in c);
      if (existing) {
        await existing.focus();
        if ("navigate" in existing) await (existing as WindowClient).navigate(url);
        return;
      }
      await self.clients.openWindow(url);
    })(),
  );
});
