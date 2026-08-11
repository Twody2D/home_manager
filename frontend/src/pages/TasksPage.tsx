import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TaskForm } from "../components/TaskForm";
import { TaskCard } from "../components/TaskCard";
import { useCreateTask, useDeleteTask, useTasks, useUpdateTask } from "../hooks/useTasks";
import { useMembers } from "../hooks/useMembers";
import { useAuth } from "../auth/useAuth";
import type { Task, TaskStatus } from "../api/types";

const FILTERS: { labelKey: string; value: TaskStatus | "all" }[] = [
  { labelKey: "tasks.filterAll", value: "all" },
  { labelKey: "tasks.filterPending", value: "pending" },
  { labelKey: "tasks.filterCompleted", value: "completed" },
];

type AssigneeFilter = "all" | "mine" | "partner";

export function TasksPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [filter, setFilter] = useState<TaskStatus | "all">("all");
  const [assigneeFilter, setAssigneeFilter] = useState<AssigneeFilter>("all");

  const membersQuery = useMembers();
  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));
  const partner = members.find((member) => member.id !== user?.id);

  const assignedTo =
    assigneeFilter === "mine" ? user?.id : assigneeFilter === "partner" ? partner?.id : undefined;
  const tasksQuery = useTasks({
    ...(filter === "all" ? {} : { status: filter }),
    ...(assignedTo ? { assigned_to: assignedTo } : {}),
  });
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

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

      <div className="flex gap-1">
        <button
          type="button"
          onClick={() => setAssigneeFilter("all")}
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            assigneeFilter === "all" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("tasks.assigneeAll")}
        </button>
        <button
          type="button"
          onClick={() => setAssigneeFilter("mine")}
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            assigneeFilter === "mine" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("tasks.assigneeMine")}
        </button>
        {partner && (
          <button
            type="button"
            onClick={() => setAssigneeFilter("partner")}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              assigneeFilter === "partner" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
            }`}
          >
            {partner.display_name}
          </button>
        )}
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
