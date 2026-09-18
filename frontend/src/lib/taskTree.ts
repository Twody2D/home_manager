import type { Task } from "../api/types";

export function childrenByParent(tasks: Task[]): Map<string, Task[]> {
  const children = new Map<string, Task[]>();
  for (const task of tasks) {
    if (!task.parent_task_id) continue;
    const siblings = children.get(task.parent_task_id) ?? [];
    siblings.push(task);
    children.set(task.parent_task_id, siblings);
  }
  return children;
}

/** How many tasks would go with this one — deleting a task cascades to its
 * whole subtree server-side, so this is what a confirmation has to warn
 * about. */
export function countDescendants(taskId: string, children: Map<string, Task[]>): number {
  return (children.get(taskId) ?? []).reduce(
    (total, child) => total + 1 + countDescendants(child.id, children),
    0,
  );
}
