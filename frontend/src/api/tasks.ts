import { apiFetch } from "./client";
import type {
  Task,
  TaskCreateInput,
  TaskList,
  TaskListCreateInput,
  TaskListsResponse,
  TaskListUpdateInput,
  TaskPageResponse,
  TaskStatus,
  TaskUpdateInput,
} from "./types";

export interface ListTasksParams {
  status?: TaskStatus;
  assigned_to?: string;
  limit?: number;
  offset?: number;
}

export function listTasks(params: ListTasksParams = {}): Promise<TaskPageResponse> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.assigned_to) search.set("assigned_to", params.assigned_to);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.toString();
  return apiFetch(`/tasks${query ? `?${query}` : ""}`);
}

export function getTask(id: string): Promise<Task> {
  return apiFetch(`/tasks/${id}`);
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

export interface ReorderTasksInput {
  list_id: string | null;
  parent_task_id: string | null;
  ordered_ids: string[];
}

export function reorderTasks(input: ReorderTasksInput): Promise<Task[]> {
  return apiFetch("/tasks/reorder", { method: "PATCH", body: input });
}

export function listTaskLists(): Promise<TaskListsResponse> {
  return apiFetch("/task-lists");
}

export function createTaskList(input: TaskListCreateInput): Promise<TaskList> {
  return apiFetch("/task-lists", { method: "POST", body: input });
}

export function updateTaskList(id: string, input: TaskListUpdateInput): Promise<TaskList> {
  return apiFetch(`/task-lists/${id}`, { method: "PATCH", body: input });
}

export function deleteTaskList(id: string): Promise<void> {
  return apiFetch(`/task-lists/${id}`, { method: "DELETE" });
}

export function reorderTaskLists(orderedIds: string[]): Promise<TaskList[]> {
  return apiFetch("/task-lists/reorder", { method: "PATCH", body: { ordered_ids: orderedIds } });
}
