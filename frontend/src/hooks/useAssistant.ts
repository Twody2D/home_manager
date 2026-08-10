import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as assistantApi from "../api/assistant";

export function useSendAssistantMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (message: string) => assistantApi.sendMessage(message),
    onSuccess: (reply) => {
      if (reply.task_id) {
        void queryClient.invalidateQueries({ queryKey: ["tasks"] });
        void queryClient.invalidateQueries({ queryKey: ["daily-plan"] });
      }
      if (reply.event_count) {
        void queryClient.invalidateQueries({ queryKey: ["calendar-events"] });
      }
    },
  });
}
