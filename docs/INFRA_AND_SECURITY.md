# Infrastructure & Security Specification - AWS Free Tier & Zero-Trust Architecture

This document details the Cloud Infrastructure-as-Code (Terraform) design, security hardening, zero-inbound port networking, and automated deployment pipeline for **Malabar Watch** on **Amazon Web Services (AWS)**.

---

## 1. Cloud Provider: Amazon Web Services (AWS) Free Tier

AWS provides 750 hours/month of Linux `t2.micro` or `t3.micro` under the 12-Month Free Tier:
- **Compute Instance:** `t2.micro` or `t3.micro` (1 vCPU, 1 GB RAM)
- **Swap Allocation:** 2 GB Linux Swap File (Ubuntu 24.04 LTS)
- **Persistent Storage:** 30 GB EBS gp3/gp2 General Purpose SSD
- **Recommended Region:** `ap-south-1` (Asia Pacific - Mumbai) for minimal latency to Kerala subscribers
- **Monthly Cost:** **₹0 / month** (within AWS Free Tier) / ~$3.50/mo on Lightsail as long-term post-free tier alternative

---

## 2. Zero-Inbound Security Topology

```
                  ┌──────────────────────────────────────────────┐
                  │            PUBLIC INTERNET / USERS           │
                  └──────────────────────┬───────────────────────┘
                                         │
                   DENY ALL INBOUND      │ (AWS Security Group blocks ALL
                   APPLICATION PORTS     │  inbound TCP/UDP traffic from 0.0.0.0/0)
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │    AWS Virtual Private Cloud (VPC)           │
                  │                                              │
                  │   ┌──────────────────────────────────────┐   │
                  │   │   Malabar Watch EC2 Instance         │   │
                  │   │   (t2.micro/t3.micro + 2GB Swap)     │   │
                  │   │                                      │   │
                  │   │   - Outbound HTTPS (Open-Meteo API)  │───┼───▶ Open-Meteo API
                  │   │   - Outbound HTTPS (Gemini / Groq)   │───┼───▶ LLM APIs
                  │   │   - Outbound Long Polling / Push     │───┼───▶ Telegram API
                  │   └──────────────────▲───────────────────┘   │
                  └──────────────────────┼───────────────────────┘
                                         │
                                         │ Keyless Admin via AWS Systems Manager (SSM)
                                         │ (IAM Role: AmazonSSMManagedInstanceCore, no port 22)
                  ┌──────────────────────┴───────────────────────┐
                  │   Developer / GitHub Actions CI/CD Deploy    │
                  └──────────────────────────────────────────────┘
```

### Key Hardening Principles:
1. **Zero Public Inbound Application Ports:** The AWS Security Group ingress contains NO inbound rules for application ports (`0.0.0.0/0` blocked). No web servers or public HTTP listeners run on the host.
2. **Keyless Administration via AWS SSM:** Rather than opening SSH (port 22) to the world, shell sessions and deployments run securely through **AWS Systems Manager (SSM) Session Manager**, requiring cryptographic AWS IAM authentication.
3. **Outbound-Only Communication:** All external connectivity (weather data fetching, LLM API calls, Telegram bot polling and alert pushes) is initiated strictly from inside the VM outward over standard HTTPS (`443`).
4. **Least-Privilege Execution:** System processes run under an unprivileged dedicated service user (`malabarwatch`), with environment secrets managed via `/etc/systemd/system/malabar-watch.service.d/override.conf`.

---

## 3. Infrastructure as Code (Terraform for AWS)

The infrastructure is defined under `terraform/`:

```hcl
# terraform/main.tf
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
  region = var.aws_region # Default: ap-south-1
}

resource "aws_vpc" "malabar_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "malabar-watch-vpc" }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.malabar_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true

  tags = { Name = "malabar-watch-subnet" }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.malabar_vpc.id
}

resource "aws_route_table" "rt" {
  vpc_id = aws_vpc.malabar_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "rta" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.rt.id
}

# ZERO INBOUND APPLICATION PORTS
resource "aws_security_group" "zero_inbound_sg" {
  name        = "malabar-watch-zero-inbound"
  description = "Block all inbound application traffic; allow all outbound HTTPS"
  vpc_id      = aws_vpc.malabar_vpc.id

  # Outbound HTTPS for API & Bot polling
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "malabar-watch-sg" }
}

# IAM Role for AWS Systems Manager (Keyless SSM access)
resource "aws_iam_role" "ssm_role" {
  name = "malabar-watch-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_attach" {
  role       = aws_iam_role.ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm_profile" {
  name = "malabar-watch-ssm-profile"
  role = aws_iam_role.ssm_role.name
}

resource "aws_instance" "malabar_host" {
  ami                  = var.ubuntu_ami_id
  instance_type        = var.instance_type # t2.micro or t3.micro
  subnet_id            = aws_subnet.public_subnet.id
  vpc_security_group_ids = [aws_security_group.zero_inbound_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ssm_profile.name

  root_block_device {
    volume_size = 30 # AWS Free Tier limit
    volume_type = "gp3"
  }

  user_data = file("${path.module}/user_data.sh")

  tags = { Name = "malabar-watch-host" }
}
```

---

## 4. Keyless Automated CI/CD Pipeline (GitHub Actions)

Deployments are automated via `.github/workflows/deploy.yml`:
1. Push to `main` branch triggers unit tests (`pytest`), linter (`ruff`), and type-checker (`mypy`).
2. On test success, GitHub Actions authenticates with AWS via **OpenID Connect (OIDC)** Web Identity (`aws-actions/configure-aws-credentials`).
3. Sends deployment commands via **AWS Systems Manager (SSM) Run Command** or syncs repository and restarts the `systemd` service cleanly without needing long-lived SSH private keys.

---

## 5. Local-First Verification Workflow

Before deploying to AWS:
1. **Local Run**: Execute the pipeline locally with test or live weather coordinates.
2. **Local Long Polling**: Connect the local bot instance to Telegram using `TELEGRAM_BOT_TOKEN`.
3. **Run Validation Checks**:
   ```bash
   uv run pytest
   uv run mypy src
   uv run ruff check .
   uv run malabar-watch
   ```
4. **Cloud Migration**: Only after all checks pass locally is Terraform applied and the AWS EC2 instance activated.

