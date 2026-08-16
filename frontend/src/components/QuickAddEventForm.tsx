import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { CalendarEventCreateInput, CalendarEventType, User } from "../api/types";

interface QuickAddEventFormProps {
  date: string;
  partner?: User;
  isSubmitting: boolean;
  onSubmit: (events: CalendarEventCreateInput[]) => Promise<void>;
}

const EVENT_TYPES: CalendarEventType[] = [
  "meeting",
  "personal",
  "sport",
  "trip",
  "working_hours",
  "sleep",
  "unavailable",
];

function toIso(date: string, time: string): string {
  return new Date(`${date}T${time}`).toISOString();
}

export function QuickAddEventForm({ date, partner, isSubmitting, onSubmit }: QuickAddEventFormProps) {
  const { t } = useTranslation();
  const [title, setTitle] = useState("");
  const [eventType, setEventType] = useState<CalendarEventType>("meeting");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [shared, setShared] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || !startTime || !endTime) return;

    const base = {
      event_type: eventType,
      title: title.trim(),
      start_at: toIso(date, startTime),
      end_at: toIso(date, endTime),
    };
    const events: CalendarEventCreateInput[] = [base];
    if (shared && partner) events.push({ ...base, user_id: partner.id });

    await onSubmit(events);

    setTitle("");
    setShared(false);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
      <input
        type="text"
        placeholder={t("calendar.newEventPlaceholder")}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={eventType}
          onChange={(e) => setEventType(e.target.value as CalendarEventType)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`eventType.${type}`)}
            </option>
          ))}
        </select>

        <input
          type="time"
          value={startTime}
          onChange={(e) => setStartTime(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />
        <span className="text-slate-400">→</span>
        <input
          type="time"
          value={endTime}
          onChange={(e) => setEndTime(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />

        <button
          type="submit"
          disabled={isSubmitting || !title.trim()}
          className="ml-auto rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {t("common.add")}
        </button>
      </div>

      {partner && (
        <label className="flex items-center gap-1.5 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={shared}
            onChange={(e) => setShared(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-300"
          />
          {t("calendar.quickAdd.shared")}
        </label>
      )}
    </form>
  );
}
