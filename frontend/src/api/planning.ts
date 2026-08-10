import { apiFetch } from "./client";
import type { DailyPlanResponse } from "./types";

export function getDailyPlan(date?: string): Promise<DailyPlanResponse> {
  const query = date ? `?date=${date}` : "";
  return apiFetch(`/planning/plan${query}`);
}
