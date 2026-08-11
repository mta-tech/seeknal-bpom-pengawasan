"""Request latency tracking and aggregate statistics for IBA test scripts.

Provides two main utilities:

``LatencyTracker``:
    Measures elapsed time for named phases of a single request
    (auth, init/POST, stream/SSE, total). Call ``start(label)``
    before each phase and ``stop(label)`` after; then call ``build()``
    to produce a ``RequestMetrics`` snapshot.

``compute_aggregate(metrics)``:
    Takes a list of ``RequestMetrics`` from multiple requests and
    returns p50/p95/p99 latency percentiles, throughput, and error rate.

Typical usage:
    tracker = LatencyTracker()
    tracker.start("total")
    tracker.start("init")
    response = client.send_message(query, domain_id)
    tracker.stop("init")
    tracker.start("stream")
    result = client.stream_response(response.message_id, response.sse_token)
    tracker.stop("stream")
    tracker.stop("total")
    metrics = tracker.build()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RequestMetrics:
    """Timing metrics for a single chat request."""

    auth_latency_ms: float = 0.0
    init_latency_ms: float = 0.0
    time_to_first_token_ms: float = 0.0
    stream_duration_ms: float = 0.0
    total_latency_ms: float = 0.0
    tool_calls: int = 0
    sqls: list[str] = field(default_factory=list)
    status_code: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "auth_latency_ms": round(self.auth_latency_ms, 1),
            "init_latency_ms": round(self.init_latency_ms, 1),
            "time_to_first_token_ms": round(self.time_to_first_token_ms, 1),
            "stream_duration_ms": round(self.stream_duration_ms, 1),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "tool_calls": self.tool_calls,
            "sqls": self.sqls,
            "status_code": self.status_code,
            "error": self.error,
        }


class LatencyTracker:
    """Context-aware timer for tracking request phases.

    Usage:
        tracker = LatencyTracker()
        tracker.start("auth")
        # ... do auth ...
        tracker.stop("auth")
        metrics = tracker.build()
    """

    def __init__(self):
        self._starts: dict[str, float] = {}
        self._stops: dict[str, float] = {}
        self._tool_calls: int = 0
        self._sqls: list[str] = []
        self._status_code: int = 0
        self._error: Optional[str] = None

    def start(self, label: str) -> None:
        self._starts[label] = time.monotonic()

    def stop(self, label: str) -> float:
        now = time.monotonic()
        self._stops[label] = now
        start = self._starts.get(label, now)
        return (now - start) * 1000  # ms

    def elapsed_ms(self, label: str) -> float:
        start = self._starts.get(label, 0)
        stop = self._stops.get(label, time.monotonic())
        return (stop - start) * 1000

    def set_tool_calls(self, count: int) -> None:
        self._tool_calls = count

    def set_sqls(self, sqls: list[str]) -> None:
        self._sqls = sqls

    def set_status_code(self, code: int) -> None:
        self._status_code = code

    def set_error(self, error: Optional[str]) -> None:
        self._error = error

    def build(self) -> RequestMetrics:
        """Build a RequestMetrics snapshot from current state."""
        return RequestMetrics(
            auth_latency_ms=self.elapsed_ms("auth"),
            init_latency_ms=self.elapsed_ms("init"),
            time_to_first_token_ms=self.elapsed_ms("ttft"),
            stream_duration_ms=self.elapsed_ms("stream"),
            total_latency_ms=self.elapsed_ms("total"),
            tool_calls=self._tool_calls,
            sqls=self._sqls,
            status_code=self._status_code,
            error=self._error,
        )

    def reset(self) -> None:
        self._starts.clear()
        self._stops.clear()
        self._tool_calls = 0
        self._sqls = []
        self._status_code = 0
        self._error = None


def compute_aggregate(all_metrics: list[RequestMetrics]) -> dict:
    """Compute aggregate statistics from a list of RequestMetrics.

    Args:
        all_metrics: List of individual request metrics.

    Returns:
        Dict with p50/p95/p99 latency, throughput, error rate, etc.
    """
    if not all_metrics:
        return {}

    latencies = sorted(m.total_latency_ms for m in all_metrics)
    errors = sum(1 for m in all_metrics if m.error)
    n = len(latencies)

    def percentile(p: float) -> float:
        idx = int(p / 100 * (n - 1))
        return latencies[min(idx, n - 1)]

    total_time_ms = sum(latencies)
    throughput = (n / (total_time_ms / 1000)) if total_time_ms > 0 else 0

    return {
        "total_requests": n,
        "successful": n - errors,
        "failed": errors,
        "latency_p50_ms": round(percentile(50), 1),
        "latency_p95_ms": round(percentile(95), 1),
        "latency_p99_ms": round(percentile(99), 1),
        "latency_min_ms": round(latencies[0], 1),
        "latency_max_ms": round(latencies[-1], 1),
        "latency_avg_ms": round(sum(latencies) / n, 1),
        "throughput_req_per_sec": round(throughput, 2),
        "error_rate_percent": round(errors / n * 100, 1) if n else 0,
    }
