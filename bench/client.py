from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import httpx

from .config import Target


@dataclass
class RequestRecord:
    target: str
    hardware_label: str
    concurrency: int
    success: bool
    error: str = ""
    status_code: int = 0
    ttft_s: float = 0.0
    total_latency_s: float = 0.0
    inter_token_latencies_s: list[float] = field(default_factory=list)
    completion_tokens: int = 0
    prompt_tokens: int = 0


async def stream_chat_completion(
    client: httpx.AsyncClient,
    target: Target,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout_s: float,
    concurrency: int,
) -> RequestRecord:
    headers = {"Content-Type": "application/json", **target.headers}
    if target.api_key:
        headers["Authorization"] = f"Bearer {target.api_key}"

    payload = {
        "model": target.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    rec = RequestRecord(
        target=target.name, hardware_label=target.hardware_label, concurrency=concurrency, success=False
    )

    start = time.perf_counter()
    last_token_time = start
    first_token_seen = False
    text_chunks = 0

    try:
        async with client.stream(
            "POST",
            f"{target.base_url}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout_s,
        ) as resp:
            rec.status_code = resp.status_code
            if resp.status_code != 200:
                body = await resp.aread()
                rec.error = f"HTTP {resp.status_code}: {body[:300]!r}"
                return rec

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue

                usage = obj.get("usage")
                if usage:
                    rec.prompt_tokens = usage.get("prompt_tokens", rec.prompt_tokens)
                    rec.completion_tokens = usage.get("completion_tokens", rec.completion_tokens)

                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                if delta.get("content"):
                    now = time.perf_counter()
                    if not first_token_seen:
                        rec.ttft_s = now - start
                        first_token_seen = True
                    else:
                        rec.inter_token_latencies_s.append(now - last_token_time)
                    last_token_time = now
                    text_chunks += 1

        rec.total_latency_s = time.perf_counter() - start
        if rec.completion_tokens == 0:
            rec.completion_tokens = text_chunks  # fallback proxy when server omits usage
        rec.success = first_token_seen
        if not first_token_seen:
            rec.error = "no content tokens received"
        return rec

    except httpx.TimeoutException:
        rec.error = "timeout"
        rec.total_latency_s = time.perf_counter() - start
        return rec
    except Exception as e:  # noqa: BLE001 - record any transport error, don't crash the run
        rec.error = f"{type(e).__name__}: {e}"
        rec.total_latency_s = time.perf_counter() - start
        return rec
