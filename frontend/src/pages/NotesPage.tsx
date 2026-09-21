import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  useConvertNoteItem,
  useCreateNote,
  useDeleteNote,
  useNotes,
  useUpdateNote,
} from "../hooks/useNotes";
import { useTaskLists } from "../hooks/useTasks";
import type { Note, NoteItem, TaskList } from "../api/types";

// A bullet plus three levels under it, matching MAX_TASK_DEPTH so any bullet
// can always be turned into a task tree.
const MAX_ITEM_DEPTH = 3;

function emptyItem(): NoteItem {
  return { text: "", children: [] };
}

/** Applies `change` to the bullet at `path` (a chain of child indexes), or
 * drops it when `change` returns null, rebuilding the tree above it. */
function editAt(
  items: NoteItem[],
  path: number[],
  change: (item: NoteItem) => NoteItem | null,
): NoteItem[] {
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

function countItems(items: NoteItem[]): number {
  return items.reduce((total, item) => total + 1 + countItems(item.children), 0);
}

function pruneEmpty(items: NoteItem[]): NoteItem[] {
  return items
    .filter((item) => item.text.trim() !== "")
    .map((item) => ({ text: item.text.trim(), children: pruneEmpty(item.children) }));
}

function BulletRow({
  item,
  path,
  depth,
  onChange,
  onAddChild,
  onRemove,
  onConvert,
}: {
  item: NoteItem;
  path: number[];
  depth: number;
  onChange: (path: number[], change: (item: NoteItem) => NoteItem) => void;
  onAddChild: (path: number[]) => void;
  onRemove: (path: number[]) => void;
  onConvert: (path: number[], item: NoteItem) => void;
}) {
  const { t } = useTranslation();
  return (
    <li className="space-y-1.5">
      <div className="space-y-1.5 rounded-lg border border-slate-200 bg-white p-2">
        <div className="flex items-center gap-1.5">
          <span className="shrink-0 text-slate-300">•</span>
          <input
            type="text"
            value={item.text}
            onChange={(e) => onChange(path, (current) => ({ ...current, text: e.target.value }))}
            placeholder={t("notes.itemPlaceholder")}
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
          <button
            type="button"
            aria-label={t("notes.removeItem")}
            onClick={() => onRemove(path)}
            className="shrink-0 rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-red-600"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
            </svg>
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {depth < MAX_ITEM_DEPTH && (
            <button
              type="button"
              onClick={() => onAddChild(path)}
              className="rounded-md border border-dashed border-slate-300 px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-50"
            >
              + {t("notes.addSubitem")}
            </button>
          )}
          <button
            type="button"
            disabled={!item.text.trim()}
            onClick={() => onConvert(path, item)}
            className="rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
          >
            → {t("notes.toTask")}
          </button>
        </div>
      </div>

      {item.children.length > 0 && (
        <ul className="ml-4 space-y-1.5 border-l border-slate-200 pl-3">
          {item.children.map((child, index) => (
            <BulletRow
              key={index}
              item={child}
              path={[...path, index]}
              depth={depth + 1}
              onChange={onChange}
              onAddChild={onAddChild}
              onRemove={onRemove}
              onConvert={onConvert}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

// Asks which folder the new task goes into, and whether the bullet should
// stay in the note afterwards.
function ConvertDialog({
  itemText,
  taskLists,
  isConverting,
  onCancel,
  onConfirm,
}: {
  itemText: string;
  taskLists: TaskList[];
  isConverting: boolean;
  onCancel: () => void;
  onConfirm: (listId: string | null, remove: boolean) => void;
}) {
  const { t } = useTranslation();
  const [listId, setListId] = useState("");
  const [remove, setRemove] = useState(false);

  return (
    <div className="space-y-2 rounded-lg border border-blue-200 bg-blue-50/50 p-3">
      <p className="text-sm font-medium text-slate-700">
        {t("notes.convertTitle", { text: itemText })}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={listId}
          onChange={(e) => setListId(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">{t("tasks.myTasks")}</option>
          {taskLists.map((list) => (
            <option key={list.id} value={list.id}>
              {list.name}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={remove}
            onChange={(e) => setRemove(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300"
          />
          {t("notes.removeAfterConvert")}
        </label>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={isConverting}
          onClick={() => onConfirm(listId || null, remove)}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {isConverting ? t("notes.converting") : t("notes.convertConfirm")}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md px-2 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-100"
        >
          {t("common.cancel")}
        </button>
      </div>
    </div>
  );
}

function NoteEditor({
  note,
  taskLists,
  onDone,
}: {
  note: Note | null;
  taskLists: TaskList[];
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const createNote = useCreateNote();
  const updateNote = useUpdateNote();
  const convertItem = useConvertNoteItem();

  const [title, setTitle] = useState(note?.title ?? "");
  const [items, setItems] = useState<NoteItem[]>(note?.items ?? [emptyItem()]);
  const [converting, setConverting] = useState<{ path: number[]; text: string } | null>(null);
  const isSaving = createNote.isPending || updateNote.isPending;

  function changeItem(path: number[], change: (item: NoteItem) => NoteItem) {
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

  async function save(): Promise<Note> {
    const input = { title: title.trim(), items: pruneEmpty(items) };
    if (note) return await updateNote.mutateAsync({ id: note.id, input });
    return await createNote.mutateAsync(input);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;
    await save();
    onDone();
  }

  // Converting works off what's on screen, so the note is saved first —
  // otherwise a bullet typed just now wouldn't exist server-side yet.
  async function handleConvert(listId: string | null, remove: boolean) {
    if (!converting || !title.trim()) return;
    const saved = await save();
    const task = await convertItem.mutateAsync({
      id: saved.id,
      input: { path: converting.path, list_id: listId, remove },
    });
    setConverting(null);
    navigate(`/tasks/${task.id}`);
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder={t("notes.titlePlaceholder")}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium focus:border-blue-500 focus:outline-none"
      />

      {converting && (
        <ConvertDialog
          itemText={converting.text}
          taskLists={taskLists}
          isConverting={convertItem.isPending || isSaving}
          onCancel={() => setConverting(null)}
          onConfirm={(listId, remove) => void handleConvert(listId, remove)}
        />
      )}

      <ul className="space-y-1.5">
        {items.map((item, index) => (
          <BulletRow
            key={index}
            item={item}
            path={[index]}
            depth={1}
            onChange={changeItem}
            onAddChild={addChild}
            onRemove={removeItem}
            onConvert={(path, item) => setConverting({ path, text: item.text })}
          />
        ))}
      </ul>

      <button
        type="button"
        onClick={() => setItems((current) => [...current, emptyItem()])}
        className="w-full rounded-lg border border-dashed border-slate-300 bg-white px-3 py-2.5 text-sm font-medium text-slate-500 hover:bg-slate-50"
      >
        + {t("notes.addItem")}
      </button>

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={isSaving || !title.trim()}
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

function NotePreview({ items, depth = 0 }: { items: NoteItem[]; depth?: number }) {
  return (
    <ul className={depth === 0 ? "space-y-0.5" : "ml-3 space-y-0.5"}>
      {items.map((item, index) => (
        <li key={index} className="text-sm text-slate-600">
          <span className="text-slate-300">• </span>
          {item.text}
          {item.children.length > 0 && <NotePreview items={item.children} depth={depth + 1} />}
        </li>
      ))}
    </ul>
  );
}

export function NotesPage() {
  const { t } = useTranslation();
  const notesQuery = useNotes();
  const taskListsQuery = useTaskLists();
  const deleteNote = useDeleteNote();

  const [editing, setEditing] = useState<Note | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const notes = notesQuery.data?.items ?? [];
  const taskLists = taskListsQuery.data?.items ?? [];

  return (
    <div className="space-y-4 pb-8">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{t("notes.title")}</h1>
        <p className="text-xs text-slate-500">{t("notes.subtitle")}</p>
      </div>

      {editing || isCreating ? (
        <NoteEditor
          key={editing?.id ?? "new"}
          note={editing}
          taskLists={taskLists}
          onDone={() => {
            setEditing(null);
            setIsCreating(false);
          }}
        />
      ) : (
        <>
          {notesQuery.isLoading && <p className="text-sm text-slate-500">{t("tasks.loading")}</p>}
          {notesQuery.isError && <p className="text-sm text-red-600">{t("tasks.error")}</p>}
          {!notesQuery.isLoading && notes.length === 0 && (
            <p className="text-sm text-slate-500">{t("notes.empty")}</p>
          )}

          <ul className="space-y-2">
            {notes.map((note) => (
              <li key={note.id} className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">{note.title}</p>
                    <p className="text-xs text-slate-400">
                      {t("notes.itemsCount", { count: countItems(note.items) })}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setEditing(note)}
                    className="rounded-md px-2 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50"
                  >
                    {t("notes.edit")}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!window.confirm(t("notes.confirmDelete", { title: note.title }))) return;
                      deleteNote.mutate(note.id);
                    }}
                    className="rounded-md px-2 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    {t("common.delete")}
                  </button>
                </div>
                {note.items.length > 0 && <NotePreview items={note.items} />}
              </li>
            ))}
          </ul>

          <button
            type="button"
            onClick={() => setIsCreating(true)}
            className="w-full rounded-lg border border-dashed border-slate-300 bg-white px-3 py-3 text-sm font-medium text-slate-500 hover:bg-slate-50"
          >
            + {t("notes.add")}
          </button>
        </>
      )}
    </div>
  );
}
