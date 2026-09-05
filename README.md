# llm-serving-bench

An end-to-end harness for benchmarking LLM serving performance across
different models and hardware, plus the AWS infrastructure (EKS + Karpenter)
to actually stand up GPU/Neuron nodes to test against.

## Fresh machine setup (e.g. a new laptop)

Repo: https://github.com/IndyRamI/llm-serving-bench

### 1. Install prerequisites

macOS (Homebrew):

```bash
brew install git python3 terraform hashicorp/tap/terraform kubectl awscli gh
```

- `python3` — 3.11+ recommended, used for the harness and mock server
- `terraform` — provisions EKS/Karpenter (Terraform installs are gated behind
  the `hashicorp/tap`, hence both lines above; the second is the one that
  actually wins)
- `kubectl` — talks to the cluster once it exists
- `awscli` — AWS auth + `aws eks update-kubeconfig`
- `gh` — only needed if you want to clone/push via `gh` instead of plain git

Docker is only required if you plan to build/push the in-cluster benchmark
image (`scripts/build_and_push_bench_image.sh`) — not needed for the
port-forward workflow.

### 2. Clone the repo

```bash
git clone https://github.com/IndyRamI/llm-serving-bench.git
cd llm-serving-bench
```

### 3. Set up the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Sanity-check the harness locally (no AWS, no cost)

```bash
uvicorn mock_server:app --port 8000 &
python cli.py --config configs/example.local.yaml
```

You should see a results table printed and `results/<timestamp>/` written
with `summary.csv`/`summary.md`. Kill the mock server when done:
`kill %1` (or `pkill -f "uvicorn mock_server"`).

### 5. Authenticate to AWS

Pick whichever matches how this AWS account is normally accessed:

```bash
aws configure                 # long-lived access key + secret
# or
aws sso login --profile <profile-name>   # if using AWS SSO
```

Verify it worked:

```bash
aws sts get-caller-identity
```

Confirm the account/region has **g5** (and, if pursuing it, **inf2**)
instance quota — check the EC2 "Service Quotas" console for "Running
On-Demand G and VT instances" / "Running On-Demand Inf instances" in the
region you're deploying to (default `us-east-1`, set in
`terraform/variables.tf`).

### 6. Provision AWS infra (costs money from this point on)

```bash
./scripts/deploy_infra.sh
```

This runs `terraform init`/`plan` and asks you to confirm before `apply`.
Review the plan carefully — it creates a VPC, an EKS cluster, a small
always-on managed node group, and the Karpenter controller.

```bash
aws eks update-kubeconfig --region us-east-1 --name llm-serving-bench
./scripts/deploy_karpenter_resources.sh
```

The second command applies the g5 `NodePool`/`EC2NodeClass` and the NVIDIA
device plugin. It prints (but does not apply) the inf2 equivalents — review
the caveats in `k8s/karpenter/ec2nodeclass-inf2.yaml` before applying those.

### 7. Deploy vLLM and run a real benchmark

```bash
cp k8s/vllm/hf-token-secret.example.yaml k8s/vllm/hf-token-secret.yaml
# edit hf-token-secret.yaml with your real Hugging Face token
kubectl apply -f k8s/vllm/hf-token-secret.yaml
kubectl apply -f k8s/vllm/deployment-g5.yaml
kubectl rollout status deployment/vllm-g5    # slow the first time (model download)

./scripts/port_forward.sh &
python cli.py --config configs/example.aws.yaml --out results/aws-run
```

### 8. Tear down when finished (stop paying for it)

```bash
kubectl delete -f k8s/vllm/deployment-g5.yaml -f k8s/vllm/deployment-inf2-neuron.yaml --ignore-not-found
cd terraform && terraform destroy
```

## Components

- **`bench/`** — the benchmarking harness itself (Python, asyncio + httpx).
  Talks to any OpenAI-compatible `/v1/chat/completions` endpoint. Captures:
  - **TTFT** (time to first token) — p50/p90/p99
  - **TPOT / inter-token latency** — p50/p90/p99
  - **End-to-end request latency** — p50/p90/p99
  - **Throughput** — requests/sec and output tokens/sec
  - **Error rate**
  - **Hardware label** attached to every result row, so you can directly
    compare e.g. `g5.xlarge (A10G)` vs `inf2.xlarge` for the same model
  Sweeps a list of concurrency levels per target and writes raw per-request
  JSONL + a summary CSV/Markdown table per run.
- **`terraform/`** — provisions an EKS cluster with Karpenter for
  autoscaling GPU/Neuron node pools on demand (nodes only exist while a
  benchmark needs them).
- **`k8s/`** — Karpenter `NodePool`/`EC2NodeClass` for g5 (A10G) and inf2
  (Inferentia2), device plugins, and vLLM `Deployment`/`Service` manifests
  to serve a model on each hardware pool.
