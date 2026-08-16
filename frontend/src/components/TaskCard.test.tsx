import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TaskCard } from "./TaskCard";
import type { Task } from "../api/types";

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: "task-1",
    tenant_id: "tenant-1",
    created_by: "user-1",
    assigned_to: null,
    title: "Buy groceries",
    description: null,
    status: "pending",
    priority: "medium",
    duration_minutes: null,
    due_at: null,
    preferred_start: null,
    preferred_end: null,
    location: null,
    recurrence: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    completed_at: null,
    ...overrides,
  };
}

describe("TaskCard", () => {
  it("renders the task title and priority", () => {
    render(
      <TaskCard task={makeTask()} onToggleComplete={() => {}} onDelete={() => {}} />,
    );

    expect(screen.getByText("Buy groceries")).toBeInTheDocument();
    expect(screen.getByText("medium")).toBeInTheDocument();
  });

  it("shows completed tasks with strikethrough styling", () => {
    render(
      <TaskCard
        task={makeTask({ status: "completed", completed_at: "2026-01-02T00:00:00Z" })}
        onToggleComplete={() => {}}
        onDelete={() => {}}
      />,
    );

    expect(screen.getByText("Buy groceries")).toHaveClass("line-through");
  });

  it("calls onToggleComplete when the checkbox is clicked", async () => {
    const user = userEvent.setup();
    const onToggleComplete = vi.fn();
    const task = makeTask();

    render(<TaskCard task={task} onToggleComplete={onToggleComplete} onDelete={() => {}} />);
    await user.click(screen.getByRole("button", { name: /mark as completed/i }));

    expect(onToggleComplete).toHaveBeenCalledWith(task);
  });

  it("calls onDelete when the delete button is clicked", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    const task = makeTask();

    render(<TaskCard task={task} onToggleComplete={() => {}} onDelete={onDelete} />);
    await user.click(screen.getByRole("button", { name: /delete task/i }));

    expect(onDelete).toHaveBeenCalledWith(task);
  });

  it("renders the assignee name when provided", () => {
    render(
      <TaskCard
        task={makeTask({ assigned_to: "user-2" })}
        assignee={{
          id: "user-2",
          tenant_id: "tenant-1",
          email: "lena@example.com",
          display_name: "Lena",
          role: "member",
          gender: null,
        }}
        onToggleComplete={() => {}}
        onDelete={() => {}}
      />,
    );

    expect(screen.getByText("Lena")).toBeInTheDocument();
  });
});
