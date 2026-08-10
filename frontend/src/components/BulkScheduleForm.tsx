import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { CalendarEventCreateInput, CalendarEventType } from "../api/types";

const EVENT_TYPES: CalendarEventType[] = [
  "working_hours",
  "sleep",
  "meeting",
  "sport",
  "trip",
  "personal",
  "unavailable",
];

// ISO weekday numbering (Mon=1..Sun=7) so "workweek" defaults read naturally
// as a contiguous 1-5 range instead of wrapping around Sunday=0.
const WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const;

interface Row {
  id: string;
  date: string;
  start: string;
  end: string;
  eventType: CalendarEventType;
}

function isoWeekday(date: Date): number {
  const day = date.getDay();
  return day === 0 ? 7 : day;
}

// Deliberately not toISOString().slice(0, 10) — that goes through UTC and
// shifts the date by a day for any timezone ahead of UTC at local midnight.
function toDateInputValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function toIsoDateTime(dateStr: string, timeStr: string): string {
  return new Date(`${dateStr}T${timeStr}:00`).toISOString();
}

function makeRow(overrides: Partial<Row> = {}): Row {
  return {
    id: crypto.randomUUID(),
    date: toDateInputValue(new Date()),
    start: "09:00",
    end: "18:00",
    eventType: "working_hours",
    ...overrides,
  };
}

interface BulkScheduleFormProps {
  onSubmit: (events: CalendarEventCreateInput[]) => Promise<void>;
  isSubmitting: boolean;
}

