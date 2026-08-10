import { useState } from "react";
import type { FormEvent } from "react";
import type { TaskCreateInput, TaskPriority, User } from "../api/types";

interface TaskFormProps {
  members: User[];
  onSubmit: (input: TaskCreateInput) => Promise<void>;
  isSubmitting: boolean;
}

const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

export function TaskForm({ members, onSubmit, isSubmitting }: TaskFormProps) {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [assignedTo, setAssignedTo] = useState("");
  const [dueAt, setDueAt] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;

    await onSubmit({
      title: title.trim(),
      priority,
      assigned_to: assignedTo || null,
      due_at: dueAt ? new Date(dueAt).toISOString() : null,
    });

    setTitle("");
    setPriority("medium");
    setAssignedTo("");
    setDueAt("");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
      <input
        type="text"
        placeholder="New task…"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />

      <div className="flex flex-wrap gap-2">
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as TaskPriority)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>

        <select
          value={assignedTo}
          onChange={(e) => setAssignedTo(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">Unassigned</option>
          {members.map((member) => (
            <option key={member.id} value={member.id}>
              {member.display_name}
            </option>
          ))}
        </select>

        <input
          type="datetime-local"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />

        <button
          type="submit"
          disabled={isSubmitting || !title.trim()}
          className="ml-auto rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          Add
        </button>
      </div>
    </form>
  );
}
