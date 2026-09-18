import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  useCreateTaskTemplate,
  useDeleteTaskTemplate,
  useTaskLists,
  useTaskTemplates,
  useUpdateTaskTemplate,
} from "../hooks/useTasks";
import type { TaskPriority, TaskTemplate, TaskTemplateItem } from "../api/types";

const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

// Root task + three levels of items, matching MAX_TASK_DEPTH on both sides.
const MAX_ITEM_DEPTH = 3;

function emptyItem(): TaskTemplateItem {
  return { title: "", description: null, priority: "medium", duration_minutes: null, children: [] };
}

/** Grows to fit its text instead of scrolling inside a fixed box, so a long
 * checklist description is readable while editing it. */
function AutoTextarea({
  value,
  onChange,
  placeholder,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  className: string;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={2}
      className={`resize-none overflow-hidden ${className}`}
    />
  );
}

// The structure every release already follows — offered as the starting
// point for a new template so a folder like "Треки" doesn't have to be
// retyped from scratch.
function trackStarterItems(): TaskTemplateItem[] {
  const item = (title: string, children: TaskTemplateItem[] = []): TaskTemplateItem => ({
    title,
    description: null,
    priority: "medium",
    duration_minutes: null,
    children,
  });
  return [
    item("Видео сторис"),
    item("Дистрибьюция", [item("Форма дистрибьюции"), item("Текст"), item("Обложка")]),
    item("Питчинг", [
      item("Форма промо"),
      item("Площадки", [
        item("Яндекс музыка (band.link)"),
        item("VK музыка"),
        item("Звук (СТУДИО)"),
        item("КИОН (МТС музыка)"),
        item("Spotify for Artists"),
        item("Apple Music for Artists"),
      ]),
    ]),
  ];
}

/** Applies `change` to the item at `path` (a chain of child indexes), or
 * drops it when `change` returns null, rebuilding the tree above it. */
function editAt(
  items: TaskTemplateItem[],
  path: number[],
  change: (item: TaskTemplateItem) => TaskTemplateItem | null,
): TaskTemplateItem[] {
  const [index, ...rest] = path;
  return items.flatMap((item, i) => {
    if (i !== index) return [item];
    if (rest.length === 0) {
      const next = change(item);
      return next ? [next] : [];
    }
    return [{ ...item, children: editAt(item.children, rest, change) }];
  });
}

function countItems(items: TaskTemplateItem[]): number {
  return items.reduce((total, item) => total + 1 + countItems(item.children), 0);
}

