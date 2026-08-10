import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSendAssistantMessage } from "../hooks/useAssistant";
import { useCreateEventsBulk } from "../hooks/useCalendar";
import type { CalendarEventCreateInput } from "../api/types";

interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
  proposedEvents?: CalendarEventCreateInput[];
  saved?: boolean;
}

function formatEventRange(event: CalendarEventCreateInput, locale: string): string {
  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  const date = start.toLocaleDateString(locale, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
  const startTime = start.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
  const endTime = end.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
  return `${date}, ${startTime}–${endTime}`;
}

const DRAFT_STORAGE_KEY = "home_manager_assistant_draft";

export function AssistantPage() {
  const { t, i18n } = useTranslation();
  const [history, setHistory] = useState<ChatEntry[]>([]);
  // Backed by localStorage (not just component state) so an unsent draft
  // survives navigating to another tab and back — the page unmounts on
  // route change, which would otherwise lose it.
  const [message, setMessage] = useState(() => localStorage.getItem(DRAFT_STORAGE_KEY) ?? "");
  const sendMessage = useSendAssistantMessage();
  const createEventsBulk = useCreateEventsBulk();

  function updateMessage(value: string) {
    setMessage(value);
    if (value) localStorage.setItem(DRAFT_STORAGE_KEY, value);
    else localStorage.removeItem(DRAFT_STORAGE_KEY);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (!text) return;

    setHistory((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    setMessage("");
    localStorage.removeItem(DRAFT_STORAGE_KEY);

    try {
      const reply = await sendMessage.mutateAsync(text);
      setHistory((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: reply.reply,
          proposedEvents: reply.proposed_events ?? undefined,
        },
      ]);
    } catch {
      setHistory((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: t("assistant.error"),
        },
      ]);
    }
  }

  function removeProposedEvent(entryId: string, index: number) {
    setHistory((prev) =>
      prev.map((entry) =>
        entry.id === entryId
          ? { ...entry, proposedEvents: entry.proposedEvents?.filter((_, i) => i !== index) }
          : entry,
      ),
    );
  }

  async function confirmProposedEvents(entryId: string) {
    const entry = history.find((e) => e.id === entryId);
    if (!entry?.proposedEvents || entry.proposedEvents.length === 0) return;
    await createEventsBulk.mutateAsync({ events: entry.proposedEvents });
    setHistory((prev) =>
      prev.map((e) => (e.id === entryId ? { ...e, saved: true, proposedEvents: [] } : e)),
    );
  }

  return (
    <div className="flex h-full flex-col space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("assistant.title")}</h1>
      <p className="text-xs text-slate-500">{t("assistant.hint")}</p>

      <div className="space-y-2">
        {history.length === 0 && (
          <p className="text-sm text-slate-500">{t("assistant.empty")}</p>
        )}
        {history.map((entry) => (
          <div key={entry.id} className={entry.role === "user" ? "flex justify-end" : ""}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                entry.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-900 shadow-sm"
              }`}
            >
              {entry.text}

              {entry.proposedEvents && entry.proposedEvents.length > 0 && (
                <div className="mt-2 space-y-1.5 border-t border-slate-100 pt-2">
                  {entry.proposedEvents.map((proposedEvent, index) => (
                    <div
                      key={`${entry.id}-${index}`}
                      className="flex items-center justify-between gap-2 rounded-md bg-slate-50 px-2 py-1 text-xs text-slate-700"
                    >
                      <span>
                        {formatEventRange(proposedEvent, i18n.language)}
                        {" — "}
                        {t(`eventType.${proposedEvent.event_type}`)}
                      </span>
                      <button
                        type="button"
                        aria-label={t("calendar.bulk.removeRow")}
                        onClick={() => removeProposedEvent(entry.id, index)}
                        className="shrink-0 rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => void confirmProposedEvents(entry.id)}
                    disabled={createEventsBulk.isPending}
                    className="w-full rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-60"
                  >
                    {createEventsBulk.isPending
                      ? t("calendar.bulk.submitting")
                      : t("assistant.confirmSchedule", { count: entry.proposedEvents.length })}
                  </button>
                </div>
              )}

              {entry.saved && (
                <p className="mt-2 border-t border-slate-100 pt-2 text-xs text-green-600">
                  {t("assistant.scheduleSaved")}
                </p>
              )}
            </div>
          </div>
        ))}
        {sendMessage.isPending && <p className="text-xs text-slate-400">{t("assistant.thinking")}</p>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => updateMessage(e.target.value)}
          placeholder={t("assistant.placeholder")}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={sendMessage.isPending || !message.trim()}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {t("assistant.send")}
        </button>
      </form>
    </div>
  );
}
