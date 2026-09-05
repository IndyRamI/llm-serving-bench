from __future__ import annotations

from dataclasses import asdict, dataclass

from .client import RequestRecord


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


@dataclass
class Summary:
    target: str
    hardware_label: str
    concurrency: int
    num_requests: int
    num_success: int
    num_errors: int
    error_rate: float
    wall_time_s: float
    requests_per_s: float
    output_tokens_per_s: float
    ttft_p50_s: float
    ttft_p90_s: float
    ttft_p99_s: float
    tpot_p50_ms: float
    tpot_p90_ms: float
    tpot_p99_ms: float
    latency_p50_s: float
    latency_p90_s: float
    latency_p99_s: float

    def as_dict(self) -> dict:
        return asdict(self)


def summarize(records: list[RequestRecord], wall_time_s: float) -> Summary:
    ok = [r for r in records if r.success]
    ttft = [r.ttft_s for r in ok]
    latency = [r.total_latency_s for r in ok]
    itl = [t for r in ok for t in r.inter_token_latencies_s]
    total_output_tokens = sum(r.completion_tokens for r in ok)

    target = records[0].target if records else "unknown"
    hw = records[0].hardware_label if records else "unknown"
    concurrency = records[0].concurrency if records else 0

    return Summary(
        target=target,
        hardware_label=hw,
        concurrency=concurrency,
        num_requests=len(records),
        num_success=len(ok),
        num_errors=len(records) - len(ok),
        error_rate=(len(records) - len(ok)) / len(records) if records else 0.0,
        wall_time_s=wall_time_s,
        requests_per_s=len(ok) / wall_time_s if wall_time_s > 0 else 0.0,
        output_tokens_per_s=total_output_tokens / wall_time_s if wall_time_s > 0 else 0.0,
        ttft_p50_s=_pct(ttft, 0.50),
        ttft_p90_s=_pct(ttft, 0.90),
        ttft_p99_s=_pct(ttft, 0.99),
        tpot_p50_ms=_pct(itl, 0.50) * 1000,
        tpot_p90_ms=_pct(itl, 0.90) * 1000,
        tpot_p99_ms=_pct(itl, 0.99) * 1000,
        latency_p50_s=_pct(latency, 0.50),
        latency_p90_s=_pct(latency, 0.90),
        latency_p99_s=_pct(latency, 0.99),
    )
