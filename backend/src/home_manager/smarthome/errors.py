from fastapi import status

from home_manager.core.errors import AppError


class SmartHomeDeviceNotFoundError(AppError):
    code = "SMART_HOME_DEVICE_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Device not found"


class SmartHomeProviderError(AppError):
    code = "SMART_HOME_PROVIDER_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY
    message = "The smart home hub failed to respond"
