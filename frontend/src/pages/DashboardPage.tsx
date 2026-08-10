import { TaskCard } from "../components/TaskCard";
import { useMembers } from "../hooks/useMembers";
import { useDeleteTask, useTasks, useUpdateTask } from "../hooks/useTasks";
import { useDailyPlan } from "../hooks/usePlanning";
import type { Task } from "../api/types";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function partitionByDueDate(tasks: Task[]) {
  const now = new Date();
  const overdue: Task[] = [];
  const today: Task[] = [];
  const other: Task[] = [];

  for (const task of tasks) {
    if (!task.due_at) {
      other.push(task);
      continue;
    }
    const dueDate = new Date(task.due_at);
    if (dueDate < now && !isSameDay(dueDate, now)) {
      overdue.push(task);
    } else if (isSameDay(dueDate, now)) {
      today.push(task);
    } else {
      other.push(task);
    }
  }

  return { overdue, today, other };
}

export function DashboardPage() {
  const tasksQuery = useTasks({ status: "pending", limit: 100 });
  const membersQuery = useMembers();
  const planQuery = useDailyPlan();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));

  function handleComplete(task: Task) {
    updateTask.mutate({ id: task.id, input: { status: "completed" } });
  }

  function handleDelete(task: Task) {
    deleteTask.mutate(task.id);
  }

  if (tasksQuery.isLoading) {
    return <p className="text-sm text-slate-500">Loading today’s plan…</p>;
  }

  if (tasksQuery.isError) {
    return <p className="text-sm text-red-600">Failed to load today’s plan.</p>;
  }

  const { overdue, today, other } = partitionByDueDate(tasksQuery.data?.items ?? []);

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-slate-900">
        Today,{" "}
        {new Date().toLocaleDateString(undefined, {
          weekday: "long",
          month: "long",
          day: "numeric",
        })}
      </h1>

      {planQuery.data && (
        <Section title="Suggested schedule">
          {planQuery.data.scheduled.length === 0 && planQuery.data.unscheduled.length === 0 && (
            <p className="text-sm text-slate-500">
              Nothing to schedule — assign yourself a task with a duration to see a plan here.
            </p>
          )}
          {planQuery.data.scheduled.map((entry) => (
            <li
              key={entry.task_id}
              className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2"
            >
              <span className="text-sm text-slate-900">{entry.title}</span>
              <span className="text-xs text-slate-500">
                {formatTime(entry.start_at)} – {formatTime(entry.end_at)}
              </span>
            </li>
          ))}
          {planQuery.data.unscheduled.map((entry) => (
            <li
              key={entry.task_id}
              className="flex items-center justify-between rounded-md border border-amber-200 bg-amber-50 px-3 py-2"
            >
              <span className="text-sm text-slate-900">{entry.title}</span>
              <span className="text-xs text-amber-700">{entry.reason}</span>
            </li>
          ))}
        </Section>
      )}

      {overdue.length === 0 && today.length === 0 && other.length === 0 && (
        <p className="text-sm text-slate-500">Nothing pending — enjoy your day.</p>
      )}

      {overdue.length > 0 && (
        <Section title="Overdue">
          {overdue.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
              isUpdating={updateTask.isPending}
              onToggleComplete={handleComplete}
              onDelete={handleDelete}
            />
          ))}
        </Section>
      )}

      {today.length > 0 && (
        <Section title="Due today">
          {today.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
              isUpdating={updateTask.isPending}
              onToggleComplete={handleComplete}
              onDelete={handleDelete}
            />
          ))}
        </Section>
      )}

      {other.length > 0 && (
        <Section title="Not scheduled">
          {other.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
              isUpdating={updateTask.isPending}
              onToggleComplete={handleComplete}
              onDelete={handleDelete}
            />
          ))}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-medium text-slate-500">{title}</h2>
      <ul className="space-y-2">{children}</ul>
    </section>
  );
}
