import { apiFetch } from "./client";
import type { SmartHomeCommand, SmartHomeDevice } from "./types";

export function listDevices(): Promise<SmartHomeDevice[]> {
  return apiFetch("/smarthome/devices");
}

export function executeCommand(
  entityId: string,
  command: SmartHomeCommand,
): Promise<SmartHomeDevice> {
  return apiFetch(`/smarthome/devices/${encodeURIComponent(entityId)}/command`, {
    method: "POST",
    body: { command },
  });
}
