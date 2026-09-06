# The Complete Beginner's Cloud Guide: AWS, Terraform & Production AI Deployment

> 💡 **Why this guide exists:** Most AI portfolio projects only run on a local Jupyter Notebook or laptop terminal. By deploying **Malabar Watch** on the cloud using **Infrastructure as Code (Terraform)** and an **Enterprise Zero-Trust Security Model (AWS SSM)**, you immediately differentiate yourself to tech leads, engineering managers, and recruiters hiring for **AI Engineer, LLMOps, and Applied AI** roles.

---

## 📚 1. Core Cloud Concepts Explained Simply

If you are new to cloud computing, here is the plain-English translation of every tool we use:

| Term | What is it? | Real-World Analogy |
| :--- | :--- | :--- |
| **AWS (Amazon Web Services)** | A cloud provider that rents computing servers, storage, and networking globally. | A giant digital utility company where you rent computers by the second instead of buying physical hardware. |
| **EC2 (Elastic Compute Cloud)** | A virtual computer (Virtual Machine or VM) running Linux in an Amazon data center. | A desktop computer without a monitor or keyboard, located in Amazon's Mumbai data center. |
| **AWS Free Tier** | Amazon gives new accounts 750 hours/month of free `t2.micro` or `t3.micro` Linux servers for 12 months. | Free 24/7 server hosting for your project (₹0 / month). |
| **Terraform (IaC)** | **Infrastructure as Code**: A tool where you write your server setup in a text file (`.tf`), and Terraform automatically creates the server, networking, and firewalls on AWS with 1 command. | A 3D printer for cloud infrastructure: instead of clicking 50 buttons in the AWS console, you describe the machine in code. |
| **AWS SSM (Systems Manager)** | A secure, keyless way to connect to your Linux server directly from your browser or terminal without needing open ports or SSH `.pem` keys. | A private, encrypted tunnel directly into your server that hacker bots on the internet cannot even see. |
| **Security Group** | An AWS virtual firewall controlling what network traffic can reach your EC2 server. | A security guard at the gate of your building. In our setup, the guard blocks **ALL** inbound visitors from the outside internet. |
| **Linux Swap** | A file on disk that the operating system uses as extra emergency RAM when physical memory gets tight. | An emergency overflow tank for memory to prevent applications from crashing. |
| **Systemd** | The Linux system process manager that keeps applications running 24/7, restarts them if they crash, and triggers scheduled tasks. | A supervisor that makes sure your bot is always alive and runs your hourly weather checks like clockwork. |

---

## 🎯 2. Why This Architecture Wows AI Hiring Managers

When senior AI engineers or CTOs review candidate GitHub profiles, they see hundreds of repositories that just call `openai.ChatCompletion.create()` inside a script that terminates when closed.

Here is what **Malabar Watch** proves about your skills:

1. **Autonomous Reliability (Not Just a Script):** You understand how to turn an AI script into an **autonomous system daemon** that runs unattended 24/7 using Linux `systemd` timers.
2. **Modern MLOps / Cloud IaC:** You don't configure servers by clicking buttons manually; you write **reproducible Terraform configurations**.
3. **Enterprise Zero-Trust Security:** You don't leave vulnerable SSH port 22 open to brute-force attacks. You use **AWS Systems Manager (SSM) Session Manager**, which is the gold standard used by enterprise security teams at Fortune 500 companies.
4. **Cost Engineering / Resource Optimization:** You engineered a system that runs a dual-LLM pipeline on a 1 GB RAM machine with 2 GB Swap at **₹0/month cost**.
5. **Observability & Resilience:** You implemented centralized rotating logs, multi-provider API failovers (Gemini $\to$ Groq $\to$ Template), and real-time subscriber delivery audits.

---

## 🛠️ 3. Prerequisites & One-Time Setup

You only need two free tools installed on your computer to deploy:
1. **AWS CLI** (Command Line Interface)
2. **Terraform CLI**

