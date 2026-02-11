import time
from typing import Callable


class TTSRuntime:
    def __init__(self, request_interval_sec: float):
        if request_interval_sec <= 0:
            raise ValueError("request_interval_sec must be greater than 0.")
        self.request_interval_sec = request_interval_sec
        self.last_request_time: float | None = None

    def enforce_rate_limit(
        self,
        monotonic_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if self.last_request_time is None:
            return
        elapsed = monotonic_fn() - self.last_request_time
        remaining = self.request_interval_sec - elapsed
        if remaining > 0:
            sleep_fn(remaining)

    def mark_request_time(self, monotonic_fn: Callable[[], float] = time.monotonic) -> None:
        self.last_request_time = monotonic_fn()

    def run_with_retry(
        self,
        func: Callable[[], None],
        attempts: int = 3,
        backoff: list[float] | None = None,
        context: str = "",
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        waits = backoff or [2.0, 4.0, 8.0]
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                func()
                return
            except Exception as error:
                last_error = error
                if attempt == attempts:
                    break
                wait = waits[min(attempt - 1, len(waits) - 1)]
                print(
                    f"RETRY {context} attempt={attempt}/{attempts} "
                    f"error={error} wait={wait:.1f}s"
                )
                sleep_fn(wait)
        if last_error is not None:
            raise last_error
