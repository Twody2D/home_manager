from datetime import datetime

from home_manager.preferences.models import EnergyPattern
from home_manager.tasks.models import Task, TaskPriority

# Soft-constraint weights. Named and centralized here — never inlined as
# magic numbers in the scheduling loop — so the ranking behavior can be
# tuned or explained without touching home_manager.planning.engine.
PRIORITY_WEIGHT: dict[TaskPriority, float] = {
    TaskPriority.URGENT: 100.0,
    TaskPriority.HIGH: 70.0,
    TaskPriority.MEDIUM: 40.0,
    TaskPriority.LOW: 15.0,
}
DUE_SOON_MAX_BONUS = 30.0
DUE_SOON_HORIZON_HOURS = 48.0
PREFERRED_WINDOW_BONUS = 20.0
ENERGY_MATCH_BONUS = 10.0
LATE_START_PENALTY_PER_HOUR = 0.5


def score_candidate(
    *,
    task: Task,
    slot_start: datetime,
    energy_pattern: EnergyPattern,
    day_start: datetime,
    day_end: datetime,
) -> float:
    """Rank a (task, candidate start time) pair. Higher is better.

    Hard constraints (does the task fit, does it beat its deadline) are
    already enforced by the caller before this is ever invoked — this
    function only breaks ties between candidates that are all otherwise
    valid.
    """
    score = PRIORITY_WEIGHT[task.priority]

    if task.due_at is not None:
        hours_until_due = max((task.due_at - slot_start).total_seconds() / 3600, 0.0)
        urgency = max(0.0, 1 - hours_until_due / DUE_SOON_HORIZON_HOURS)
        score += urgency * DUE_SOON_MAX_BONUS

    if (
        task.preferred_start is not None
        and task.preferred_end is not None
        and task.preferred_start <= slot_start <= task.preferred_end
    ):
        score += PREFERRED_WINDOW_BONUS

    day_span_seconds = (day_end - day_start).total_seconds() or 1.0
    position_in_day = (slot_start - day_start).total_seconds() / day_span_seconds
    morning_match = energy_pattern == EnergyPattern.MORNING and position_in_day < 0.5
    evening_match = energy_pattern == EnergyPattern.EVENING and position_in_day >= 0.5
    if morning_match or evening_match:
        score += ENERGY_MATCH_BONUS

    hours_from_day_start = (slot_start - day_start).total_seconds() / 3600
    score -= hours_from_day_start * LATE_START_PENALTY_PER_HOUR

    return score
