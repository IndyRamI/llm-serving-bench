#!/usr/bin/env bash
# Port-forwards vLLM Services to localhost for use with configs/example.aws.yaml.
set -euo pipefail
kubectl port-forward svc/vllm-g5 8001:8000 &
kubectl port-forward svc/vllm-inf2 8002:8000 &
echo "Forwarding vllm-g5 -> localhost:8001, vllm-inf2 -> localhost:8002"
echo "Press Ctrl+C to stop."
wait
