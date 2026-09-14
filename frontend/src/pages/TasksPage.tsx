import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { TaskForm } from "../components/TaskForm";
import { TaskCard } from "../components/TaskCard";
import {
  useCreateTask,
  useCreateTaskList,
  useDeleteTask,
  useDeleteTaskList,
  useRenameTaskList,
  useTaskLists,
  useTasks,
  useUpdateTask,
} from "../hooks/useTasks";
import { useMembers } from "../hooks/useMembers";
import { useAuth } from "../auth/useAuth";
import type { Task, TaskList, TaskStatus, User } from "../api/types";

const FILTERS: { labelKey: string; value: TaskStatus | "all" }[] = [
  { labelKey: "tasks.filterAll", value: "all" },
  { labelKey: "tasks.filterPending", value: "pending" },
  { labelKey: "tasks.filterCompleted", value: "completed" },
];

type AssigneeFilter = "all" | "mine" | "partner";

function TaskListTabs({
  taskLists,
  activeListId,
  onSelect,
}: {
  taskLists: TaskList[];
  activeListId: string | null;
  onSelect: (listId: string | null) => void;
}) {
  const { t } = useTranslation();
  const createTaskList = useCreateTaskList();
  const renameTaskList = useRenameTaskList();
  const deleteTaskList = useDeleteTaskList();

  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");

  const activeList = taskLists.find((list) => list.id === activeListId);

  async function handleAdd(event: FormEvent) {
    event.preventDefault();
    if (!newName.trim()) return;
    const list = await createTaskList.mutateAsync({ name: newName.trim() });
    setNewName("");
    setIsAdding(false);
    onSelect(list.id);
  }

  async function handleRename(event: FormEvent) {
    event.preventDefault();
    if (!activeListId || !renameValue.trim()) return;
    await renameTaskList.mutateAsync({ id: activeListId, input: { name: renameValue.trim() } });
    setIsRenaming(false);
  }

  function handleDelete() {
    if (!activeListId) return;
    deleteTaskList.mutate(activeListId);
    onSelect(null);
  }

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-1">
        <button
          type="button"
          onClick={() => onSelect(null)}
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            activeListId === null ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("tasks.myTasks")}
        </button>
        {taskLists.map((list) => (
          <button
            key={list.id}
            type="button"
            onClick={() => onSelect(list.id)}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              activeListId === list.id ? "bg-blue-600 text-white" : "bg-white text-slate-600"
            }`}
          >
            {list.name}
          </button>
        ))}
        {isAdding ? (
          <form onSubmit={(e) => void handleAdd(e)} className="flex items-center gap-1">
            <input
              type="text"
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t("tasks.newListPlaceholder")}
              className="w-32 rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
            <button
              type="submit"
              disabled={!newName.trim()}
              className="rounded-md bg-blue-600 px-2 py-1 text-sm font-medium text-white disabled:opacity-60"
            >
              {t("common.add")}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsAdding(false);
                setNewName("");
              }}
              className="rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
            >
              {t("common.cancel")}
            </button>
          </form>
        ) : (
          <button
            type="button"
            onClick={() => setIsAdding(true)}
            className="rounded-full border border-dashed border-slate-300 px-3 py-1 text-sm font-medium text-slate-500 hover:bg-slate-50"
          >
            + {t("tasks.addList")}
          </button>
        )}
      </div>

      {activeList &&
        (isRenaming ? (
          <form onSubmit={(e) => void handleRename(e)} className="flex items-center gap-1">
            <input
              type="text"
              autoFocus
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              className="w-40 rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
            <button
              type="submit"
              disabled={!renameValue.trim()}
              className="rounded-md bg-blue-600 px-2 py-1 text-sm font-medium text-white disabled:opacity-60"
            >
              {t("common.save")}
            </button>
            <button
              type="button"
              onClick={() => setIsRenaming(false)}
              className="rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
            >
              {t("common.cancel")}
            </button>
          </form>
        ) : (
          <div className="flex gap-3 text-xs">
            <button
              type="button"
              onClick={() => {
                setRenameValue(activeList.name);
                setIsRenaming(true);
              }}
              className="text-slate-500 hover:text-slate-700 hover:underline"
            >
              {t("tasks.renameList")}
            </button>
            <button
              type="button"
              onClick={handleDelete}
              className="text-red-500 hover:text-red-700 hover:underline"
            >
              {t("tasks.deleteList")}
            </button>
          </div>
        ))}
    </div>
  );
}

function TaskGroup({
  task,
  subtasks,
  membersById,
  isUpdating,
  onToggleComplete,
  onDelete,
  onAddSubtask,
}: {
  task: Task;
  subtasks: Task[];
  membersById: Map<string, User>;
  isUpdating: boolean;
  onToggleComplete: (task: Task) => void;
  onDelete: (task: Task) => void;
  onAddSubtask: (parentId: string, title: string) => Promise<void>;
}) {
  const { t } = useTranslation();
  const [isAdding, setIsAdding] = useState(false);
  const [title, setTitle] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;
    await onAddSubtask(task.id, title.trim());
    setTitle("");
    setIsAdding(false);
  }

  return (
    <li className="space-y-1.5">
      <ul>
        <TaskCard
          task={task}
          assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
          budgetOwner={
            task.budget_owner_user_id ? membersById.get(task.budget_owner_user_id) : undefined
          }
          isUpdating={isUpdating}
          onToggleComplete={onToggleComplete}
          onDelete={onDelete}
        />
      </ul>

      <ul className="ml-6 space-y-1.5 border-l border-slate-200 pl-3">
        {subtasks.map((subtask) => (
          <TaskCard
            key={subtask.id}
            task={subtask}
            assignee={subtask.assigned_to ? membersById.get(subtask.assigned_to) : undefined}
            isUpdating={isUpdating}
            onToggleComplete={onToggleComplete}
            onDelete={onDelete}
            nested
          />
        ))}
        {isAdding ? (
          <form onSubmit={(e) => void handleSubmit(e)} className="flex items-center gap-1">
            <input
              type="text"
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("tasks.subtaskPlaceholder")}
              className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
            <button
              type="submit"
              disabled={!title.trim()}
              className="shrink-0 rounded-md bg-blue-600 px-2 py-1 text-sm font-medium text-white disabled:opacity-60"
            >
              {t("common.add")}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsAdding(false);
                setTitle("");
              }}
              className="shrink-0 rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
            >
              {t("common.cancel")}
            </button>
          </form>
        ) : (
          <button
            type="button"
            onClick={() => setIsAdding(true)}
            className="text-xs font-medium text-slate-400 hover:text-slate-600"
          >
            + {t("tasks.addSubtask")}
          </button>
        )}
      </ul>
    </li>
  );
}

export function TasksPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [filter, setFilter] = useState<TaskStatus | "all">("all");
  const [assigneeFilter, setAssigneeFilter] = useState<AssigneeFilter>("all");
  const [activeListId, setActiveListId] = useState<string | null>(null);

  const membersQuery = useMembers();
  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));
  const partner = members.find((member) => member.id !== user?.id);

  const taskListsQuery = useTaskLists();
  const taskLists = taskListsQuery.data?.items ?? [];

  const assignedTo =
    assigneeFilter === "mine" ? user?.id : assigneeFilter === "partner" ? partner?.id : undefined;
  const tasksQuery = useTasks({
    ...(filter === "all" ? {} : { status: filter }),
    ...(assignedTo ? { assigned_to: assignedTo } : {}),
    limit: 100,
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

  async function handleAddSubtask(parentId: string, title: string) {
    await createTask.mutateAsync({ title, parent_task_id: parentId });
  }

  const allTasks = tasksQuery.data?.items ?? [];
  const subtasksByParent = new Map<string, Task[]>();
  for (const task of allTasks) {
    if (!task.parent_task_id) continue;
    const list = subtasksByParent.get(task.parent_task_id) ?? [];
    list.push(task);
    subtasksByParent.set(task.parent_task_id, list);
  }
  const rootTasks = allTasks.filter(
    (task) => task.parent_task_id === null && task.list_id === activeListId,
  );

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("tasks.title")}</h1>

      <TaskListTabs taskLists={taskLists} activeListId={activeListId} onSelect={setActiveListId} />

      <TaskForm
        members={members}
        listId={activeListId}
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
          {rootTasks.length === 0 ? (
            <p className="text-sm text-slate-500">{t("tasks.empty")}</p>
          ) : (
            <ul className="space-y-3">
              {rootTasks.map((task) => (
                <TaskGroup
                  key={task.id}
                  task={task}
                  subtasks={subtasksByParent.get(task.id) ?? []}
                  membersById={membersById}
                  isUpdating={updateTask.isPending}
                  onToggleComplete={handleToggleComplete}
                  onDelete={(t) => deleteTask.mutate(t.id)}
                  onAddSubtask={handleAddSubtask}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
