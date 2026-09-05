variable "region" {
  description = "AWS region to deploy into. Must have g5 and inf2 capacity."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
  default     = "llm-serving-bench"
}

variable "kubernetes_version" {
  type    = string
  default = "1.30"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "azs" {
  description = "Availability zones to spread subnets across. Confirm g5/inf2 capacity in these AZs for your account/region."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "system_instance_types" {
  description = "Instance types for the small always-on managed node group running core add-ons (CoreDNS, Karpenter controller, etc). Not used for LLM serving."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "system_node_min_size" {
  type    = number
  default = 2
}

variable "system_node_max_size" {
  type    = number
  default = 3
}

variable "tags" {
  type = map(string)
  default = {
    Project = "llm-serving-bench"
  }
}
