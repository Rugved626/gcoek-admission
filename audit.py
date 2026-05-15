# ================================================================
#  audit.py  —  Structured audit trail helpers
#  Writes to the audit_logs table.  Never stores passwords or
#  full bank account numbers.
# ================================================================

import logging
from database import get_db

logger = logging.getLogger(__name__)

# Action constants — use these everywhere for consistency
A_STUDENT_REGISTER     = "student_register"
A_STUDENT_LOGIN_OK     = "student_login_ok"
A_STUDENT_LOGIN_FAIL   = "student_login_fail"
A_ADMIN_LOGIN_OK       = "admin_login_ok"
A_ADMIN_LOGIN_FAIL     = "admin_login_fail"
A_APP_SUBMIT           = "application_submit"
A_APP_UPDATE           = "application_update"
A_APP_APPROVE          = "application_approve"
A_APP_REJECT           = "application_reject"
A_APP_DELETE           = "application_delete"
A_EXPORT               = "data_export"
A_REAUTH_OK            = "reauth_ok"
A_REAUTH_FAIL          = "reauth_fail"
A_SUSPICIOUS           = "suspicious_activity"


def log_action(action: str, actor: str = None, ip: str = None,
               target_id: int = None, detail: str = None):
    """
    Write one row to audit_logs.
    Failures are logged to stderr but never raise — audit must not
    crash the main request.
    """
    try:
        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO audit_logs (action, actor, ip_address, target_id, detail)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (action, actor, ip, target_id, detail)
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()
    except Exception as exc:
        logger.error("Audit log write failed: %s", exc)
