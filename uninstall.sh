#!/usr/bin/env bash
set -euo pipefail
systemctl disable --now holderbot-pasarguard.target
for component in holder monitoring expired limiteder reseter; do
    systemctl stop "holderbot-pasarguard@${component}.service"
done
echo "PG Assistant stopped and autostart disabled."
echo "Code, databases, sessions and /etc/holderbot-pasarguard.env are preserved for recovery."
echo "This does not delete users or change the PasarGuard panel."
