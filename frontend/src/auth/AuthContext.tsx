import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import * as authApi from "../api/auth";
import { setAccessToken, subscribeAccessToken } from "../api/tokenStore";
import type { User } from "../api/types";
import { AuthContext } from "./authContextInstance";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => subscribeAccessToken((token) => {
    if (!token) setUser(null);
  }), []);

  useEffect(() => {
    let cancelled = false;

    // A page load starts with no in-memory access token. This call fails
    // with 401 and the API client transparently retries it after attempting
    // a silent refresh via the httpOnly cookie — that's what restores the
    // session (or confirms there isn't one) after a reload.
    authApi
      .fetchCurrentUser()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function login(input: authApi.LoginInput): Promise<void> {
    const response = await authApi.login(input);
    setAccessToken(response.access_token);
    setUser(response.user);
  }

  async function register(input: authApi.RegisterInput): Promise<void> {
    const response = await authApi.register(input);
    setAccessToken(response.access_token);
    setUser(response.user);
  }

  async function redeemInvite(token: string, input: authApi.RedeemInviteInput): Promise<void> {
    const response = await authApi.redeemInvite(token, input);
    setAccessToken(response.access_token);
    setUser(response.user);
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout();
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, redeemInvite, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
