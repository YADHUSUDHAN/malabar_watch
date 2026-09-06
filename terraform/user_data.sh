#!/usr/bin/env bash
# ==============================================================================
# Cloud-Init User Data Script - Malabar Watch Production Deployment
# Runs automatically as root on initial EC2 instance provisioning
# ==============================================================================

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "==> [1/6] Configuring 2 GB Linux Swap Memory to prevent OOM..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.d/99-swappiness.conf
fi

echo "==> [2/6] Updating Ubuntu packages and installing core tools..."
apt-get update -y
apt-get install -y \
    curl \
    git \
    sqlite3 \
    python3 \
    python3-pip \
    python3-venv \
    ca-certificates

echo "==> [3/6] Ensuring AWS Systems Manager (SSM) Agent is active..."
# On official Ubuntu AMIs, SSM Agent is pre-installed. Ensure it is started reliably:
if ! systemctl is-active --quiet snap.amazon-ssm-agent.amazon-ssm-agent.service && ! systemctl is-active --quiet amazon-ssm-agent; then
    snap install amazon-ssm-agent --classic 2>/dev/null || apt-get install -y amazon-ssm-agent 2>/dev/null || true
fi
systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null || systemctl enable amazon-ssm-agent 2>/dev/null || true
systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null || systemctl start amazon-ssm-agent 2>/dev/null || true

echo "==> [4/6] Installing uv package manager..."
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh
chmod +x /usr/local/bin/uv || true

echo "==> [5/6] Setting up application user and directories..."
if ! id "malabarwatch" &>/dev/null; then
    useradd -m -d /opt/malabar_watch -s /bin/bash malabarwatch
fi

mkdir -p /opt/malabar_watch/data
mkdir -p /opt/malabar_watch/logs
chown -R malabarwatch:malabarwatch /opt/malabar_watch
git config --system --add safe.directory /opt/malabar_watch

echo "==> [6/6] Cloud initialization complete! Server ready for code deployment."
