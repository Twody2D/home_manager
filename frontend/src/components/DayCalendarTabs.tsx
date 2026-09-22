import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

// "Today" and the month calendar are two views of the same thing, so they
// share one slot in the bottom nav and switch here instead of each taking up
// a tab of their own.
export function DayCalendarTabs() {
  const { t } = useTranslation();
  const tabClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-full px-3.5 py-2 text-sm font-medium ${
      isActive ? "bg-blue-600 text-white" : "bg-white text-slate-600"
    }`;

  return (
    <div className="flex gap-1.5">
      <NavLink to="/" end className={tabClass}>
        {t("nav.today")}
      </NavLink>
      <NavLink to="/calendar" end className={tabClass}>
        {t("nav.calendar")}
      </NavLink>
    </div>
  );
}
