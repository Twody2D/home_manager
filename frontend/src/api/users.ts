import { apiFetch } from "./client";
import type { Role, User } from "./types";

export interface InviteMemberInput {
  email: string;
  display_name: string;
  password: string;
  role?: Role;
}

export function listMembers(): Promise<User[]> {
  return apiFetch("/users");
}

export function inviteMember(input: InviteMemberInput): Promise<User> {
  return apiFetch("/users", { method: "POST", body: input });
}
