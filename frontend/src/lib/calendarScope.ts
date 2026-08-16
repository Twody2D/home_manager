import type { CalendarEvent } from "../api/types";

export type EventScope = "mine" | "partner" | "shared";

export interface ScopedEvent {
  event: CalendarEvent;
  scope: EventScope;
}

function pairKey(event: CalendarEvent): string {
  return `${event.title}|${event.event_type}|${event.start_at}|${event.end_at}`;
}

// A "shared" event is stored as two independent per-user rows (see
// QuickAddEventForm's shared checkbox) rather than a single row with a
// shared flag — the backend has no such concept. We detect a shared pair
// here by matching title/type/start/end between my event and my partner's,
// and collapse the pair into one representative (mine) for display.
export function scopeEvents(
  events: CalendarEvent[],
  myId: string | undefined,
  partnerId: string | undefined,
): ScopedEvent[] {
  const byKey = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const key = pairKey(event);
    const bucket = byKey.get(key);
    if (bucket) bucket.push(event);
    else byKey.set(key, [event]);
  }

  const sharedIds = new Set<string>();
  const hiddenIds = new Set<string>();
  for (const bucket of byKey.values()) {
    const mine = bucket.find((e) => e.user_id === myId);
    const partnerCopy = partnerId ? bucket.find((e) => e.user_id === partnerId) : undefined;
    if (mine && partnerCopy) {
      sharedIds.add(mine.id);
      hiddenIds.add(partnerCopy.id);
    }
  }

  const result: ScopedEvent[] = [];
  for (const event of events) {
    if (hiddenIds.has(event.id)) continue;
    if (sharedIds.has(event.id)) {
      result.push({ event, scope: "shared" });
    } else if (event.user_id === myId) {
      result.push({ event, scope: "mine" });
    } else {
      result.push({ event, scope: "partner" });
    }
  }
  return result;
}

export const SCOPE_DOT_STYLES: Record<EventScope, string> = {
  mine: "bg-sky-500",
  partner: "bg-pink-500",
  shared: "bg-violet-500",
};

export const SCOPE_BORDER_STYLES: Record<EventScope, string> = {
  mine: "border-l-4 border-l-sky-500",
  partner: "border-l-4 border-l-pink-500",
  shared: "border-l-4 border-l-violet-500",
};
