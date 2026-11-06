variable "namespace" {
  description = "Namespace do Kubernetes para o Cérebro da Transparência"
  type        = string
  default     = "transparencia-prod"
}

variable "environment" {
  description = "Ambiente de execução (dev, staging, prod)"
  type        = string
  default     = "prod"
}
