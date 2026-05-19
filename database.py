# ================================================================
#  database.py  —  PostgreSQL connection, schema init, indexes
#  • psycopg2 + RealDictCursor
#  • Connection retry with exponential back-off (Render restart)
#  • Automatic rollback on any exception
#  • All tables + indexes created idempotently on startup
# ================================================================

import os
import time
import logging
import psycopg
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ── Resolve URL once ─────────────────────────────────────────────

def _resolve_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Add it to .env (local) or the Render dashboard (production)."
        )
    # Render free-tier emits 'postgres://' which psycopg2 rejects
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


# ── Connection (with retry) ──────────────────────────────────────

def get_db(retries: int = 3, delay: float = 1.0):
    """
    Return a fresh psycopg2 connection.
    Retries up to `retries` times on OperationalError (e.g. cold
    start after Render spin-down) with exponential back-off.
    Caller is responsible for .commit() and .close().
    """
    url      = _resolve_url()
    last_exc = None

    for attempt in range(1, retries + 1):
        try:
            return psycopg2.connect(
                url,
                cursor_factory=psycopg2.extras.RealDictCursor,
                connect_timeout=10,
            )
        except psycopg2.OperationalError as exc:
            last_exc = exc
            logger.warning("DB connect attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay * attempt)          # 1 s, 2 s, 3 s …

    raise last_exc


# ── Safe single-statement helper ─────────────────────────────────

def _run(conn, sql: str, params=None) -> None:
    """Execute one statement; rolls back conn on failure."""
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


# ── Schema + indexes ─────────────────────────────────────────────

def init_db() -> None:
    """
    Idempotent schema bootstrap.  Safe to call on every restart.
    Creates tables, runs safe ALTER migrations, then creates indexes.
    """
    conn = get_db()
    try:

        # ── students ──────────────────────────────────────────────
        _run(conn, """
            CREATE TABLE IF NOT EXISTS students (
                id         SERIAL       PRIMARY KEY,
                username   VARCHAR(100) UNIQUE NOT NULL,
                password   VARCHAR(255) NOT NULL,
                created_at TIMESTAMPTZ  DEFAULT NOW()
            );
        """)

        # ── applications ─────────────────────────────────────────
        _run(conn, """
            CREATE TABLE IF NOT EXISTS applications (
                id                          SERIAL       PRIMARY KEY,
                student_id                  INTEGER      UNIQUE NOT NULL
                                                REFERENCES students(id) ON DELETE CASCADE,
                status                      VARCHAR(20)  DEFAULT 'Pending',
                rejection_reason            TEXT,

                full_name                   VARCHAR(200),
                email                       VARCHAR(200),
                bank_account_number         VARCHAR(60),
                ifsc_code                   VARCHAR(20),
                branch                      VARCHAR(120),
                caste                       VARCHAR(100),
                category                    VARCHAR(20),
                gender                      VARCHAR(20),

                student_mobile              VARCHAR(15),
                parent_mobile               VARCHAR(15),
                local_address               TEXT,
                permanent_address           TEXT,

                cet_application_number      VARCHAR(60),
                prn_number                  VARCHAR(60),
                admission_taking_year       VARCHAR(20),
                year_transition             VARCHAR(30),
                admission_receipt           VARCHAR(120),
                first_year_credits          INTEGER,
                second_year_credits         INTEGER,
                third_year_credits          INTEGER,
                total_credits               INTEGER,

                applied_for_scholarship     VARCHAR(10),
                income_certificate_number   VARCHAR(120),
                actual_income               VARCHAR(60),
                scholarship_registration_no VARCHAR(120),
                scholarship_reg_year1       VARCHAR(60),
                scholarship_reg_year2       VARCHAR(60),
                scholarship_reg_year3       VARCHAR(60),
                scholarship_id              VARCHAR(120),
                custom_scheme_name          VARCHAR(255),

                created_at  TIMESTAMPTZ DEFAULT NOW(),
                updated_at  TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # ── audit_logs ────────────────────────────────────────────
        _run(conn, """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id         SERIAL      PRIMARY KEY,
                timestamp  TIMESTAMPTZ DEFAULT NOW(),
                ip_address VARCHAR(45),
                action     VARCHAR(80) NOT NULL,
                actor      VARCHAR(100),
                target_id  INTEGER,
                detail     TEXT
            );
        """)

        # ── Safe column migrations ────────────────────────────────
        for migration in [
            "ALTER TABLE applications ADD COLUMN IF NOT EXISTS custom_scheme_name VARCHAR(255);",
            "ALTER TABLE students     ALTER COLUMN password TYPE VARCHAR(255);",
        ]:
            _run(conn, migration)

        # ── Performance indexes ───────────────────────────────────
        for idx in [
            "CREATE INDEX IF NOT EXISTS idx_apps_student_id ON applications(student_id);",
            "CREATE INDEX IF NOT EXISTS idx_apps_status     ON applications(status);",
            "CREATE INDEX IF NOT EXISTS idx_apps_email      ON applications(email);",
            "CREATE INDEX IF NOT EXISTS idx_apps_branch     ON applications(branch);",
            "CREATE INDEX IF NOT EXISTS idx_apps_created_at ON applications(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_audit_actor     ON audit_logs(actor);",
            "CREATE INDEX IF NOT EXISTS idx_audit_action    ON audit_logs(action);",
            "CREATE INDEX IF NOT EXISTS idx_audit_ts        ON audit_logs(timestamp);",
        ]:
            _run(conn, idx)

        conn.commit()
        logger.info("Database schema, migrations and indexes verified.")

    except Exception as exc:
        conn.rollback()
        logger.critical("Database init FAILED: %s", exc)
        raise
    finally:
        conn.close()
