#!/usr/bin/env bash
# Provisions the EKS cluster + Karpenter controller via Terraform.
# Costs real money the moment this runs (EKS control plane + system nodes).
set -euo pipefail
cd "$(dirname "$0")/../terraform"

terraform init
terraform plan -out=tfplan
echo
read -p "Review the plan above. Apply? [y/N] " confirm
if [[ "$confirm" != "y" ]]; then
  echo "Aborted."
  exit 1
fi
terraform apply tfplan
