from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import perf_counter
from typing import Any


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._timings: defaultdict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def observe_ms(self, name: str, value: float) -> None:
        with self._lock:
            self._timings[name].append(value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            timings = {
                name: _timing_summary(values)
                for name, values in self._timings.items()
            }
            return {
                "counters": dict(self._counters),
                "timings_ms": timings,
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._timings.clear()


class timer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.started_at = 0.0

    def __enter__(self) -> "timer":
        self.started_at = perf_counter()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        elapsed_ms = (perf_counter() - self.started_at) * 1000
        metrics.observe_ms(self.name, elapsed_ms)


def _timing_summary(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}
    return {
        "count": count,
        "avg": round(sum(ordered) / count, 2),
        "min": round(ordered[0], 2),
        "max": round(ordered[-1], 2),
        "p95": round(ordered[min(count - 1, int(count * 0.95))], 2),
    }


metrics = MetricsRegistry()
