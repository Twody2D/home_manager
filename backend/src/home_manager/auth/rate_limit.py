import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import status

from home_manager.core.errors import AppError


class TooManyLoginAttemptsError(AppError):
    code = "TOO_MANY_LOGIN_ATTEMPTS"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Too many login attempts. Try again later."


@dataclass
class _Bucket:
    attempt_timestamps: list[float] = field(default_factory=list)


class LoginRateLimiter:
    """In-memory login throttle, keyed by client IP + email.

    Single-process only — sufficient for the current single-instance deployment.
    Revisit (e.g. move state to Postgres or Redis) if the backend is ever scaled
    to multiple instances.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = defaultdict(_Bucket)

    def check(self, key: str) -> None:
        bucket = self._buckets[key]
        now = time.monotonic()
        bucket.attempt_timestamps = [
            t for t in bucket.attempt_timestamps if now - t < self._window_seconds
        ]
        if len(bucket.attempt_timestamps) >= self._max_attempts:
            raise TooManyLoginAttemptsError()

    def record_failure(self, key: str) -> None:
        self._buckets[key].attempt_timestamps.append(time.monotonic())

    def reset(self, key: str) -> None:
        self._buckets.pop(key, None)

    def reset_all(self) -> None:
        self._buckets.clear()


login_rate_limiter = LoginRateLimiter()
