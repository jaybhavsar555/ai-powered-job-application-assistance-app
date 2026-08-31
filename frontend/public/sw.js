/* Career OS — Web Push service worker for Loop Engineer packet alerts */

self.addEventListener("push", (event) => {
  let data = { title: "Career OS", body: "Job packets ready", url: "/loop" };
  try {
    if (event.data) {
      data = { ...data, ...event.data.json() };
    }
  } catch {
    /* ignore */
  }
  const url = data.url || "/loop";
  event.waitUntil(
    self.registration.showNotification(data.title || "Career OS", {
      body: data.body || "Review job packets",
      icon: "/favicon.ico",
      data: { url },
      tag: "career-os-loop-packet",
      renotify: true,
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/loop";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if ("focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});
