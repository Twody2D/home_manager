// Shared "whose is this" color vocabulary, used by both the calendar and
// finance pages so the same person always reads as the same color across
// the app.
export type PersonScope = "mine" | "partner" | "shared";

export function scopeForOwner(
  ownerId: string | null | undefined,
  myId: string | undefined,
  partnerId: string | undefined,
): PersonScope {
  if (!ownerId) return "shared";
  if (ownerId === myId) return "mine";
  if (ownerId === partnerId) return "partner";
  return "shared";
}

export const SCOPE_DOT_STYLES: Record<PersonScope, string> = {
  mine: "bg-sky-500",
  partner: "bg-pink-500",
  shared: "bg-violet-500",
};

export const SCOPE_BORDER_STYLES: Record<PersonScope, string> = {
  mine: "border-l-4 border-l-sky-500",
  partner: "border-l-4 border-l-pink-500",
  shared: "border-l-4 border-l-violet-500",
};
