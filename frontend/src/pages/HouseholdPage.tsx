import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { useCreateInviteLink, useHousehold, useMembers, useUpdateHousehold } from "../hooks/useMembers";
import { householdTitle } from "../lib/householdTitle";
import type { User } from "../api/types";

function HouseholdNameSection({ isOwner, members }: { isOwner: boolean; members: User[] }) {
  const { t } = useTranslation();
  const householdQuery = useHousehold();
  const updateHousehold = useUpdateHousehold();
  const [name, setName] = useState("");
  const [savedMessage, setSavedMessage] = useState(false);

  useEffect(() => {
    setName(householdQuery.data?.display_name ?? "");
  }, [householdQuery.data]);

  const autoName = householdTitle(undefined, members);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSavedMessage(false);
    await updateHousehold.mutateAsync(name.trim() || null);
    setSavedMessage(true);
  }

  if (!isOwner) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-900">{t("household.nameTitle")}</h2>
        <p className="mt-1 text-sm text-slate-700">
          {householdQuery.data?.display_name || autoName}
        </p>
      </section>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-2 rounded-lg border border-slate-200 bg-white p-4"
    >
      <h2 className="text-sm font-semibold text-slate-900">{t("household.nameTitle")}</h2>
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder={autoName}
        className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
      />
      <p className="text-xs text-slate-400">{t("household.nameHint", { auto: autoName })}</p>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={updateHousehold.isPending}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {t("common.save")}
        </button>
        {savedMessage && !updateHousehold.isPending && (
          <span className="text-sm text-emerald-600">{t("common.saved")}</span>
        )}
      </div>
    </form>
  );
}

function MemberCard({ member, isYou, t }: { member: User; isYou: boolean; t: (key: string) => string }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2.5">
      <div>
        <p className="text-sm font-medium text-slate-900">
          {member.display_name}
          {isYou && <span className="ml-1.5 text-xs font-normal text-slate-500">({t("household.you")})</span>}
        </p>
        <p className="text-xs text-slate-500">{member.email}</p>
      </div>
      <span className="text-xs text-slate-500">
        {member.role === "owner" ? t("household.owner") : t("household.member")}
      </span>
    </div>
  );
}

export function HouseholdPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const membersQuery = useMembers();
  const createInviteLink = useCreateInviteLink();
  const [copied, setCopied] = useState(false);

  const members = membersQuery.data ?? [];
  const me = members.find((member) => member.id === user?.id);
  const others = members.filter((member) => member.id !== user?.id);
  const isOwner = user?.role === "owner";

  const inviteUrl = createInviteLink.data
    ? `${window.location.origin}/invite/${createInviteLink.data.token}`
    : null;

  async function handleCopy() {
    if (!inviteUrl) return;
    await navigator.clipboard.writeText(inviteUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{t("household.title")}</h1>
        <p className="text-xs text-slate-500">{t("household.subtitle")}</p>
      </div>

      <HouseholdNameSection isOwner={isOwner} members={members} />

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-500">{t("household.myProfile")}</h2>
        {me && <MemberCard member={me} isYou t={t} />}
        <Link to="/preferences" className="block text-xs font-medium text-blue-600">
          {t("household.editInPreferences")}
        </Link>
      </section>

      {others.length > 0 && (
        <section className="space-y-2">
          {others.map((member) => (
            <MemberCard key={member.id} member={member} isYou={false} t={t} />
          ))}
        </section>
      )}

      {others.length === 0 && (
        <p className="text-sm text-slate-500">{t("household.noPartnerYet")}</p>
      )}

      {isOwner && (
        <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">{t("household.inviteTitle")}</h2>
          <p className="text-xs text-slate-500">{t("household.inviteIntro")}</p>

          <button
            type="button"
            onClick={() => createInviteLink.mutate()}
            disabled={createInviteLink.isPending}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {createInviteLink.isPending
              ? t("household.inviteGenerating")
              : t("household.inviteGenerate")}
          </button>

          {inviteUrl && createInviteLink.data && (
            <div className="space-y-1.5 rounded-md bg-slate-50 p-3">
              <code className="block break-all rounded bg-white p-2 text-xs text-slate-800">
                {inviteUrl}
              </code>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void handleCopy()}
                  className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
                >
                  {copied ? t("household.inviteCopied") : t("household.inviteCopy")}
                </button>
                <span className="text-xs text-slate-500">
                  {t("household.inviteExpiresAt", {
                    date: new Date(createInviteLink.data.expires_at).toLocaleString(i18n.language),
                  })}
                </span>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
