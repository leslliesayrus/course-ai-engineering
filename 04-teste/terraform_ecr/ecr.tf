resource "aws_ecr_repository" "backend" {
  name                 = "chat-backend-${var.env}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project = "04-teste"
    Service = "backend"
    Env     = var.env
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "chat-frontend-${var.env}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project = "04-teste"
    Service = "frontend"
    Env     = var.env
  }
}

output "ecr_backend_repository_url" {
  description = "URL para login/push/pull da imagem do backend."
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  description = "URL para login/push/pull da imagem do frontend."
  value       = aws_ecr_repository.frontend.repository_url
}
