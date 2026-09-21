import { apiFetch } from "./client";
import type { Note, NoteConvertInput, NoteInput, NotesResponse, Task } from "./types";

export function listNotes(): Promise<NotesResponse> {
  return apiFetch("/notes");
}

export function createNote(input: NoteInput): Promise<Note> {
  return apiFetch("/notes", { method: "POST", body: input });
}

export function updateNote(id: string, input: NoteInput): Promise<Note> {
  return apiFetch(`/notes/${id}`, { method: "PATCH", body: input });
}

export function deleteNote(id: string): Promise<void> {
  return apiFetch(`/notes/${id}`, { method: "DELETE" });
}

export function convertNoteItem(id: string, input: NoteConvertInput): Promise<Task> {
  return apiFetch(`/notes/${id}/convert`, { method: "POST", body: input });
}
