import { useState } from "react";
import { TaskForm } from "../components/TaskForm";
import { TaskCard } from "../components/TaskCard";
import { useCreateTask, useDeleteTask, useTasks, useUpdateTask } from "../hooks/useTasks";
import { useMembers } from "../hooks/useMembers";
import type { Task, TaskStatus } from "../api/types";

const FILTERS: { label: string; value: TaskStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Completed", value: "completed" },
];

export function TasksPage() {
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
      <h1 className="text-lg font-semibold text-slate-900">Tasks</h1>

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
            {f.label}
          </button>
        ))}
      </div>

      {tasksQuery.isLoading && <p className="text-sm text-slate-500">Loading tasks…</p>}
      {tasksQuery.isError && <p className="text-sm text-red-600">Failed to load tasks.</p>}

      {tasksQuery.data && (
        <>
          {tasksQuery.data.items.length === 0 ? (
            <p className="text-sm text-slate-500">No tasks here yet.</p>
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
