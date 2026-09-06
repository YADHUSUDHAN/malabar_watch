# Feature Spec: Autonomous Systemd Scheduler, Monitoring & Zero-Trust AWS Deployment

- **Spec ID**: `SPEC-005`
- **Status**: Proposed
- **Owner**: Malabar Watch Engineering
- **Target Release**: `v0.1.0`
- **Dependencies**: `SPEC-001`, `SPEC-002`, `SPEC-003`, `SPEC-004`, `AWS EC2 Free Tier`, `Terraform`

---

## 1. Overview & Business Intent

To function as a true real-world early-warning system, **Malabar Watch must run autonomously 24/7/365 without manual developer intervention**. If heavy monsoon rains hit Wayanad or Idukki at 3:00 AM, the agent must awaken, poll rainfall, evaluate landslide thresholds, generate bilingual warnings, and broadcast alerts to residents without anyone sitting at a laptop.

**`SPEC-005`** defines the production hosting, automated scheduling, self-healing watchdog supervision, and Infrastructure-as-Code (Terraform) deployment on the **AWS EC2 Free Tier (`t2.micro`/`t3.micro`, `ap-south-1` Mumbai)** at **₹0 / month cost**.

---

## 2. Production Deployment Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AWS Cloud (ap-south-1 Mumbai Region)                     │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ AWS Default VPC (Public Subnet)                                       │  │
│  │                                                                       │  │
│  │   Security Group (Zero Inbound Rules):                                │  │
│  │   - Inbound: NONE (0.0.0.0/0 Blocked, No Port 22 SSH, No Port 80/443)  │  │
│  │   - Outbound: All Traffic Allowed (HTTPS port 443)                    │  │
│  │                                                                       │  │
│  │   ┌───────────────────────────────────────────────────────────────┐   │  │
│  │   │ EC2 Instance: t2.micro / t3.micro (Ubuntu 24.04 LTS)          │   │  │
│  │   │ IAM Instance Profile: AmazonSSMManagedInstanceCore            │   │  │
│  │   │                                                               │   │  │
│  │   │  RAM: 1 GB Physical + 2 GB Swap File (Prevents OOM)           │   │  │
│  │   │  Storage: 30 GB EBS gp3 Root Volume                           │   │  │
│  │   │                                                               │   │  │
│  │   │  ┌─────────────────────────────────────────────────────────┐  │   │  │
│  │   │  │ Systemd Supervisors:                                    │  │   │  │
│  │   │  │  1. malabar-watch-bot.service (Bot Daemon, Polling)     │  │   │  │
│  │   │  │  2. malabar-watch-pipeline.timer (Hourly Trigger)       │  │   │  │
│  │   │  │  3. malabar-watch-pipeline.service (Ingest->Risk->LLM)  │  │   │  │
│  │   │  └─────────────────────────────────────────────────────────┘  │   │  │
│  │   └───────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────▲────────────────────────────────────┘  │
│                                     │                                       │
│                       AWS SSM Session Manager                               │
│              (Secure Web Shell / CLI without SSH Keys)                      │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
                         Developer / Administrator
```

---

## 3. Core Architectural Pillars

### 3.1 Zero-Trust Keyless Security (AWS Systems Manager)
- **No Open SSH Port (Port 22)**: Traditional EC2 instances expose port 22, making them targets for automated internet botnet brute-force scans.
- **SSM Session Manager**: Remote access is authenticated cryptographically via AWS IAM roles (`AmazonSSMManagedInstanceCore`). Access is granted through the AWS Console or `aws ssm start-session` without needing `.pem` private keys or inbound firewall holes.

### 3.2 Linux Swap Memory Hardening (1 GB RAM + 2 GB Swap)
- Free Tier `t2.micro` instances provide 1 GB RAM. Python package installations and LLM JSON parsing can cause transient memory spikes.
- Automated `cloud-init` user-data script provisions a **2 GB Swap file** (`/swapfile`) with `swappiness=10`, guaranteeing zero Out-Of-Memory (OOM) kernel kills.

### 3.3 Autonomous Scheduling via Systemd Timers
Rather than running an unreliable infinite `while True: sleep(3600)` loop inside Python:
1. **`malabar-watch-bot.service`**: Always-on daemon supervised with `Restart=always` and `RestartSec=10s`.
2. **`malabar-watch-pipeline.timer`**: Triggers hourly on the hour (`*:00:00`) with persistent state catch-up if the server reboots.
3. **`malabar-watch-pipeline.service`**: One-shot execution running `malabar-watch --run-pipeline`.

### 3.4 Observability & Self-Healing
- **Journalctl Logging**: All standard output and error streams are captured natively by `systemd-journald`.
- **Log Rotation**: Automated application log rotation via `logging.handlers.RotatingFileHandler` (5 MB max, 5 backups).
- **Health Check Command**: `malabar-watch status` provides instantaneous diagnostics of database size, last observation time, and active subscriber count.

---

## 4. Infrastructure-as-Code (Terraform Specifications)

### Files under `terraform/`:
- `main.tf`: AWS provider (`ap-south-1`), VPC lookup, Security Group (zero inbound), IAM role for SSM, EC2 instance with user-data script.
- `variables.tf`: Configurable parameters (instance type, AWS region, project tag, disk size).
- `outputs.tf`: Instance ID, Public IP (for reference), SSM connect command.
- `user_data.sh`: Bash script executing on initial boot:
  - Updates Ubuntu packages
  - Sets up 2 GB swapfile
  - Installs Python 3.12, `uv`, Git, SQLite3
  - Installs AWS SSM Agent
  - Clones repository and installs Python dependencies
  - Installs and enables `systemd` units

---

## 5. Acceptance Criteria

- [ ] **AC-1 (Infrastructure as Code)**: Complete Terraform configuration runs `terraform plan` and `terraform apply` cleanly.
- [ ] **AC-2 (Zero Inbound Rules)**: Security group contains 0 inbound rules (`0.0.0.0/0` blocked).
- [ ] **AC-3 (Keyless SSM Access)**: Instance registers with AWS SSM; connects via AWS Systems Manager Session Manager.
- [ ] **AC-4 (Systemd Supervised Bot)**: `malabar-watch-bot.service` runs in the background and automatically restarts on failure.
- [ ] **AC-5 (Systemd Hourly Pipeline Timer)**: `malabar-watch-pipeline.timer` fires hourly and executes end-to-end early warning cycles.
- [ ] **AC-6 (Portfolio Guide Documentation)**: Step-by-step beginner guide explaining cloud concepts, Terraform, deployment steps, and AI role interview talking points.
