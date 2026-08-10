import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CalendarEventCard } from "./CalendarEventCard";
import type { CalendarEvent } from "../api/types";

function makeEvent(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: "event-1",
    tenant_id: "tenant-1",
    user_id: "user-1",
    event_type: "meeting",
    title: "Team sync",
    description: null,
    start_at: "2026-01-05T09:00:00Z",
    end_at: "2026-01-05T10:00:00Z",
    all_day: false,
    location: null,
    recurrence: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("CalendarEventCard", () => {
  it("renders the event title and type", () => {
    render(<CalendarEventCard event={makeEvent()} isOwn={false} onDelete={() => {}} />);

    expect(screen.getByText("Team sync")).toBeInTheDocument();
    expect(screen.getByText("meeting")).toBeInTheDocument();
  });

  it("shows a delete button only for the current user's own events", () => {
    const { rerender } = render(
      <CalendarEventCard event={makeEvent()} isOwn={false} onDelete={() => {}} />,
    );
    expect(screen.queryByRole("button", { name: /delete event/i })).not.toBeInTheDocument();

    rerender(<CalendarEventCard event={makeEvent()} isOwn={true} onDelete={() => {}} />);
    expect(screen.getByRole("button", { name: /delete event/i })).toBeInTheDocument();
  });

  it("calls onDelete with the event when the delete button is clicked", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    const event = makeEvent();

    render(<CalendarEventCard event={event} isOwn={true} onDelete={onDelete} />);
    await user.click(screen.getByRole("button", { name: /delete event/i }));

    expect(onDelete).toHaveBeenCalledWith(event);
  });
});
