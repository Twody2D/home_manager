import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { TaskCreateInput, TaskPriority, User } from "../api/types";

interface TaskFormProps {
  members: User[];
  onSubmit: (input: TaskCreateInput) => Promise<void>;
  isSubmitting: boolean;
}

const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

export function TaskForm({ members, onSubmit, isSubmitting }: TaskFormProps) {
  const { t } = useTranslation();
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [assignedTo, setAssignedTo] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("");
  const [showBudget, setShowBudget] = useState(false);
  const [budgetAmount, setBudgetAmount] = useState("");
  const [budgetOwnerId, setBudgetOwnerId] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;

    await onSubmit({
      title: title.trim(),
      priority,
      assigned_to: assignedTo || null,
      due_at: dueAt ? new Date(dueAt).toISOString() : null,
      duration_minutes: durationMinutes ? Number(durationMinutes) : null,
      budget_amount: budgetAmount || null,
      budget_owner_user_id: budgetAmount ? budgetOwnerId || null : null,
    });

    setTitle("");
    setPriority("medium");
    setAssignedTo("");
    setDueAt("");
    setDurationMinutes("");
    setShowBudget(false);
    setBudgetAmount("");
    setBudgetOwnerId("");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
      <input
        type="text"
        placeholder={t("tasks.newTaskPlaceholder")}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />

      <div className="flex flex-wrap gap-2">
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as TaskPriority)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {t(`taskPriority.${p}`)}
            </option>
          ))}
        </select>

        <select
          value={assignedTo}
          onChange={(e) => setAssignedTo(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">{t("tasks.unassigned")}</option>
          {members.map((member) => (
            <option key={member.id} value={member.id}>
              {member.display_name}
            </option>
          ))}
        </select>

        <input
          type="datetime-local"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />

        <input
          type="number"
          min={1}
          placeholder={t("tasks.durationPlaceholder")}
          value={durationMinutes}
          onChange={(e) => setDurationMinutes(e.target.value)}
          className="w-32 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />

        {!showBudget ? (
          <button
            type="button"
            onClick={() => setShowBudget(true)}
            className="rounded-md border border-dashed border-slate-300 px-2 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            + {t("tasks.budget.add")}
          </button>
        ) : (
          <>
            <input
              type="number"
              min="0.01"
              step="0.01"
              placeholder={t("tasks.budget.amountPlaceholder")}
              value={budgetAmount}
              onChange={(e) => setBudgetAmount(e.target.value)}
              className="w-28 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
            <select
              value={budgetOwnerId}
              onChange={(e) => setBudgetOwnerId(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            >
              <option value="">{t("tasks.budget.shared")}</option>
              {members.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.display_name}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                setShowBudget(false);
                setBudgetAmount("");
                setBudgetOwnerId("");
              }}
              className="rounded-md px-2 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-100"
            >
              {t("finance.subscriptions.cancel")}
            </button>
          </>
        )}

        <button
          type="submit"
          disabled={isSubmitting || !title.trim()}
          className="ml-auto rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {t("common.add")}
        </button>
      </div>
    </form>
  );
}
