"""Minimal OpenAI-compatible streaming server for validating the harness
locally, without needing real GPUs. NOT for benchmarking real hardware.

Run: uvicorn mock_server:app --port 8000
"""
from __future__ import annotations

import asyncio
import json
import random
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

PREFILL_DELAY_S = 0.15  # simulated TTFT
PER_TOKEN_DELAY_S = 0.02  # simulated inter-token latency
RESPONSE_WORDS = ("the quick brown fox jumps over the lazy dog " * 20).split()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    max_tokens = body.get("max_tokens", 64)
    model = body.get("model", "mock-model")
    stream = body.get("stream", False)

    if not stream:
        text = " ".join(RESPONSE_WORDS[:max_tokens])
        return {
            "id": "mock-1",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": max_tokens, "total_tokens": 20 + max_tokens},
        }

    async def gen():
        await asyncio.sleep(PREFILL_DELAY_S + random.uniform(0, 0.05))
        n = min(max_tokens, len(RESPONSE_WORDS))
        for i in range(n):
            chunk = {
                "id": "mock-1",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {"content": RESPONSE_WORDS[i] + " "}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(PER_TOKEN_DELAY_S + random.uniform(0, 0.01))

        final = {
            "id": "mock-1",
            "object": "chat.completion.chunk",
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": n, "total_tokens": 20 + n},
        }
        yield f"data: {json.dumps(final)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}
