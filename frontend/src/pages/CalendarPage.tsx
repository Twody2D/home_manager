import { useState } from "react";
import { CalendarEventForm } from "../components/CalendarEventForm";
import { CalendarEventCard } from "../components/CalendarEventCard";
import { useCalendarEvents, useCreateEvent, useDeleteEvent } from "../hooks/useCalendar";
import { useMembers } from "../hooks/useMembers";
import { useAuth } from "../auth/useAuth";
import type { CalendarEvent } from "../api/types";

function groupByDay(events: CalendarEvent[]): [string, CalendarEvent[]][] {
  const groups = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const key = new Date(event.start_at).toLocaleDateString(undefined, {
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
  const { user } = useAuth();
  // Stable for the page's lifetime — recomputing this on every render would
  // change the query key each time and the query would never settle.
  const [now] = useState(() => new Date().toISOString());
  const eventsQuery = useCalendarEvents({ ends_after: now });
  const membersQuery = useMembers();
  const createEvent = useCreateEvent();
  const deleteEvent = useDeleteEvent();

  const members = membersQuery.data ?? [];
  const membersById = new Map(members.map((member) => [member.id, member]));

  if (eventsQuery.isLoading) {
    return <p className="text-sm text-slate-500">Loading calendar…</p>;
  }

  if (eventsQuery.isError) {
    return <p className="text-sm text-red-600">Failed to load calendar.</p>;
  }

  const grouped = groupByDay(eventsQuery.data ?? []);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">Calendar</h1>
      <p className="text-xs text-slate-500">
        You can only add or remove your own events, but you can see the whole household's schedule.
      </p>

      <CalendarEventForm
        isSubmitting={createEvent.isPending}
        onSubmit={async (input) => {
          await createEvent.mutateAsync(input);
        }}
      />

      {grouped.length === 0 && (
        <p className="text-sm text-slate-500">No upcoming events for the household.</p>
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
