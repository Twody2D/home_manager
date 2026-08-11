import { apiFetch } from "./client";
import type { Household, InviteLink, InvitePreview, User } from "./types";

export function listMembers(): Promise<User[]> {
  return apiFetch("/users");
}

export function createInviteLink(): Promise<InviteLink> {
  return apiFetch("/users/invites", { method: "POST" });
}

export function previewInvite(token: string): Promise<InvitePreview> {
  return apiFetch(`/users/invites/${encodeURIComponent(token)}`);
}

export function getHousehold(): Promise<Household> {
  return apiFetch("/users/household");
}

export function updateHousehold(displayName: string | null): Promise<Household> {
  return apiFetch("/users/household", {
    method: "PATCH",
    body: { display_name: displayName },
  });
}
