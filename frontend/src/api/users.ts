import { apiFetch } from "./client";
import type { InviteLink, InvitePreview, User } from "./types";

export function listMembers(): Promise<User[]> {
  return apiFetch("/users");
}

export function createInviteLink(): Promise<InviteLink> {
  return apiFetch("/users/invites", { method: "POST" });
}

export function previewInvite(token: string): Promise<InvitePreview> {
  return apiFetch(`/users/invites/${encodeURIComponent(token)}`);
}
