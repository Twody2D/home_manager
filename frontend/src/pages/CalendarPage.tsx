import { useState } from "react";
import { useTranslation } from "react-i18next";
import { CalendarEventForm } from "../components/CalendarEventForm";
import { CalendarEventCard } from "../components/CalendarEventCard";
import { BulkScheduleForm } from "../components/BulkScheduleForm";
import {
  useCalendarEvents,
  useCreateEvent,
  useCreateEventsBulk,
  useDeleteEvent,
} from "../hooks/useCalendar";
import { useMembers } from "../hooks/useMembers";
import { useAuth } from "../auth/useAuth";
import type { CalendarEvent } from "../api/types";

function groupByDay(events: CalendarEvent[], locale: string): [string, CalendarEvent[]][] {
  const groups = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const key = new Date(event.start_at).toLocaleDateString(locale, {
      weekday: "long",
      month: "long",
      day: "numeric",
    });
    const bucket = groups.get(key);
    if (bucket) {
      bucket.push(event);
    } else {
      groups.set(key, [event]);
    }
  }
  return Array.from(groups.entries());
}

export function CalendarPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  // Stable for the page's lifetime — recomputing this on every render would
  // change the query key each time and the query would never settle.
  const [now] = useState(() => new Date().toISOString());
  const eventsQuery = useCalendarEvents({ ends_after: now });
  const membersQuery = useMembers();
  const createEvent = useCreateEvent();
  const createEventsBulk = useCreateEventsBulk();
  const deleteEvent = useDeleteEvent();

  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));

  if (eventsQuery.isLoading) {
    return <p className="text-sm text-slate-500">{t("calendar.loading")}</p>;
  }

  if (eventsQuery.isError) {
    return <p className="text-sm text-red-600">{t("calendar.error")}</p>;
  }

  const grouped = groupByDay(eventsQuery.data ?? [], i18n.language);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("calendar.title")}</h1>
      <p className="text-xs text-slate-500">{t("calendar.subtitle")}</p>

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

      {grouped.length === 0 && (
        <p className="text-sm text-slate-500">{t("calendar.empty")}</p>
      )}

      {grouped.map(([day, events]) => (
        <section key={day} className="space-y-2">
          <h2 className="text-sm font-medium text-slate-500">{day}</h2>
          <ul className="space-y-2">
            {events.map((event) => (
              <CalendarEventCard
                key={event.id}
                event={event}
                owner={membersById.get(event.user_id)}
                isOwn={event.user_id === user?.id}
                onDelete={(e) => deleteEvent.mutate(e.id)}
              />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