- **`mock_server.py`** — a fake OpenAI-compatible streaming server used to
  validate the harness locally without any cloud spend. Already verified
  end-to-end (see below) — not for real benchmarking.

## Status / what's been tested here

- ✅ The harness (`bench/`, `cli.py`) is fully implemented and was run
  end-to-end against `mock_server.py` locally — streaming, TTFT/TPOT
  capture, concurrency sweeps, and CSV/Markdown report generation all work.
- ✅ `terraform validate` passes for the EKS + Karpenter config.
- ✅ All `k8s/*.yaml` manifests parse as valid YAML.
- ⚠️ **Nothing has been deployed to AWS.** Provisioning EKS + GPU nodes
  costs real money and needs your AWS credentials — that step is on you,
  run via the scripts below when you're ready.
- ⚠️ The **inf2/Neuron path is best-effort scaffolding**, not a verified
  config — see the caveats in `k8s/karpenter/ec2nodeclass-inf2.yaml` and
  `k8s/vllm/deployment-inf2-neuron.yaml`. The g5/NVIDIA path uses the
  stock `vllm/vllm-openai` image and is much more likely to work as-is;
  inf2 requires building a Neuron-specific vLLM image yourself.

## 1. Validate the harness locally (no cloud cost)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn mock_server:app --port 8000 &
python cli.py --config configs/example.local.yaml
```

Results land in `results/<timestamp>/` (`summary.csv`, `summary.md`, raw
per-request `.jsonl`).

## 2. Provision AWS infra

Requires AWS credentials with permission to create EKS/VPC/IAM resources,
and confirm your account/region has g5 and inf2 capacity/quota.

```bash
./scripts/deploy_infra.sh          # terraform init/plan/apply, asks to confirm
aws eks update-kubeconfig --region <region> --name llm-serving-bench
./scripts/deploy_karpenter_resources.sh   # applies g5 NodePool + NVIDIA device plugin
```

The inf2 NodePool/EC2NodeClass and Neuron device plugin are **not** applied
automatically — review the caveats in `k8s/karpenter/ec2nodeclass-inf2.yaml`
first, then apply them manually if you want to pursue that path.

Edit `terraform/variables.tf` (or add a `terraform.tfvars`) to change
region, cluster name, or AZs before applying.

## 3. Deploy vLLM and run a benchmark

```bash
cp k8s/vllm/hf-token-secret.example.yaml k8s/vllm/hf-token-secret.yaml
# edit in your HF token, then:
kubectl apply -f k8s/vllm/hf-token-secret.yaml
kubectl apply -f k8s/vllm/deployment-g5.yaml
kubectl rollout status deployment/vllm-g5   # first pull + model download takes a while

./scripts/port_forward.sh &                 # localhost:8001 -> vllm-g5
python cli.py --config configs/example.aws.yaml --out results/aws-run
```

Or run the harness in-cluster as a Job instead of port-forwarding:

```bash
./scripts/build_and_push_bench_image.sh <your-ecr-repo-uri>
# update k8s/bench-job.yaml's image field to match, then:
kubectl apply -f k8s/bench-job.yaml
kubectl logs -f job/llm-bench
kubectl cp $(kubectl get pod -l job-name=llm-bench -o name | cut -d/ -f2):/app/results ./results/incluster-run
```

## 4. Compare hardware

Add more `targets` entries to a config (same model, different
`hardware_label`/`base_url` per GPU pool) and the summary table/CSV will
have them side by side, ready to sort by tok/s or TTFT per dollar.

## Cost control

- Karpenter `NodePool.spec.template.spec.expireAfter: 12h` forces GPU nodes
  to recycle even if you forget to tear them down.
- `disruption.consolidateAfter: 5m` lets Karpenter deprovision idle nodes
  quickly once a benchmark finishes.
- Nothing GPU-shaped runs until you `kubectl apply` a vLLM Deployment —
  the EKS control plane + small system node group are the only always-on
  cost after `deploy_infra.sh`.
- **Tear down when done:**
  ```bash
  kubectl delete -f k8s/vllm/deployment-g5.yaml -f k8s/vllm/deployment-inf2-neuron.yaml --ignore-not-found
  cd terraform && terraform destroy
  ```

## Extending

- Add a target model/hardware: copy a `k8s/vllm/deployment-*.yaml`, change
  `nodeSelector`/`--model`/resource requests, add a matching `NodePool` if
  it's a new instance family.
- Add a metric: extend `RequestRecord` in `bench/client.py` and `Summary`
  in `bench/metrics.py`.
- Swap the serving engine: the harness only assumes an OpenAI-compatible
  `/v1/chat/completions` streaming endpoint, so any backend (TGI, Ray Serve
  LLM, SGLang, Ollama) works — only the `k8s/vllm/` manifests are
  vLLM-specific.
