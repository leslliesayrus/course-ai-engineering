variable "aws_region" {
  description = "AWS region for ECS resources"
  type        = string
  default     = "us-east-1"
}

variable "ecr_repository_url" {
  description = "ECR repository URL without tag (example: 123456789012.dkr.ecr.us-east-1.amazonaws.com/04-teste-backend)"
  type        = string
  default     = "437274056715.dkr.ecr.us-east-1.amazonaws.com/04-teste-backend"
}

variable "image_tag" {
  description = "Image tag to deploy"
  type        = string
  default     = "latest"
}

variable "task_cpu" {
  description = "Fargate task CPU units"
  type        = string
  default     = "256"
}

variable "task_memory" {
  description = "Fargate task memory in MiB"
  type        = string
  default     = "512"
}

variable "container_port" {
  description = "Container port exposed by the application"
  type        = number
  default     = 8000
}
