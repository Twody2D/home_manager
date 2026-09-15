import { useState } from "react";
import type { CSSProperties, FormEvent, ReactNode } from "react";
import { flushSync } from "react-dom";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  horizontalListSortingStrategy,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { TaskForm } from "../components/TaskForm";
import { TaskCard } from "../components/TaskCard";
import { SortableListItem } from "../components/SortableListItem";
import {
  useCreateTask,
  useCreateTaskList,
  useDeleteTask,
  useDeleteTaskList,
  useRenameTaskList,
  useReorderTaskLists,
  useReorderTasks,
  useTaskLists,
  useTasks,
  useUpdateTask,
} from "../hooks/useTasks";
import { useMembers } from "../hooks/useMembers";
import { useAuth } from "../auth/useAuth";
import type { Task, TaskList, User } from "../api/types";

type AssigneeFilter = "all" | "mine" | "partner";
// "all" = every list combined (drag-and-drop is only enabled here when the
// visible tasks happen to all share one real list_id — otherwise siblings
// would span more than one actual sibling group).
type ListScope = string | "all";

// Levels: task / subtask / sub-subtask / sub-sub-subtask — kept in sync
// with MAX_TASK_DEPTH in the backend's tasks/service.py.
const MAX_TASK_DEPTH = 4;

// Dragging a task at least this far to the right while dropping it onto
// another task nests it as that task's new child instead of reordering —
// the familiar "drag right to indent" outliner gesture. Comfortably past
// incidental horizontal jitter during an otherwise-vertical reorder drag.
const NEST_DRAG_THRESHOLD = 40;

interface TabSlotArgs {
  innerRef: (node: HTMLButtonElement | null) => void;
  style: CSSProperties;
  dragHandleProps?: Record<string, unknown>;
}

