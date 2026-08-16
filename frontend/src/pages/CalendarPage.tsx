import { useState } from "react";
import { useTranslation } from "react-i18next";
import { QuickAddEventForm } from "../components/QuickAddEventForm";
import { CalendarEventCard } from "../components/CalendarEventCard";
import { BulkScheduleForm } from "../components/BulkScheduleForm";
import { MonthCalendarGrid } from "../components/MonthCalendarGrid";
import { useCalendarEvents, useCreateEventsBulk, useDeleteEvent } from "../hooks/useCalendar";
import { useMembers } from "../hooks/useMembers";
import { useAuth } from "../auth/useAuth";
import { SCOPE_DOT_STYLES, scopeEvents } from "../lib/calendarScope";
import type { EventScope } from "../lib/calendarScope";
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
  const scopedDayEvents = scopeEvents(selectedDayEvents, user?.id, partner?.id);
  const dayGroups = [
    { key: "shared", label: t("calendar.dayList.shared"), items: scopedDayEvents.filter((s) => s.scope === "shared") },
    { key: "mine", label: t("calendar.dayList.mine"), items: scopedDayEvents.filter((s) => s.scope === "mine") },
    ...(partner
      ? [
          {
            key: "partner",
            label: partner.display_name,
            items: scopedDayEvents.filter((s) => s.scope === "partner"),
          },
        ]
      : []),
  ].filter((group) => group.items.length > 0);
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

      {eventsQuery.isLoading ? (
        <p className="text-sm text-slate-500">{t("calendar.loading")}</p>
      ) : eventsQuery.isError ? (
        <p className="text-sm text-red-600">{t("calendar.error")}</p>
      ) : (
        <MonthCalendarGrid
          monthDate={viewMonth}
          events={events}
          myId={user?.id}
          partnerId={partner?.id}
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
        {dayGroups.length === 0 ? (
          <p className="text-sm text-slate-400">{t("calendar.grid.dayEmpty")}</p>
        ) : (
          dayGroups.map((group) => (
            <div key={group.key} className="space-y-1">
              <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                <span className={`h-2 w-2 rounded-full ${SCOPE_DOT_STYLES[group.key as EventScope]}`} />
                {group.label}
              </h3>
              <ul className="space-y-2">
                {group.items.map(({ event }) => (
                  <CalendarEventCard
                    key={event.id}
                    event={event}
                    owner={group.key === "shared" ? undefined : membersById.get(event.user_id)}
                    isOwn={event.user_id === user?.id}
                    scope={group.key as EventScope}
                    onDelete={(e) => deleteEvent.mutate(e.id)}
                  />
                ))}
              </ul>
            </div>
          ))
        )}

        <QuickAddEventForm
          date={selectedDate}
          partner={partner}
          isSubmitting={createEventsBulk.isPending}
          onSubmit={async (events) => {
            await createEventsBulk.mutateAsync({ events });
          }}
        />
      </section>

      <BulkScheduleForm
        isSubmitting={createEventsBulk.isPending}
        onSubmit={async (events) => {
          await createEventsBulk.mutateAsync({ events });
        }}
      />
    </div>
  );
}
