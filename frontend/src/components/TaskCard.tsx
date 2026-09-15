import type { CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { Task, User } from "../api/types";
import { formatMoney } from "../lib/money";

const PRIORITY_STYLES: Record<Task["priority"], string> = {
  low: "bg-slate-100 text-slate-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-amber-100 text-amber-700",
  urgent: "bg-red-100 text-red-700",
};

export function GripIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
      <circle cx="7" cy="5" r="1.3" />
      <circle cx="13" cy="5" r="1.3" />
      <circle cx="7" cy="10" r="1.3" />
      <circle cx="13" cy="10" r="1.3" />
      <circle cx="7" cy="15" r="1.3" />
      <circle cx="13" cy="15" r="1.3" />
    </svg>
  );
}

interface TaskCardProps {
  task: Task;
  assignee?: User;
  budgetOwner?: User;
  // Shown as a small side label when this card is rendered in a flat list
  // that mixes subtasks in with root tasks (e.g. the dashboard's "no due
  // date" bucket), so it's clear which task a subtask belongs to.
  parentTitle?: string;
  // Present only when this task has subtasks — renders a chevron that
  // expands/collapses them, so a long subtask list can be tucked away.
  subtaskToggle?: { expanded: boolean; onToggle: () => void };
  onToggleComplete: (task: Task) => void;
  onDelete: (task: Task) => void;
  isUpdating?: boolean;
  nested?: boolean;
  // True while another task is being dragged and would be nested under
  // this one if dropped right now — highlights the card as the pending
  // drop target so the "drag onto to nest" gesture is discoverable.
  nestPreview?: boolean;
  // Applied to the root <li> by a dnd-kit useSortable() wrapper in the
  // caller — kept generic here so this component doesn't need to know
  // about dnd-kit's own types.
  innerRef?: (node: HTMLLIElement | null) => void;
  style?: CSSProperties;
  dragHandleProps?: Record<string, unknown>;
}

export function TaskCard({
  task,
  assignee,
  budgetOwner,
  parentTitle,
  subtaskToggle,
  onToggleComplete,
  onDelete,
  isUpdating,
  nested,
  nestPreview,
  innerRef,
  style,
  dragHandleProps,
}: TaskCardProps) {
  const { t, i18n } = useTranslation();
  const isCompleted = task.status === "completed";

  return (
    <li
      ref={innerRef}
      style={style}
      className={`flex items-center gap-2 rounded-lg border shadow-sm ${
        nestPreview ? "border-blue-400 bg-blue-50 ring-2 ring-blue-400" : "border-slate-200 bg-white"
      } ${nested ? "py-1.5 pl-1.5 pr-2" : "py-2 pl-2 pr-2.5"}`}
    >
      {dragHandleProps && (
        <button
          type="button"
          aria-label={t("taskCard.reorder")}
          className="flex h-9 w-8 shrink-0 touch-none items-center justify-center text-slate-300 hover:text-slate-500"
          {...dragHandleProps}
        >
          <GripIcon />
        </button>
      )}

      <button
        type="button"
        aria-label={isCompleted ? t("taskCard.markAsPending") : t("taskCard.markAsCompleted")}
        onClick={() => onToggleComplete(task)}
        disabled={isUpdating}
        className={`flex shrink-0 items-center justify-center rounded-full border-2 ${
          nested ? "h-5 w-5" : "h-6 w-6"
        } ${isCompleted ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300"}`}
      >
        {isCompleted && (
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
            <path d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0l-3.5-3.5a1 1 0 1 1 1.4-1.4l2.8 2.8 6.8-6.8a1 1 0 0 1 1.4 0Z" />
          </svg>
        )}
      </button>

      {subtaskToggle && (
        <button
          type="button"
          aria-label={t("taskCard.toggleSubtasks")}
          onClick={subtaskToggle.onToggle}
          className="flex h-8 w-7 shrink-0 items-center justify-center text-slate-400 hover:text-slate-600"
        >
          <svg
            viewBox="0 0 20 20"
            fill="currentColor"
            className={`h-4 w-4 transition-transform ${subtaskToggle.expanded ? "rotate-90" : ""}`}
          >
            <path d="M7.3 4.3a1 1 0 0 1 1.4 0l5 5a1 1 0 0 1 0 1.4l-5 5a1 1 0 1 1-1.4-1.4L11.58 10 7.3 5.7a1 1 0 0 1 0-1.4Z" />
          </svg>
        </button>
      )}

      <Link to={`/tasks/${task.id}`} className="min-w-0 flex-1 py-0.5" draggable={false}>
        <p
          className={`truncate text-sm font-medium ${
            isCompleted ? "text-slate-400 line-through" : "text-slate-900"
          }`}
        >
          {task.title}
        </p>
        {(task.priority !== "medium" ||
          task.due_at ||
          assignee ||
          task.budget_amount ||
          parentTitle) && (
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs">
            {parentTitle && (
              <span className="truncate rounded-full bg-slate-100 px-2 py-0.5 text-slate-500">
                {t("tasks.subtaskOf", { title: parentTitle })}
              </span>
            )}
            {task.priority !== "medium" && (
              <span className={`rounded-full px-2 py-0.5 font-medium ${PRIORITY_STYLES[task.priority]}`}>
                {t(`taskPriority.${task.priority}`)}
              </span>
            )}
            {task.due_at && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                {t("taskCard.due", { date: new Date(task.due_at).toLocaleString(i18n.language) })}
              </span>
            )}
            {assignee && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                {assignee.display_name}
              </span>
            )}
            {task.budget_amount && (
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-700">
                {formatMoney(task.budget_amount, i18n.language)}
                {budgetOwner ? ` · ${budgetOwner.display_name}` : ` · ${t("tasks.budget.shared")}`}
              </span>
            )}
          </div>
        )}
      </Link>

      <button
        type="button"
        aria-label={t("taskCard.deleteTask")}
        onClick={() => onDelete(task)}
        className="shrink-0 rounded-md p-2.5 text-slate-400 hover:bg-slate-100 hover:text-red-600"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
        </svg>
      </button>
    </li>
  );
}
