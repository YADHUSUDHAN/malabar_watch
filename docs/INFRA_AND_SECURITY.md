# Infrastructure & Security Specification - GCP Compute Engine Always Free & Zero-Trust Architecture

This document details the Cloud Infrastructure-as-Code (Terraform) design, security hardening, zero-inbound port networking, and automated deployment pipeline for **Malabar Watch**.

---

## 1. Cloud Provider: Google Cloud Platform (GCP) Compute Engine Always Free Tier

GCP provides a permanent Always Free Compute Engine VM shape:
- **Compute Instance:** `e2-micro` (0.25–2 vCPU, 1 GB RAM)
- **Swap Allocation:** 2 GB Linux Swap File (Ubuntu 24.04 LTS)
- **Persistent Storage:** 30 GB Standard Persistent Disk
- **Free Tier Region:** `us-central1` (Iowa), `us-east1` (South Carolina), or `us-west1` (Oregon)
- **Monthly Cost:** **₹0 / month (Permanently Free)**

---

## 2. Zero-Inbound Security Topology

```
                  ┌──────────────────────────────────────────────┐
                  │            PUBLIC INTERNET / USERS           │
                  └──────────────────────┬───────────────────────┘
                                         │
                   DENY ALL INBOUND      │ (GCP VPC Firewall Rules block all
                   APPLICATION PORTS     │  inbound TCP/UDP application traffic)
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │    Google Cloud VPC Network                  │
                  │                                              │
                  │   ┌──────────────────────────────────────┐   │
                  │   │   Malabar Watch Compute Instance     │   │
                  │   │   (e2-micro + 2GB Swap)              │   │
                  │   │                                      │   │
                  │   │   - Outbound HTTPS (Open-Meteo API)  │───┼───▶ Open-Meteo API
                  │   │   - Outbound HTTPS (Gemini / Groq)   │───┼───▶ LLM APIs
                  │   │   - Outbound Long Polling / Push     │───┼───▶ Telegram API
                  │   └──────────────────▲───────────────────┘   │
                  └──────────────────────┼───────────────────────┘
                                         │
                                         │ Admin SSH via Keyless SSH / GCP Cloud IAP Tunnels
                                         │ (Authenticated IAM, no public app ports open)
                  ┌──────────────────────┴───────────────────────┐
                  │   Developer / GitHub Actions CI/CD Deploy    │
                  └──────────────────────────────────────────────┘
```

### Key Hardening Principles:
1. **Zero Public Inbound Application Ports:** GCP VPC Firewall ingress rules block all incoming traffic to application ports (`DENY ALL`). No web servers or public HTTP listeners run on the host.
2. **Outbound-Only Communication:** All external connectivity (weather data fetching, LLM API calls, Telegram bot polling and alert pushes) is initiated strictly from inside the VM outward over standard HTTPS (`443`).
3. **Least-Privilege Execution:** System processes run under an unprivileged dedicated service user (`malabarwatch`), with environment secrets managed via `/etc/systemd/system/malabar-watch.service.d/override.conf`.

---

## 3. Infrastructure as Code (Terraform)

The infrastructure is defined under `terraform/`:

```hcl
# terraform/main.tf
resource "google_compute_network" "malabar_vpc" {
  name                    = "malabar-watch-vpc"
  auto_create_subnetworks = true
}

resource "google_compute_firewall" "zero_inbound_fw" {
  name    = "malabar-watch-zero-inbound"
  network = google_compute_network.malabar_vpc.name

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}
```

---

## 4. Keyless Automated CI/CD Pipeline (GitHub Actions)

Deployments are automated via `.github/workflows/deploy.yml`:
1. Push to `main` branch triggers unit tests (`pytest`).
2. On test success, GitHub Actions authenticates with GCP via **OpenID Connect (OIDC)** Workload Identity Federation.
3. Syncs codebase (`rsync` / `git pull`), restarts `systemd` service cleanly.
