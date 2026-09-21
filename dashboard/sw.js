/* BELTSENTINEL AI - Web Push Service Worker */

"use strict";

self.addEventListener("install", event => {
    self.skipWaiting();
});

self.addEventListener("activate", event => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener("push", event => {
    let payload = {};

    try {
        payload = event.data ? event.data.json() : {};
    } catch (error) {
        payload = {
            title: "BELTSENTINEL AI",
            body: event.data ? event.data.text() : "New conveyor alert"
        };
    }

    const title = payload.title || "BELTSENTINEL AI";
    const options = {
        body: payload.body || "New conveyor alert",
        tag: `beltsentinel-${payload.severity || "alert"}`,
        renotify: true,
        requireInteraction: payload.severity === "CRITICAL",
        timestamp: Date.now(),
        data: {
            url: payload.url || "/#alerts",
            severity: payload.severity || "WARNING",
            alert: payload.alert || null,
            telemetry: payload.telemetry || null,
            risk: payload.risk || null,
            detection: payload.detection || null
        }
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener("notificationclick", event => {
    event.notification.close();

    const targetUrl =
        event.notification.data &&
        event.notification.data.url
            ? event.notification.data.url
            : "/#alerts";

    event.waitUntil(
        clients.matchAll({
            type: "window",
            includeUncontrolled: true
        }).then(clientList => {
            for (const client of clientList) {
                if ("focus" in client) {
                    client.navigate(targetUrl);
                    return client.focus();
                }
            }

            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }

            return undefined;
        })
    );
});
