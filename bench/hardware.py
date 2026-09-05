from __future__ import annotations

import platform
import shutil
import subprocess


def detect_hardware(override: str = "") -> str:
    """Best-effort local hardware label. In-cluster runs should set
    hardware_label explicitly in config (Karpenter's instance-type label
    is the source of truth), so this is only a fallback for local runs."""
    if override and override != "unknown":
        return override

    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,count",
                    "--format=csv,noheader",
                ],
                text=True,
                timeout=5,
            ).strip()
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if lines:
                name, mem, _ = lines[0].split(",")
                return f"{name.strip()} x{len(lines)} ({mem.strip()})"
        except Exception:
            pass

    if shutil.which("neuron-ls"):
        try:
            out = subprocess.check_output(["neuron-ls"], text=True, timeout=5)
            if out.strip():
                return "AWS Neuron (inf2)"
        except Exception:
            pass

    return f"cpu:{platform.processor() or platform.machine()}"
