import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as usersApi from "../api/users";

const MEMBERS_KEY = ["members"] as const;
const HOUSEHOLD_KEY = ["household"] as const;

export function useMembers() {
  return useQuery({
    queryKey: MEMBERS_KEY,
    queryFn: () => usersApi.listMembers(),
  });
}

export function useCreateInviteLink() {
  return useMutation({
    mutationFn: () => usersApi.createInviteLink(),
  });
}

export function useHousehold() {
  return useQuery({
    queryKey: HOUSEHOLD_KEY,
    queryFn: () => usersApi.getHousehold(),
  });
}

export function useUpdateHousehold() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (displayName: string | null) => usersApi.updateHousehold(displayName),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: HOUSEHOLD_KEY });
    },
  });
}
