import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useMyPreferences, useUpdateMyPreferences } from "../hooks/usePreferences";
import {
  isPushSupported,
  useCurrentPushSubscription,
  useDisablePushNotifications,
  useEnablePushNotifications,
  useSendTestNotification,
} from "../hooks/useNotifications";
import { useAliceLinkStatus, useIssueAliceToken, useRevokeAliceToken } from "../hooks/useAlice";
import { ApiError } from "../api/client";
import type { EnergyPattern } from "../api/types";

function NotificationsSection() {
  const subscriptionQuery = useCurrentPushSubscription();
  const enable = useEnablePushNotifications();
  const disable = useDisablePushNotifications();
  const sendTest = useSendTestNotification();

  if (!isPushSupported()) {
    return (
      <section className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-900">Notifications</h2>
        <p className="text-sm text-slate-500">
          This browser doesn't support push notifications.
        </p>
      </section>
    );
  }

  const isSubscribed = Boolean(subscriptionQuery.data);
  const errorMessage =
    enable.error instanceof ApiError
      ? enable.error.message
      : enable.error instanceof Error
        ? enable.error.message
        : null;

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">Notifications</h2>
      <p className="text-xs text-slate-500">
        Get notified on this device when someone assigns you a task.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        {isSubscribed ? (
          <button
            type="button"
            onClick={() => disable.mutate()}
            disabled={disable.isPending}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {disable.isPending ? "Disabling…" : "Disable notifications"}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => enable.mutate()}
            disabled={enable.isPending}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {enable.isPending ? "Enabling…" : "Enable notifications"}
          </button>
        )}

        {isSubscribed && (
          <button
            type="button"
            onClick={() => sendTest.mutate()}
            disabled={sendTest.isPending}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {sendTest.isPending ? "Sending…" : "Send test notification"}
          </button>
        )}
      </div>

      {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
      {sendTest.isSuccess && sendTest.data.sent === 0 && (
        <p className="text-sm text-amber-600">
          No notification was delivered — the server may not have push configured yet.
        </p>
      )}
      {sendTest.isSuccess && sendTest.data.sent > 0 && (
        <p className="text-sm text-emerald-600">Test notification sent.</p>
      )}
    </section>
  );
}

function toCsv(items: string[]): string {
  return items.join(", ");
}

function fromCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function AliceSection() {
  const statusQuery = useAliceLinkStatus();
  const issueToken = useIssueAliceToken();
  const revokeToken = useRevokeAliceToken();

  const webhookUrl = issueToken.data
    ? `${window.location.origin}${issueToken.data.webhook_url}`
    : null;

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">Yandex Alice</h2>
      <p className="text-xs text-slate-500">
        Link this account to a Yandex Dialogs skill so you can say things like "create task: water
        the plants" to Alice.
      </p>

      {statusQuery.data?.linked && !webhookUrl && (
        <p className="text-sm text-slate-600">
          Linked
          {statusQuery.data.last_used_at &&
            ` — last used ${new Date(statusQuery.data.last_used_at).toLocaleString()}`}
          .
        </p>
      )}

      {webhookUrl && (
        <div className="space-y-1 rounded-md bg-slate-50 p-3 text-xs">
          <p className="font-medium text-slate-700">
            Paste this as your Dialogs skill's webhook URL — it's shown only once:
          </p>
          <code className="block break-all rounded bg-white p-2 text-slate-800">{webhookUrl}</code>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => issueToken.mutate()}
          disabled={issueToken.isPending}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {issueToken.isPending
            ? "Generating…"
            : statusQuery.data?.linked
              ? "Regenerate webhook URL"
              : "Generate webhook URL"}
        </button>

        {statusQuery.data?.linked && (
          <button
            type="button"
            onClick={() => revokeToken.mutate()}
            disabled={revokeToken.isPending}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {revokeToken.isPending ? "Revoking…" : "Unlink"}
          </button>
        )}
      </div>
    </section>
  );
}

