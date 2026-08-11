import { useState } from "react";
import type { FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/useAuth";
import { ApiError } from "../api/client";
import * as usersApi from "../api/users";
import { LanguageSwitcher } from "../components/LanguageSwitcher";

export function AcceptInvitePage() {
  const { t } = useTranslation();
  const { token = "" } = useParams<{ token: string }>();
  const { redeemInvite } = useAuth();
  const navigate = useNavigate();

  const previewQuery = useQuery({
    queryKey: ["invite-preview", token],
    queryFn: () => usersApi.previewInvite(token),
    retry: false,
  });

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await redeemInvite(token, { email, display_name: displayName, password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.somethingWentWrong"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm space-y-3">
        <div className="flex justify-end">
          <LanguageSwitcher />
        </div>

        <div className="w-full space-y-4 rounded-xl bg-white p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-slate-900">{t("acceptInvite.title")}</h1>

          {previewQuery.isLoading && (
            <p className="text-sm text-slate-500">{t("acceptInvite.loading")}</p>
          )}

          {previewQuery.isError && (
            <div className="space-y-3">
              <p className="text-sm text-red-600">{t("acceptInvite.invalid")}</p>
              <Link to="/login" className="text-sm font-medium text-blue-600">
                {t("acceptInvite.backToLogin")}
              </Link>
            </div>
          )}

          {previewQuery.data && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <p className="text-sm text-slate-600">
                {t("acceptInvite.intro", { household: previewQuery.data.household_name })}
              </p>

              <label className="block text-sm">
                <span className="mb-1 block text-slate-600">{t("acceptInvite.yourName")}</span>
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
                />
              </label>

              <label className="block text-sm">
                <span className="mb-1 block text-slate-600">{t("auth.email")}</span>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
                />
              </label>

              <label className="block text-sm">
                <span className="mb-1 block text-slate-600">{t("auth.password")}</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
                />
              </label>

              {error && <p className="text-sm text-red-600">{error}</p>}

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-md bg-blue-600 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
              >
                {isSubmitting ? t("acceptInvite.submitting") : t("acceptInvite.submit")}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