function ItemRow({
  item,
  path,
  depth,
  onChange,
  onAddChild,
  onRemove,
}: {
  item: TaskTemplateItem;
  path: number[];
  depth: number;
  onChange: (path: number[], change: (item: TaskTemplateItem) => TaskTemplateItem) => void;
  onAddChild: (path: number[]) => void;
  onRemove: (path: number[]) => void;
}) {
  const { t } = useTranslation();
  // Descriptions are optional and most items don't need one, so the field
  // only takes up space once it's asked for (or already holds text).
  const [showDescription, setShowDescription] = useState(Boolean(item.description));

  return (
    <li className="space-y-1.5">
      <div className="space-y-1.5 rounded-lg border border-slate-200 bg-white p-2">
        {/* Title gets its own full-width row — sharing one line with the
            controls squeezed it to a few characters on a phone. */}
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={item.title}
            onChange={(e) => onChange(path, (current) => ({ ...current, title: e.target.value }))}
            placeholder={t("templates.itemTitlePlaceholder")}
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
          <button
            type="button"
            aria-label={t("templates.removeItem")}
            onClick={() => onRemove(path)}
            className="shrink-0 rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-red-600"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
            </svg>
          </button>
        </div>
        {showDescription && (
          <AutoTextarea
            value={item.description ?? ""}
            onChange={(value) =>
              onChange(path, (current) => ({ ...current, description: value || null }))
            }
            placeholder={t("templates.descriptionPlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
        )}

        <div className="flex flex-wrap items-center gap-1.5">
          <select
            value={item.priority}
            onChange={(e) =>
              onChange(path, (current) => ({
                ...current,
                priority: e.target.value as TaskPriority,
              }))
            }
            className="rounded-md border border-slate-300 px-2 py-1 text-xs"
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {t(`taskPriority.${p}`)}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={1}
            value={item.duration_minutes ?? ""}
            onChange={(e) =>
              onChange(path, (current) => ({
                ...current,
                duration_minutes: e.target.value ? Number(e.target.value) : null,
              }))
            }
            placeholder={t("templates.durationPlaceholder")}
            className="w-20 rounded-md border border-slate-300 px-2 py-1 text-xs"
          />
          {!showDescription && (
            <button
              type="button"
              onClick={() => setShowDescription(true)}
              className="rounded-md border border-dashed border-slate-300 px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-50"
            >
              + {t("templates.addDescription")}
            </button>
          )}
          {depth < MAX_ITEM_DEPTH && (
            <button
              type="button"
              onClick={() => onAddChild(path)}
              className="rounded-md border border-dashed border-slate-300 px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-50"
            >
              + {t("templates.addSubitem")}
            </button>
          )}
        </div>
      </div>

      {item.children.length > 0 && (
        <ul className="ml-4 space-y-1.5 border-l border-slate-200 pl-3">
          {item.children.map((child, index) => (
            <ItemRow
              key={index}
              item={child}
              path={[...path, index]}
              depth={depth + 1}
              onChange={onChange}
              onAddChild={onAddChild}
              onRemove={onRemove}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function TemplateForm({
  template,
  listId,
  onDone,
}: {
  template: TaskTemplate | null;
  listId: string | null;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const createTemplate = useCreateTaskTemplate();
  const updateTemplate = useUpdateTaskTemplate();

  const [name, setName] = useState(template?.name ?? "");
  const [description, setDescription] = useState(template?.description ?? "");
  const [priority, setPriority] = useState<TaskPriority>(template?.priority ?? "medium");
  const [duration, setDuration] = useState(
    template?.duration_minutes ? String(template.duration_minutes) : "",
  );
  const [items, setItems] = useState<TaskTemplateItem[]>(template?.items ?? []);
  const isSaving = createTemplate.isPending || updateTemplate.isPending;

  function changeItem(path: number[], change: (item: TaskTemplateItem) => TaskTemplateItem) {
    setItems((current) => editAt(current, path, change));
  }

  function addChild(path: number[]) {
    setItems((current) =>
      editAt(current, path, (item) => ({ ...item, children: [...item.children, emptyItem()] })),
    );
  }

  function removeItem(path: number[]) {
    setItems((current) => editAt(current, path, () => null));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    const input = {
      name: name.trim(),
      list_id: listId,
      description: description.trim() || null,
      priority,
      duration_minutes: duration ? Number(duration) : null,
      // A blank row the user never filled in would fail validation server
      // side, so empty titles are dropped rather than sent.
      items: pruneEmpty(items),
    };
    if (template) await updateTemplate.mutateAsync({ id: template.id, input });
    else await createTemplate.mutateAsync(input);
    onDone();
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
      <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("templates.namePlaceholder")}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-medium focus:border-blue-500 focus:outline-none"
        />
        <AutoTextarea
          value={description}
          onChange={setDescription}
          placeholder={t("templates.descriptionPlaceholder")}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <p className="text-xs text-slate-500">{t("templates.rootHint")}</p>
        <div className="flex flex-wrap gap-2">
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as TaskPriority)}
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {t(`taskPriority.${p}`)}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={1}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder={t("templates.durationPlaceholder")}
            className="w-40 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-slate-500">
            {t("templates.itemsTitle", { count: countItems(items) })}
          </h2>
          {items.length === 0 && (
            <button
              type="button"
              onClick={() => setItems(trackStarterItems())}
              className="text-xs font-medium text-blue-600 hover:underline"
            >
              {t("templates.useTrackStarter")}
            </button>
          )}
        </div>
        <ul className="space-y-1.5">
          {items.map((item, index) => (
            <ItemRow
              key={index}
              item={item}
              path={[index]}
              depth={1}
              onChange={changeItem}
              onAddChild={addChild}
              onRemove={removeItem}
            />
          ))}
        </ul>
        <button
          type="button"
          onClick={() => setItems((current) => [...current, emptyItem()])}
          className="w-full rounded-lg border border-dashed border-slate-300 bg-white px-3 py-2.5 text-sm font-medium text-slate-500 hover:bg-slate-50"
        >
          + {t("templates.addItem")}
        </button>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={isSaving || !name.trim()}
          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {t("common.save")}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-md px-3 py-2 text-sm font-medium text-slate-500 hover:bg-slate-100"
        >
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}

function pruneEmpty(items: TaskTemplateItem[]): TaskTemplateItem[] {
  return items
    .filter((item) => item.title.trim() !== "")
    .map((item) => ({
      ...item,
      title: item.title.trim(),
      description: item.description?.trim() || null,
      children: pruneEmpty(item.children),
    }));
}

export function TaskTemplatesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const listId = searchParams.get("list");

  const taskListsQuery = useTaskLists();
  const templatesQuery = useTaskTemplates(listId);
  const deleteTemplate = useDeleteTaskTemplate();

  const [editing, setEditing] = useState<TaskTemplate | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const folder = taskListsQuery.data?.items.find((list) => list.id === listId);
  const templates = templatesQuery.data?.items ?? [];

  return (
    <div className="space-y-4 pb-8">
      <button
        type="button"
        onClick={() => navigate(listId ? `/tasks?list=${listId}` : "/tasks")}
        className="-mx-2 flex items-center gap-1 px-2 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M12.7 4.3a1 1 0 0 1 0 1.4L8.42 10l4.3 4.3a1 1 0 1 1-1.42 1.4l-5-5a1 1 0 0 1 0-1.4l5-5a1 1 0 0 1 1.42 0Z" />
        </svg>
        {t("tasks.detail.back")}
      </button>

      <div>
        <h1 className="text-lg font-semibold text-slate-900">{t("templates.title")}</h1>
        <p className="text-xs text-slate-500">
          {folder ? folder.name : t("tasks.myTasks")} · {t("templates.subtitle")}
        </p>
      </div>

      {editing || isCreating ? (
        <TemplateForm
          key={editing?.id ?? "new"}
          template={editing}
          listId={listId}
          onDone={() => {
            setEditing(null);
            setIsCreating(false);
          }}
        />
      ) : (
        <>
          {templatesQuery.isLoading && <p className="text-sm text-slate-500">{t("tasks.loading")}</p>}
          {templates.length === 0 && !templatesQuery.isLoading && (
            <p className="text-sm text-slate-500">{t("templates.empty")}</p>
          )}
          <ul className="space-y-2">
            {templates.map((template) => (
              <li
                key={template.id}
                className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-900">{template.name}</p>
                  <p className="text-xs text-slate-500">
                    {t("templates.itemsCount", { count: countItems(template.items) })}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setEditing(template)}
                  className="rounded-md px-2 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50"
                >
                  {t("templates.edit")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (!window.confirm(t("templates.confirmDelete", { name: template.name }))) {
                      return;
                    }
                    deleteTemplate.mutate(template.id);
                  }}
                  className="rounded-md px-2 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                >
                  {t("common.delete")}
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => setIsCreating(true)}
            className="w-full rounded-lg border border-dashed border-slate-300 bg-white px-3 py-3 text-sm font-medium text-slate-500 hover:bg-slate-50"
          >
            + {t("templates.add")}
          </button>
        </>
      )}
    </div>
  );
}
