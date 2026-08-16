import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useMyPreferences, useUpdateMyPreferences } from "../hooks/usePreferences";
import {
  isPushSupported,
  useCurrentPushSubscription,
  useDisablePushNotifications,
  useEnablePushNotifications,
  useSendTestNotification,
} from "../hooks/useNotifications";
import { useAliceLinkStatus, useIssueAliceToken, useRevokeAliceToken } from "../hooks/useAlice";
import { useUpdateMe } from "../hooks/useMembers";
import { useAuth } from "../auth/useAuth";
import { ApiError } from "../api/client";
import type { EnergyPattern, Gender } from "../api/types";

function MyNameSection() {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();
  const updateMe = useUpdateMe();
  const [name, setName] = useState(user?.display_name ?? "");
  const [gender, setGender] = useState<Gender | "">(user?.gender ?? "");
  const [savedMessage, setSavedMessage] = useState(false);

  useEffect(() => {
    setName(user?.display_name ?? "");
    setGender(user?.gender ?? "");
  }, [user?.display_name, user?.gender]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSavedMessage(false);
    const updated = await updateMe.mutateAsync({
      displayName: name.trim(),
      gender: gender || null,
    });
    setUser(updated);
    setSavedMessage(true);
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="space-y-2 rounded-lg border border-slate-200 bg-white p-4"
    >
      <h2 className="text-sm font-semibold text-slate-900">{t("preferences.myNameTitle")}</h2>
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
      />
      <p className="text-xs text-slate-400">{t("preferences.myNameHint")}</p>

      <label className="block text-sm">
        <span className="mb-1 block text-slate-600">{t("preferences.genderTitle")}</span>
        <select
          value={gender}
          onChange={(e) => setGender(e.target.value as Gender | "")}
          className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">{t("preferences.genderUnset")}</option>
          <option value="male">{t("preferences.genderMale")}</option>
          <option value="female">{t("preferences.genderFemale")}</option>
        </select>
        <span className="mt-1 block text-xs text-slate-400">{t("preferences.genderHint")}</span>
      </label>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={updateMe.isPending || !name.trim()}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {t("common.save")}
        </button>
        {savedMessage && !updateMe.isPending && (
          <span className="text-sm text-emerald-600">{t("common.saved")}</span>
        )}
      </div>
    </form>
  );
}

function NotificationsSection() {
  const { t } = useTranslation();
  const subscriptionQuery = useCurrentPushSubscription();
  const enable = useEnablePushNotifications();
  const disable = useDisablePushNotifications();
  const sendTest = useSendTestNotification();

  if (!isPushSupported()) {
    return (
      <section className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-900">{t("notifications.title")}</h2>
        <p className="text-sm text-slate-500">{t("notifications.unsupported")}</p>
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
      <h2 className="text-sm font-semibold text-slate-900">{t("notifications.title")}</h2>
      <p className="text-xs text-slate-500">{t("notifications.description")}</p>

      <div className="flex flex-wrap items-center gap-2">
        {isSubscribed ? (
          <button
            type="button"
            onClick={() => disable.mutate()}
            disabled={disable.isPending}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {disable.isPending ? t("notifications.disabling") : t("notifications.disable")}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => enable.mutate()}
            disabled={enable.isPending}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {enable.isPending ? t("notifications.enabling") : t("notifications.enable")}
          </button>
        )}

        {isSubscribed && (
          <button
            type="button"
            onClick={() => sendTest.mutate()}
            disabled={sendTest.isPending}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {sendTest.isPending ? t("notifications.sending") : t("notifications.sendTest")}
          </button>
        )}
      </div>

      {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
      {sendTest.isSuccess && sendTest.data.sent === 0 && (
        <p className="text-sm text-amber-600">{t("notifications.testNotSent")}</p>
      )}
      {sendTest.isSuccess && sendTest.data.sent > 0 && (
        <p className="text-sm text-emerald-600">{t("notifications.testSent")}</p>
      )}
    </section>
  );
}

function AliceSection() {
  const { t, i18n } = useTranslation();
  const statusQuery = useAliceLinkStatus();
  const issueToken = useIssueAliceToken();
  const revokeToken = useRevokeAliceToken();

  const webhookUrl = issueToken.data
    ? `${window.location.origin}${issueToken.data.webhook_url}`
    : null;

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">{t("alice.title")}</h2>
      <p className="text-xs text-slate-500">{t("alice.description")}</p>

      {statusQuery.data?.linked && !webhookUrl && (
        <p className="text-sm text-slate-600">
          {statusQuery.data.last_used_at
            ? t("alice.linkedLastUsed", {
                date: new Date(statusQuery.data.last_used_at).toLocaleString(i18n.language),
              })
            : `${t("alice.linked")}.`}
        </p>
      )}

      {webhookUrl && (
        <div className="space-y-1 rounded-md bg-slate-50 p-3 text-xs">
          <p className="font-medium text-slate-700">{t("alice.webhookInstructions")}</p>
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
            ? t("alice.generating")
            : statusQuery.data?.linked
              ? t("alice.regenerate")
              : t("alice.generate")}
        </button>

        {statusQuery.data?.linked && (
          <button
            type="button"
            onClick={() => revokeToken.mutate()}
            disabled={revokeToken.isPending}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {revokeToken.isPending ? t("alice.unlinking") : t("alice.unlink")}
          </button>
        )}
      </div>
    </section>
  );
}

const TASK_SPEED_PRESETS = [
  { value: 0.75, labelKey: "preferences.taskSpeedFaster" },
  { value: 1, labelKey: "preferences.taskSpeedNormal" },
  { value: 1.3, labelKey: "preferences.taskSpeedSlower" },
] as const;

function nearestTaskSpeedPreset(value: number): number {
  return TASK_SPEED_PRESETS.reduce<number>(
    (best, preset) => (Math.abs(preset.value - value) < Math.abs(best - value) ? preset.value : best),
    TASK_SPEED_PRESETS[0].value,
  );
}

interface PreferencesDraft {
  workplace: string;
  energyPattern: EnergyPattern;
  taskSpeed: number;
  hasFixedWorkingHours: boolean;
  workingStart: string;
  workingEnd: string;
  hasPredictableSleep: boolean;
  sleepStart: string;
  sleepEnd: string;
  notes: string;
}

const DRAFT_STORAGE_KEY = "home_manager_preferences_draft";

function loadDraft(): PreferencesDraft | null {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PreferencesDraft) : null;
  } catch {
    return null;
  }
}

