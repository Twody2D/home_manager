import type { Subscription } from "../api/types";

export const PAYMENT_DOT_STYLE = "bg-amber-500";
export const PAYMENT_BORDER_STYLE = "border-l-4 border-l-amber-500";

function daysInMonth(year: number, monthIndex0: number): number {
  return new Date(year, monthIndex0 + 1, 0).getDate();
}

// Subscriptions/recurring expenses recur on a day-of-month; a month shorter
// than that day gets the charge on its last day instead (mirrors the
// backend's payment_day semantics — see finance/models.py's Income comment).
export function subscriptionsDueOn(
  subscriptions: Subscription[],
  dateStr: string,
): Subscription[] {
  const [year, month, day] = dateStr.split("-").map(Number);
  const dim = daysInMonth(year, month - 1);
  return subscriptions.filter((s) => {
    if (!s.active) return false;
    if (s.cadence === "yearly" && s.payment_month !== month) return false;
    return Math.min(s.payment_day, dim) === day;
  });
}
