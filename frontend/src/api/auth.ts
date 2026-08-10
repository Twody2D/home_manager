import { apiFetch } from "./client";
import type { TokenResponse, User } from "./types";

export interface RegisterInput {
  household_name: string;
  display_name: string;
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export function register(input: RegisterInput): Promise<TokenResponse> {
  return apiFetch("/auth/register", { method: "POST", body: input });
}

export function login(input: LoginInput): Promise<TokenResponse> {
  return apiFetch("/auth/login", { method: "POST", body: input });
}

export function fetchCurrentUser(): Promise<User> {
  return apiFetch("/auth/me");
}

export function logout(): Promise<void> {
  return apiFetch("/auth/logout", { method: "POST" });
}
