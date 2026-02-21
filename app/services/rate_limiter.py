from __future__ import annotations

import threading
import time


class InMemoryFixedWindowRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, int]] = {}

    def is_allowed(self, key: str, limit_per_min: int) -> bool:
        safe_key = key or "__anonymous__"
        current_window = int(time.time() // 60)

        with self._lock:
            window_start, count = self._windows.get(safe_key, (current_window, 0))
            if window_start != current_window:
                window_start = current_window
                count = 0

            if count >= limit_per_min:
                self._windows[safe_key] = (window_start, count)
                return False

            self._windows[safe_key] = (window_start, count + 1)
            return True

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()


post_stories_rate_limiter = InMemoryFixedWindowRateLimiter()

