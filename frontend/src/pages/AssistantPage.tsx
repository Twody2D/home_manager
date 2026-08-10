import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSendAssistantMessage } from "../hooks/useAssistant";

interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export function AssistantPage() {
  const { t } = useTranslation();
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const [message, setMessage] = useState("");
  const sendMessage = useSendAssistantMessage();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (!text) return;

    setHistory((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    setMessage("");

    try {
      const reply = await sendMessage.mutateAsync(text);
      setHistory((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", text: reply.reply },
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

  return (
    <div className="flex h-full flex-col space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("assistant.title")}</h1>
      <p className="text-xs text-slate-500">{t("assistant.hint")}</p>

      <div className="space-y-2">
        {history.length === 0 && (
          <p className="text-sm text-slate-500">{t("assistant.empty")}</p>
        )}
        {history.map((entry) => (
          <div
            key={entry.id}
            className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
              entry.role === "user"
                ? "ml-auto bg-blue-600 text-white"
                : "bg-white text-slate-900 shadow-sm"
            }`}
          >
            {entry.text}
          </div>
        ))}
        {sendMessage.isPending && <p className="text-xs text-slate-400">{t("assistant.thinking")}</p>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
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
