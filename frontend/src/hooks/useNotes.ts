import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as notesApi from "../api/notes";
import type { NoteConvertInput, NoteFolderInput, NoteInput } from "../api/types";

const NOTES_KEY = ["notes"] as const;
const NOTE_FOLDERS_KEY = ["note-folders"] as const;
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

export function useNoteFolders() {
  return useQuery({ queryKey: NOTE_FOLDERS_KEY, queryFn: () => notesApi.listNoteFolders() });
}

export function useCreateNoteFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NoteFolderInput) => notesApi.createNoteFolder(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTE_FOLDERS_KEY }),
  });
}

export function useUpdateNoteFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: NoteFolderInput }) =>
      notesApi.updateNoteFolder(id, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTE_FOLDERS_KEY }),
  });
}

export function useDeleteNoteFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notesApi.deleteNoteFolder(id),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: NOTE_FOLDERS_KEY }),
        // Its notes move out of the folder server-side rather than being
        // deleted, so the note list needs refreshing too.
        queryClient.invalidateQueries({ queryKey: NOTES_KEY }),
      ]),
  });
}