export function PreferencesPage() {
  const prefsQuery = useMyPreferences();
  const updatePrefs = useUpdateMyPreferences();

  const [energyPattern, setEnergyPattern] = useState<EnergyPattern>("steady");
  const [taskSpeed, setTaskSpeed] = useState("1");
  const [workingStart, setWorkingStart] = useState("");
  const [workingEnd, setWorkingEnd] = useState("");
  const [sleepStart, setSleepStart] = useState("");
  const [sleepEnd, setSleepEnd] = useState("");
  const [preferredCategories, setPreferredCategories] = useState("");
  const [dislikedCategories, setDislikedCategories] = useState("");
  const [notes, setNotes] = useState("");
  const [savedMessage, setSavedMessage] = useState(false);

  useEffect(() => {
    const prefs = prefsQuery.data;
    if (!prefs) return;
    setEnergyPattern(prefs.energy_pattern);
    setTaskSpeed(String(prefs.task_speed_multiplier));
    setWorkingStart(prefs.working_hours_start ?? "");
    setWorkingEnd(prefs.working_hours_end ?? "");
    setSleepStart(prefs.sleep_start ?? "");
    setSleepEnd(prefs.sleep_end ?? "");
    setPreferredCategories(toCsv(prefs.preferred_categories));
    setDislikedCategories(toCsv(prefs.disliked_categories));
    setNotes(prefs.notes ?? "");
  }, [prefsQuery.data]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSavedMessage(false);
    await updatePrefs.mutateAsync({
      energy_pattern: energyPattern,
      task_speed_multiplier: Number(taskSpeed) || 1,
      working_hours_start: workingStart || null,
      working_hours_end: workingEnd || null,
      sleep_start: sleepStart || null,
      sleep_end: sleepEnd || null,
      preferred_categories: fromCsv(preferredCategories),
      disliked_categories: fromCsv(dislikedCategories),
      notes: notes || null,
    });
    setSavedMessage(true);
  }

  if (prefsQuery.isLoading) {
    return <p className="text-sm text-slate-500">Loading preferences…</p>;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">My preferences</h1>
      <p className="text-xs text-slate-500">
        These are personal — only you can see and change them. They'll guide how tasks get planned
        for you once the planning engine ships.
      </p>

      <NotificationsSection />
      <AliceSection />

      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Working hours start</span>
            <input
              type="time"
              value={workingStart}
              onChange={(e) => setWorkingStart(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Working hours end</span>
            <input
              type="time"
              value={workingEnd}
              onChange={(e) => setWorkingEnd(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Sleep start</span>
            <input
              type="time"
              value={sleepStart}
              onChange={(e) => setSleepStart(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Sleep end</span>
            <input
              type="time"
              value={sleepEnd}
              onChange={(e) => setSleepEnd(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5"
            />
          </label>
        </div>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-600">Energy pattern</span>
          <select
            value={energyPattern}
            onChange={(e) => setEnergyPattern(e.target.value as EnergyPattern)}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5"
          >
            <option value="morning">Morning person</option>
            <option value="evening">Evening person</option>
            <option value="steady">Steady throughout the day</option>
          </select>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-600">
            Task speed multiplier ({taskSpeed}× — 1.0 is average, higher takes longer)
          </span>
          <input
            type="number"
            min="0.1"
            max="5"
            step="0.1"
            value={taskSpeed}
            onChange={(e) => setTaskSpeed(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5"
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-600">Preferred task categories (comma-separated)</span>
          <input
            type="text"
            value={preferredCategories}
            onChange={(e) => setPreferredCategories(e.target.value)}
            placeholder="cooking, gardening"
            className="w-full rounded-md border border-slate-300 px-2 py-1.5"
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-600">Disliked task categories (comma-separated)</span>
          <input
            type="text"
            value={dislikedCategories}
            onChange={(e) => setDislikedCategories(e.target.value)}
            placeholder="laundry"
            className="w-full rounded-md border border-slate-300 px-2 py-1.5"
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-600">Notes / recurring habits</span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5"
          />
        </label>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={updatePrefs.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {updatePrefs.isPending ? "Saving…" : "Save"}
          </button>
          {savedMessage && !updatePrefs.isPending && (
            <span className="text-sm text-emerald-600">Saved.</span>
          )}
        </div>
      </form>
    </div>
  );
}
