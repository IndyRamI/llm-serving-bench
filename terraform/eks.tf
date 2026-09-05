module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.24"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version

  cluster_endpoint_public_access = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  enable_cluster_creator_admin_permissions = true

  cluster_addons = {
    coredns            = {}
    kube-proxy         = {}
    vpc-cni            = {}
    aws-ebs-csi-driver = {}
  }

  # Small, always-on node group for system workloads (CoreDNS, Karpenter
  # controller, NVIDIA/Neuron device plugin daemonsets' control-plane bits).
  # Actual LLM-serving GPU nodes are provisioned on demand by Karpenter,
  # not by this managed node group.
  eks_managed_node_groups = {
    system = {
      instance_types = var.system_instance_types
      min_size       = var.system_node_min_size
      max_size       = var.system_node_max_size
      desired_size   = var.system_node_min_size

      labels = {
        "workload" = "system"
      }
    }
  }

  # So Karpenter-launched nodes can join this cluster.
  node_security_group_tags = {
    "karpenter.sh/discovery" = var.cluster_name
  }

  tags = var.tags
}
