import { useEffect, useRef } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/useAuth";
import { useHousehold, useMembers } from "../hooks/useMembers";
import { householdTitle } from "../lib/householdTitle";
import { LanguageSwitcher } from "./LanguageSwitcher";

// The tabs a horizontal swipe on the main content cycles through, in
// on-screen order. Kept separate from the <nav> markup below so the swipe
// handler doesn't have to reverse-engineer tab order from rendered DOM.
const SWIPE_TABS = ["/", "/tasks", "/calendar", "/finance", "/assistant", "/preferences"];
const SWIPE_DISTANCE_THRESHOLD = 60;
// Horizontal movement must dominate vertical by this ratio, or a mostly-
// vertical scroll gesture would misfire as a tab swipe.
const SWIPE_DIRECTION_RATIO = 1.5;

export function AppShell() {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const householdQuery = useHousehold();
  const membersQuery = useMembers();
  const title = householdTitle(householdQuery.data, membersQuery.data ?? []);
  const navigate = useNavigate();
  const location = useLocation();
  const mainRef = useRef<HTMLElement | null>(null);
  // Kept in a ref (not state/closure-only) so the touchmove listener below
  // — attached once — always reads the current route without having to
  // tear down and re-attach on every navigation.
  const pathnameRef = useRef(location.pathname);
  pathnameRef.current = location.pathname;

  useEffect(() => {
    const el = mainRef.current;
    if (!el) return;

    let start: { x: number; y: number } | null = null;
    // Undecided until the first move past a small jitter threshold, so a
    // vertical scroll never gets treated as a horizontal swipe mid-gesture.
    let horizontal: boolean | null = null;

    function onTouchStart(event: TouchEvent) {
      const touch = event.touches[0];
      start = { x: touch.clientX, y: touch.clientY };
      horizontal = null;
    }

    function onTouchMove(event: TouchEvent) {
      if (!start) return;
      const touch = event.touches[0];
      const dx = touch.clientX - start.x;
      const dy = touch.clientY - start.y;
      if (horizontal === null && (Math.abs(dx) > 10 || Math.abs(dy) > 10)) {
        horizontal = Math.abs(dx) > Math.abs(dy) * SWIPE_DIRECTION_RATIO;
      }
      // React's synthetic touch handlers are passive and can't call
      // preventDefault — that's what let the browser's own back/forward
      // edge-swipe gesture keep firing alongside ours, landing on
      // whatever the history stack had (including stale tabs) instead of
      // the neighboring one. A manually-attached, non-passive listener
      // can actually suppress it once a swipe reads as horizontal.
      if (horizontal) event.preventDefault();
    }

    function onTouchEnd(event: TouchEvent) {
      const startPos = start;
      start = null;
      if (!startPos || !horizontal) return;

      const touch = event.changedTouches[0];
      const dx = touch.clientX - startPos.x;
      const dy = touch.clientY - startPos.y;
      if (Math.abs(dx) < SWIPE_DISTANCE_THRESHOLD) return;
      if (Math.abs(dx) < Math.abs(dy) * SWIPE_DIRECTION_RATIO) return;

      const currentIndex = SWIPE_TABS.indexOf(pathnameRef.current);
      if (currentIndex === -1) return;
      const nextIndex = currentIndex + (dx < 0 ? 1 : -1);
      if (nextIndex < 0 || nextIndex >= SWIPE_TABS.length) return;
      navigate(SWIPE_TABS[nextIndex]);
    }

    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchmove", onTouchMove, { passive: false });
    el.addEventListener("touchend", onTouchEnd, { passive: true });
    return () => {
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchmove", onTouchMove);
      el.removeEventListener("touchend", onTouchEnd);
    };
  }, [navigate]);

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <span className="text-lg font-semibold text-slate-900">{title}</span>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <LanguageSwitcher />
            <span>{user?.display_name}</span>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100"
            >
              {t("appShell.logout")}
            </button>
          </div>
        </div>
      </header>

      <main
        ref={mainRef}
        className="mx-auto w-full max-w-2xl flex-1 px-4 py-4 pb-20"
        style={{ touchAction: "pan-y", overscrollBehaviorX: "none" }}
      >
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto flex max-w-2xl">
          <NavTab to="/" label={t("nav.today")} icon={TodayIcon} />
          <NavTab to="/tasks" label={t("nav.tasks")} icon={TasksIcon} />
          <NavTab to="/calendar" label={t("nav.calendar")} icon={CalendarIcon} />
          <NavTab to="/finance" label={t("nav.finance")} icon={FinanceIcon} />
          <NavTab to="/assistant" label={t("nav.assistant")} icon={AssistantIcon} />
          <NavTab to="/preferences" label={t("nav.preferences")} icon={PreferencesIcon} />
        </div>
      </nav>
    </div>
  );
}

type IconComponent = (props: { className?: string }) => React.ReactElement;

function NavTab({ to, label, icon: Icon }: { to: string; label: string; icon: IconComponent }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `flex min-w-0 flex-1 flex-col items-center gap-0.5 py-2 text-center ${
          isActive ? "text-blue-600" : "text-slate-500"
        }`
      }
    >
      <Icon className="h-5 w-5 shrink-0" />
      <span className="w-full truncate px-0.5 text-[11px] font-medium leading-tight">{label}</span>
    </NavLink>
  );
}

function TodayIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className}>
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M3 9h18M8 2v4M16 2v4" strokeLinecap="round" />
    </svg>
  );
}

function TasksIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className}>
      <path d="m4 12 4 4 4-8M13 8h7M13 16h7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CalendarIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className}>
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M3 9h18M8 2v4M16 2v4M8 14h.01M12 14h.01M16 14h.01" strokeLinecap="round" />
    </svg>
  );
}

function FinanceIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v10M9.5 9.5c0-1.1 1.12-2 2.5-2s2.5.9 2.5 2-1.12 2-2.5 2-2.5.9-2.5 2 1.12 2 2.5 2 2.5-.9 2.5-2" strokeLinecap="round" />
    </svg>
  );
}

function AssistantIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className}>
      <path
        d="M12 3a7 7 0 0 0-7 7c0 3.5 2.5 5.5 3 8l1-2h6l1 2c.5-2.5 3-4.5 3-8a7 7 0 0 0-7-7Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M9 10a3 3 0 0 1 6 0" strokeLinecap="round" />
    </svg>
  );
}

function PreferencesIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className}>
      <circle cx="12" cy="12" r="3" />
      <path
        d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.04 1.56V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 9 19.35a1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.65 15a1.7 1.7 0 0 0-1.56-1.04H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.65 9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.65a1.7 1.7 0 0 0 1.04-1.56V3a2 2 0 1 1 4 0v.09A1.7 1.7 0 0 0 15 4.65a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.35 9a1.7 1.7 0 0 0 1.56 1.04H21a2 2 0 1 1 0 4h-.09A1.7 1.7 0 0 0 19.4 15Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
