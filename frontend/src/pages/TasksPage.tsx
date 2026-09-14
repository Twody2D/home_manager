import { useState } from "react";
import type { CSSProperties, FormEvent, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { TaskForm } from "../components/TaskForm";
import { TaskCard } from "../components/TaskCard";
import {
  useCreateTask,
  useCreateTaskList,
  useDeleteTask,
  useDeleteTaskList,
  useRenameTaskList,
  useReorderTasks,
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
// null = the default "My Tasks" bucket, "all" = every list combined (view
// only — root-level drag-and-drop is disabled here since siblings would
// span more than one actual list group).
type ListScope = string | null | "all";

function TaskListTabs({
  taskLists,
  activeListId,
  onSelect,
}: {
  taskLists: TaskList[];
  activeListId: ListScope;
  onSelect: (listId: ListScope) => void;
}) {
  const { t } = useTranslation();
  const createTaskList = useCreateTaskList();
  const renameTaskList = useRenameTaskList();
  const deleteTaskList = useDeleteTaskList();

  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

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
    if (!activeList || !renameValue.trim()) return;
    await renameTaskList.mutateAsync({ id: activeList.id, input: { name: renameValue.trim() } });
    setIsRenaming(false);
  }

  function handleDelete() {
    if (!activeList) return;
    deleteTaskList.mutate(activeList.id);
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
        <button
          type="button"
          onClick={() => onSelect("all")}
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            activeListId === "all" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("tasks.allLists")}
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

        {activeList && (
          <div
            className="relative ml-auto"
            tabIndex={-1}
            onBlur={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget as Node)) setMenuOpen(false);
            }}
          >
            <button
              type="button"
              aria-label={t("tasks.listMenu")}
              onClick={() => setMenuOpen((open) => !open)}
              className="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
                <circle cx="10" cy="4" r="1.6" />
                <circle cx="10" cy="10" r="1.6" />
                <circle cx="10" cy="16" r="1.6" />
              </svg>
            </button>
            {menuOpen && (
              <div className="absolute right-0 z-10 mt-1 w-44 overflow-hidden rounded-md border border-slate-200 bg-white py-1 shadow-lg">
                <button
                  type="button"
                  onClick={() => {
                    setRenameValue(activeList.name);
                    setIsRenaming(true);
                    setMenuOpen(false);
                  }}
                  className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                >
                  {t("tasks.renameList")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    handleDelete();
                    setMenuOpen(false);
                  }}
                  className="block w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                >
                  {t("tasks.deleteList")}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {activeList && isRenaming && (
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
      )}
    </div>
  );
}

interface SortableSlotArgs {
  innerRef: (node: HTMLLIElement | null) => void;
  style: CSSProperties;
  dragHandleProps?: Record<string, unknown>;
}