### Step 3.1: Create a Free AWS Account
1. Visit [aws.amazon.com/free](https://aws.amazon.com/free/) and sign up for a free account.
2. Choose the **Free Tier** (includes 12 months free of EC2 `t2.micro` or `t3.micro`).

### Step 3.2: Create an IAM User for Deployment
1. Log in to the [AWS Management Console](https://console.aws.amazon.com/).
2. In the top search bar, search for **IAM** (Identity and Access Management).
3. Click **Users** ➔ **Create user**.
4. Name the user: `malabar-deployer`.
5. Under **Permissions options**, select **Attach policies directly**.
6. Check **AdministratorAccess** (for automated Terraform provisioning) ➔ Click **Next** ➔ **Create user**.
7. Click on your newly created user `malabar-deployer` ➔ Open the **Security credentials** tab.
8. Scroll to **Access keys** ➔ Click **Create access key** ➔ Select **Command Line Interface (CLI)**.
9. Copy your **Access Key ID** and **Secret Access Key**. *(Save them securely!)*

### Step 3.3: Install the AWS CLI & Configure Credentials
If you do not have AWS CLI installed, install it via PowerShell:
```powershell
# In PowerShell (or download from https://aws.amazon.com/cli/)
winget install Amazon.AWSCLI
```

Once installed, run:
```bash
aws configure
```
Fill in the prompt:
- **AWS Access Key ID**: Paste your Access Key
- **AWS Secret Access Key**: Paste your Secret Key
- **Default region name**: `ap-south-1` *(Mumbai region for lowest latency to Kerala)*
- **Default output format**: `json`

### Step 3.4: Install Terraform
In PowerShell:
```powershell
winget install Hashicorp.Terraform
```
Verify installation:
```bash
terraform version
```

---

## 🚀 4. Step-by-Step Deployment Guide (Using Terraform)

All cloud infrastructure is packaged in the `terraform/` directory of this repository.

### Step 4.1: Review Terraform Configuration
Navigate to `terraform/`:
- `main.tf`: Configures the AWS provider in `ap-south-1` (Mumbai), an IAM Role for SSM Session Manager, an EC2 instance (`t3.micro` or `t2.micro`), a 30 GB gp3 volume, and a Security Group with **zero inbound ports**.
- `variables.tf`: Contains default settings (region, instance type, tags).
- `user_data.sh`: A startup script that runs automatically when the EC2 instance launches. It installs Python 3.12, `uv`, Git, enables a 2 GB Swap file, clones your repository, and sets up `systemd` services.

### Step 4.2: Initialize Terraform
In your terminal, navigate to the `terraform` folder:
```bash
cd terraform
terraform init
```
*What this does:* Downloads the official AWS cloud provider plugin for Terraform.

### Step 4.3: Preview the Plan
Run:
```bash
terraform plan
```
*What this does:* Terraform compares your code against your AWS account and prints an exact list of resources it will create (1 EC2 instance, 1 Security Group, 1 IAM Role, 1 Instance Profile).

### Step 4.4: Apply the Plan (Launch Your Cloud Server!)
Run:
```bash
terraform apply
```
Type `yes` when prompted.

In ~45 seconds, Terraform will complete and print output like:
```text
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:
instance_id = "i-0abc123456789def0"
ssm_connect_command = "aws ssm start-session --target i-0abc123456789def0"
```

---

## 🔐 5. How to Connect to Your Server (No SSH Keys Needed!)

Because our server uses **Zero Inbound Ports**, port 22 (SSH) is blocked. Instead, we connect using **AWS Systems Manager (SSM)**:

### Option A: From AWS Console (Browser)
1. Open the [AWS EC2 Console](https://ap-south-1.console.aws.amazon.com/ec2/).
2. Select your instance (`malabar-watch-agent`).
3. Click **Connect** at the top.
4. Select the **Session Manager** tab ➔ Click **Connect**.
5. A secure Linux terminal opens directly in your browser!

### Option B: From Your Local Terminal
Simply run the output command generated by Terraform:
```bash
aws ssm start-session --target <YOUR_INSTANCE_ID>
```

---

## ⚙️ 6. Configuring Your Secrets on the Cloud Server

Once connected to your EC2 instance via SSM:

1. Switch to the `malabarwatch` application user:
   ```bash
   sudo su - malabarwatch
   cd /opt/malabar_watch
   ```

2. Create the production `.env` file:
   ```bash
   nano .env
   ```
   Paste your real API keys:
   ```env
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   DATABASE_URL=sqlite:////opt/malabar_watch/data/malabar_watch.sqlite
   ```
   Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit.

   Lock down `.env` file permissions (security hardening):
   ```bash
   chmod 600 .env
   ```

3. Install and enable the systemd services:
   ```bash
   # Exit back to root
   exit

   # Copy systemd unit definitions
   sudo cp /opt/malabar_watch/systemd/malabar-watch-bot.service /etc/systemd/system/
   sudo cp /opt/malabar_watch/systemd/malabar-watch-pipeline.service /etc/systemd/system/
   sudo cp /opt/malabar_watch/systemd/malabar-watch-pipeline.timer /etc/systemd/system/
   sudo systemctl daemon-reload

   # Start the 24/7 Telegram bot daemon
   sudo systemctl start malabar-watch-bot
   sudo systemctl enable malabar-watch-bot

   # Start the autonomous hourly weather checking timer
   sudo systemctl start malabar-watch-pipeline.timer
   sudo systemctl enable malabar-watch-pipeline.timer
   ```

---

## 📊 7. Monitoring & Verifying Your Cloud Agent

### Check Bot Status
```bash
sudo systemctl status malabar-watch-bot
```
You should see: `Active: active (running)`.

### View Live Bot Logs (Journalctl)
```bash
sudo journalctl -u malabar-watch-bot -f
```
You will see live messages as users interact with the bot from Telegram!

### Check Next Scheduled Hourly Execution
```bash
sudo systemctl list-timers malabar-watch-pipeline.timer
```
Shows the exact time of the next automatic rainfall check.

### Test On-Demand Execution
```bash
sudo systemctl start malabar-watch-pipeline.service
sudo journalctl -u malabar-watch-pipeline.service -n 50
```

---

## 🧹 8. How to Tear Down (When You're Done)

If you ever want to shut down and delete all cloud resources to ensure zero accidental costs:
```bash
cd terraform
terraform destroy
```
Type `yes`. Terraform will cleanly delete the EC2 instance, security group, and IAM roles in ~30 seconds.

---

## 💼 9. AI Engineer Interview Cheatsheet: What to Say

When an interviewer or hiring manager asks:
> *"Tell me about a complex project you built and how you took it to production."*

### Your 2-Minute Answer:
> *"I built **Malabar Watch**, an autonomous AI rainfall and landslide early-warning agent for high-risk monsoon regions in Kerala.*
> 
> *Instead of treating AI as just a prompt in a notebook, I designed a resilient production pipeline:*
> 1. *First, data ingestion polls high-resolution Open-Meteo precipitation metrics every hour and computes rolling Antecedent Precipitation Indices (API) to model soil saturation.*
> 2. *Second, risk evaluation is strictly deterministic — I didn't delegate life-safety geotechnical threshold math to LLMs to prevent hallucinations.*
> 3. *Third, for advisory synthesis, I built a zero-downtime Dual-LLM Gateway: Google Gemini is primary, with automatic sub-second failover to Groq LLaMA-3.3-70B on rate limits, and a deterministic template fallback.*
> 4. *Fourth, for distribution, I developed a long-polling bilingual Telegram bot delivering plain-language English and Malayalam warnings.*
> 5. *Finally, for cloud deployment, I provisioned an AWS EC2 instance in Mumbai using Terraform Infrastructure-as-Code. To meet enterprise zero-trust standards, I used a security group with zero inbound ports and managed the instance keylessly via AWS SSM Session Manager, while Linux systemd timers govern hourly autonomous executions under a ₹0/month Free Tier budget."*

### Why this response wins:
- It shows you understand **safety-critical AI engineering** (deterministic math vs generative empathy).
- It shows you understand **fault tolerance** (LLM gateway failover).
- It demonstrates **production DevOps/MLOps skills** (Terraform, systemd, Zero-Trust AWS SSM).
- It proves **end-to-end capability** from data ingestion to cloud infrastructure.
