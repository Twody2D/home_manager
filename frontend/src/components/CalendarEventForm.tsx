import { useState } from "react";
import type { FormEvent } from "react";
import type { CalendarEventCreateInput, CalendarEventType } from "../api/types";

interface CalendarEventFormProps {
  onSubmit: (input: CalendarEventCreateInput) => Promise<void>;
  isSubmitting: boolean;
}

const EVENT_TYPES: CalendarEventType[] = [
  "working_hours",
  "sleep",
  "meeting",
  "sport",
  "trip",
  "personal",
  "unavailable",
];

function toIsoOrNull(localDateTime: string): string | null {
  return localDateTime ? new Date(localDateTime).toISOString() : null;
}

export function CalendarEventForm({ onSubmit, isSubmitting }: CalendarEventFormProps) {
  const [title, setTitle] = useState("");
  const [eventType, setEventType] = useState<CalendarEventType>("meeting");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const startAt = toIsoOrNull(start);
    const endAt = toIsoOrNull(end);
    if (!title.trim() || !startAt || !endAt) return;

    await onSubmit({ title: title.trim(), event_type: eventType, start_at: startAt, end_at: endAt });

    setTitle("");
    setStart("");
    setEnd("");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
      <input
        type="text"
        placeholder="New event…"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />

      <div className="flex flex-wrap gap-2">
        <select
          value={eventType}
          onChange={(e) => setEventType(e.target.value as CalendarEventType)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type.replace("_", " ")}
            </option>
          ))}
        </select>

        <input
          type="datetime-local"
          value={start}
          onChange={(e) => setStart(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />
        <span className="self-center text-slate-400">→</span>
        <input
          type="datetime-local"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />

        <button
          type="submit"
          disabled={isSubmitting || !title.trim() || !start || !end}
          className="ml-auto rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          Add
        </button>
      </div>
    </form>
  );
}
