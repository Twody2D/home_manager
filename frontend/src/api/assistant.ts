import { apiFetch } from "./client";
import type { AssistantReply } from "./types";

// ISO 8601 with the device's own UTC offset (e.g. "2026-08-10T22:30:00+03:00").
// Deliberately not toISOString(), which always reports UTC and would strip
// the offset the backend needs to resolve "tomorrow"/"Monday" and store
// shift times in the user's actual local time.
function clientNowWithOffset(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const offsetMinutes = -now.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMinutes);
  const offset = `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}${offset}`
  );
}

export function sendMessage(message: string): Promise<AssistantReply> {
  return apiFetch("/assistant/message", {
    method: "POST",
    body: { message, client_now: clientNowWithOffset() },
  });
}
