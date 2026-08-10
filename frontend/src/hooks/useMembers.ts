import { useQuery } from "@tanstack/react-query";
import * as usersApi from "../api/users";

export function useMembers() {
  return useQuery({
    queryKey: ["members"],
    queryFn: () => usersApi.listMembers(),
  });
}
