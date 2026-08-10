import { apiFetch } from "./client";

export interface AliceLinkStatus {
  linked: boolean;
  last_used_at: string | null;
}

export interface AliceTokenResponse {
  token: string;
  webhook_url: string;
}

export function getAliceLinkStatus(): Promise<AliceLinkStatus> {
  return apiFetch("/integrations/alice/token");
}

export function issueAliceToken(): Promise<AliceTokenResponse> {
  return apiFetch("/integrations/alice/token", { method: "POST" });
}

export function revokeAliceToken(): Promise<void> {
  return apiFetch("/integrations/alice/token", { method: "DELETE" });
}
