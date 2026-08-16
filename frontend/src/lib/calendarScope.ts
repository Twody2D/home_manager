import type { CalendarEvent, User } from "../api/types";
import { scopeForOwner } from "./personScope";
import type { PersonScope } from "./personScope";

export type { PersonScope as EventScope } from "./personScope";
export { SCOPE_BORDER_STYLES, SCOPE_DOT_STYLES } from "./personScope";

export interface ScopedEvent {
  event: CalendarEvent;
  scope: PersonScope;
}

function pairKey(event: CalendarEvent): string {
  return `${event.title}|${event.event_type}|${event.start_at}|${event.end_at}`;
}

// A "shared" event is stored as two independent per-user rows (see
// QuickAddEventForm's shared checkbox) rather than a single row with a
// shared flag — the backend has no such concept. We detect a shared pair
// here by matching title/type/start/end between two different household
// members' events, and collapse the pair into one representative for
// display — this works for any two-person household, not just "me" vs "my
// partner", so it stays correct regardless of who's logged in.
export function scopeEvents(events: CalendarEvent[], members: User[]): ScopedEvent[] {
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
    const distinctOwners = new Set(bucket.map((e) => e.user_id));
    if (bucket.length === 2 && distinctOwners.size === 2) {
      sharedIds.add(bucket[0].id);
      hiddenIds.add(bucket[1].id);
    }
  }

  const result: ScopedEvent[] = [];
  for (const event of events) {
    if (hiddenIds.has(event.id)) continue;
    if (sharedIds.has(event.id)) {
      result.push({ event, scope: "shared" });
    } else {
      result.push({ event, scope: scopeForOwner(event.user_id, members) });
    }
  }
  return result;
}
