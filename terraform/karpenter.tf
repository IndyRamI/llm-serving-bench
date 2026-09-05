module "karpenter" {
  source  = "terraform-aws-modules/eks/aws//modules/karpenter"
  version = "~> 20.24"

  cluster_name = module.eks.cluster_name

  enable_v1_permissions = true

  node_iam_role_use_name_prefix = false
  node_iam_role_name            = "${var.cluster_name}-karpenter-node"

  create_pod_identity_association = true

  tags = var.tags
}

resource "helm_release" "karpenter" {
  namespace        = "kube-system"
  name             = "karpenter"
  repository       = "oci://public.ecr.aws/karpenter"
  chart            = "karpenter"
  version          = "1.0.6"
  create_namespace = false

  values = [
    yamlencode({
      settings = {
        clusterName       = module.eks.cluster_name
        clusterEndpoint   = module.eks.cluster_endpoint
        interruptionQueue = module.karpenter.queue_name
      }
      serviceAccount = {
        name = "karpenter"
      }
      controller = {
        resources = {
          requests = { cpu = "1", memory = "1Gi" }
          limits   = { memory = "1Gi" }
        }
      }
    })
  ]

  depends_on = [module.eks]
}

output "karpenter_node_iam_role_name" {
  value = module.karpenter.node_iam_role_name
}
