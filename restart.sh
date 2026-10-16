#!/usr/bin/env bash
set -euo pipefail
# Restart only this deployment; never kill unrelated Python processes.
systemctl restart holderbot-pasarguard.target
systemctl --no-pager status holderbot-pasarguard.target
