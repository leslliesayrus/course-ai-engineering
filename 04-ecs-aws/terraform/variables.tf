variable "environ" {
  description = "Ambiente (ex.: dev, prd). Usado em nomes chat-<environ>-* e nos repositórios ECR chat-*-<environ>."
  type        = string
}

variable "groq_api_key" {
  description = "Chave Groq; no CI vem do secret GROQ_API_KEY (TF_VAR_groq_api_key)."
  type        = string
  sensitive   = true
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "image_tag" {
  description = "Tag das imagens no ECR. A pipeline define TF_VAR_image_tag com o SHA do commit para cada deploy; sem isso :latest não altera a task definition. Fora do CI o default latest costuma bastar."
  type        = string
  default     = "latest"
}

variable "backend_cpu" {
  type    = string
  default = "256"
}

variable "backend_memory" {
  type    = string
  default = "512"
}

variable "frontend_cpu" {
  type    = string
  default = "512"
}

variable "frontend_memory" {
  type    = string
  default = "1024"
}

variable "backend_port" {
  type    = number
  default = 8000
}

variable "frontend_port" {
  type    = number
  default = 8005
}
