import { useQuery } from "@tanstack/react-query";
import * as planningApi from "../api/planning";

export function useDailyPlan(date?: string) {
  return useQuery({
    queryKey: ["daily-plan", date ?? "today"],
    queryFn: () => planningApi.getDailyPlan(date),
  });
}
