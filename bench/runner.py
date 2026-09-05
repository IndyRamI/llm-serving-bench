from __future__ import annotations

import asyncio
import itertools
import json
import time
from pathlib import Path

import httpx

from .client import RequestRecord, stream_chat_completion
from .config import BenchmarkConfig, Target
from .metrics import Summary, summarize


async def _run_one_level(
    target: Target,
    prompts: list[str],
    concurrency: int,
    num_requests: int,
    max_tokens: int,
    temperature: float,
    timeout_s: float,
) -> tuple[list[RequestRecord], float]:
    prompt_cycle = itertools.cycle(prompts)
    limits = httpx.Limits(max_connections=concurrency + 5, max_keepalive_connections=concurrency)

    async with httpx.AsyncClient(limits=limits) as client:
        sem = asyncio.Semaphore(concurrency)

        async def worker(prompt: str) -> RequestRecord:
            async with sem:
                return await stream_chat_completion(
                    client, target, prompt, max_tokens, temperature, timeout_s, concurrency
                )

        start = time.perf_counter()
        tasks = [asyncio.create_task(worker(next(prompt_cycle))) for _ in range(num_requests)]
        records = await asyncio.gather(*tasks)
        wall_time = time.perf_counter() - start

    return list(records), wall_time


async def run_benchmark(cfg: BenchmarkConfig, out_dir: str, progress=print) -> list[Summary]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    prompts = cfg.prompts
    summaries: list[Summary] = []

    for target in cfg.targets:
        if cfg.warmup_requests > 0:
            progress(f"[{target.name}] warming up ({cfg.warmup_requests} requests)...")
            await _run_one_level(
                target, prompts, min(cfg.warmup_requests, max(cfg.concurrency_levels)),
                cfg.warmup_requests, cfg.max_tokens, cfg.temperature, cfg.request_timeout_s,
            )

        for concurrency in cfg.concurrency_levels:
            progress(f"[{target.name}] running concurrency={concurrency}, n={cfg.requests_per_level} ...")
            records, wall_time = await _run_one_level(
                target, prompts, concurrency, cfg.requests_per_level,
                cfg.max_tokens, cfg.temperature, cfg.request_timeout_s,
            )
            summary = summarize(records, wall_time)
            summaries.append(summary)

            raw_file = out_path / f"{target.name}_c{concurrency}.jsonl"
            with raw_file.open("w") as f:
                for r in records:
                    f.write(json.dumps(r.__dict__) + "\n")

            progress(
                f"[{target.name}] c={concurrency}: "
                f"{summary.num_success}/{summary.num_requests} ok, "
                f"ttft_p50={summary.ttft_p50_s*1000:.0f}ms, "
                f"tpot_p50={summary.tpot_p50_ms:.1f}ms, "
                f"throughput={summary.output_tokens_per_s:.1f} tok/s"
            )

    return summaries
