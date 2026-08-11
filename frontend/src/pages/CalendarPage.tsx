import { useState } from "react";
import { useTranslation } from "react-i18next";
import { CalendarEventForm } from "../components/CalendarEventForm";
import { CalendarEventCard } from "../components/CalendarEventCard";
import { BulkScheduleForm } from "../components/BulkScheduleForm";
import { MonthCalendarGrid } from "../components/MonthCalendarGrid";
import {
  useCalendarEvents,
  useCreateEvent,
  useCreateEventsBulk,
  useDeleteEvent,
} from "../hooks/useCalendar";
import { useMembers } from "../hooks/useMembers";
import { useAuth } from "../auth/useAuth";
import type { CalendarEvent } from "../api/types";

function toDateInputValue(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isoWeekday(d: Date): number {
  const day = d.getDay();
  return day === 0 ? 7 : day;
}

// The grid always renders full weeks, so the fetch window should match
// exactly — otherwise a leading/trailing day from the neighboring month
// would show an empty cell even though it has events just outside the
// requested range.
function gridWindow(monthDate: Date): { start: Date; endExclusive: Date } {
  const year = monthDate.getFullYear();
  const monthIndex0 = monthDate.getMonth();
  const firstOfMonth = new Date(year, monthIndex0, 1);
  const daysInMonth = new Date(year, monthIndex0 + 1, 0).getDate();
  const leadingBlanks = isoWeekday(firstOfMonth) - 1;
  const totalCells = Math.ceil((leadingBlanks + daysInMonth) / 7) * 7;
  const start = new Date(year, monthIndex0, 1 - leadingBlanks);
  const endExclusive = new Date(year, monthIndex0, 1 - leadingBlanks + totalCells);
  return { start, endExclusive };
}

type ViewFilter = "all" | "mine" | "partner";

export function CalendarPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [viewMonth, setViewMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [selectedDate, setSelectedDate] = useState(() => toDateInputValue(new Date()));
  const [viewFilter, setViewFilter] = useState<ViewFilter>("all");

  const { start, endExclusive } = gridWindow(viewMonth);
  const eventsQuery = useCalendarEvents({
    ends_after: start.toISOString(),
    starts_before: endExclusive.toISOString(),
  });
  const membersQuery = useMembers();
  const createEvent = useCreateEvent();
  const createEventsBulk = useCreateEventsBulk();
  const deleteEvent = useDeleteEvent();

  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));
  const partner = members.find((member) => member.id !== user?.id);

  function changeMonth(delta: number) {
    setViewMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  }

  function goToToday() {
    const now = new Date();
    setViewMonth(new Date(now.getFullYear(), now.getMonth(), 1));
    setSelectedDate(toDateInputValue(now));
  }

  const allEvents = eventsQuery.data ?? [];
  const events = allEvents.filter((event: CalendarEvent) => {
    if (viewFilter === "mine") return event.user_id === user?.id;
    if (viewFilter === "partner") return partner !== undefined && event.user_id === partner.id;
    return true;
  });
  const selectedDayEvents = events
    .filter((event: CalendarEvent) => toDateInputValue(new Date(event.start_at)) === selectedDate)
    .sort((a, b) => a.start_at.localeCompare(b.start_at));
  const rawSelectedDateLabel = new Date(`${selectedDate}T00:00:00`).toLocaleDateString(
    i18n.language,
    { weekday: "long", month: "long", day: "numeric" },
  );
  // Capitalize only the first character — see MonthCalendarGrid for why not
  // CSS text-transform:capitalize.
  const selectedDateLabel =
    rawSelectedDateLabel.charAt(0).toUpperCase() + rawSelectedDateLabel.slice(1);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("calendar.title")}</h1>
      <p className="text-xs text-slate-500">{t("calendar.subtitle")}</p>

      <div className="flex gap-1">
        <button
          type="button"
          onClick={() => setViewFilter("all")}
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            viewFilter === "all" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("calendar.viewAll")}
        </button>
        <button
          type="button"
          onClick={() => setViewFilter("mine")}
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            viewFilter === "mine" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
          }`}
        >
          {t("calendar.viewMine")}
        </button>
        {partner && (
          <button
            type="button"
            onClick={() => setViewFilter("partner")}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              viewFilter === "partner" ? "bg-blue-600 text-white" : "bg-white text-slate-600"
            }`}
          >
            {partner.display_name}
          </button>
        )}
      </div>

      <CalendarEventForm
        isSubmitting={createEvent.isPending}
        onSubmit={async (input) => {
          await createEvent.mutateAsync(input);
        }}
      />

      <BulkScheduleForm
        isSubmitting={createEventsBulk.isPending}
        onSubmit={async (events) => {
          await createEventsBulk.mutateAsync({ events });
        }}
      />

      {eventsQuery.isLoading ? (
        <p className="text-sm text-slate-500">{t("calendar.loading")}</p>
      ) : eventsQuery.isError ? (
        <p className="text-sm text-red-600">{t("calendar.error")}</p>
      ) : (
        <MonthCalendarGrid
          monthDate={viewMonth}
          events={events}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
          onPrevMonth={() => changeMonth(-1)}
          onNextMonth={() => changeMonth(1)}
          onToday={goToToday}
          locale={i18n.language}
        />
      )}

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-500">{selectedDateLabel}</h2>
        {selectedDayEvents.length === 0 ? (
          <p className="text-sm text-slate-400">{t("calendar.grid.dayEmpty")}</p>
        ) : (
          <ul className="space-y-2">
            {selectedDayEvents.map((event) => (
              <CalendarEventCard
                key={event.id}
                event={event}
                owner={membersById.get(event.user_id)}
                isOwn={event.user_id === user?.id}
                onDelete={(e) => deleteEvent.mutate(e.id)}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
