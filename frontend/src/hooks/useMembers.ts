import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as usersApi from "../api/users";
import type { InviteMemberInput } from "../api/users";

const MEMBERS_KEY = ["members"] as const;

export function useMembers() {
  return useQuery({
    queryKey: MEMBERS_KEY,
    queryFn: () => usersApi.listMembers(),
  });
}

export function useInviteMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: InviteMemberInput) => usersApi.inviteMember(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: MEMBERS_KEY });
    },
  });
}
