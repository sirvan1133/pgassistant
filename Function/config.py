"""Deployment-specific settings; never commit real credentials."""
import os

TELEGRAM_API_ID = int(os.environ.get("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
# Opt out only for an intentionally self-signed panel on a trusted network.
PANEL_VERIFY_TLS = os.environ.get("PANEL_VERIFY_TLS", "true").lower() not in {
    "0", "false", "no", "off"
}
