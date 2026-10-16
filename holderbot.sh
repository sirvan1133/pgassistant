#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ "$(id -u)" != 0 ]]; then
    echo "Please run as root."
    exit 1
fi

target="/root/holderbot"
legacy_dir="/root/holderbot"

echo "=== PG Assistant PasarGuard Installer & Updater ==="

# 1. Stop any running legacy or current holderbot processes
echo "Stopping any existing bot processes..."
pkill -f "holder.py" || true
pkill -f "monitoring.py" || true
pkill -f "limiteder.py" || true
pkill -f "expired.py" || true
pkill -f "reseter.py" || true
systemctl stop 'holderbot*' || true
systemctl stop 'holderbot-pasarguard*' || true

# 2. Backup existing databases and private files if present
backup_dir="/root/holderbot_backup_$(date +%Y%m%d%H%M%S)"
has_existing=0

if [[ -d "$target" ]]; then
    mkdir -p "$backup_dir"
    for f in holder.db reset.db *.session *.session-journal; do
        if compgen -G "$target/$f" > /dev/null; then
            cp -a "$target"/$f "$backup_dir/" || true
            has_existing=1
        fi
    done
    if [[ -f "/etc/holderbot-pasarguard.env" ]]; then
        cp -a /etc/holderbot-pasarguard.env "$backup_dir/" || true
    fi
    if [[ $has_existing -eq 1 ]]; then
        echo "Preserved existing database/session files in $backup_dir"
    fi
fi

# 3. Install packages
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-dev git build-essential libjpeg-dev

# 4. Clone or update repository
if [[ -d "$target/.git" ]]; then
    echo "Updating existing repository at $target..."
    git -C "$target" fetch origin
    git -C "$target" reset --hard origin/main
else
    if [[ -d "$target" ]]; then
        mv "$target" "${target}_old_$(date +%Y%m%d%H%M%S)"
    fi
    echo "Cloning repository to $target..."
    git clone https://github.com/sirvan1133/pgassistant.git "$target"
fi

# 5. Restore databases if we backed them up
if [[ $has_existing -eq 1 ]]; then
    echo "Restoring existing database files into $target..."
    cp -a "$backup_dir"/* "$target/" 2>/dev/null || true
fi

cd "$target"

# 6. Python virtualenv
echo "Setting up Python environment..."
python3 -m venv hold
hold/bin/python -m pip install --upgrade pip
hold/bin/python -m pip install -r requirements.txt

# 7. Run setup (it automatically preserves holder.db if already exists!)
hold/bin/python setup_pasarguard.py

# 8. Setup Systemd services
# Adjust service template working directory to /root/holderbot
cat << 'EOF' > /etc/systemd/system/holderbot@.service
[Unit]
Description=PG Assistant PasarGuard Service %i
After=network-online.target
Wants=network-online.target
PartOf=holderbot.target

[Service]
Type=simple
WorkingDirectory=/root/holderbot
ExecStart=/root/holderbot/hold/bin/python /root/holderbot/%i.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/holderbot-pasarguard.env
UMask=0077

[Install]
WantedBy=multi-user.target
EOF

cat << 'EOF' > /etc/systemd/system/holderbot.target
[Unit]
Description=PG Assistant PasarGuard Target
Wants=holderbot@holder.service holderbot@monitoring.service holderbot@limiteder.service holderbot@expired.service holderbot@reseter.service

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable holderbot.target
systemctl restart holderbot.target

echo "=========================================="
echo "PG Assistant PasarGuard successfully installed/updated!"
echo "Status check: systemctl status 'holderbot@*'"
echo "Logs: journalctl -u 'holderbot@*' -f"
echo "=========================================="