function SortableSlot({
  id,
  disabled,
  children,
}: {
  id: string;
  disabled?: boolean;
  children: (args: SortableSlotArgs) => ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    disabled,
  });
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
    zIndex: isDragging ? 1 : undefined,
  };
  return (
    <>
      {children({
        innerRef: setNodeRef,
        style,
        dragHandleProps: disabled ? undefined : { ...attributes, ...listeners },
      })}
    </>
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
  rootDragDisabled,
}: {
  task: Task;
  subtasks: Task[];
  membersById: Map<string, User>;
  isUpdating: boolean;
  onToggleComplete: (task: Task) => void;
  onDelete: (task: Task) => void;
  onAddSubtask: (parentId: string, title: string) => Promise<void>;
  rootDragDisabled: boolean;
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
        <SortableSlot id={task.id} disabled={rootDragDisabled}>
          {(slot) => (
            <TaskCard
              task={task}
              assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
              budgetOwner={
                task.budget_owner_user_id ? membersById.get(task.budget_owner_user_id) : undefined
              }
              isUpdating={isUpdating}
              onToggleComplete={onToggleComplete}
              onDelete={onDelete}
              {...slot}
            />
          )}
        </SortableSlot>
      </ul>

      <ul className="ml-6 space-y-1.5 border-l border-slate-200 pl-3">
        <SortableContext items={subtasks.map((s) => s.id)} strategy={verticalListSortingStrategy}>
          {subtasks.map((subtask) => (
            <SortableSlot key={subtask.id} id={subtask.id}>
              {(slot) => (
                <TaskCard
                  task={subtask}
                  assignee={subtask.assigned_to ? membersById.get(subtask.assigned_to) : undefined}
                  isUpdating={isUpdating}
                  onToggleComplete={onToggleComplete}
                  onDelete={onDelete}
                  nested
                  {...slot}
                />
              )}
            </SortableSlot>
          ))}
        </SortableContext>
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

interface SiblingGroup {
  listId: string | null;
  parentId: string | null;
  ids: string[];
}

export function TasksPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [filter, setFilter] = useState<TaskStatus | "all">("all");
  const [assigneeFilter, setAssigneeFilter] = useState<AssigneeFilter>("all");
  const [activeListId, setActiveListId] = useState<ListScope>(null);
  const [isAddingTask, setIsAddingTask] = useState(false);
  // Immediate local reflection of a just-dropped reorder, keyed by sibling
  // group, so the list doesn't snap back while the request round-trips.
  // Cleared once that group's mutation settles (the refetched data already
  // matches by then).
  const [localOrder, setLocalOrder] = useState<Record<string, string[]>>({});

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
  const reorderTasks = useReorderTasks();

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

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
  const byId = new Map(allTasks.map((task) => [task.id, task]));

  function applyOrder(tasks: Task[], key: string): Task[] {
    const override = localOrder[key];
    if (!override) return tasks;
    const known = new Set(tasks.map((task) => task.id));
    const ordered = override.filter((id) => known.has(id)).map((id) => byId.get(id) as Task);
    const missing = tasks.filter((task) => !override.includes(task.id));
    return [...ordered, ...missing];
  }

  const subtasksByParent = new Map<string, Task[]>();
  for (const task of allTasks) {
    if (!task.parent_task_id) continue;
    const list = subtasksByParent.get(task.parent_task_id) ?? [];
    list.push(task);
    subtasksByParent.set(task.parent_task_id, list);
  }
  for (const [parentId, subtasks] of subtasksByParent) {
    subtasksByParent.set(parentId, applyOrder(subtasks, `sub:${parentId}`));
  }

  const rootDragDisabled = activeListId === "all";
  const rootTasks = applyOrder(
    allTasks.filter(
      (task) =>
        task.parent_task_id === null && (activeListId === "all" || task.list_id === activeListId),
    ),
    "root",
  );

  const groups = new Map<string, SiblingGroup>();
  groups.set("root", { listId: activeListId === "all" ? null : activeListId, parentId: null, ids: rootTasks.map((t) => t.id) });
  const idToGroupKey = new Map<string, string>();
  if (!rootDragDisabled) {
    for (const task of rootTasks) idToGroupKey.set(task.id, "root");
  }
  for (const [parentId, subtasks] of subtasksByParent) {
    const key = `sub:${parentId}`;
    const parentTask = byId.get(parentId);
    groups.set(key, { listId: parentTask?.list_id ?? null, parentId, ids: subtasks.map((s) => s.id) });
    for (const subtask of subtasks) idToGroupKey.set(subtask.id, key);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const activeKey = idToGroupKey.get(String(active.id));
    const overKey = idToGroupKey.get(String(over.id));
    if (!activeKey || !overKey || activeKey !== overKey) return;
    const group = groups.get(activeKey);
    if (!group) return;
    const oldIndex = group.ids.indexOf(String(active.id));
    const newIndex = group.ids.indexOf(String(over.id));
    if (oldIndex === -1 || newIndex === -1) return;
    const reordered = arrayMove(group.ids, oldIndex, newIndex);
    setLocalOrder((prev) => ({ ...prev, [activeKey]: reordered }));
    reorderTasks.mutate(
      { list_id: group.listId, parent_task_id: group.parentId, ordered_ids: reordered },
      {
        onSettled: () => {
          setLocalOrder((prev) => {
            const next = { ...prev };
            delete next[activeKey];
            return next;
          });
        },
      },
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("tasks.title")}</h1>

      <TaskListTabs taskLists={taskLists} activeListId={activeListId} onSelect={setActiveListId} />

      {!isAddingTask ? (
        <button
          type="button"
          onClick={() => setIsAddingTask(true)}
          className="w-full rounded-lg border border-dashed border-slate-300 bg-white px-3 py-2 text-left text-sm font-medium text-slate-500 hover:bg-slate-50"
        >
          + {t("tasks.quickAdd")}
        </button>
      ) : (
        <TaskForm
          members={members}
          listId={activeListId === "all" ? null : activeListId}
          isSubmitting={createTask.isPending}
          onSubmit={async (input) => {
            await createTask.mutateAsync(input);
            setIsAddingTask(false);
          }}
        />
      )}

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
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext
                items={rootDragDisabled ? [] : rootTasks.map((t) => t.id)}
                strategy={verticalListSortingStrategy}
              >
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
                      rootDragDisabled={rootDragDisabled}
                    />
                  ))}
                </ul>
              </SortableContext>
            </DndContext>
          )}
        </>
      )}
    </div>
  );
}
