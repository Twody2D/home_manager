import { useTranslation } from "react-i18next";
import { useDevices, useExecuteCommand } from "../hooks/useSmartHome";
import type { SmartHomeDevice } from "../api/types";

function DeviceRow({ device }: { device: SmartHomeDevice }) {
  const { t } = useTranslation();
  const executeCommand = useExecuteCommand();

  return (
    <li className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div>
        <p className="text-sm font-medium text-slate-900">{device.name}</p>
        <p className="text-xs text-slate-500">{device.is_on ? t("devices.on") : t("devices.off")}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={device.is_on}
        aria-label={t("devices.toggle", { name: device.name })}
        onClick={() =>
          executeCommand.mutate({ entityId: device.entity_id, command: "toggle" })
        }
        disabled={executeCommand.isPending}
        className={`h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-60 ${
          device.is_on ? "bg-blue-600" : "bg-slate-300"
        }`}
      >
        <span
          className={`block h-5 w-5 translate-x-1 rounded-full bg-white transition-transform ${
            device.is_on ? "translate-x-6" : ""
          }`}
        />
      </button>
    </li>
  );
}

export function DevicesPage() {
  const { t } = useTranslation();
  const devicesQuery = useDevices();

  if (devicesQuery.isLoading) {
    return <p className="text-sm text-slate-500">{t("devices.loading")}</p>;
  }

  if (devicesQuery.isError) {
    return <p className="text-sm text-red-600">{t("devices.error")}</p>;
  }

  const devices = devicesQuery.data ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900">{t("devices.title")}</h1>

      {devices.length === 0 ? (
        <p className="text-sm text-slate-500">{t("devices.empty")}</p>
      ) : (
        <ul className="space-y-2">
          {devices.map((device) => (
            <DeviceRow key={device.entity_id} device={device} />
          ))}
        </ul>
      )}
    </div>
  );
}
