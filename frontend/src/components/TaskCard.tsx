import type { Task, User } from "../api/types";

const PRIORITY_STYLES: Record<Task["priority"], string> = {
  low: "bg-slate-100 text-slate-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-amber-100 text-amber-700",
  urgent: "bg-red-100 text-red-700",
};

interface TaskCardProps {
  task: Task;
  assignee?: User;
  onToggleComplete: (task: Task) => void;
  onDelete: (task: Task) => void;
  isUpdating?: boolean;
}

export function TaskCard({ task, assignee, onToggleComplete, onDelete, isUpdating }: TaskCardProps) {
  const isCompleted = task.status === "completed";

  return (
    <li className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <button
        type="button"
        aria-label={isCompleted ? "Mark as pending" : "Mark as completed"}
        onClick={() => onToggleComplete(task)}
        disabled={isUpdating}
        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
          isCompleted ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300"
        }`}
      >
        {isCompleted && (
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-3 w-3">
            <path d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0l-3.5-3.5a1 1 0 1 1 1.4-1.4l2.8 2.8 6.8-6.8a1 1 0 0 1 1.4 0Z" />
          </svg>
        )}
      </button>

      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium ${isCompleted ? "text-slate-400 line-through" : "text-slate-900"}`}>
          {task.title}
        </p>
        {task.description && <p className="mt-0.5 text-xs text-slate-500">{task.description}</p>}
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
          <span className={`rounded-full px-2 py-0.5 font-medium ${PRIORITY_STYLES[task.priority]}`}>
            {task.priority}
          </span>
          {task.due_at && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
              Due {new Date(task.due_at).toLocaleString()}
            </span>
          )}
          {assignee && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
              {assignee.display_name}
            </span>
          )}
        </div>
      </div>

      <button
        type="button"
        aria-label="Delete task"
        onClick={() => onDelete(task)}
        className="shrink-0 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
        </svg>
      </button>
    </li>
  );
}
