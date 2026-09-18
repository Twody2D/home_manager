import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { TaskCard } from "../components/TaskCard";
import { CalendarEventCard } from "../components/CalendarEventCard";
import { useMembers } from "../hooks/useMembers";
import { useDeleteTask, useTaskLists, useTasks, useUpdateTask } from "../hooks/useTasks";
import { useDailyPlan } from "../hooks/usePlanning";
import { useCalendarEvents, useDeleteEvent } from "../hooks/useCalendar";
import { useAuth } from "../auth/useAuth";
import { buildTaskPath } from "../lib/taskPath";
import type { Task, TaskList } from "../api/types";

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

const PRIORITY_RANK: Record<Task["priority"], number> = {
  urgent: 0,
  high: 1,
  medium: 2,
  low: 3,
};

interface FolderGroup {
  key: string;
  label: string;
  tasks: Task[];
}

// The undated bucket is the one that grows without bound, so it's split by
// folder (in the same order the Tasks page shows them) and sorted with the
// most urgent first, rather than left as one long undifferentiated list.
function groupByFolder(tasks: Task[], taskLists: TaskList[], defaultLabel: string): FolderGroup[] {
  const byList = new Map<string | null, Task[]>();
  for (const task of tasks) {
    const group = byList.get(task.list_id) ?? [];
    group.push(task);
    byList.set(task.list_id, group);
  }

  const listOrder: (string | null)[] = [null, ...taskLists.map((list) => list.id)];
  return listOrder
    .filter((listId) => byList.has(listId))
    .map((listId) => ({
      key: listId ?? "none",
      label: listId === null ? defaultLabel : (taskLists.find((l) => l.id === listId)?.name ?? ""),
      tasks: [...(byList.get(listId) ?? [])].sort(
        (a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority],
      ),
    }));
}

export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  // See the matching comment in TasksPage — must cover every pending task,
  // not just the first page, or overdue/unscheduled ones past the cutoff
  // silently vanish from this list while still showing up in the plan.
  const tasksQuery = useTasks({ status: "pending", limit: 1000 });
  const taskListsQuery = useTaskLists();
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
  const allTasks = tasksQuery.data?.items ?? [];
  const taskLists = taskListsQuery.data?.items ?? [];
  const tasksById = new Map(allTasks.map((task) => [task.id, task]));
  const listsById = new Map(taskLists.map((list) => [list.id, list]));

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

  const { overdue, today, other } = partitionByDueDate(allTasks);
  const undatedGroups = groupByFolder(other, taskLists, t("tasks.myTasks"));

  function renderTask(task: Task) {
    return (
      <TaskCard
        key={task.id}
        task={task}
        assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
        budgetOwner={
          task.budget_owner_user_id ? membersById.get(task.budget_owner_user_id) : undefined
        }
        path={buildTaskPath(task, tasksById, listsById, t("tasks.myTasks"))}
        isUpdating={updateTask.isPending}
        onToggleComplete={handleComplete}
        onDelete={handleDelete}
      />
    );
  }

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
        <Section title={t("dashboard.overdue")} count={overdue.length}>
          {overdue.map(renderTask)}
        </Section>
      )}

      {today.length > 0 && (
        <Section title={t("dashboard.dueToday")} count={today.length}>
          {today.map(renderTask)}
        </Section>
      )}

      {other.length > 0 && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-medium text-slate-500">
            {t("dashboard.notScheduled")}
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
              {other.length}
            </span>
          </h2>
          <div className="space-y-1.5">
            {undatedGroups.map((group) => (
              <FolderGroupBlock key={group.key} label={group.label} count={group.tasks.length}>
                {group.tasks.map(renderTask)}
              </FolderGroupBlock>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <h2 className="flex items-center gap-2 text-sm font-medium text-slate-500">
        {title}
        {count !== undefined && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
            {count}
          </span>
        )}
      </h2>
      <ul className="space-y-2">{children}</ul>
    </section>
  );
}

// Collapsed by default: the undated bucket holds everything that has no date
// yet, which is most of the household's backlog — it belongs on this page as
// a reachable summary, not as a wall of cards above the fold.
function FolderGroupBlock({
  label,
  count,
  children,
}: {
  label: string;
  count: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left hover:bg-slate-50"
      >
        <span className={`text-slate-400 transition-transform ${open ? "rotate-90" : ""}`}>›</span>
        <span className="flex-1 truncate text-sm font-medium text-slate-700">{label}</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{count}</span>
      </button>
      {open && <ul className="space-y-1.5 border-t border-slate-100 p-2">{children}</ul>}
    </div>
  );
}
