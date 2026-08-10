import { apiFetch } from "./client";
import type { CalendarEvent, CalendarEventCreateInput, CalendarEventUpdateInput } from "./types";

export interface ListEventsParams {
  user_id?: string;
  starts_before?: string;
  ends_after?: string;
}

export function listEvents(params: ListEventsParams = {}): Promise<CalendarEvent[]> {
  const search = new URLSearchParams();
  if (params.user_id) search.set("user_id", params.user_id);
  if (params.starts_before) search.set("starts_before", params.starts_before);
  if (params.ends_after) search.set("ends_after", params.ends_after);
  const query = search.toString();
  return apiFetch(`/calendar/events${query ? `?${query}` : ""}`);
}

export function createEvent(input: CalendarEventCreateInput): Promise<CalendarEvent> {
  return apiFetch("/calendar/events", { method: "POST", body: input });
}

export function updateEvent(id: string, input: CalendarEventUpdateInput): Promise<CalendarEvent> {
  return apiFetch(`/calendar/events/${id}`, { method: "PATCH", body: input });
}

export function deleteEvent(id: string): Promise<void> {
  return apiFetch(`/calendar/events/${id}`, { method: "DELETE" });
}
