variable "key_pair" {
  description = "Name of the existing AWS EC2 Key Pair"
  type        = string
  default     = "terraform"
}

variable "instance_state" {
  description = "The desired state of the EC2 instance (running or stopped)"
  type        = string
  default     = "running"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "app_repo" {
  description = "Git repository URL for the application"
  type        = string
  default     = "https://github.com/wjjackson7/learn-terraform.git"
}

variable "app_path" {
  description = "Path where the application will be installed"
  type        = string
  default     = "/opt/app"
}
