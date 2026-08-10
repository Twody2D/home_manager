import { apiFetch } from "./client";

export interface VapidPublicKeyResponse {
  public_key: string;
}

export interface TestNotificationResponse {
  sent: number;
}

export function getVapidPublicKey(): Promise<VapidPublicKeyResponse> {
  return apiFetch("/notifications/vapid-public-key");
}

export function subscribe(subscription: PushSubscriptionJSON): Promise<void> {
  return apiFetch("/notifications/subscriptions", {
    method: "POST",
    body: {
      endpoint: subscription.endpoint,
      keys: { p256dh: subscription.keys?.p256dh, auth: subscription.keys?.auth },
    },
  });
}

export function unsubscribe(endpoint: string): Promise<void> {
  return apiFetch(`/notifications/subscriptions?endpoint=${encodeURIComponent(endpoint)}`, {
    method: "DELETE",
  });
}

export function sendTestNotification(): Promise<TestNotificationResponse> {
  return apiFetch("/notifications/test", { method: "POST" });
}
