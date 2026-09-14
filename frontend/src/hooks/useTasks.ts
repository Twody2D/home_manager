import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as tasksApi from "../api/tasks";
import type { TaskCreateInput, TaskListCreateInput, TaskUpdateInput } from "../api/types";

const TASKS_KEY = ["tasks"] as const;
const TASK_LISTS_KEY = ["task-lists"] as const;

export function useTasks(params: tasksApi.ListTasksParams = {}) {
  return useQuery({
    queryKey: [...TASKS_KEY, params],
    queryFn: () => tasksApi.listTasks(params),
  });
}

export function useTask(id: string | undefined) {
  return useQuery({
    queryKey: [...TASKS_KEY, "detail", id],
    queryFn: () => tasksApi.getTask(id as string),
    enabled: id !== undefined,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TaskCreateInput) => tasksApi.createTask(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TASKS_KEY });
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: TaskUpdateInput }) =>
      tasksApi.updateTask(id, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TASKS_KEY });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => tasksApi.deleteTask(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TASKS_KEY });
    },
  });
}

export function useReorderTasks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: tasksApi.ReorderTasksInput) => tasksApi.reorderTasks(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TASKS_KEY });
    },
  });
}

export function useTaskLists() {
  return useQuery({
    queryKey: TASK_LISTS_KEY,
    queryFn: () => tasksApi.listTaskLists(),
  });
}

export function useCreateTaskList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TaskListCreateInput) => tasksApi.createTaskList(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TASK_LISTS_KEY });
    },
  });
}

export function useRenameTaskList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: TaskListCreateInput }) =>
      tasksApi.renameTaskList(id, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TASK_LISTS_KEY });
    },
  });
}

export function useDeleteTaskList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => tasksApi.deleteTaskList(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TASK_LISTS_KEY });
      // Deleted-list tasks move back to "My Tasks" server-side — refresh
      // the task list too so that shows up immediately.
      void queryClient.invalidateQueries({ queryKey: TASKS_KEY });
    },
  });
}

export function useReorderTaskLists() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderedIds: string[]) => tasksApi.reorderTaskLists(orderedIds),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TASK_LISTS_KEY });
    },
  });
}
