import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  useCreateTask,
  useDeleteTask,
  useTask,
  useTasks,
  useTaskLists,
  useUpdateTask,
} from "../hooks/useTasks";
import { useMembers } from "../hooks/useMembers";
import type { TaskPriority, TaskUpdateInput } from "../api/types";

const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

function FieldLabel({ children }: { children: string }) {
  return <span className="mb-1 block text-xs font-medium text-slate-600">{children}</span>;
}

export function TaskDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { taskId } = useParams<{ taskId: string }>();

  const taskQuery = useTask(taskId);
  const task = taskQuery.data;
  const parentQuery = useTask(task?.parent_task_id ?? undefined);
  const membersQuery = useMembers();
  const taskListsQuery = useTaskLists();
  const allTasksQuery = useTasks({ limit: 100 });

  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();
  const createTask = useCreateTask();

  const members = membersQuery.data ?? [];
  const taskLists = taskListsQuery.data?.items ?? [];
  const subtasks = (allTasksQuery.data?.items ?? []).filter((t) => t.parent_task_id === task?.id);

  const [loadedId, setLoadedId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState("");
  const [location, setLocation] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [isAddingSubtask, setIsAddingSubtask] = useState(false);
  const [subtaskTitle, setSubtaskTitle] = useState("");

  useEffect(() => {
    if (task && task.id !== loadedId) {
      setTitle(task.title);
      setDescription(task.description ?? "");
      setDuration(task.duration_minutes ? String(task.duration_minutes) : "");
      setLocation(task.location ?? "");
      setBudgetAmount(task.budget_amount ?? "");
      setLoadedId(task.id);
    }
  }, [task, loadedId]);

  function save(input: TaskUpdateInput) {
    if (!task) return;
    updateTask.mutate({ id: task.id, input });
  }

  async function handleAddSubtask(event: FormEvent) {
    event.preventDefault();
    if (!task || !subtaskTitle.trim()) return;
    await createTask.mutateAsync({ title: subtaskTitle.trim(), parent_task_id: task.id });
    setSubtaskTitle("");
    setIsAddingSubtask(false);
  }

  async function handleDelete() {
    if (!task) return;
    await deleteTask.mutateAsync(task.id);
    navigate("/tasks");
  }

  if (taskQuery.isLoading) {
    return <p className="text-sm text-slate-500">{t("tasks.detail.loading")}</p>;
  }
  if (taskQuery.isError || !task) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-600">{t("tasks.detail.notFound")}</p>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-sm font-medium text-blue-600 hover:underline"
        >
          ← {t("tasks.detail.back")}
        </button>
      </div>
    );
  }

  const isCompleted = task.status === "completed";
  const isSubtask = task.parent_task_id !== null;

  return (
    <div className="space-y-4 pb-8">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-700"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M12.7 4.3a1 1 0 0 1 0 1.4L8.42 10l4.3 4.3a1 1 0 1 1-1.42 1.4l-5-5a1 1 0 0 1 0-1.4l5-5a1 1 0 0 1 1.42 0Z" />
        </svg>
        {t("tasks.detail.back")}
      </button>

      {isSubtask && parentQuery.data && (
        <p className="text-xs text-slate-500">
          {t("tasks.detail.parentTask", { title: parentQuery.data.title })}
        </p>
      )}

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={() => title.trim() && title.trim() !== task.title && save({ title: title.trim() })}
        placeholder={t("tasks.detail.titlePlaceholder")}
        className={`w-full border-b border-slate-200 pb-2 text-lg font-semibold focus:border-blue-500 focus:outline-none ${
          isCompleted ? "text-slate-400 line-through" : "text-slate-900"
        }`}
      />

      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        onBlur={() =>
          description !== (task.description ?? "") && save({ description: description || null })
        }
        placeholder={t("tasks.detail.descriptionPlaceholder")}
        rows={2}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />

      <div className="grid grid-cols-2 gap-3">
        <label className="block text-sm">
          <FieldLabel>{t("tasks.detail.priority")}</FieldLabel>
          <select
            value={task.priority}
            onChange={(e) => save({ priority: e.target.value as TaskPriority })}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {t(`taskPriority.${p}`)}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <FieldLabel>{t("tasks.detail.assignee")}</FieldLabel>
          <select
            value={task.assigned_to ?? ""}
            onChange={(e) => save({ assigned_to: e.target.value || null })}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">{t("tasks.unassigned")}</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <FieldLabel>{t("tasks.detail.dueDate")}</FieldLabel>
          <input
            type="datetime-local"
            defaultValue={toDatetimeLocal(task.due_at)}
            onChange={(e) =>
              save({ due_at: e.target.value ? new Date(e.target.value).toISOString() : null })
            }
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <label className="block text-sm">
          <FieldLabel>{t("tasks.detail.duration")}</FieldLabel>
          <input
            type="number"
            min={1}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            onBlur={() => {
              const next = duration ? Number(duration) : null;
              if (next !== task.duration_minutes) save({ duration_minutes: next });
            }}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <label className="col-span-2 block text-sm">
          <FieldLabel>{t("tasks.detail.location")}</FieldLabel>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            onBlur={() => location !== (task.location ?? "") && save({ location: location || null })}
            placeholder={t("tasks.detail.locationPlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        {!isSubtask && (
          <label className="col-span-2 block text-sm">
            <FieldLabel>{t("tasks.detail.list")}</FieldLabel>
            <select
              value={task.list_id ?? ""}
              onChange={(e) => save({ list_id: e.target.value || null })}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            >
              <option value="">{t("tasks.myTasks")}</option>
              {taskLists.map((list) => (
                <option key={list.id} value={list.id}>
                  {list.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block text-sm">
          <FieldLabel>{t("tasks.budget.add")}</FieldLabel>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={budgetAmount}
            onChange={(e) => setBudgetAmount(e.target.value)}
            onBlur={() =>
              budgetAmount !== (task.budget_amount ?? "") &&
              save({ budget_amount: budgetAmount || null })
            }
            placeholder={t("tasks.budget.amountPlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <label className="block text-sm">
          <FieldLabel>{t("tasks.budget.shared")}</FieldLabel>
          <select
            value={task.budget_owner_user_id ?? ""}
            onChange={(e) => save({ budget_owner_user_id: e.target.value || null })}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">{t("tasks.budget.shared")}</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!isSubtask && (
        <div className="space-y-2 border-t border-slate-100 pt-3">
          <h2 className="text-sm font-semibold text-slate-900">{t("tasks.detail.subtasksTitle")}</h2>
          {subtasks.length === 0 && <p className="text-sm text-slate-400">{t("tasks.empty")}</p>}
          <ul className="space-y-1.5">
            {subtasks.map((subtask) => (
              <li
                key={subtask.id}
                className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2 py-1.5"
              >
                <button
                  type="button"
                  onClick={() =>
                    updateTask.mutate({
                      id: subtask.id,
                      input: { status: subtask.status === "completed" ? "pending" : "completed" },
                    })
                  }
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 ${
                    subtask.status === "completed"
                      ? "border-blue-600 bg-blue-600"
                      : "border-slate-300"
                  }`}
                />
                <Link
                  to={`/tasks/${subtask.id}`}
                  className={`flex-1 truncate text-sm ${
                    subtask.status === "completed" ? "text-slate-400 line-through" : "text-slate-900"
                  }`}
                >
                  {subtask.title}
                </Link>
                <button
                  type="button"
                  aria-label={t("taskCard.deleteTask")}
                  onClick={() => deleteTask.mutate(subtask.id)}
                  className="shrink-0 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                >
                  <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                    <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
          {isAddingSubtask ? (
            <form onSubmit={(e) => void handleAddSubtask(e)} className="flex items-center gap-1">
              <input
                type="text"
                autoFocus
                value={subtaskTitle}
                onChange={(e) => setSubtaskTitle(e.target.value)}
                placeholder={t("tasks.subtaskPlaceholder")}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              />
              <button
                type="submit"
                disabled={!subtaskTitle.trim()}
                className="shrink-0 rounded-md bg-blue-600 px-2 py-1.5 text-sm font-medium text-white disabled:opacity-60"
              >
                {t("common.add")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsAddingSubtask(false);
                  setSubtaskTitle("");
                }}
                className="shrink-0 rounded-md px-2 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
              >
                {t("common.cancel")}
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setIsAddingSubtask(true)}
              className="text-sm font-medium text-slate-400 hover:text-slate-600"
            >
              + {t("tasks.addSubtask")}
            </button>
          )}
        </div>
      )}

      <div className="flex gap-2 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={() => save({ status: isCompleted ? "pending" : "completed" })}
          className="flex-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {isCompleted ? t("tasks.detail.markIncomplete") : t("tasks.detail.markComplete")}
        </button>
        <button
          type="button"
          onClick={() => void handleDelete()}
          className="rounded-md border border-red-200 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
        >
          {t("tasks.detail.delete")}
        </button>
      </div>
    </div>
  );
}
