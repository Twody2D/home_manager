import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <span className="text-lg font-semibold text-slate-900">Home Manager</span>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <span>{user?.display_name}</span>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-4 pb-20">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto flex max-w-2xl">
          <NavTab to="/" label="Today" />
          <NavTab to="/tasks" label="Tasks" />
          <NavTab to="/calendar" label="Calendar" />
          <NavTab to="/devices" label="Devices" />
          <NavTab to="/assistant" label="Assistant" />
          <NavTab to="/preferences" label="Prefs" />
        </div>
      </nav>
    </div>
  );
}

function NavTab({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `flex-1 py-3 text-center text-sm font-medium ${
          isActive ? "text-blue-600" : "text-slate-500"
        }`
      }
    >
      {label}
    </NavLink>
  );
}
