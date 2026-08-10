import uuid
from datetime import UTC, datetime, timedelta
from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.calendar.models import CalendarEvent
from home_manager.planning.availability import TimeSlot, compute_free_slots, day_window
from home_manager.planning.schemas import (
    DailyPlanResponse,
    ScheduledTaskEntry,
    UnscheduledTaskEntry,
)
from home_manager.planning.scoring import PRIORITY_WEIGHT, score_candidate
from home_manager.preferences.service import get_or_create_preferences
from home_manager.tasks.models import Task, TaskStatus

REASON_NO_DURATION = "No duration estimate — cannot be auto-scheduled"
REASON_NO_SLOT = "No available time slot large enough today"
REASON_DEADLINE = "Would not finish before its deadline"

SCHEDULABLE_STATUSES = (TaskStatus.PENDING, TaskStatus.SCHEDULED)


async def _fetch_schedulable_tasks(
    session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> list[Task]:
    query = select(Task).where(
        Task.tenant_id == tenant_id,
        Task.assigned_to == user_id,
        Task.status.in_(SCHEDULABLE_STATUSES),
    )
    tasks = list((await session.scalars(query)).all())
    # Deterministic scheduling order: highest priority first, then soonest
    # deadline, then oldest task — this is what determines who gets first
    # pick of the best-scoring free slot when time is scarce, independent of
    # the (also priority-aware) tie-breaking inside score_candidate.
    never_due = datetime.max.replace(tzinfo=UTC)
    tasks.sort(
        key=lambda task: (
            -PRIORITY_WEIGHT[task.priority],
            task.due_at or never_due,
            task.created_at,
        )
    )
    return tasks


async def _fetch_busy_intervals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
) -> list[tuple[datetime, datetime]]:
    query = select(CalendarEvent).where(
        CalendarEvent.tenant_id == tenant_id,
        CalendarEvent.user_id == user_id,
        CalendarEvent.start_at < window_end,
        CalendarEvent.end_at > window_start,
    )
    events = list((await session.scalars(query)).all())
    return [(event.start_at, event.end_at) for event in events]


def _needed_minutes(task: Task, speed_multiplier: float) -> int | None:
    if task.duration_minutes is None:
        return None
    return max(1, round(task.duration_minutes * speed_multiplier))


def _split_slot(slot: TimeSlot, used_start: datetime, used_end: datetime) -> list[TimeSlot]:
    remaining = []
    if used_start > slot.start:
        remaining.append(TimeSlot(slot.start, used_start))
    if used_end < slot.end:
        remaining.append(TimeSlot(used_end, slot.end))
    return remaining


async def build_daily_plan(
    session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID, plan_date: date_
) -> DailyPlanResponse:
    prefs = await get_or_create_preferences(session, tenant_id=tenant_id, user_id=user_id)
    window_start, window_end = day_window(
        plan_date, prefs.working_hours_start, prefs.working_hours_end
    )

    busy_intervals = await _fetch_busy_intervals(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
    )
    sleep_start, sleep_end = prefs.sleep_start, prefs.sleep_end
    if sleep_start is not None and sleep_end is not None and sleep_start < sleep_end:
        busy_intervals.append(
            (
                datetime.combine(plan_date, sleep_start, tzinfo=UTC),
                datetime.combine(plan_date, sleep_end, tzinfo=UTC),
            )
        )

    free_slots = compute_free_slots(
        window_start=window_start,
        window_end=window_end,
        busy_intervals=busy_intervals,
        now=datetime.now(UTC),
    )

    tasks = await _fetch_schedulable_tasks(session, tenant_id=tenant_id, user_id=user_id)

    scheduled: list[ScheduledTaskEntry] = []
    unscheduled: list[UnscheduledTaskEntry] = []

    for task in tasks:
        needed_minutes = _needed_minutes(task, prefs.task_speed_multiplier)
        if needed_minutes is None:
            unscheduled.append(
                UnscheduledTaskEntry(
                    task_id=task.id,
                    title=task.title,
                    priority=task.priority,
                    reason=REASON_NO_DURATION,
                )
            )
            continue

        best_index: int | None = None
        best_score = float("-inf")
        fits_ignoring_deadline = False
        for index, slot in enumerate(free_slots):
            if slot.duration_minutes < needed_minutes:
                continue
            fits_ignoring_deadline = True
            candidate_end = slot.start + timedelta(minutes=needed_minutes)
            if task.due_at is not None and candidate_end > task.due_at:
                continue
            score = score_candidate(
                task=task,
                slot_start=slot.start,
                energy_pattern=prefs.energy_pattern,
                day_start=window_start,
                day_end=window_end,
            )
            if score > best_score:
                best_score = score
                best_index = index

        if best_index is None:
            has_deadline = fits_ignoring_deadline and task.due_at is not None
            reason = REASON_DEADLINE if has_deadline else REASON_NO_SLOT
            unscheduled.append(
                UnscheduledTaskEntry(
                    task_id=task.id, title=task.title, priority=task.priority, reason=reason
                )
            )
            continue

        slot = free_slots[best_index]
        start = slot.start
        end = start + timedelta(minutes=needed_minutes)
        scheduled.append(
            ScheduledTaskEntry(
                task_id=task.id,
                title=task.title,
                priority=task.priority,
                start_at=start,
                end_at=end,
                score=round(best_score, 2),
            )
        )
        free_slots[best_index : best_index + 1] = _split_slot(slot, start, end)

    scheduled.sort(key=lambda entry: entry.start_at)
    return DailyPlanResponse(date=plan_date, scheduled=scheduled, unscheduled=unscheduled)
