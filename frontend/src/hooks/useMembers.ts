import { useMutation, useQuery } from "@tanstack/react-query";
import * as usersApi from "../api/users";

const MEMBERS_KEY = ["members"] as const;

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
