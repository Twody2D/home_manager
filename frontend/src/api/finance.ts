import { apiFetch } from "./client";
import type {
  Income,
  IncomeCreateInput,
  IncomeListResponse,
  IncomeUpdateInput,
  Subscription,
  SubscriptionCreateInput,
  SubscriptionListResponse,
  SubscriptionUpdateInput,
} from "./types";

export function listIncomes(): Promise<IncomeListResponse> {
  return apiFetch("/finance/incomes?limit=100");
}

export function createIncome(input: IncomeCreateInput): Promise<Income> {
  return apiFetch("/finance/incomes", { method: "POST", body: input });
}

export function updateIncome(id: string, input: IncomeUpdateInput): Promise<Income> {
  return apiFetch(`/finance/incomes/${id}`, { method: "PATCH", body: input });
}

export function deleteIncome(id: string): Promise<void> {
  return apiFetch(`/finance/incomes/${id}`, { method: "DELETE" });
}

export interface ListSubscriptionsParams {
  active_only?: boolean;
}

export function listSubscriptions(
  params: ListSubscriptionsParams = {},
): Promise<SubscriptionListResponse> {
  const search = new URLSearchParams({ limit: "100" });
  if (params.active_only) search.set("active_only", "true");
  return apiFetch(`/finance/subscriptions?${search.toString()}`);
}

export function createSubscription(input: SubscriptionCreateInput): Promise<Subscription> {
  return apiFetch("/finance/subscriptions", { method: "POST", body: input });
}

export function updateSubscription(
  id: string,
  input: SubscriptionUpdateInput,
): Promise<Subscription> {
  return apiFetch(`/finance/subscriptions/${id}`, { method: "PATCH", body: input });
}

export function deleteSubscription(id: string): Promise<void> {
  return apiFetch(`/finance/subscriptions/${id}`, { method: "DELETE" });
}
