import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as notificationsApi from "../api/notifications";
import { urlBase64ToUint8Array } from "../lib/push";

const SUBSCRIPTION_KEY = ["push-subscription"] as const;

export function isPushSupported(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window;
}

export function useCurrentPushSubscription() {
  return useQuery({
    queryKey: SUBSCRIPTION_KEY,
    queryFn: async () => {
      if (!isPushSupported()) return null;
      const registration = await navigator.serviceWorker.ready;
      return registration.pushManager.getSubscription();
    },
    enabled: isPushSupported(),
  });
}

export function useEnablePushNotifications() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        throw new Error("Notification permission was not granted");
      }

      const { public_key: publicKey } = await notificationsApi.getVapidPublicKey();
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
      });

      await notificationsApi.subscribe(subscription.toJSON());
      return subscription;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SUBSCRIPTION_KEY });
    },
  });
}

export function useDisablePushNotifications() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) return;

      await notificationsApi.unsubscribe(subscription.endpoint);
      await subscription.unsubscribe();
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SUBSCRIPTION_KEY });
    },
  });
}

export function useSendTestNotification() {
  return useMutation({
    mutationFn: () => notificationsApi.sendTestNotification(),
  });
}
