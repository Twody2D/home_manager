import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { TaskCard } from "../components/TaskCard";
import { CalendarEventCard } from "../components/CalendarEventCard";
import { useMembers } from "../hooks/useMembers";
import { useDeleteTask, useTasks, useUpdateTask } from "../hooks/useTasks";
import { useDailyPlan } from "../hooks/usePlanning";
import { useCalendarEvents, useDeleteEvent } from "../hooks/useCalendar";
import { useAuth } from "../auth/useAuth";
import type { Task } from "../api/types";

function todayRange(): { start: Date; end: Date } {
  const now = new Date();
  return {
    start: new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0),
    end: new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59),
  };
}

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
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const tasksQuery = useTasks({ status: "pending", limit: 100 });
  const membersQuery = useMembers();
  const planQuery = useDailyPlan();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();
  const { start: todayStart, end: todayEnd } = todayRange();
  const todayEventsQuery = useCalendarEvents({
    ends_after: todayStart.toISOString(),
    starts_before: todayEnd.toISOString(),
  });
  const deleteEvent = useDeleteEvent();

  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));
  const todayEvents = [...(todayEventsQuery.data ?? [])].sort((a, b) =>
    a.start_at.localeCompare(b.start_at),
  );

  function handleComplete(task: Task) {
    updateTask.mutate({ id: task.id, input: { status: "completed" } });
  }

  function handleDelete(task: Task) {
    deleteTask.mutate(task.id);
  }

  if (tasksQuery.isLoading) {
    return <p className="text-sm text-slate-500">{t("dashboard.loading")}</p>;
  }

  if (tasksQuery.isError) {
    return <p className="text-sm text-red-600">{t("dashboard.error")}</p>;
  }

  const { overdue, today, other } = partitionByDueDate(tasksQuery.data?.items ?? []);
  const dateLabel = new Date().toLocaleDateString(i18n.language, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  const partner = members.find((member) => member.id !== user?.id);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">
          {t("dashboard.title", { date: dateLabel })}
        </h1>
        {partner && (
          <Link to="/household" className="text-xs text-slate-500 hover:text-slate-700">
            {t("dashboard.household", { name: partner.display_name })}
          </Link>
        )}
      </div>

      {todayEvents.length > 0 && (
        <Section title={t("dashboard.todaySchedule")}>
          {todayEvents.map((event) => (
            <CalendarEventCard
              key={event.id}
              event={event}
              owner={membersById.get(event.user_id)}
              isOwn={event.user_id === user?.id}
              onDelete={(e) => deleteEvent.mutate(e.id)}
            />
          ))}
        </Section>
      )}

      {planQuery.data && (
        <Section title={t("dashboard.suggestedSchedule")}>
          {planQuery.data.scheduled.length === 0 && planQuery.data.unscheduled.length === 0 && (
            <p className="text-sm text-slate-500">{t("dashboard.noSchedule")}</p>
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
        <p className="text-sm text-slate-500">{t("dashboard.nothingPending")}</p>
      )}

      {overdue.length > 0 && (
        <Section title={t("dashboard.overdue")}>
          {overdue.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
              budgetOwner={
                task.budget_owner_user_id ? membersById.get(task.budget_owner_user_id) : undefined
              }
              isUpdating={updateTask.isPending}
              onToggleComplete={handleComplete}
              onDelete={handleDelete}
            />
          ))}
        </Section>
      )}

      {today.length > 0 && (
        <Section title={t("dashboard.dueToday")}>
          {today.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
              budgetOwner={
                task.budget_owner_user_id ? membersById.get(task.budget_owner_user_id) : undefined
              }
              isUpdating={updateTask.isPending}
              onToggleComplete={handleComplete}
              onDelete={handleDelete}
            />
          ))}
        </Section>
      )}

      {other.length > 0 && (
        <Section title={t("dashboard.notScheduled")}>
          {other.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
              budgetOwner={
                task.budget_owner_user_id ? membersById.get(task.budget_owner_user_id) : undefined
              }
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
