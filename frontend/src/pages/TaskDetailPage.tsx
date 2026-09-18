import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { flushSync } from "react-dom";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent, DragMoveEvent } from "@dnd-kit/core";
import { SortableContext, arrayMove, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { ApiError } from "../api/client";
import { GripIcon } from "../components/TaskCard";
import { SortableListItem } from "../components/SortableListItem";
import {
  useCreateTask,
  useDeleteTask,
  useReorderTasks,
  useTask,
  useTasks,
  useTaskLists,
  useUpdateTask,
} from "../hooks/useTasks";
import { useMembers } from "../hooks/useMembers";
import type { Task, TaskPriority, TaskUpdateInput } from "../api/types";

// Levels: task / subtask / sub-subtask / sub-sub-subtask — kept in sync
// with MAX_TASK_DEPTH in the backend's tasks/service.py.
const MAX_TASK_DEPTH = 4;

// See NEST_ZONE_OFFSET in TasksPage — once the dragged subtask's left edge
// has moved this far past a sibling's own left edge, it's hovering over
// that sibling's content (not lined up with its grip/checkbox column),
// which nests it under that sibling instead of reordering.
const NEST_ZONE_OFFSET = 24;

const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

function FieldLabel({ children }: { children: string }) {
  return <span className="mb-1 block text-xs font-medium text-slate-600">{children}</span>;
}

// A sub-subtask (and deeper) row nested under its parent — shown so the
// whole tree is visible without drilling in. No drag support at this depth
// (that stays available by opening the row's own detail page); recurses for
// however many further levels of children it has, so it naturally renders
// a sub-sub-subtask nested under a sub-subtask too.
function SubSubtaskRow({
  task,
  childrenByParent,
  onToggleComplete,
  onDelete,
  t,
}: {
  task: Task;
  childrenByParent: Map<string, Task[]>;
  onToggleComplete: (id: string) => void;
  onDelete: (id: string) => void;
  t: (key: string, options?: Record<string, unknown>) => string;
}) {
  const isCompleted = task.status === "completed";
  const children = childrenByParent.get(task.id) ?? [];
  return (
    <li className="space-y-1">
      <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2 py-1.5">
        <button
          type="button"
          onClick={() => onToggleComplete(task.id)}
          className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 ${
            isCompleted ? "border-blue-600 bg-blue-600" : "border-slate-300"
          }`}
        />
        <Link
          to={`/tasks/${task.id}`}
          className={`flex-1 truncate text-sm ${
            isCompleted ? "text-slate-400 line-through" : "text-slate-700"
          }`}
          draggable={false}
        >
          {task.title}
        </Link>
        <button
          type="button"
          aria-label={t("taskCard.deleteTask")}
          onClick={() => onDelete(task.id)}
          className="shrink-0 rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-red-600"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
            <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
          </svg>
        </button>
      </div>
      {children.length > 0 && (
        <ul className="ml-5 space-y-1 border-l border-slate-200 pl-3">
          {children.map((child) => (
            <SubSubtaskRow
              key={child.id}
              task={child}
              childrenByParent={childrenByParent}
              onToggleComplete={onToggleComplete}
              onDelete={onDelete}
              t={t}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export function TaskDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { taskId } = useParams<{ taskId: string }>();

  const taskQuery = useTask(taskId);
  const task = taskQuery.data;
  const parentQuery = useTask(task?.parent_task_id ?? undefined);
  const membersQuery = useMembers();
  const taskListsQuery = useTaskLists();
  // Must cover the whole household task set — see the matching comment in
  // TasksPage, same reasoning (this builds grandchildrenByParent for the
  // subtask tree and for duplicateSubtree's descendant lookup, both of
  // which need every task, not just the first page).
  const allTasksQuery = useTasks({ limit: 1000 });

  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();
  const createTask = useCreateTask();
  const reorderTasks = useReorderTasks();

  const members = membersQuery.data ?? [];
  const taskLists = taskListsQuery.data?.items ?? [];
  const allTasks = allTasksQuery.data?.items ?? [];
  const byId = new Map(allTasks.map((t) => [t.id, t]));
  const subtasks = allTasks.filter((t) => t.parent_task_id === task?.id);
  // Every non-root task, keyed by its immediate parent id, so each subtask
  // row can recursively show its own children — covers sub-subtasks and
  // sub-sub-subtasks alike, at whatever depth they occur.
  const grandchildrenByParent = new Map<string, Task[]>();
  for (const t of allTasks) {
    if (!t.parent_task_id) continue;
    const list = grandchildrenByParent.get(t.parent_task_id) ?? [];
    list.push(t);
    grandchildrenByParent.set(t.parent_task_id, list);
  }

  // 0 for a top-level task, 1 for a subtask, and so on — walked locally from
  // the already-fetched household task list rather than another request.
  function taskDepth(id: string): number {
    let depth = 0;
    let current = byId.get(id);
    while (current?.parent_task_id) {
      depth += 1;
      current = byId.get(current.parent_task_id);
    }
    return depth;
  }

  // 0 if id has no children, otherwise 1 + its tallest child subtree — see
  // the same helper in TasksPage.
  function subtreeHeight(id: string): number {
    const children = grandchildrenByParent.get(id) ?? [];
    if (children.length === 0) return 0;
    return 1 + Math.max(...children.map((child) => subtreeHeight(child.id)));
  }

  function isDescendantOf(ancestorId: string, candidateId: string): boolean {
    const stack = [...(grandchildrenByParent.get(ancestorId) ?? [])];
    while (stack.length > 0) {
      const current = stack.pop();
      if (!current) continue;
      if (current.id === candidateId) return true;
      stack.push(...(grandchildrenByParent.get(current.id) ?? []));
    }
    return false;
  }

  // Whether activeId, currently dragged to activeRect, is hovering over
  // overId's name (rather than lined up with its grip/checkbox column) —
  // null if not, or if nesting there wouldn't be valid. Shared by the live
  // drag-move preview and the actual drop handler.
  function resolveNestTarget(
    activeId: string,
    overId: string,
    activeRect: { left: number } | null,
    overRect: { left: number },
  ): string | null {
    if (activeId === overId || !activeRect) return null;
    if (activeRect.left - overRect.left < NEST_ZONE_OFFSET) return null;
    if (isDescendantOf(activeId, overId)) return null;
    const newDepth = taskDepth(overId) + 1;
    if (newDepth + subtreeHeight(activeId) > MAX_TASK_DEPTH - 1) return null;
    return overId;
  }

  const [loadedId, setLoadedId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const descriptionRef = useRef<HTMLTextAreaElement | null>(null);
  const [duration, setDuration] = useState("");
  const [location, setLocation] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [isAddingSubtask, setIsAddingSubtask] = useState(false);
  const [subtaskTitle, setSubtaskTitle] = useState("");
  // Immediate local reflection of a just-dropped subtask reorder — see the
  // same pattern (and the reason it's needed) in TasksPage.
  const [subtaskOrder, setSubtaskOrder] = useState<string[] | null>(null);
  // The subtask currently highlighted as the pending drop target for
  // nesting — see the same pattern in TasksPage.
  const [nestTargetId, setNestTargetId] = useState<string | null>(null);
  const [isDuplicating, setIsDuplicating] = useState(false);
  // A ref (not just the isDuplicating state) because state updates are
  // batched/async — a fast double-click could otherwise slip a second
  // handleDuplicate() past the isDuplicating check before the first one's
  // setIsDuplicating(true) has actually re-rendered, launching two
  // duplicate operations (and two competing navigations) in parallel.
  const isDuplicatingRef = useRef(false);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  // Belt-and-braces reset: react-router keeps this same component instance
  // mounted across /tasks/:taskId -> /tasks/:otherId navigations (only the
  // param changes), so isDuplicating is otherwise scoped to the page, not
  // the specific task. If a duplicate's promise chain is ever interrupted
  // in a way that skips handleDuplicate's own finally (a stale in-flight
  // request racing a fast subsequent navigation, browser back/forward,
  // etc.), the button could stay stuck disabled on every task viewed
  // afterwards. Tying the reset to taskId guarantees every task page starts
  // with a clean, clickable button regardless of what happened before.
  useEffect(() => {
    isDuplicatingRef.current = false;
    setIsDuplicating(false);
  }, [taskId]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") navigate(-1);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navigate]);

  useEffect(() => {
    if (task && task.id !== loadedId) {
      setTitle(task.title);
      setDescription(task.description ?? "");
      setDuration(task.duration_minutes ? String(task.duration_minutes) : "");
      setLocation(task.location ?? "");
      setBudgetAmount(task.budget_amount ?? "");
      setLoadedId(task.id);
    }
  }, [task, loadedId]);

  // Grow the description box to fit all of its text instead of scrolling
  // inside a fixed-height box, so the full description is visible at once.
  useEffect(() => {
    const el = descriptionRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [description]);

  function save(input: TaskUpdateInput) {
    if (!task) return;
    updateTask.mutate({ id: task.id, input });
  }

  async function handleAddSubtask(event: FormEvent) {
    event.preventDefault();
    if (!task || !subtaskTitle.trim()) return;
    await createTask.mutateAsync({ title: subtaskTitle.trim(), parent_task_id: task.id });
    setSubtaskTitle("");
    setIsAddingSubtask(false);
  }

  // Copies source and, recursively, every one of its descendants (so
  // duplicating a task with a subtask structure — e.g. a release checklist
  // — reproduces the whole tree, not just the top task) under parentId.
  async function duplicateSubtree(source: Task, parentId: string | null): Promise<Task> {
    const created = await createTask.mutateAsync({
      title: source.title,
      description: source.description,
      assigned_to: source.assigned_to,
      priority: source.priority,
      duration_minutes: source.duration_minutes,
      due_at: source.due_at,
      preferred_start: source.preferred_start,
      preferred_end: source.preferred_end,
      location: source.location,
      recurrence: source.recurrence,
      budget_amount: source.budget_amount,
      budget_owner_user_id: source.budget_owner_user_id,
      list_id: source.list_id,
      parent_task_id: parentId,
    });
    for (const child of grandchildrenByParent.get(source.id) ?? []) {
      await duplicateSubtree(child, created.id);
    }
    return created;
  }

  async function handleDuplicate() {
    if (!task || isDuplicatingRef.current) return;
    isDuplicatingRef.current = true;
    setIsDuplicating(true);
    try {
      const duplicate = await duplicateSubtree(
        { ...task, title: `${task.title} ${t("tasks.detail.duplicateSuffix")}` },
        task.parent_task_id,
      );
      navigate(`/tasks/${duplicate.id}`);
    } catch {
      // Surfaced rather than swallowed — an interrupted duplicate can
      // otherwise leave a partial copy behind with no feedback at all.
      window.alert(t("tasks.detail.duplicateFailed"));
    } finally {
      isDuplicatingRef.current = false;
      setIsDuplicating(false);
    }
  }

  const orderedSubtasks = (() => {
    if (!subtaskOrder) return subtasks;
    const byId = new Map(subtasks.map((s) => [s.id, s]));
    const known = new Set(subtasks.map((s) => s.id));
    const ordered = subtaskOrder.filter((id) => known.has(id)).map((id) => byId.get(id)!);
    const missing = subtasks.filter((s) => !subtaskOrder.includes(s.id));
    return [...ordered, ...missing];
  })();

  function handleSubtaskDragMove(event: DragMoveEvent) {
    const { active, over } = event;
    const target = over
      ? resolveNestTarget(String(active.id), String(over.id), active.rect.current.translated, over.rect)
      : null;
    setNestTargetId((prev) => (prev === target ? prev : target));
  }

  function handleSubtaskDragCancel() {
    setNestTargetId(null);
  }

  function handleSubtaskDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setNestTargetId(null);
    if (!task || !over || active.id === over.id) return;

    const nestTarget = resolveNestTarget(
      String(active.id),
      String(over.id),
      active.rect.current.translated,
      over.rect,
    );
    if (nestTarget) {
      // Hovering over the sibling's name rather than reordering — nest the
      // dragged subtask under that sibling instead.
      updateTask.mutate({ id: String(active.id), input: { parent_task_id: nestTarget } });
      return;
    }

    const ids = orderedSubtasks.map((s) => s.id);
    const oldIndex = ids.indexOf(String(active.id));
    const newIndex = ids.indexOf(String(over.id));
    if (oldIndex === -1 || newIndex === -1) return;
    const reordered = arrayMove(ids, oldIndex, newIndex);
    // See TasksPage.handleDragEnd for why this is wrapped in flushSync.
    flushSync(() => setSubtaskOrder(reordered));
    reorderTasks.mutate(
      { list_id: task.list_id, parent_task_id: task.id, ordered_ids: reordered },
      { onSettled: () => setSubtaskOrder(null) },
    );
  }

  async function handleDelete() {
    if (!task) return;
    if (!window.confirm(t("tasks.confirmDelete", { title: task.title }))) return;
    await deleteTask.mutateAsync(task.id);
    navigate("/tasks");
  }

  if (taskQuery.isLoading) {
    return <p className="text-sm text-slate-500">{t("tasks.detail.loading")}</p>;
  }
  if (taskQuery.isError || !task) {
    // A genuine 404 (task really doesn't exist — deleted, wrong link) is
    // the only case where "not found" is actually true. Any other failure
    // (a dropped connection, a timeout, a server hiccup) previously showed
    // the exact same "not found" text, which reads as "this task is gone"
    // when the task is very likely still there — misleading right when a
    // long-running action like duplicating a large subtree is most likely
    // to hit a transient network blip mid-flight. Only offer the retry
    // button for the latter case; a real 404 has nothing to retry.
    const isNotFound = taskQuery.error instanceof ApiError && taskQuery.error.status === 404;
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-600">
          {isNotFound ? t("tasks.detail.notFound") : t("tasks.detail.loadFailed")}
        </p>
        <div className="flex items-center gap-4">
          {!isNotFound && (
            <button
              type="button"
              onClick={() => void taskQuery.refetch()}
              className="text-sm font-medium text-blue-600 hover:underline"
            >
              {t("common.retry")}
            </button>
          )}
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="text-sm font-medium text-blue-600 hover:underline"
          >
            ← {t("tasks.detail.back")}
          </button>
        </div>
      </div>
    );
  }

  const isCompleted = task.status === "completed";
  const isSubtask = task.parent_task_id !== null;
  // A task can have children as long as they'd still fit under the depth
  // cap — only a task at the deepest allowed level can't.
  const canHaveSubtasks = taskDepth(task.id) < MAX_TASK_DEPTH - 1;

  return (
    <div className="space-y-4 pb-8">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="-mx-2 flex items-center gap-1 px-2 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M12.7 4.3a1 1 0 0 1 0 1.4L8.42 10l4.3 4.3a1 1 0 1 1-1.42 1.4l-5-5a1 1 0 0 1 0-1.4l5-5a1 1 0 0 1 1.42 0Z" />
        </svg>
        {t("tasks.detail.back")}
      </button>

      {isSubtask && parentQuery.data && (
        <p className="text-xs text-slate-500">
          {t("tasks.detail.parentTask", { title: parentQuery.data.title })}
        </p>
      )}

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={() => title.trim() && title.trim() !== task.title && save({ title: title.trim() })}
        placeholder={t("tasks.detail.titlePlaceholder")}
        className={`w-full border-b border-slate-200 pb-2 text-lg font-semibold focus:border-blue-500 focus:outline-none ${
          isCompleted ? "text-slate-400 line-through" : "text-slate-900"
        }`}
      />

      <textarea
        ref={descriptionRef}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        onBlur={() =>
          description !== (task.description ?? "") && save({ description: description || null })
        }
        placeholder={t("tasks.detail.descriptionPlaceholder")}
        rows={2}
        className="w-full resize-none overflow-hidden rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />

      <div className="grid grid-cols-2 gap-3">
        <label className="block text-sm">
          <FieldLabel>{t("tasks.detail.priority")}</FieldLabel>
          <select
            value={task.priority}
            onChange={(e) => save({ priority: e.target.value as TaskPriority })}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {t(`taskPriority.${p}`)}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <FieldLabel>{t("tasks.detail.assignee")}</FieldLabel>
          <select
            value={task.assigned_to ?? ""}
            onChange={(e) => save({ assigned_to: e.target.value || null })}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">{t("tasks.unassigned")}</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <FieldLabel>{t("tasks.detail.dueDate")}</FieldLabel>
          <input
            type="datetime-local"
            defaultValue={toDatetimeLocal(task.due_at)}
            onChange={(e) =>
              save({ due_at: e.target.value ? new Date(e.target.value).toISOString() : null })
            }
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <label className="block text-sm">
          <FieldLabel>{t("tasks.detail.duration")}</FieldLabel>
          <input
            type="number"
            min={1}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            onBlur={() => {
              const next = duration ? Number(duration) : null;
              if (next !== task.duration_minutes) save({ duration_minutes: next });
            }}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <label className="col-span-2 block text-sm">
          <FieldLabel>{t("tasks.detail.location")}</FieldLabel>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            onBlur={() => location !== (task.location ?? "") && save({ location: location || null })}
            placeholder={t("tasks.detail.locationPlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        {!isSubtask && (
          <label className="col-span-2 block text-sm">
            <FieldLabel>{t("tasks.detail.list")}</FieldLabel>
            <select
              value={task.list_id ?? ""}
              onChange={(e) => save({ list_id: e.target.value || null })}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            >
              <option value="">{t("tasks.myTasks")}</option>
              {taskLists.map((list) => (
                <option key={list.id} value={list.id}>
                  {list.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block text-sm">
          <FieldLabel>{t("tasks.budget.add")}</FieldLabel>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={budgetAmount}
            onChange={(e) => setBudgetAmount(e.target.value)}
            onBlur={() =>
              budgetAmount !== (task.budget_amount ?? "") &&
              save({ budget_amount: budgetAmount || null })
            }
            placeholder={t("tasks.budget.amountPlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <label className="block text-sm">
          <FieldLabel>{t("tasks.budget.owner")}</FieldLabel>
          <select
            value={task.budget_owner_user_id ?? ""}
            onChange={(e) => save({ budget_owner_user_id: e.target.value || null })}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">{t("tasks.budget.shared")}</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {canHaveSubtasks && (
        <div className="space-y-2 border-t border-slate-100 pt-3">
          <h2 className="text-sm font-semibold text-slate-900">{t("tasks.detail.subtasksTitle")}</h2>
          {subtasks.length === 0 && <p className="text-sm text-slate-400">{t("tasks.empty")}</p>}
          {subtasks.length > 0 && (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragMove={handleSubtaskDragMove}
              onDragEnd={handleSubtaskDragEnd}
              onDragCancel={handleSubtaskDragCancel}
            >
              <SortableContext
                items={orderedSubtasks.map((s) => s.id)}
                strategy={verticalListSortingStrategy}
              >
                <ul className="space-y-1.5">
                  {orderedSubtasks.map((subtask) => {
                    const grandchildren = grandchildrenByParent.get(subtask.id) ?? [];
                    return (
                      <SortableListItem key={subtask.id} id={subtask.id}>
                        {(slot) => (
                          <li ref={slot.innerRef} style={slot.style} className="space-y-1.5">
                            <div
                              className={`flex items-center gap-2 rounded-md border px-2 py-2 ${
                                nestTargetId === subtask.id
                                  ? "border-blue-400 bg-blue-50 ring-2 ring-blue-400"
                                  : "border-slate-200 bg-white"
                              }`}
                            >
                              <button
                                type="button"
                                aria-label={t("taskCard.reorder")}
                                className="flex h-9 w-8 shrink-0 touch-none items-center justify-center text-slate-300 hover:text-slate-500"
                                {...slot.dragHandleProps}
                              >
                                <GripIcon />
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  updateTask.mutate({
                                    id: subtask.id,
                                    input: {
                                      status: subtask.status === "completed" ? "pending" : "completed",
                                    },
                                  })
                                }
                                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                                  subtask.status === "completed"
                                    ? "border-blue-600 bg-blue-600"
                                    : "border-slate-300"
                                }`}
                              />
                              <Link
                                to={`/tasks/${subtask.id}`}
                                className={`flex-1 truncate text-sm ${
                                  subtask.status === "completed"
                                    ? "text-slate-400 line-through"
                                    : "text-slate-900"
                                }`}
                                draggable={false}
                              >
                                {subtask.title}
                              </Link>
                              <button
                                type="button"
                                aria-label={t("taskCard.deleteTask")}
                                onClick={() => deleteTask.mutate(subtask.id)}
                                className="shrink-0 rounded-md p-2.5 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                              >
                                <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                                  <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
                                </svg>
                              </button>
                            </div>
                            {grandchildren.length > 0 && (
                              <ul className="ml-6 space-y-1 border-l border-slate-200 pl-3">
                                {grandchildren.map((grandchild) => (
                                  <SubSubtaskRow
                                    key={grandchild.id}
                                    task={grandchild}
                                    childrenByParent={grandchildrenByParent}
                                    onToggleComplete={(id) =>
                                      updateTask.mutate({
                                        id,
                                        input: {
                                          status:
                                            byId.get(id)?.status === "completed"
                                              ? "pending"
                                              : "completed",
                                        },
                                      })
                                    }
                                    onDelete={(id) => deleteTask.mutate(id)}
                                    t={t}
                                  />
                                ))}
                              </ul>
                            )}
                          </li>
                        )}
                      </SortableListItem>
                    );
                  })}
                </ul>
              </SortableContext>
            </DndContext>
          )}
          {isAddingSubtask ? (
            <form onSubmit={(e) => void handleAddSubtask(e)} className="flex items-center gap-1">
              <input
                type="text"
                autoFocus
                value={subtaskTitle}
                onChange={(e) => setSubtaskTitle(e.target.value)}
                placeholder={t("tasks.subtaskPlaceholder")}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              />
              <button
                type="submit"
                disabled={!subtaskTitle.trim()}
                className="shrink-0 rounded-md bg-blue-600 px-2 py-1.5 text-sm font-medium text-white disabled:opacity-60"
              >
                {t("common.add")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsAddingSubtask(false);
                  setSubtaskTitle("");
                }}
                className="shrink-0 rounded-md px-2 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
              >
                {t("common.cancel")}
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setIsAddingSubtask(true)}
              className="text-sm font-medium text-slate-400 hover:text-slate-600"
            >
              + {t("tasks.addSubtask")}
            </button>
          )}
        </div>
      )}

      <div className="flex gap-2 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={() => save({ status: isCompleted ? "pending" : "completed" })}
          className="flex-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {isCompleted ? t("tasks.detail.markIncomplete") : t("tasks.detail.markComplete")}
        </button>
        <button
          type="button"
          onClick={() => void handleDuplicate()}
          disabled={isDuplicating}
          className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60"
        >
          {isDuplicating ? t("tasks.detail.duplicating") : t("tasks.detail.duplicate")}
        </button>
        <button
          type="button"
          onClick={() => void handleDelete()}
          className="rounded-md border border-red-200 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
        >
          {t("tasks.detail.delete")}
        </button>
      </div>
    </div>
  );
}
