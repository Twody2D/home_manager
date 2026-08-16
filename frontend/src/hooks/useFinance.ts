import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as financeApi from "../api/finance";
import type {
  IncomeCreateInput,
  IncomeUpdateInput,
  SubscriptionCreateInput,
  SubscriptionUpdateInput,
} from "../api/types";

const INCOMES_KEY = ["finance", "incomes"] as const;
const SUBSCRIPTIONS_KEY = ["finance", "subscriptions"] as const;

export function useIncomes() {
  return useQuery({
    queryKey: INCOMES_KEY,
    queryFn: () => financeApi.listIncomes(),
  });
}

export function useCreateIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: IncomeCreateInput) => financeApi.createIncome(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: INCOMES_KEY });
    },
  });
}

export function useUpdateIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: IncomeUpdateInput }) =>
      financeApi.updateIncome(id, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: INCOMES_KEY });
    },
  });
}

export function useDeleteIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => financeApi.deleteIncome(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: INCOMES_KEY });
    },
  });
}

export function useSubscriptions(params: financeApi.ListSubscriptionsParams = {}) {
  return useQuery({
    queryKey: [...SUBSCRIPTIONS_KEY, params],
    queryFn: () => financeApi.listSubscriptions(params),
  });
}

export function useCreateSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SubscriptionCreateInput) => financeApi.createSubscription(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SUBSCRIPTIONS_KEY });
    },
  });
}

export function useUpdateSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: SubscriptionUpdateInput }) =>
      financeApi.updateSubscription(id, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SUBSCRIPTIONS_KEY });
    },
  });
}

export function useDeleteSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => financeApi.deleteSubscription(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SUBSCRIPTIONS_KEY });
    },
  });
}
