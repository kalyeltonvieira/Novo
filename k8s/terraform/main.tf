# Provedor Terraform para Kubernetes e Infraestrutura em Nuvem
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23.0"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

# Namespace exclusivo da aplicação
resource "kubernetes_namespace" "transparencia_ns" {
  metadata {
    name = var.namespace
    labels = {
      environment = var.environment
      app         = "transparencia-ia"
    }
  }
}
