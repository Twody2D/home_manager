import { apiFetch } from "./client";
import type { AssistantReply } from "./types";

export function sendMessage(message: string): Promise<AssistantReply> {
  return apiFetch("/assistant/message", { method: "POST", body: { message } });
}
