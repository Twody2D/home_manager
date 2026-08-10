import { useTranslation } from "react-i18next";
import { TYPE_STYLES } from "../lib/eventTypeStyles";
import type { CalendarEvent, User } from "../api/types";

function formatTimeRange(startAt: string, endAt: string): string {
  const start = new Date(startAt);
  const end = new Date(endAt);
  const opts: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit" };
  return `${start.toLocaleTimeString(undefined, opts)} – ${end.toLocaleTimeString(undefined, opts)}`;
}

interface CalendarEventCardProps {
  event: CalendarEvent;
  owner?: User;
  isOwn: boolean;
  onDelete: (event: CalendarEvent) => void;
}

export function CalendarEventCard({ event, owner, isOwn, onDelete }: CalendarEventCardProps) {
  const { t } = useTranslation();
  return (
    <li className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900">{event.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs">
          <span className={`rounded-full px-2 py-0.5 font-medium ${TYPE_STYLES[event.event_type]}`}>
            {t(`eventType.${event.event_type}`)}
          </span>
          <span className="text-slate-500">{formatTimeRange(event.start_at, event.end_at)}</span>
          {owner && <span className="text-slate-400">· {owner.display_name}</span>}
        </div>
      </div>

      {isOwn && (
        <button
          type="button"
          aria-label={t("calendarEventCard.deleteEvent")}
          onClick={() => onDelete(event)}
          className="shrink-0 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
            <path d="M8 2a1 1 0 0 0-1 1v1H4a1 1 0 0 0 0 2h.35l.65 10.02A2 2 0 0 0 6.99 18h6.02a2 2 0 0 0 2-1.98L15.65 6H16a1 1 0 1 0 0-2h-3V3a1 1 0 0 0-1-1H8Zm1 2V3h2v1H9Zm-1.63 2h7.26l-.63 9.9a.5.5 0 0 1-.5.1H7.5a.5.5 0 0 1-.5-.1L6.37 6Z" />
          </svg>
        </button>
      )}
    </li>
  );
}
