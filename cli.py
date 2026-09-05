from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from bench.config import load_config
from bench.hardware import detect_hardware
from bench.report import print_table, write_csv, write_markdown
from bench.runner import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM serving benchmark harness")
    parser.add_argument("--config", required=True, help="Path to benchmark YAML config")
    parser.add_argument("--out", default=None, help="Output directory (default: results/<timestamp>)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    for t in cfg.targets:
        if t.hardware_label == "unknown":
            t.hardware_label = detect_hardware()

    out_dir = args.out or f"results/{datetime.now():%Y%m%d-%H%M%S}"
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    summaries = asyncio.run(run_benchmark(cfg, out_dir))

    write_csv(summaries, str(Path(out_dir) / "summary.csv"))
    write_markdown(summaries, str(Path(out_dir) / "summary.md"))

    print()
    print(f"Results written to {out_dir}/")
    print()
    print_table(summaries)


if __name__ == "__main__":
    main()
