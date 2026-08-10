import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as calendarApi from "../api/calendar";
import type { CalendarEventCreateInput, CalendarEventUpdateInput } from "../api/types";

const EVENTS_KEY = ["calendar-events"] as const;

export function useCalendarEvents(params: calendarApi.ListEventsParams = {}) {
  return useQuery({
    queryKey: [...EVENTS_KEY, params],
    queryFn: () => calendarApi.listEvents(params),
  });
}

export function useCreateEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CalendarEventCreateInput) => calendarApi.createEvent(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: EVENTS_KEY });
    },
  });
}

export function useUpdateEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: CalendarEventUpdateInput }) =>
      calendarApi.updateEvent(id, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: EVENTS_KEY });
    },
  });
}

export function useDeleteEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => calendarApi.deleteEvent(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: EVENTS_KEY });
    },
  });
}
