output "namespace_name" {
  value       = kubernetes_namespace.transparencia_ns.metadata[0].name
  description = "Nome do Namespace Kubernetes criado"
}
