#!/usr/bin/env bash
# Applies Karpenter EC2NodeClass/NodePool + device plugins, substituting
# terraform outputs into the node-role/cluster-name placeholders.
set -euo pipefail
cd "$(dirname "$0")/.."

CLUSTER_NAME=$(terraform -chdir=terraform output -raw cluster_name)
NODE_ROLE=$(terraform -chdir=terraform output -raw karpenter_node_iam_role_name)

echo "cluster_name=$CLUSTER_NAME"
echo "karpenter_node_role=$NODE_ROLE"

tmpdir=$(mktemp -d)
for f in k8s/karpenter/ec2nodeclass-g5.yaml k8s/karpenter/ec2nodeclass-inf2.yaml; do
  sed -e "s/REPLACE_ME_CLUSTER_NAME/${CLUSTER_NAME}/g" \
      -e "s/REPLACE_ME_NODE_ROLE_NAME/${NODE_ROLE}/g" \
      "$f" > "$tmpdir/$(basename "$f")"
done

kubectl apply -f "$tmpdir/ec2nodeclass-g5.yaml"
kubectl apply -f k8s/device-plugins/nvidia-device-plugin.yaml

echo
echo "inf2 NodePool/EC2NodeClass rendered but NOT applied automatically" \
     "(review caveats in k8s/karpenter/ec2nodeclass-inf2.yaml first):"
echo "  kubectl apply -f $tmpdir/ec2nodeclass-inf2.yaml"
echo "  kubectl apply -f k8s/device-plugins/neuron-device-plugin.yaml"

rm -rf "$tmpdir"
