# ==============================================================================
# Terraform Variables - Malabar Watch AWS Infrastructure
# ==============================================================================

variable "aws_region" {
  description = "Target AWS Region for deployment (ap-south-1 Mumbai for lowest latency to Kerala)"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 Instance Type (t2.micro / t3.micro are eligible for AWS Free Tier)"
  type        = string
  default     = "t3.micro"
}

variable "disk_size_gb" {
  description = "EBS Root Volume Disk Size in GB (up to 30 GB is free in AWS Free Tier)"
  type        = number
  default     = 30
}

variable "project_tag" {
  description = "Tag name applied to all AWS resources for identification"
  type        = string
  default     = "malabar-watch"
}
