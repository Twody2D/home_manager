import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as tasksApi from "../api/tasks";
import type { TaskCreateInput, TaskUpdateInput } from "../api/types";

const TASKS_KEY = ["tasks"] as const;

export function useTasks(params: tasksApi.ListTasksParams = {}) {
  return useQuery({
    queryKey: [...TASKS_KEY, params],
    queryFn: () => tasksApi.listTasks(params),
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
