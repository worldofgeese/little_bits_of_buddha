data "template_file" "kubeconfig" {
  template = file("${path.module}/kubeconfig-template.yaml")

  vars = {
    cluster_name    = var.cluster_name
    endpoint        = var.endpoint
    token           = var.loft_access_key
  }
}

resource "local_sensitive_file" "kubeconfig" {
  filename = "${path.module}/kubeconfig.yaml"
  content  = data.template_file.kubeconfig.rendered
}

output "kubeconfig_path" {
  value = local_sensitive_file.kubeconfig.filename
}

variable "loft_access_key" {
  description = "API access key to cluster issued by your admin"
}

variable "endpoint" {
  description = "Name of K8s cluster endpoint"
}

variable "cluster_name" {
  description = "Name of K8s cluster"
}

