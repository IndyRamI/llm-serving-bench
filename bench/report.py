from __future__ import annotations

import csv
from pathlib import Path

from .metrics import Summary

COLUMNS = [
    "target", "hardware_label", "concurrency", "num_requests", "num_success",
    "error_rate", "requests_per_s", "output_tokens_per_s",
    "ttft_p50_s", "ttft_p90_s", "ttft_p99_s",
    "tpot_p50_ms", "tpot_p90_ms", "tpot_p99_ms",
    "latency_p50_s", "latency_p90_s", "latency_p99_s",
]


def write_csv(summaries: list[Summary], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for s in summaries:
            writer.writerow({k: s.as_dict()[k] for k in COLUMNS})


def write_markdown(summaries: list[Summary], path: str) -> None:
    header = "| target | hardware | conc | ok/n | err% | req/s | tok/s | ttft p50/p90 (ms) | tpot p50/p90 (ms) | latency p50/p90 (s) |"
    sep = "|---" * 10 + "|"
    lines = [header, sep]
    for s in summaries:
        lines.append(
            f"| {s.target} | {s.hardware_label} | {s.concurrency} | {s.num_success}/{s.num_requests} "
            f"| {s.error_rate*100:.1f}% | {s.requests_per_s:.2f} | {s.output_tokens_per_s:.1f} "
            f"| {s.ttft_p50_s*1000:.0f}/{s.ttft_p90_s*1000:.0f} "
            f"| {s.tpot_p50_ms:.1f}/{s.tpot_p90_ms:.1f} "
            f"| {s.latency_p50_s:.2f}/{s.latency_p90_s:.2f} |"
        )
    Path(path).write_text("\n".join(lines) + "\n")


def print_table(summaries: list[Summary]) -> None:
    fmt = "{:<14}{:<22}{:>5}{:>8}{:>8}{:>10}{:>10}{:>12}{:>12}"
    print(fmt.format("target", "hardware", "conc", "ok/n", "err%", "req/s", "tok/s", "ttft_p50ms", "tpot_p50ms"))
    for s in summaries:
        print(fmt.format(
            s.target, s.hardware_label[:21], s.concurrency,
            f"{s.num_success}/{s.num_requests}", f"{s.error_rate*100:.1f}",
            f"{s.requests_per_s:.2f}", f"{s.output_tokens_per_s:.1f}",
            f"{s.ttft_p50_s*1000:.0f}", f"{s.tpot_p50_ms:.1f}",
        ))
