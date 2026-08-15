# Infrastructure & Security Specification - Oracle Cloud ARM & Zero-Trust Architecture

This document details the Cloud Infrastructure-as-Code (Terraform) design, security hardening, zero-inbound port networking, and automated deployment pipeline for **Malabar Watch**.

---

## 1. Cloud Provider: Oracle Cloud Infrastructure (OCI) Always Free Tier

Oracle Cloud provides the industry's most generous free tier compute shape:
- **Compute Shape:** `VM.Standard.A1.Flex` (ARM Ampere A1 Core)
- **Allocated Resources:** 4 OCPU, 24 GB RAM, 200 GB NVMe Storage
- **Operating System:** Ubuntu 24.04 LTS (aarch64)
- **Monthly Cost:** **₹0 / month (Permanently Free)**

---

## 2. Zero-Inbound Security Topology

```
                  ┌──────────────────────────────────────────────┐
                  │            PUBLIC INTERNET / USERS           │
                  └──────────────────────┬───────────────────────┘
                                         │
                   DENY ALL INBOUND      │ (Firewall Security List blocks all
                   PORTS (0.0.0.0/0)     │  inbound TCP/UDP traffic)
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │    Oracle Virtual Cloud Network (VCN)        │
                  │                                              │
                  │   ┌──────────────────────────────────────┐   │
                  │   │   Malabar Watch Compute Instance     │   │
                  │   │   (ARM 4 OCPU / 24GB RAM)            │   │
                  │   │                                      │   │
                  │   │   - Outbound HTTPS (Open-Meteo API)  │───┼───▶ Open-Meteo API
                  │   │   - Outbound HTTPS (Gemini / Groq)   │───┼───▶ LLM APIs
                  │   │   - Outbound Long Polling / Push     │───┼───▶ Telegram API
                  │   └──────────────────▲───────────────────┘   │
                  └──────────────────────┼───────────────────────┘
                                         │
                                         │ Admin SSH via Oracle Cloud Bastion Service
                                         │ (Authenticated IAM, no public port 22 open)
                  ┌──────────────────────┴───────────────────────┐
                  │   Developer / GitHub Actions CI/CD Deploy    │
                  └──────────────────────────────────────────────┘
```

### Key Hardening Principles:
1. **Zero Open Public Inbound Ports:** Security List inbound rules are set to `DENY ALL`. No web servers, open SSH ports, or administrative listeners run on public IPs.
2. **Oracle Cloud Bastion Service:** Developer SSH access and deployment tunnels are dynamically established via OCI Bastion with time-limited ephemeral sessions.
3. **Outbound-Only Communication:** All external connectivity (weather data fetching, LLM API calls, Telegram bot polling and alert pushes) is initiated strictly from inside the VM outward over standard HTTPS (`443`).
4. **Least-Privilege Execution:** System processes run under an unprivileged dedicated service user (`malabarwatch`), with environment secrets managed via `/etc/systemd/system/malabar-watch.service.d/override.conf`.

---

## 3. Infrastructure as Code (Terraform)

The infrastructure is defined under `terraform/`:

```hcl
# terraform/main.tf
resource "oci_core_vcn" "malabar_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_id
  display_name   = "malabar-watch-vcn"
}

resource "oci_core_security_list" "zero_inbound_sl" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.malabar_vcn.id
  display_name   = "zero-inbound-security-list"

  # NO egress restrictions, ZERO ingress rules
  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }
}
```

---

## 4. Keyless Automated CI/CD Pipeline (GitHub Actions)

Deployments are automated via `.github/workflows/deploy.yml`:
1. Push to `main` branch triggers unit tests (`pytest`).
2. On test success, GitHub Actions authenticates with OCI via **OpenID Connect (OIDC)** (keyless workload identity).
3. Opens a temporary SSH session via Oracle Bastion tunnel.
4. Syncs codebase (`rsync` / `git pull`), restarts `systemd` service cleanly.
