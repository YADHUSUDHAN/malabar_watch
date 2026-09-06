# ==============================================================================
# Terraform Main Configuration - Malabar Watch AWS Infrastructure
# Zero-Inbound Port Security + AWS SSM Session Manager
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_tag
      Environment = "production"
      ManagedBy   = "Terraform"
    }
  }
}

# ------------------------------------------------------------------------------
# 1. Base AMI: Ubuntu 24.04 LTS (Noble Numbat)
# ------------------------------------------------------------------------------
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical official AWS account

  filter {
    name   = "name"
    values = ["ubuntu/images/*ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ------------------------------------------------------------------------------
# 2. Networking: Default VPC Lookup & Zero-Inbound Security Group
# ------------------------------------------------------------------------------
data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "malabar_sg" {
  name_prefix = "${var.project_tag}-zero-inbound-"
  description = "Zero inbound ports. Outbound HTTPS exclusively for API calls and Telegram polling."
  vpc_id      = data.aws_vpc.default.id

  # ZERO INBOUND RULES - No open ports from the internet (no SSH port 22, no HTTP port 80)
  ingress = []

  # Allow all outbound traffic (needed for Open-Meteo, Gemini/Groq, Telegram, and SSM)
  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
    description      = "Allow all outbound traffic"
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_tag}-zero-inbound-sg"
  }
}

# ------------------------------------------------------------------------------
# 3. IAM Role & Instance Profile for Keyless AWS SSM Session Manager
# ------------------------------------------------------------------------------
resource "aws_iam_role" "ssm_role" {
  name_prefix = "${var.project_tag}-ssm-role-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_tag}-ssm-role"
  }
}

# Attach standard AWS managed policy for SSM Session Manager
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm_profile" {
  name_prefix = "${var.project_tag}-ssm-profile-"
  role        = aws_iam_role.ssm_role.name

  lifecycle {
    create_before_destroy = true
  }
}

# ------------------------------------------------------------------------------
# 4. EC2 Instance (AWS Free Tier Eligible)
# ------------------------------------------------------------------------------
resource "aws_instance" "malabar_agent" {
  ami                  = data.aws_ami.ubuntu.id
  instance_type        = var.instance_type
  iam_instance_profile = aws_iam_instance_profile.ssm_profile.name

  vpc_security_group_ids = [aws_security_group.malabar_sg.id]

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.disk_size_gb
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name = "${var.project_tag}-root-volume"
    }
  }

  # Security Hardening: Enforce IMDSv2 (CIS AWS Benchmark & Well-Architected Best Practice)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name = "${var.project_tag}-agent"
  }
}
