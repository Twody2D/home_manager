import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as notesApi from "../api/notes";
import type { NoteConvertInput, NoteInput } from "../api/types";

const NOTES_KEY = ["notes"] as const;
const TASKS_KEY = ["tasks"] as const;

export function useNotes() {
  return useQuery({ queryKey: NOTES_KEY, queryFn: () => notesApi.listNotes() });
}

export function useCreateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NoteInput) => notesApi.createNote(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTES_KEY }),
  });
}

export function useUpdateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: NoteInput }) =>
      notesApi.updateNote(id, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTES_KEY }),
  });
}

export function useDeleteNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notesApi.deleteNote(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTES_KEY }),
  });
}

export function useConvertNoteItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: NoteConvertInput }) =>
      notesApi.convertNoteItem(id, input),
    // Converting can also remove the bullet it moved, so both lists refresh.
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: TASKS_KEY }),
        queryClient.invalidateQueries({ queryKey: NOTES_KEY }),
      ]),
  });
}
