import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as aliceApi from "../api/alice";

const STATUS_KEY = ["alice-link-status"] as const;

export function useAliceLinkStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: () => aliceApi.getAliceLinkStatus(),
  });
}

export function useIssueAliceToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => aliceApi.issueAliceToken(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useRevokeAliceToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => aliceApi.revokeAliceToken(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}
