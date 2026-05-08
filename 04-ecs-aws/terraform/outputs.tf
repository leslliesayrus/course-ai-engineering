output "environ" {
  value       = var.environ
  description = "Ambiente aplicado."
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "backend_url" {
  description = "URL base do ALB do backend (HTTP)."
  value       = "http://${aws_lb.backend.dns_name}"
}

output "backend_message_url" {
  description = "POST /message (SSE) no backend."
  value       = "http://${aws_lb.backend.dns_name}/message"
}

output "frontend_url" {
  description = "URL do Chainlit no ALB do frontend (HTTP)."
  value       = "http://${aws_lb.frontend.dns_name}"
}

output "groq_secret_name" {
  description = "Nome do secret no Secrets Manager (GROQ-API-KEY dentro do JSON)."
  value       = aws_secretsmanager_secret.groq.name
}
