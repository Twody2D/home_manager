import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as smartHomeApi from "../api/smarthome";
import type { SmartHomeCommand } from "../api/types";

const DEVICES_KEY = ["smarthome-devices"] as const;

export function useDevices() {
  return useQuery({
    queryKey: DEVICES_KEY,
    queryFn: () => smartHomeApi.listDevices(),
  });
}

export function useExecuteCommand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ entityId, command }: { entityId: string; command: SmartHomeCommand }) =>
      smartHomeApi.executeCommand(entityId, command),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DEVICES_KEY });
    },
  });
}
