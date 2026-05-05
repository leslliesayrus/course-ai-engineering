resource "aws_ecr_repository" "backend" {
  name                 = "04-teste-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project = "04-teste"
    Service = "backend"
  }
}

output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}
