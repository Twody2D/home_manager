import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TaskForm } from "../components/TaskForm";
import { TaskCard } from "../components/TaskCard";
import { useCreateTask, useDeleteTask, useTasks, useUpdateTask } from "../hooks/useTasks";
import { useMembers } from "../hooks/useMembers";
import type { Task, TaskStatus } from "../api/types";

const FILTERS: { labelKey: string; value: TaskStatus | "all" }[] = [
  { labelKey: "tasks.filterAll", value: "all" },
  { labelKey: "tasks.filterPending", value: "pending" },
  { labelKey: "tasks.filterCompleted", value: "completed" },
];

export function TasksPage() {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<TaskStatus | "all">("all");

  const tasksQuery = useTasks(filter === "all" ? {} : { status: filter });
  const membersQuery = useMembers();
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));

  function handleToggleComplete(task: Task) {
    updateTask.mutate({
      id: task.id,
      input: { status: task.status === "completed" ? "pending" : "completed" },
    });
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("tasks.title")}</h1>

      <TaskForm
        members={members}
        isSubmitting={createTask.isPending}
        onSubmit={async (input) => {
          await createTask.mutateAsync(input);
        }}
      />

      <div className="flex gap-1">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFilter(f.value)}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              filter === f.value ? "bg-blue-600 text-white" : "bg-white text-slate-600"
            }`}
          >
            {t(f.labelKey)}
          </button>
        ))}
      </div>

      {tasksQuery.isLoading && <p className="text-sm text-slate-500">{t("tasks.loading")}</p>}
      {tasksQuery.isError && <p className="text-sm text-red-600">{t("tasks.error")}</p>}

      {tasksQuery.data && (
        <>
          {tasksQuery.data.items.length === 0 ? (
            <p className="text-sm text-slate-500">{t("tasks.empty")}</p>
          ) : (
            <ul className="space-y-2">
              {tasksQuery.data.items.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
                  isUpdating={updateTask.isPending}
                  onToggleComplete={handleToggleComplete}
                  onDelete={(t) => deleteTask.mutate(t.id)}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
