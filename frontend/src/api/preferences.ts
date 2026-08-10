import { apiFetch } from "./client";
import type { UserPreferences, UserPreferencesUpdateInput } from "./types";

export function getMyPreferences(): Promise<UserPreferences> {
  return apiFetch("/preferences/me");
}

export function updateMyPreferences(input: UserPreferencesUpdateInput): Promise<UserPreferences> {
  return apiFetch("/preferences/me", { method: "PATCH", body: input });
}
