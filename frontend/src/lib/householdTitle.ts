import type { Household, User } from "../api/types";

const APP_NAME = "Home Manager";

export function householdTitle(household: Household | undefined, members: User[]): string {
  if (household?.display_name) return household.display_name;
  if (members.length >= 2) {
    return `${members.map((m) => m.display_name).join("+")} ❤`;
  }
  return APP_NAME;
}
