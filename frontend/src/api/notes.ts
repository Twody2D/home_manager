import { apiFetch } from "./client";
import type {
  Note,
  NoteConvertInput,
  NoteFolder,
  NoteFolderInput,
  NoteFoldersResponse,
  NoteInput,
  NotesResponse,
  Task,
} from "./types";

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

export function listNoteFolders(): Promise<NoteFoldersResponse> {
  return apiFetch("/note-folders");
}

export function createNoteFolder(input: NoteFolderInput): Promise<NoteFolder> {
  return apiFetch("/note-folders", { method: "POST", body: input });
}

export function updateNoteFolder(id: string, input: NoteFolderInput): Promise<NoteFolder> {
  return apiFetch(`/note-folders/${id}`, { method: "PATCH", body: input });
}

export function deleteNoteFolder(id: string): Promise<void> {
  return apiFetch(`/note-folders/${id}`, { method: "DELETE" });
}