function saveDraft(draft: PreferencesDraft): void {
  try {
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Best-effort — losing the draft just means falling back to server data.
  }
}

function clearDraft(): void {
  localStorage.removeItem(DRAFT_STORAGE_KEY);
}

export function PreferencesPage() {
  const { t } = useTranslation();
  const prefsQuery = useMyPreferences();
  const updatePrefs = useUpdateMyPreferences();

  const [workplace, setWorkplace] = useState("");
  const [energyPattern, setEnergyPattern] = useState<EnergyPattern>("steady");
  const [taskSpeed, setTaskSpeed] = useState(1);
  const [hasFixedWorkingHours, setHasFixedWorkingHours] = useState(false);
  const [workingStart, setWorkingStart] = useState("");
  const [workingEnd, setWorkingEnd] = useState("");
  const [hasPredictableSleep, setHasPredictableSleep] = useState(false);
  const [sleepStart, setSleepStart] = useState("");
  const [sleepEnd, setSleepEnd] = useState("");
  const [notes, setNotes] = useState("");
  const [savedMessage, setSavedMessage] = useState(false);

  const hasHydrated = useRef(false);

  useEffect(() => {
    const prefs = prefsQuery.data;
    if (!prefs) return;
    if (!hasHydrated.current) {
      const draft = loadDraft();
      hasHydrated.current = true;
      if (draft) {
        setWorkplace(draft.workplace);
        setEnergyPattern(draft.energyPattern);
        setTaskSpeed(draft.taskSpeed);
        setHasFixedWorkingHours(draft.hasFixedWorkingHours);
        setWorkingStart(draft.workingStart);
        setWorkingEnd(draft.workingEnd);
        setHasPredictableSleep(draft.hasPredictableSleep);
        setSleepStart(draft.sleepStart);
        setSleepEnd(draft.sleepEnd);
        setNotes(draft.notes);
        return;
      }
    }
    setWorkplace(prefs.workplace ?? "");
    setEnergyPattern(prefs.energy_pattern);
    setTaskSpeed(nearestTaskSpeedPreset(prefs.task_speed_multiplier));
    setHasFixedWorkingHours(Boolean(prefs.working_hours_start && prefs.working_hours_end));
    setWorkingStart(prefs.working_hours_start ?? "");
    setWorkingEnd(prefs.working_hours_end ?? "");
    setHasPredictableSleep(Boolean(prefs.sleep_start && prefs.sleep_end));
    setSleepStart(prefs.sleep_start ?? "");
    setSleepEnd(prefs.sleep_end ?? "");
    setNotes(prefs.notes ?? "");
  }, [prefsQuery.data]);

  // Persist in-progress edits so switching browser tabs (or app routes) and
  // coming back doesn't lose them — mirrors the assistant page's draft.
  useEffect(() => {
    if (!hasHydrated.current) return;
    saveDraft({
      workplace,
      energyPattern,
      taskSpeed,
      hasFixedWorkingHours,
      workingStart,
      workingEnd,
      hasPredictableSleep,
      sleepStart,
      sleepEnd,
      notes,
    });
  }, [
    workplace,
    energyPattern,
    taskSpeed,
    hasFixedWorkingHours,
    workingStart,
    workingEnd,
    hasPredictableSleep,
    sleepStart,
    sleepEnd,
    notes,
  ]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSavedMessage(false);
    await updatePrefs.mutateAsync({
      workplace: workplace.trim() || null,
      energy_pattern: energyPattern,
      task_speed_multiplier: taskSpeed,
      working_hours_start: hasFixedWorkingHours && workingStart ? workingStart : null,
      working_hours_end: hasFixedWorkingHours && workingEnd ? workingEnd : null,
      sleep_start: hasPredictableSleep && sleepStart ? sleepStart : null,
      sleep_end: hasPredictableSleep && sleepEnd ? sleepEnd : null,
      notes: notes || null,
    });
    clearDraft();
    setSavedMessage(true);
  }

  if (prefsQuery.isLoading) {
    return <p className="text-sm text-slate-500">{t("preferences.loading")}</p>;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("preferences.title")}</h1>
      <p className="text-xs text-slate-500">{t("preferences.subtitle")}</p>

      <Link
        to="/household"
        className="block rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-blue-600 hover:bg-slate-50"
      >
        {t("preferences.householdLink")}
      </Link>

      <MyNameSection />
      <NotificationsSection />
      <AliceSection />

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-4"
      >
        <h2 className="text-sm font-semibold text-slate-900">{t("preferences.aboutMeTitle")}</h2>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-600">{t("preferences.workplace")}</span>
          <input
            type="text"
            value={workplace}
            onChange={(e) => setWorkplace(e.target.value)}
            placeholder={t("preferences.workplacePlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5"
          />
          <span className="mt-1 block text-xs text-slate-400">{t("preferences.workplaceHint")}</span>
        </label>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={hasFixedWorkingHours}
              onChange={(e) => setHasFixedWorkingHours(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            {t("preferences.fixedWorkingHours")}
          </label>
          <p className="pl-6 text-xs text-slate-400">{t("preferences.fixedWorkingHoursHint")}</p>
          {hasFixedWorkingHours && (
            <div className="grid grid-cols-2 gap-3 pl-6">
              <label className="text-sm">
                <span className="mb-1 block text-slate-600">
                  {t("preferences.workingHoursStart")}
                </span>
                <input
                  type="time"
                  value={workingStart}
                  onChange={(e) => setWorkingStart(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-2 py-1.5"
                />
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-slate-600">
                  {t("preferences.workingHoursEnd")}
                </span>
                <input
                  type="time"
                  value={workingEnd}
                  onChange={(e) => setWorkingEnd(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-2 py-1.5"
                />
              </label>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={hasPredictableSleep}
              onChange={(e) => setHasPredictableSleep(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            {t("preferences.predictableSleep")}
          </label>
          <p className="pl-6 text-xs text-slate-400">{t("preferences.predictableSleepHint")}</p>
          {hasPredictableSleep && (
            <div className="grid grid-cols-2 gap-3 pl-6">
              <label className="text-sm">
                <span className="mb-1 block text-slate-600">{t("preferences.sleepStart")}</span>
                <input
                  type="time"
                  value={sleepStart}
                  onChange={(e) => setSleepStart(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-2 py-1.5"
                />
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-slate-600">{t("preferences.sleepEnd")}</span>
                <input
                  type="time"
                  value={sleepEnd}
                  onChange={(e) => setSleepEnd(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-2 py-1.5"
                />
              </label>
            </div>
          )}
        </div>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-600">{t("preferences.energyPattern")}</span>
          <select
            value={energyPattern}
            onChange={(e) => setEnergyPattern(e.target.value as EnergyPattern)}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5"
          >
            <option value="morning">{t("preferences.energyMorning")}</option>
            <option value="evening">{t("preferences.energyEvening")}</option>
            <option value="steady">{t("preferences.energySteady")}</option>
          </select>
          <span className="mt-1 block text-xs text-slate-400">{t("preferences.energyPatternHint")}</span>
        </label>

        <div className="text-sm">
          <span className="mb-1 block text-slate-600">{t("preferences.taskSpeedTitle")}</span>
          <div className="flex gap-2">
            {TASK_SPEED_PRESETS.map((preset) => (
              <button
                key={preset.value}
                type="button"
                onClick={() => setTaskSpeed(preset.value)}
                className={`flex-1 rounded-md border px-2 py-1.5 text-sm font-medium ${
                  taskSpeed === preset.value
                    ? "border-blue-600 bg-blue-50 text-blue-700"
                    : "border-slate-300 text-slate-700 hover:bg-slate-50"
                }`}
              >
                {t(preset.labelKey)}
              </button>
            ))}
          </div>
          <span className="mt-1 block text-xs text-slate-400">{t("preferences.taskSpeedHint")}</span>
        </div>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-600">{t("preferences.notes")}</span>
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
            {updatePrefs.isPending ? t("preferences.saving") : t("common.save")}
          </button>
          {savedMessage && !updatePrefs.isPending && (
            <span className="text-sm text-emerald-600">{t("common.saved")}</span>
          )}
        </div>
      </form>
    </div>
  );
}
