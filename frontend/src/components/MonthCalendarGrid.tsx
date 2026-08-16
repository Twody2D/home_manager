import { useTranslation } from "react-i18next";
import { SCOPE_DOT_STYLES, scopeEvents } from "../lib/calendarScope";
import type { CalendarEvent } from "../api/types";

const WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const;
const MAX_CHIPS_PER_DAY = 3;

function toDateInputValue(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isoWeekday(d: Date): number {
  const day = d.getDay();
  return day === 0 ? 7 : day;
}

function isSameDate(a: string, b: string): boolean {
  return a === b;
}

interface MonthCalendarGridProps {
  monthDate: Date;
  events: CalendarEvent[];
  myId: string | undefined;
  partnerId: string | undefined;
  selectedDate: string;
  onSelectDate: (date: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  onToday: () => void;
  locale: string;
}

export function MonthCalendarGrid({
  monthDate,
  events,
  myId,
  partnerId,
  selectedDate,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
  onToday,
  locale,
}: MonthCalendarGridProps) {
  const { t } = useTranslation();
  const year = monthDate.getFullYear();
  const monthIndex0 = monthDate.getMonth();
  const firstOfMonth = new Date(year, monthIndex0, 1);
  const daysInMonth = new Date(year, monthIndex0 + 1, 0).getDate();
  const leadingBlanks = isoWeekday(firstOfMonth) - 1;
  const totalCells = Math.ceil((leadingBlanks + daysInMonth) / 7) * 7;

  const scopedEvents = scopeEvents(events, myId, partnerId);
  const eventsByDate = new Map<string, typeof scopedEvents>();
  for (const scoped of scopedEvents) {
    const key = toDateInputValue(new Date(scoped.event.start_at));
    const bucket = eventsByDate.get(key);
    if (bucket) bucket.push(scoped);
    else eventsByDate.set(key, [scoped]);
  }
  for (const bucket of eventsByDate.values()) {
    bucket.sort((a, b) => a.event.start_at.localeCompare(b.event.start_at));
  }

  const todayStr = toDateInputValue(new Date());
  const rawMonthLabel = firstOfMonth.toLocaleDateString(locale, {
    month: "long",
    year: "numeric",
  });
  // Capitalize only the first character — CSS text-transform:capitalize
  // would also capitalize "г." (year abbreviation) mid-string in Russian.
  const monthLabel = rawMonthLabel.charAt(0).toUpperCase() + rawMonthLabel.slice(1);

  const cells: { date: string; dayNum: number; inMonth: boolean }[] = [];
  for (let i = 0; i < totalCells; i++) {
    const cellDate = new Date(year, monthIndex0, 1 - leadingBlanks + i);
    cells.push({
      date: toDateInputValue(cellDate),
      dayNum: cellDate.getDate(),
      inMonth: cellDate.getMonth() === monthIndex0,
    });
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2">
      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={onPrevMonth}
          aria-label={t("calendar.grid.prevMonth")}
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
        >
          ‹
        </button>
        <button
          type="button"
          onClick={onToday}
          className="rounded-md px-2 py-1 text-sm font-medium text-slate-900 hover:bg-slate-100"
        >
          {monthLabel}
        </button>
        <button
          type="button"
          onClick={onNextMonth}
          aria-label={t("calendar.grid.nextMonth")}
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
        >
          ›
        </button>
      </div>

      <div className="grid grid-cols-7 gap-px text-center text-[10px] font-medium text-slate-400">
        {WEEKDAYS.map((day) => (
          <span key={day} className="py-1">
            {t(`weekday.${day}`)}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-md bg-slate-100">
        {cells.map((cell) => {
          const dayEvents = eventsByDate.get(cell.date) ?? [];
          const isSelected = isSameDate(cell.date, selectedDate);
          const isToday = cell.date === todayStr;
          return (
            <button
              key={cell.date}
              type="button"
              onClick={() => onSelectDate(cell.date)}
              className={`flex min-h-[3.75rem] flex-col items-stretch gap-0.5 bg-white p-1 text-left align-top ${
                cell.inMonth ? "" : "opacity-40"
              } ${isSelected ? "ring-2 ring-inset ring-blue-500" : ""}`}
            >
              <span
                className={`self-start text-[11px] leading-none ${
                  isToday
                    ? "flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 font-semibold text-white"
                    : "text-slate-600"
                }`}
              >
                {cell.dayNum}
              </span>
              <span className="flex flex-wrap gap-0.5">
                {dayEvents.slice(0, MAX_CHIPS_PER_DAY).map((scoped) => (
                  <span
                    key={scoped.event.id}
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${SCOPE_DOT_STYLES[scoped.scope]}`}
                  />
                ))}
                {dayEvents.length > MAX_CHIPS_PER_DAY && (
                  <span className="text-[9px] leading-none text-slate-400">
                    +{dayEvents.length - MAX_CHIPS_PER_DAY}
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
