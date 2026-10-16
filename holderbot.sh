#!/usr/bin/env bash
set -euo pipefail
umask 077
[[ "$(id -u)" == 0 ]] || { echo "Run as root."; exit 1; }
target=/root/holderbot-pasarguard
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-dev git build-essential
if [[ -e "$target" ]]; then
    [[ -d "$target/.git" && -f "$target/setup_pasarguard.py" ]] || {
        echo "Existing installation preserved. Follow PASARGUARD_MIGRATION.md; no files were removed."
        exit 1
    }
else
    git clone https://github.com/sirvan1133/holderbot.git "$target"
fi
cd "$target"
python3 -m venv hold
hold/bin/python -m pip install -r requirements.txt
hold/bin/python setup_pasarguard.py
install -m 644 deploy/holderbot-pasarguard@.service /etc/systemd/system/
install -m 644 deploy/holderbot-pasarguard.target /etc/systemd/system/
systemctl daemon-reload
systemctl enable holderbot-pasarguard.target
systemctl restart holderbot-pasarguard.target
echo "Started. Logs: journalctl -u 'holderbot-pasarguard@*' -f"
