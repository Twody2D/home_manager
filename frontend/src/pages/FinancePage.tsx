import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/useAuth";
import { useMembers } from "../hooks/useMembers";
import {
  useCreateIncome,
  useCreateSubscription,
  useDeleteIncome,
  useDeleteSubscription,
  useIncomes,
  useSubscriptions,
  useUpdateSubscription,
} from "../hooks/useFinance";
import { formatMoney } from "../lib/money";
import { SCOPE_BORDER_STYLES, scopeForOwner } from "../lib/personScope";
import type { Income, Subscription, SubscriptionCadence, SubscriptionKind, User } from "../api/types";

function sumAmounts(items: { amount: string }[]): number {
  return items.reduce((total, item) => total + Number(item.amount), 0);
}

// Yearly subscriptions are amortized into the monthly total so it reflects
// what the household actually sets aside per month, not just what's billed
// this month.
function sumMonthlyEquivalent(items: { amount: string; cadence: SubscriptionCadence }[]): number {
  return items.reduce(
    (total, item) =>
      total + (item.cadence === "yearly" ? Number(item.amount) / 12 : Number(item.amount)),
    0,
  );
}

function DeleteIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
      <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
    </svg>
  );
}

function FieldLabel({ children }: { children: string }) {
  return <span className="mb-1 block text-xs font-medium text-slate-600">{children}</span>;
}

