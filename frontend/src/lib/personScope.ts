import type { Gender, User } from "../api/types";

// Shared "whose is this" color vocabulary, used by the calendar and finance
// pages so the same person always reads as the same color everywhere —
// driven by each person's chosen gender, never hardcoded to a specific
// name, so it still works correctly if Pasha and Lena's accounts were
// swapped or a household has different members entirely.
export type PersonScope = "male" | "female" | "shared";

export function scopeForGender(gender: Gender | null | undefined): PersonScope {
  if (gender === "male") return "male";
  if (gender === "female") return "female";
  // Gender not set yet — fall back to the neutral "shared" color rather
  // than guessing, so an unconfigured account doesn't silently claim blue.
  return "shared";
}

export function scopeForOwner(
  ownerId: string | null | undefined,
  members: User[],
): PersonScope {
  if (!ownerId) return "shared";
  const owner = members.find((member) => member.id === ownerId);
  return scopeForGender(owner?.gender);
}

export const SCOPE_DOT_STYLES: Record<PersonScope, string> = {
  male: "bg-sky-500",
  female: "bg-pink-500",
  shared: "bg-violet-500",
};

export const SCOPE_BORDER_STYLES: Record<PersonScope, string> = {
  male: "border-l-4 border-l-sky-500",
  female: "border-l-4 border-l-pink-500",
  shared: "border-l-4 border-l-violet-500",
};
