# ================================================================
#  startup.py  —  Pre-flight environment validation
#  Called once at app boot. Exits with a clear error message
#  instead of letting the app crash mid-request.
# ================================================================

import os
import sys
import logging

logger = logging.getLogger(__name__)


def validate_env() -> None:
    """Hard-fail on missing critical vars; warn on weak values."""

    # ── Hard requirements ────────────────────────────────────────
    missing = [k for k in ("SECRET_KEY", "DATABASE_URL") if not os.environ.get(k)]
    if missing:
        logger.critical(
            "FATAL — Required environment variable(s) not set: %s  "
            "Set them in .env (local) or the Render dashboard (production).",
            ", ".join(missing),
        )
        sys.exit(1)

    # ── Strength warnings (don't exit — warn loudly) ─────────────
    secret = os.environ.get("SECRET_KEY", "")
    if len(secret) < 32:
        logger.warning(
            "SECRET_KEY is shorter than 32 chars — use a random hex string: "
            "python3 -c \"import secrets; print(secrets.token_hex(32))\""
        )

    for weak in ("admin123", "admin", "password", "123456", "changeme"):
        if os.environ.get("ADMIN_PASSWORD", "") == weak:
            logger.warning(
                "ADMIN_PASSWORD is set to a well-known default ('%s'). "
                "Change it before going to production.",
                weak,
            )
            break

    if not os.environ.get("ADMIN_USERNAME"):
        logger.warning("ADMIN_USERNAME not set — defaulting to 'admin'.")
    if not os.environ.get("ADMIN_PASSWORD"):
        logger.warning("ADMIN_PASSWORD not set — defaulting to 'admin123'. Change this!")