function SortableTab({
  id,
  children,
}: {
  id: string;
  children: (args: TabSlotArgs) => ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  });
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
    zIndex: isDragging ? 1 : undefined,
  };
  return <>{children({ innerRef: setNodeRef, style, dragHandleProps: { ...attributes, ...listeners } })}</>;
}

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
  const reorderTaskLists = useReorderTaskLists();

  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [localOrder, setLocalOrder] = useState<string[] | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const orderedLists = localOrder
    ? (localOrder.map((id) => taskLists.find((l) => l.id === id)).filter(Boolean) as TaskList[])
    : taskLists;

  const activeList = taskLists.find((list) => list.id === activeListId);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const ids = orderedLists.map((l) => l.id);
    const oldIndex = ids.indexOf(String(active.id));
    const newIndex = ids.indexOf(String(over.id));
    if (oldIndex === -1 || newIndex === -1) return;
    const reordered = arrayMove(ids, oldIndex, newIndex);
    flushSync(() => setLocalOrder(reordered));
    reorderTaskLists.mutate(reordered, { onSettled: () => setLocalOrder(null) });
  }

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
    onSelect("all");
  }

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-1">
        <button
          type="button"
          onClick={() => onSelect("all")}
          className={`rounded-full px-3.5 py-2 text-sm font-medium ${
            activeListId === "all" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("tasks.allLists")}
        </button>

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext
            items={orderedLists.map((l) => l.id)}
            strategy={horizontalListSortingStrategy}
          >
            {orderedLists.map((list) => (
              <SortableTab key={list.id} id={list.id}>
                {(slot) => (
                  <button
                    ref={slot.innerRef}
                    style={slot.style}
                    type="button"
                    onClick={() => onSelect(list.id)}
                    className={`touch-none rounded-full px-3.5 py-2 text-sm font-medium ${
                      activeListId === list.id ? "bg-blue-600 text-white" : "bg-white text-slate-600"
                    }`}
                    {...slot.dragHandleProps}
                  >
                    {list.name}
                  </button>
                )}
              </SortableTab>
            ))}
          </SortableContext>
        </DndContext>

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
            className="rounded-full border border-dashed border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-500 hover:bg-slate-50"
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
              className="flex h-10 w-10 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-600"
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

function splitByStatus(tasks: Task[]): { active: Task[]; completed: Task[] } {
  const active: Task[] = [];
  const completed: Task[] = [];
  for (const task of tasks) {
    (task.status === "completed" ? completed : active).push(task);
  }
  return { active, completed };
}

function CompletedToggle({
  count,
  open,
  onToggle,
}: {
  count: number;
  open: boolean;
  onToggle: () => void;
}) {
  const { t } = useTranslation();
  if (count === 0) return null;
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-slate-600"
    >
      <span className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}>›</span>
      {t("tasks.completedCount", { count })}
    </button>
  );
}

// Renders a task and (recursively) its children — used for both root tasks
// and subtasks, at whatever depth: calling this again for each subtask
// naturally renders the next level one indent deeper, and terminates on its
// own once a level has no children (enforced up to MAX_TASK_DEPTH backend-
// side), no depth tracking needed here.
function TaskGroup({
  task,
  subtasksByParent,
  membersById,
  isUpdating,
  onToggleComplete,
  onDelete,
  nested,
}: {
  task: Task;
  subtasksByParent: Map<string, Task[]>;
  membersById: Map<string, User>;
  isUpdating: boolean;
  onToggleComplete: (task: Task) => void;
  onDelete: (task: Task) => void;
  nested?: boolean;
}) {
  const [subtasksCollapsed, setSubtasksCollapsed] = useState(false);
  // Subtasks are never split off into a separate completed section like
  // root tasks are — toggling one complete should just strike it through
  // in place, not make it jump out of the list.
  const subtasks = subtasksByParent.get(task.id) ?? [];
  const hasSubtasks = subtasks.length > 0;

  return (
    <li className="space-y-1.5">
      <ul>
        <SortableListItem id={task.id}>
          {(slot) => (
            <TaskCard
              task={task}
              assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
              budgetOwner={
                task.budget_owner_user_id ? membersById.get(task.budget_owner_user_id) : undefined
              }
              subtaskToggle={
                hasSubtasks
                  ? { expanded: !subtasksCollapsed, onToggle: () => setSubtasksCollapsed((c) => !c) }
                  : undefined
              }
              isUpdating={isUpdating}
              onToggleComplete={onToggleComplete}
              onDelete={onDelete}
              nested={nested}
              {...slot}
            />
          )}
        </SortableListItem>
      </ul>

      {hasSubtasks && !subtasksCollapsed && (
        <ul className="ml-6 space-y-1.5 border-l border-slate-200 pl-3">
          <SortableContext items={subtasks.map((s) => s.id)} strategy={verticalListSortingStrategy}>
            {subtasks.map((subtask) => (
              <TaskGroup
                key={subtask.id}
                task={subtask}
                subtasksByParent={subtasksByParent}
                membersById={membersById}
                isUpdating={isUpdating}
                onToggleComplete={onToggleComplete}
                onDelete={onDelete}
                nested
              />
            ))}
          </SortableContext>
        </ul>
      )}
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
  const [assigneeFilter, setAssigneeFilter] = useState<AssigneeFilter>("all");
  const [searchParams, setSearchParams] = useSearchParams();
  const activeListId: ListScope = searchParams.get("list") ?? "all";
  const [isAddingTask, setIsAddingTask] = useState(false);
  const [showCompletedRoot, setShowCompletedRoot] = useState(false);
  // Immediate local reflection of a just-dropped reorder, keyed by sibling
  // group, so the list doesn't snap back while the request round-trips.
  // Cleared once that group's mutation settles (the refetched data already
  // matches by then).
  const [localOrder, setLocalOrder] = useState<Record<string, string[]>>({});

  function setActiveListId(listId: ListScope) {
    setSearchParams(listId === "all" ? {} : { list: listId });
  }

  const membersQuery = useMembers();
  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));
  const partner = members.find((member) => member.id !== user?.id);

  const taskListsQuery = useTaskLists();
  const taskLists = taskListsQuery.data?.items ?? [];

  const assignedTo =
    assigneeFilter === "mine" ? user?.id : assigneeFilter === "partner" ? partner?.id : undefined;
  const tasksQuery = useTasks({
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

  const rootTasks = applyOrder(
    allTasks.filter(
      (task) =>
        task.parent_task_id === null && (activeListId === "all" || task.list_id === activeListId),
    ),
    "root",
  );
  const { completed: completedRootTasks } = splitByStatus(rootTasks);

  // Reordering only ever makes sense within one real (list_id, null) sibling
  // group, so the "Все задачи" view is rendered as one section per list
  // (default bucket first, then each folder in tab order) rather than one
  // flat merged list — that keeps every task genuinely draggable, including
  // in "Все задачи", instead of disabling drag whenever more than one list
  // is visible at once. Selecting a single folder tab naturally yields
  // exactly one section here, so this is also the single-group case.
  const rootTasksByList = new Map<string | null, Task[]>();
  for (const task of rootTasks) {
    const list = rootTasksByList.get(task.list_id) ?? [];
    list.push(task);
    rootTasksByList.set(task.list_id, list);
  }
  const listSectionOrder: (string | null)[] = [null, ...taskLists.map((l) => l.id)];
  const rootSections = listSectionOrder
    .filter((listId) => rootTasksByList.has(listId))
    .map((listId) => {
      const key = `root:${listId ?? "none"}`;
      const fullTasks = applyOrder(rootTasksByList.get(listId) ?? [], key);
      const { active } = splitByStatus(fullTasks);
      return {
        key,
        listId,
        label: listId === null ? t("tasks.myTasks") : (taskLists.find((l) => l.id === listId)?.name ?? ""),
        fullTasks,
        activeTasks: active,
      };
    });
  const showSectionHeaders = rootSections.length > 1;

  const groups = new Map<string, SiblingGroup>();
  const idToGroupKey = new Map<string, string>();
  for (const section of rootSections) {
    groups.set(section.key, { listId: section.listId, parentId: null, ids: section.fullTasks.map((t) => t.id) });
    for (const task of section.fullTasks) idToGroupKey.set(task.id, section.key);
  }
  for (const [parentId, subtasks] of subtasksByParent) {
    const key = `sub:${parentId}`;
    const parentTask = byId.get(parentId);
    groups.set(key, { listId: parentTask?.list_id ?? null, parentId, ids: subtasks.map((s) => s.id) });
    for (const subtask of subtasks) idToGroupKey.set(subtask.id, key);
  }

  // 0 for a top-level task, 1 for a subtask, and so on up the parent chain.
  function taskDepth(id: string): number {
    let depth = 0;
    let current = byId.get(id);
    while (current?.parent_task_id) {
      depth += 1;
      current = byId.get(current.parent_task_id);
    }
    return depth;
  }

  // 0 if id has no children, otherwise 1 + its tallest child subtree — how
  // many further levels would move along with it if id were nested deeper.
  function subtreeHeight(id: string): number {
    const children = subtasksByParent.get(id) ?? [];
    if (children.length === 0) return 0;
    return 1 + Math.max(...children.map((child) => subtreeHeight(child.id)));
  }

  function isDescendantOf(ancestorId: string, candidateId: string): boolean {
    const stack = [...(subtasksByParent.get(ancestorId) ?? [])];
    while (stack.length > 0) {
      const current = stack.pop();
      if (!current) continue;
      if (current.id === candidateId) return true;
      stack.push(...(subtasksByParent.get(current.id) ?? []));
    }
    return false;
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over, delta } = event;
    if (!over || active.id === over.id) return;
    const activeId = String(active.id);
    const overId = String(over.id);
    const activeKey = idToGroupKey.get(activeId);
    const overKey = idToGroupKey.get(overId);
    if (!activeKey || !overKey) return;

    if (delta.x > NEST_DRAG_THRESHOLD) {
      // Dragged noticeably to the right while dropping onto another task —
      // nest the dragged task as that task's new child instead of
      // reordering, regardless of whether the two started out as siblings.
      // Guard against a cycle (dropping onto your own descendant) and
      // against exceeding the depth cap (also enforced backend-side, but
      // checking here avoids a pointless request for an obviously invalid
      // drop).
      if (isDescendantOf(activeId, overId)) return;
      const newDepth = taskDepth(overId) + 1;
      if (newDepth + subtreeHeight(activeId) > MAX_TASK_DEPTH - 1) return;
      updateTask.mutate({ id: activeId, input: { parent_task_id: overId } });
      return;
    }

    if (activeKey !== overKey) return;
    const group = groups.get(activeKey);
    if (!group) return;
    const oldIndex = group.ids.indexOf(String(active.id));
    const newIndex = group.ids.indexOf(String(over.id));
    if (oldIndex === -1 || newIndex === -1) return;
    const reordered = arrayMove(group.ids, oldIndex, newIndex);
    // Force the reordered DOM to commit in the same paint as the drop so
    // dnd-kit's own transform reset doesn't land a frame later than the
    // list re-sorting — without this the card visibly "moves" and only
    // then its text updates to match the new position.
    flushSync(() => {
      setLocalOrder((prev) => ({ ...prev, [activeKey]: reordered }));
    });
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

      <div className="flex gap-1.5">
        <button
          type="button"
          onClick={() => setAssigneeFilter("all")}
          className={`rounded-full px-3.5 py-2 text-sm font-medium ${
            assigneeFilter === "all" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("tasks.assigneeAll")}
        </button>
        <button
          type="button"
          onClick={() => setAssigneeFilter("mine")}
          className={`rounded-full px-3.5 py-2 text-sm font-medium ${
            assigneeFilter === "mine" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("tasks.assigneeMine")}
        </button>
        {partner && (
          <button
            type="button"
            onClick={() => setAssigneeFilter("partner")}
            className={`rounded-full px-3.5 py-2 text-sm font-medium ${
              assigneeFilter === "partner" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
            }`}
          >
            {partner.display_name}
          </button>
        )}
      </div>

      <TaskListTabs taskLists={taskLists} activeListId={activeListId} onSelect={setActiveListId} />

      {!isAddingTask ? (
        <button
          type="button"
          onClick={() => setIsAddingTask(true)}
          className="w-full rounded-lg border border-dashed border-slate-300 bg-white px-3 py-3 text-left text-sm font-medium text-slate-500 hover:bg-slate-50"
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

      {tasksQuery.isLoading && <p className="text-sm text-slate-500">{t("tasks.loading")}</p>}
      {tasksQuery.isError && <p className="text-sm text-red-600">{t("tasks.error")}</p>}

      {tasksQuery.data && (
        <>
          {rootTasks.length === 0 ? (
            <p className="text-sm text-slate-500">{t("tasks.empty")}</p>
          ) : (
            <>
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <div className="space-y-4">
                  {rootSections.map((section) => (
                    <div key={section.key} className="space-y-2">
                      {showSectionHeaders && (
                        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                          {section.label}
                        </h2>
                      )}
                      <SortableContext
                        items={section.activeTasks.map((t) => t.id)}
                        strategy={verticalListSortingStrategy}
                      >
                        <ul className="space-y-3">
                          {section.activeTasks.map((task) => (
                            <TaskGroup
                              key={task.id}
                              task={task}
                              subtasksByParent={subtasksByParent}
                              membersById={membersById}
                              isUpdating={updateTask.isPending}
                              onToggleComplete={handleToggleComplete}
                              onDelete={(t) => deleteTask.mutate(t.id)}
                            />
                          ))}
                        </ul>
                      </SortableContext>
                    </div>
                  ))}
                </div>
              </DndContext>

              {completedRootTasks.length > 0 && (
                <div className="space-y-1.5">
                  <CompletedToggle
                    count={completedRootTasks.length}
                    open={showCompletedRoot}
                    onToggle={() => setShowCompletedRoot((o) => !o)}
                  />
                  {showCompletedRoot && (
                    <ul className="space-y-1.5">
                      {completedRootTasks.map((task) => (
                        <TaskCard
                          key={task.id}
                          task={task}
                          assignee={task.assigned_to ? membersById.get(task.assigned_to) : undefined}
                          budgetOwner={
                            task.budget_owner_user_id
                              ? membersById.get(task.budget_owner_user_id)
                              : undefined
                          }
                          isUpdating={updateTask.isPending}
                          onToggleComplete={handleToggleComplete}
                          onDelete={(t) => deleteTask.mutate(t.id)}
                        />
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
