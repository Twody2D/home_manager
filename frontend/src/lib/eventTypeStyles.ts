import type { CalendarEvent } from "../api/types";

export const TYPE_STYLES: Record<CalendarEvent["event_type"], string> = {
  working_hours: "bg-blue-100 text-blue-700",
  sleep: "bg-indigo-100 text-indigo-700",
  meeting: "bg-amber-100 text-amber-700",
  sport: "bg-emerald-100 text-emerald-700",
  trip: "bg-purple-100 text-purple-700",
  personal: "bg-slate-100 text-slate-600",
  unavailable: "bg-red-100 text-red-700",
};

export const TYPE_DOT_STYLES: Record<CalendarEvent["event_type"], string> = {
  working_hours: "bg-blue-500",
  sleep: "bg-indigo-500",
  meeting: "bg-amber-500",
  sport: "bg-emerald-500",
  trip: "bg-purple-500",
  personal: "bg-slate-400",
  unavailable: "bg-red-500",
};
