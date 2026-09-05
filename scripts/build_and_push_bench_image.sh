#!/usr/bin/env bash
# Builds the harness image and pushes it to an ECR repo you own, for use
# by k8s/bench-job.yaml. Usage: ./build_and_push_bench_image.sh <ecr-repo-uri>
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${1:?Usage: $0 <ecr-repo-uri>}"

aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%%/*}"
docker build -t "$REPO:latest" .
docker push "$REPO:latest"

echo "Pushed $REPO:latest — update k8s/bench-job.yaml's image field to match."
