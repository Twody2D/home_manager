import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useMyPreferences, useUpdateMyPreferences } from "../hooks/usePreferences";
import { useInviteMember, useMembers } from "../hooks/useMembers";
import {
  isPushSupported,
  useCurrentPushSubscription,
  useDisablePushNotifications,
  useEnablePushNotifications,
  useSendTestNotification,
} from "../hooks/useNotifications";
import { useAliceLinkStatus, useIssueAliceToken, useRevokeAliceToken } from "../hooks/useAlice";
import { useAuth } from "../auth/useAuth";
import { ApiError } from "../api/client";
import type { EnergyPattern } from "../api/types";

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

function HouseholdSection() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const membersQuery = useMembers();
  const inviteMember = useInviteMember();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [successName, setSuccessName] = useState<string | null>(null);

  const members = membersQuery.data ?? [];
  const isOwner = user?.role === "owner";

  async function handleInvite(event: FormEvent) {
    event.preventDefault();
    setSuccessName(null);
    const invited = await inviteMember.mutateAsync({ display_name: name, email, password });
    setSuccessName(invited.display_name);
    setName("");
    setEmail("");
    setPassword("");
  }

  const inviteError =
    inviteMember.error instanceof ApiError ? inviteMember.error.message : null;

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">{t("household.title")}</h2>

      <ul className="space-y-1.5">
        {members.map((member) => (
          <li
            key={member.id}
            className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm"
          >
            <span className="text-slate-900">
              {member.display_name}
              {member.id === user?.id && (
                <span className="ml-1.5 text-xs text-slate-500">({t("household.you")})</span>
              )}
            </span>
            <span className="text-xs text-slate-500">
              {member.role === "owner" ? t("household.owner") : t("household.member")}
            </span>
          </li>
        ))}
      </ul>

      {isOwner && (
        <form onSubmit={handleInvite} className="space-y-2 border-t border-slate-100 pt-3">
          <p className="text-xs text-slate-500">{t("household.inviteIntro")}</p>

          <label className="block text-sm">
            <span className="mb-1 block text-slate-600">{t("household.inviteName")}</span>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5"
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-slate-600">{t("household.inviteEmail")}</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5"
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-slate-600">{t("household.invitePassword")}</span>
            <input
              type="text"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5"
            />
            <span className="mt-1 block text-xs text-slate-400">
              {t("household.invitePasswordHint")}
            </span>
          </label>

          {inviteError && <p className="text-sm text-red-600">{inviteError}</p>}
          {successName && (
            <p className="text-sm text-emerald-600">
              {t("household.inviteSuccess", { name: successName })}
            </p>
          )}

          <button
            type="submit"
            disabled={inviteMember.isPending}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {inviteMember.isPending ? t("household.inviteSubmitting") : t("household.inviteSubmit")}
          </button>
        </form>
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

function taskSpeedLabel(
  t: ReturnType<typeof useTranslation>["t"],
  multiplier: number,
): string {
  const percent = Math.round(Math.abs(multiplier - 1) * 100);
  if (percent < 5) return t("preferences.taskSpeedAverage");
  return multiplier < 1
    ? t("preferences.taskSpeedFasterBy", { percent })
    : t("preferences.taskSpeedSlowerBy", { percent });
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

  useEffect(() => {
    const prefs = prefsQuery.data;
    if (!prefs) return;
    setWorkplace(prefs.workplace ?? "");
    setEnergyPattern(prefs.energy_pattern);
    setTaskSpeed(prefs.task_speed_multiplier);
    setHasFixedWorkingHours(Boolean(prefs.working_hours_start && prefs.working_hours_end));
    setWorkingStart(prefs.working_hours_start ?? "");
    setWorkingEnd(prefs.working_hours_end ?? "");
    setHasPredictableSleep(Boolean(prefs.sleep_start && prefs.sleep_end));
    setSleepStart(prefs.sleep_start ?? "");
    setSleepEnd(prefs.sleep_end ?? "");
    setNotes(prefs.notes ?? "");
  }, [prefsQuery.data]);

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
    setSavedMessage(true);
  }

  if (prefsQuery.isLoading) {
    return <p className="text-sm text-slate-500">{t("preferences.loading")}</p>;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("preferences.title")}</h1>
      <p className="text-xs text-slate-500">{t("preferences.subtitle")}</p>

      <NotificationsSection />
      <AliceSection />
      <HouseholdSection />

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
        </label>

        <div className="text-sm">
          <span className="mb-1 block text-slate-600">{t("preferences.taskSpeedTitle")}</span>
          <input
            type="range"
            min="0.5"
            max="2"
            step="0.1"
            value={taskSpeed}
            onChange={(e) => setTaskSpeed(Number(e.target.value))}
            className="w-full"
          />
          <p className="mt-1 text-sm text-slate-700">{taskSpeedLabel(t, taskSpeed)}</p>
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