export function BulkScheduleForm({ onSubmit, isSubmitting }: BulkScheduleFormProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const [selectedWeekdays, setSelectedWeekdays] = useState<Set<number>>(new Set([1, 2, 3, 4, 5]));
  const [rangeFrom, setRangeFrom] = useState("");
  const [rangeTo, setRangeTo] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("18:00");
  const [eventType, setEventType] = useState<CalendarEventType>("working_hours");
  const [title, setTitle] = useState("");
  const [rows, setRows] = useState<Row[]>([]);

  function toggleWeekday(day: number) {
    setSelectedWeekdays((prev) => {
      const next = new Set(prev);
      if (next.has(day)) next.delete(day);
      else next.add(day);
      return next;
    });
  }

  function handleGenerate() {
    if (!rangeFrom || !rangeTo) return;
    const from = new Date(`${rangeFrom}T00:00:00`);
    const to = new Date(`${rangeTo}T00:00:00`);
    if (to < from) return;

    const generated: Row[] = [];
    for (const cursor = new Date(from); cursor <= to; cursor.setDate(cursor.getDate() + 1)) {
      if (selectedWeekdays.has(isoWeekday(cursor))) {
        generated.push(
          makeRow({
            date: toDateInputValue(cursor),
            start: startTime,
            end: endTime,
            eventType,
          }),
        );
      }
    }
    setRows((prev) => [...prev, ...generated]);
  }

  function updateRow(id: string, patch: Partial<Row>) {
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }

  function removeRow(id: string) {
    setRows((prev) => prev.filter((row) => row.id !== id));
  }

  function rowToInput(row: Row): CalendarEventCreateInput {
    const startAt = toIsoDateTime(row.date, row.start);
    let endDate = row.date;
    if (row.end <= row.start) {
      const rolled = new Date(`${row.date}T00:00:00`);
      rolled.setDate(rolled.getDate() + 1);
      endDate = toDateInputValue(rolled);
    }
    return {
      event_type: row.eventType,
      title: title.trim() || t(`eventType.${row.eventType}`),
      start_at: startAt,
      end_at: toIsoDateTime(endDate, row.end),
    };
  }

  async function handleSubmitAll() {
    if (rows.length === 0) return;
    await onSubmit(rows.map(rowToInput));
    setRows([]);
  }

  if (!expanded) {
    return (
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="w-full rounded-lg border border-dashed border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:border-blue-400 hover:text-blue-600"
      >
        {t("calendar.bulk.toggleOpen")}
      </button>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">{t("calendar.bulk.title")}</h2>
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="text-xs font-medium text-slate-500 hover:text-slate-700"
        >
          {t("calendar.bulk.toggleClose")}
        </button>
      </div>
      <p className="text-xs text-slate-500">{t("calendar.bulk.intro")}</p>

      <div className="space-y-2 rounded-md bg-slate-50 p-3">
        <div>
          <span className="mb-1 block text-xs font-medium text-slate-600">
            {t("calendar.bulk.weekdays")}
          </span>
          <div className="flex flex-wrap gap-1">
            {WEEKDAYS.map((day) => (
              <button
                key={day}
                type="button"
                aria-pressed={selectedWeekdays.has(day)}
                onClick={() => toggleWeekday(day)}
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                  selectedWeekdays.has(day)
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-600 ring-1 ring-inset ring-slate-300"
                }`}
              >
                {t(`weekday.${day}`)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <label className="text-xs">
            <span className="mb-1 block text-slate-600">{t("calendar.bulk.from")}</span>
            <input
              type="date"
              value={rangeFrom}
              onChange={(e) => setRangeFrom(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs">
            <span className="mb-1 block text-slate-600">{t("calendar.bulk.to")}</span>
            <input
              type="date"
              value={rangeTo}
              onChange={(e) => setRangeTo(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs">
            <span className="mb-1 block text-slate-600">{t("calendar.bulk.startTime")}</span>
            <input
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs">
            <span className="mb-1 block text-slate-600">{t("calendar.bulk.endTime")}</span>
            <input
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs">
            <span className="mb-1 block text-slate-600">{t("calendar.bulk.type")}</span>
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
          </label>
        </div>

        <label className="block text-xs">
          <span className="mb-1 block text-slate-600">{t("calendar.bulk.titleOptional")}</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t("calendar.bulk.titlePlaceholder")}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <button
          type="button"
          onClick={handleGenerate}
          disabled={!rangeFrom || !rangeTo || selectedWeekdays.size === 0}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-white disabled:opacity-50"
        >
          {t("calendar.bulk.generate")}
        </button>
      </div>

      <div className="space-y-1.5">
        {rows.length === 0 ? (
          <p className="text-xs text-slate-400">{t("calendar.bulk.rowsEmpty")}</p>
        ) : (
          rows.map((row) => (
            <div key={row.id} className="flex flex-wrap items-center gap-1.5 rounded-md border border-slate-200 p-1.5">
              <input
                type="date"
                value={row.date}
                onChange={(e) => updateRow(row.id, { date: e.target.value })}
                className="rounded border border-slate-300 px-1.5 py-1 text-xs"
              />
              <input
                type="time"
                value={row.start}
                onChange={(e) => updateRow(row.id, { start: e.target.value })}
                className="w-[5.5rem] rounded border border-slate-300 px-1.5 py-1 text-xs"
              />
              <span className="text-slate-400">–</span>
              <input
                type="time"
                value={row.end}
                onChange={(e) => updateRow(row.id, { end: e.target.value })}
                className="w-[5.5rem] rounded border border-slate-300 px-1.5 py-1 text-xs"
              />
              <select
                value={row.eventType}
                onChange={(e) => updateRow(row.id, { eventType: e.target.value as CalendarEventType })}
                className="rounded border border-slate-300 px-1.5 py-1 text-xs"
              >
                {EVENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`eventType.${type}`)}
                  </option>
                ))}
              </select>
              <button
                type="button"
                aria-label={t("calendar.bulk.removeRow")}
                onClick={() => removeRow(row.id)}
                className="ml-auto rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setRows((prev) => [...prev, makeRow()])}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          {t("calendar.bulk.addRow")}
        </button>
        <button
          type="button"
          onClick={() => void handleSubmitAll()}
          disabled={rows.length === 0 || isSubmitting}
          className="ml-auto rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {isSubmitting ? t("calendar.bulk.submitting") : t("calendar.bulk.submit", { count: rows.length })}
        </button>
      </div>
    </div>
  );
}
