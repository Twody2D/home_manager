import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as preferencesApi from "../api/preferences";
import type { UserPreferencesUpdateInput } from "../api/types";

const PREFERENCES_KEY = ["preferences", "me"] as const;

export function useMyPreferences() {
  return useQuery({
    queryKey: PREFERENCES_KEY,
    queryFn: () => preferencesApi.getMyPreferences(),
  });
}

export function useUpdateMyPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UserPreferencesUpdateInput) => preferencesApi.updateMyPreferences(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PREFERENCES_KEY });
    },
  });
}
