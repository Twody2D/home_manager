from dataclasses import dataclass
from datetime import UTC, datetime, time
from datetime import date as date_

# Fallback window used when a user hasn't set working hours in their
# preferences yet — a broad "awake and available" default, not a claim about
# anyone's actual job hours.
DEFAULT_DAY_START = time(9, 0)
DEFAULT_DAY_END = time(21, 0)


@dataclass(frozen=True)
class TimeSlot:
    start: datetime
    end: datetime

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


def day_window(
    plan_date: date_, start_time: time | None, end_time: time | None
) -> tuple[datetime, datetime]:
    return (
        datetime.combine(plan_date, start_time or DEFAULT_DAY_START, tzinfo=UTC),
        datetime.combine(plan_date, end_time or DEFAULT_DAY_END, tzinfo=UTC),
    )


def compute_free_slots(
    *,
    window_start: datetime,
    window_end: datetime,
    busy_intervals: list[tuple[datetime, datetime]],
    now: datetime,
) -> list[TimeSlot]:
    """Free time within [window_start, window_end), with busy_intervals and
    anything already in the past (relative to `now`) carved out.
    """
    if now > window_start:
        window_start = min(now, window_end)
    if window_end <= window_start:
        return []

    clipped = sorted(
        (max(start, window_start), min(end, window_end))
        for start, end in busy_intervals
        if end > window_start and start < window_end
    )

    free: list[TimeSlot] = []
    cursor = window_start
    for busy_start, busy_end in clipped:
        if busy_start > cursor:
            free.append(TimeSlot(cursor, busy_start))
        cursor = max(cursor, busy_end)
    if cursor < window_end:
        free.append(TimeSlot(cursor, window_end))

    return [slot for slot in free if slot.duration_minutes > 0]
