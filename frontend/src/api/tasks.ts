import { apiFetch } from "./client";
import type { Task, TaskCreateInput, TaskListResponse, TaskStatus, TaskUpdateInput } from "./types";

export interface ListTasksParams {
  status?: TaskStatus;
  assigned_to?: string;
  limit?: number;
  offset?: number;
}

export function listTasks(params: ListTasksParams = {}): Promise<TaskListResponse> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.assigned_to) search.set("assigned_to", params.assigned_to);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.toString();
  return apiFetch(`/tasks${query ? `?${query}` : ""}`);
}

export function createTask(input: TaskCreateInput): Promise<Task> {
  return apiFetch("/tasks", { method: "POST", body: input });
}

export function updateTask(id: string, input: TaskUpdateInput): Promise<Task> {
  return apiFetch(`/tasks/${id}`, { method: "PATCH", body: input });
}

export function deleteTask(id: string): Promise<void> {
  return apiFetch(`/tasks/${id}`, { method: "DELETE" });
}