function IncomeSection() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const membersQuery = useMembers();
  const incomesQuery = useIncomes();
  const createIncome = useCreateIncome();
  const deleteIncome = useDeleteIncome();

  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));
  const incomes = incomesQuery.data?.items ?? [];

  const [label, setLabel] = useState("");
  const [amount, setAmount] = useState("");
  const [paymentDay, setPaymentDay] = useState("25");
  const [forUserId, setForUserId] = useState(user?.id ?? "");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!label.trim() || !amount) return;
    await createIncome.mutateAsync({
      user_id: forUserId || null,
      label: label.trim(),
      amount,
      payment_day: Number(paymentDay),
    });
    setLabel("");
    setAmount("");
  }

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">{t("finance.income.title")}</h2>
        <span className="text-sm font-medium text-emerald-600">
          {formatMoney(sumAmounts(incomes), i18n.language)}
        </span>
      </div>

      {incomes.length === 0 ? (
        <p className="text-sm text-slate-400">{t("finance.income.empty")}</p>
      ) : (
        <ul className="space-y-1.5">
          {incomes.map((income: Income) => (
            <li key={income.id} className="rounded-md border border-slate-200 px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <p className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900">
                  {income.label}
                </p>
                <span className="shrink-0 text-sm font-medium text-slate-900">
                  {formatMoney(income.amount, i18n.language)}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between gap-2">
                <p className="min-w-0 truncate text-xs text-slate-500">
                  {membersById.get(income.user_id)?.display_name ?? "—"} ·{" "}
                  {t("finance.dayOfMonth", { day: income.payment_day })}
                </p>
                <button
                  type="button"
                  onClick={() => deleteIncome.mutate(income.id)}
                  aria-label={t("finance.income.delete")}
                  className="shrink-0 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                >
                  <DeleteIcon />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form
        onSubmit={(e) => void handleSubmit(e)}
        className="grid grid-cols-2 gap-2 border-t border-slate-100 pt-3"
      >
        <label className="col-span-2 block text-sm">
          <FieldLabel>{t("finance.income.nameLabel")}</FieldLabel>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder={t("finance.income.labelPlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="block text-sm">
          <FieldLabel>{t("finance.income.amountLabel")}</FieldLabel>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder={t("finance.income.amountPlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="block text-sm">
          <FieldLabel>{t("finance.income.paymentDay")}</FieldLabel>
          <input
            type="number"
            min="1"
            max="31"
            value={paymentDay}
            onChange={(e) => setPaymentDay(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        {members.length > 1 && (
          <label className="col-span-2 block text-sm">
            <FieldLabel>{t("finance.income.forUser")}</FieldLabel>
            <select
              value={forUserId}
              onChange={(e) => setForUserId(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            >
              {members.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.display_name}
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          type="submit"
          disabled={createIncome.isPending || !label.trim() || !amount}
          className="col-span-2 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {createIncome.isPending ? t("finance.income.adding") : t("finance.income.add")}
        </button>
      </form>
    </section>
  );
}

interface SubscriptionDraft {
  name: string;
  amount: string;
  cadence: SubscriptionCadence;
  paymentDay: string;
  paymentMonth: string;
  ownerId: string;
}

function emptySubscriptionDraft(): SubscriptionDraft {
  return { name: "", amount: "", cadence: "monthly", paymentDay: "1", paymentMonth: "1", ownerId: "" };
}

function subscriptionToDraft(subscription: Subscription): SubscriptionDraft {
  return {
    name: subscription.name,
    amount: subscription.amount,
    cadence: subscription.cadence,
    paymentDay: String(subscription.payment_day),
    paymentMonth: String(subscription.payment_month ?? 1),
    ownerId: subscription.owner_user_id ?? "",
  };
}

function SubscriptionFields({
  draft,
  onChange,
  members,
  nameLabel,
  namePlaceholder,
}: {
  draft: SubscriptionDraft;
  onChange: (draft: SubscriptionDraft) => void;
  members: User[];
  nameLabel: string;
  namePlaceholder: string;
}) {
  const { t } = useTranslation();
  return (
    <>
      <label className="col-span-2 block text-sm">
        <FieldLabel>{nameLabel}</FieldLabel>
        <input
          type="text"
          value={draft.name}
          onChange={(e) => onChange({ ...draft, name: e.target.value })}
          placeholder={namePlaceholder}
          className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />
      </label>
      <label className="block text-sm">
        <FieldLabel>{t("finance.subscriptions.amountLabel")}</FieldLabel>
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={draft.amount}
          onChange={(e) => onChange({ ...draft, amount: e.target.value })}
          placeholder={t("finance.subscriptions.amountPlaceholder")}
          className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />
      </label>
      <label className="block text-sm">
        <FieldLabel>{t("finance.subscriptions.cadence")}</FieldLabel>
        <select
          value={draft.cadence}
          onChange={(e) => onChange({ ...draft, cadence: e.target.value as SubscriptionCadence })}
          className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="monthly">{t("finance.subscriptions.cadenceMonthly")}</option>
          <option value="yearly">{t("finance.subscriptions.cadenceYearly")}</option>
        </select>
      </label>
      <label className="block text-sm">
        <FieldLabel>{t("finance.subscriptions.paymentDay")}</FieldLabel>
        <input
          type="number"
          min="1"
          max="31"
          value={draft.paymentDay}
          onChange={(e) => onChange({ ...draft, paymentDay: e.target.value })}
          className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />
      </label>
      {draft.cadence === "yearly" && (
        <label className="block text-sm">
          <FieldLabel>{t("finance.subscriptions.paymentMonth")}</FieldLabel>
          <select
            value={draft.paymentMonth}
            onChange={(e) => onChange({ ...draft, paymentMonth: e.target.value })}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
              <option key={month} value={month}>
                {t(`month.${month}`)}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="col-span-2 block text-sm">
        <FieldLabel>{t("finance.subscriptions.owner")}</FieldLabel>
        <select
          value={draft.ownerId}
          onChange={(e) => onChange({ ...draft, ownerId: e.target.value })}
          className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">{t("finance.subscriptions.ownerNone")}</option>
          {members.map((member) => (
            <option key={member.id} value={member.id}>
              {member.display_name}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

function SubscriptionSection({
  kind,
  title,
  emptyText,
  nameLabel,
  namePlaceholder,
  addLabel,
}: {
  kind: SubscriptionKind;
  title: string;
  emptyText: string;
  nameLabel: string;
  namePlaceholder: string;
  addLabel: string;
}) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const membersQuery = useMembers();
  const subscriptionsQuery = useSubscriptions();
  const createSubscription = useCreateSubscription();
  const updateSubscription = useUpdateSubscription();
  const deleteSubscription = useDeleteSubscription();

  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));
  const partner = members.find((member) => member.id !== user?.id);
  const subscriptions = (subscriptionsQuery.data?.items ?? []).filter((s) => s.kind === kind);
  const activeSubscriptions = subscriptions.filter((s: Subscription) => s.active);

  const [draft, setDraft] = useState<SubscriptionDraft>(emptySubscriptionDraft());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<SubscriptionDraft>(emptySubscriptionDraft());

  function draftToInput(d: SubscriptionDraft) {
    return {
      name: d.name.trim(),
      amount: d.amount,
      kind,
      cadence: d.cadence,
      payment_day: Number(d.paymentDay),
      payment_month: d.cadence === "yearly" ? Number(d.paymentMonth) : null,
      owner_user_id: d.ownerId || null,
    };
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!draft.name.trim() || !draft.amount) return;
    await createSubscription.mutateAsync(draftToInput(draft));
    setDraft(emptySubscriptionDraft());
  }

  function startEditing(subscription: Subscription) {
    setEditingId(subscription.id);
    setEditDraft(subscriptionToDraft(subscription));
  }

  async function handleEditSubmit(event: FormEvent) {
    event.preventDefault();
    if (!editingId || !editDraft.name.trim() || !editDraft.amount) return;
    await updateSubscription.mutateAsync({ id: editingId, input: draftToInput(editDraft) });
    setEditingId(null);
  }

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        <span className="text-sm font-medium text-emerald-600">
          {formatMoney(sumMonthlyEquivalent(activeSubscriptions), i18n.language)}
        </span>
      </div>

      {subscriptions.length === 0 ? (
        <p className="text-sm text-slate-400">{emptyText}</p>
      ) : (
        <ul className="space-y-1.5">
          {subscriptions.map((subscription: Subscription) => {
            if (editingId === subscription.id) {
              return (
                <li key={subscription.id} className="rounded-md border border-blue-300 px-3 py-2">
                  <form
                    onSubmit={(e) => void handleEditSubmit(e)}
                    className="grid grid-cols-2 gap-2"
                  >
                    <SubscriptionFields
                      draft={editDraft}
                      onChange={setEditDraft}
                      members={members}
                      nameLabel={nameLabel}
                      namePlaceholder={namePlaceholder}
                    />
                    <div className="col-span-2 flex gap-2">
                      <button
                        type="submit"
                        disabled={updateSubscription.isPending || !editDraft.name.trim() || !editDraft.amount}
                        className="flex-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
                      >
                        {t("finance.subscriptions.save")}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                      >
                        {t("finance.subscriptions.cancel")}
                      </button>
                    </div>
                  </form>
                </li>
              );
            }

            const owner = subscription.owner_user_id
              ? membersById.get(subscription.owner_user_id)
              : undefined;
            const scope = scopeForOwner(subscription.owner_user_id, user?.id, partner?.id);
            return (
              <li
                key={subscription.id}
                className={`rounded-md border border-slate-200 px-3 py-2 ${SCOPE_BORDER_STYLES[scope]} ${
                  subscription.active ? "" : "opacity-50"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900">
                    {subscription.name}
                    {subscription.cadence === "yearly" && (
                      <span className="ml-1.5 text-xs font-normal text-slate-500">
                        ({t("finance.subscriptions.yearlyBadge")})
                      </span>
                    )}
                    {!subscription.active && (
                      <span className="ml-1.5 text-xs font-normal text-slate-500">
                        ({t("finance.subscriptions.inactiveBadge")})
                      </span>
                    )}
                  </p>
                  <span className="shrink-0 text-sm font-medium text-slate-900">
                    {formatMoney(subscription.amount, i18n.language)}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between gap-2">
                  <p className="min-w-0 truncate text-xs text-slate-500">
                    {subscription.cadence === "yearly"
                      ? `${t(`month.${subscription.payment_month}`)}, ${subscription.payment_day}`
                      : t("finance.dayOfMonth", { day: subscription.payment_day })}
                    {" · "}
                    {owner ? owner.display_name : t("finance.subscriptions.ownerNone")}
                  </p>
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => startEditing(subscription)}
                      className="rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      {t("finance.subscriptions.edit")}
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        updateSubscription.mutate({
                          id: subscription.id,
                          input: { active: !subscription.active },
                        })
                      }
                      className="rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      {subscription.active
                        ? t("finance.subscriptions.deactivate")
                        : t("finance.subscriptions.activate")}
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteSubscription.mutate(subscription.id)}
                      aria-label={t("finance.subscriptions.delete")}
                      className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                    >
                      <DeleteIcon />
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <form
        onSubmit={(e) => void handleSubmit(e)}
        className="grid grid-cols-2 gap-2 border-t border-slate-100 pt-3"
      >
        <SubscriptionFields
          draft={draft}
          onChange={setDraft}
          members={members}
          nameLabel={nameLabel}
          namePlaceholder={namePlaceholder}
        />
        <button
          type="submit"
          disabled={createSubscription.isPending || !draft.name.trim() || !draft.amount}
          className="col-span-2 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {createSubscription.isPending ? t("finance.subscriptions.adding") : addLabel}
        </button>
      </form>
    </section>
  );
}

export function FinancePage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{t("finance.title")}</h1>
        <p className="text-xs text-slate-500">{t("finance.subtitle")}</p>
      </div>

      <IncomeSection />
      <SubscriptionSection
        kind="subscription"
        title={t("finance.subscriptions.title")}
        emptyText={t("finance.subscriptions.empty")}
        nameLabel={t("finance.subscriptions.nameLabel")}
        namePlaceholder={t("finance.subscriptions.namePlaceholder")}
        addLabel={t("finance.subscriptions.add")}
      />
      <SubscriptionSection
        kind="recurring_expense"
        title={t("finance.recurring.title")}
        emptyText={t("finance.recurring.empty")}
        nameLabel={t("finance.recurring.nameLabel")}
        namePlaceholder={t("finance.recurring.namePlaceholder")}
        addLabel={t("finance.recurring.add")}
      />
    </div>
  );
}
