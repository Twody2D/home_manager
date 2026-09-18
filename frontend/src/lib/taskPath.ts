import type { Task, TaskList } from "../api/types";

export interface TaskPathSegment {
  label: string;
  /** Set for the folder segment — null means the default "My tasks" bucket. */
  listId?: string | null;
  /** Set for an ancestor task segment. */
  taskId?: string;
}

/** The chain a task sits in — its folder first, then each ancestor task from
 * the top down, excluding the task itself. Ancestors missing from `tasksById`
 * just end the chain early, so a partially loaded task set yields a shorter
 * path rather than a wrong one. */
export function buildTaskPathSegments(
  task: Task,
  tasksById: Map<string, Task>,
  listsById: Map<string, TaskList>,
  defaultListLabel: string,
): TaskPathSegment[] {
  const ancestors: TaskPathSegment[] = [];
  let current = task.parent_task_id ? tasksById.get(task.parent_task_id) : undefined;
  while (current) {
    ancestors.unshift({ label: current.title, taskId: current.id });
    current = current.parent_task_id ? tasksById.get(current.parent_task_id) : undefined;
  }

  const listName = task.list_id ? listsById.get(task.list_id)?.name : defaultListLabel;
  return listName ? [{ label: listName, listId: task.list_id }, ...ancestors] : ancestors;
}

export function buildTaskPath(
  task: Task,
  tasksById: Map<string, Task>,
  listsById: Map<string, TaskList>,
  defaultListLabel: string,
): string[] {
  return buildTaskPathSegments(task, tasksById, listsById, defaultListLabel).map((s) => s.label);
}

export const TASK_PATH_SEPARATOR = " › ";
