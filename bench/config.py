from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Target:
    name: str
    base_url: str
    model: str
    hardware_label: str
    api_key: str = ""
    headers: dict = field(default_factory=dict)


@dataclass
class BenchmarkConfig:
    targets: list[Target]
    concurrency_levels: list[int]
    requests_per_level: int
    max_tokens: int
    temperature: float
    prompts_file: str
    request_timeout_s: float
    warmup_requests: int

    @property
    def prompts(self) -> list[str]:
        path = Path(self.prompts_file)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent.parent / self.prompts_file
        lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]
        return lines


def load_config(path: str) -> BenchmarkConfig:
    raw = yaml.safe_load(Path(path).read_text())

    targets = [
        Target(
            name=t["name"],
            base_url=t["base_url"].rstrip("/"),
            model=t["model"],
            hardware_label=t.get("hardware_label", "unknown"),
            api_key=t.get("api_key", ""),
            headers=t.get("headers", {}),
        )
        for t in raw["targets"]
    ]

    load = raw.get("load", {})
    return BenchmarkConfig(
        targets=targets,
        concurrency_levels=load.get("concurrency_levels", [1, 4, 16]),
        requests_per_level=load.get("requests_per_level", 20),
        max_tokens=load.get("max_tokens", 128),
        temperature=load.get("temperature", 0.0),
        prompts_file=raw.get("prompts_file", "configs/prompts.txt"),
        request_timeout_s=load.get("request_timeout_s", 120.0),
        warmup_requests=load.get("warmup_requests", 2),
    )
