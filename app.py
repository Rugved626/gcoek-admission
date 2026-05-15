# ================================================================
#  app.py  —  GCE Kolhapur Admission Management System
#  Flask + PostgreSQL  |  Production-hardened v3
# ================================================================

import io, os, csv, hmac, logging
from datetime import timedelta
from functools import wraps

from flask import (Flask, render_template, request, redirect,
                   session, Response, abort, g, url_for)
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

# ── Pre-flight checks ────────────────────────────────────────────
from startup import validate_env
validate_env()

from database import get_db, init_db
from security import (
    hash_password, check_password,
    validate_signup, validate_application,
    sanitize_application_fields, sanitize_csv_value,
    mask_bank_account,
)
from audit import (
    log_action,
    A_STUDENT_REGISTER, A_STUDENT_LOGIN_OK, A_STUDENT_LOGIN_FAIL,
    A_ADMIN_LOGIN_OK, A_ADMIN_LOGIN_FAIL,
    A_APP_SUBMIT, A_APP_UPDATE, A_APP_APPROVE, A_APP_REJECT, A_APP_DELETE,
    A_EXPORT, A_REAUTH_OK, A_REAUTH_FAIL, A_SUSPICIOUS,
)

# ================================================================
#  LOGGING  (structured, ISO timestamp, no sensitive data)
# ================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ================================================================
#  APP SETUP
# ================================================================
app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")   # validated by startup.py

IS_PRODUCTION = os.environ.get("FLASK_ENV", "production") != "development"

app.config.update(
    # Session security
    SESSION_COOKIE_HTTPONLY    = True,
    SESSION_COOKIE_SECURE      = IS_PRODUCTION,   # HTTPS-only cookies in prod
    SESSION_COOKIE_SAMESITE    = "Lax",
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1),

    # CSRF
    WTF_CSRF_TIME_LIMIT        = 3600,
    WTF_CSRF_SSL_STRICT        = IS_PRODUCTION,

    # Disable caching of sensitive pages
    SEND_FILE_MAX_AGE_DEFAULT  = 0,
)

# ── CSRF ────────────────────────────────────────────────────────
csrf = CSRFProtect(app)

# ── Rate limiter ─────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=os.environ.get("LIMITER_STORAGE_URI", "memory://"),
)


# ================================================================
#  DATABASE INIT  (with full retry + rollback safety)
# ================================================================
with app.app_context():
    try:
        init_db()
    except Exception as exc:
        logger.critical("Database initialisation failed: %s", exc)
        raise


# ================================================================
#  HTTPS REDIRECT  (production only)
# ================================================================
@app.before_request
def enforce_https():
    """Redirect HTTP → HTTPS in production (Render sets X-Forwarded-Proto)."""
    if IS_PRODUCTION:
        proto = request.headers.get("X-Forwarded-Proto", "https")
        if proto == "http":
            url = request.url.replace("http://", "https://", 1)
            return redirect(url, code=301)

@app.before_request
def no_cache_sensitive():
    """Store user so we can reference it in after_request."""
    g.user = session.get("user")
    g.role = session.get("role")


# ================================================================
#  SECURITY HEADERS  (every response)
# ================================================================
@app.after_request
def set_security_headers(response):
    # Clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Referrer
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # HSTS — 2 years, include subdomains, preload
    response.headers["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains; preload"
    )
    # Permissions policy — disable unnecessary browser features
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=()"
    )
    # CSP — reduced unsafe-inline; inline styles still needed for Tailwind
    # All JavaScript is in external files — no inline JS needed
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' "
            "https://cdn.tailwindcss.com "
            "https://cdnjs.cloudflare.com; "
        "style-src 'self' "
            "https://fonts.googleapis.com "
            "https://cdn.tailwindcss.com "
            "'unsafe-inline'; "           # Tailwind requires this; JS inline removed
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    # Prevent browser caching on authenticated pages
    if g.get("user"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ================================================================
#  ROUTE DECORATORS
# ================================================================
def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "student":
            logger.warning("Unauthorized access to %s from %s", request.path, request.remote_addr)
            return redirect("/")
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            logger.warning("Unauthorized admin access to %s from %s", request.path, request.remote_addr)
            return redirect("/")
        return f(*args, **kwargs)
    return decorated


def reauth_required(f):
    """
    For critical admin actions: require re-entry of admin password
    within the last 5 minutes (stored as a session timestamp).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect("/")
        import time
        reauth_ts = session.get("reauth_ts", 0)
        if time.time() - reauth_ts > 300:   # 5 minutes
            # Store where to return after re-auth
            session["reauth_next"] = request.path
            return redirect("/admin/reauth")
        return f(*args, **kwargs)
    return decorated


# ================================================================
#  ERROR HANDLERS
# ================================================================
@app.errorhandler(CSRFError)
def handle_csrf(e):
    logger.warning("CSRF failure from %s: %s", request.remote_addr, e.description)
    return render_template("error.html", code=400,
        message="Your session has expired or the form token was invalid. "
                "Please go back and try again."), 400

@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, message="Bad request."), 400

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="Access denied."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404

@app.errorhandler(429)
def too_many(e):
    logger.warning("Rate limit hit from %s on %s", request.remote_addr, request.path)
    log_action(A_SUSPICIOUS, ip=request.remote_addr,
               detail=f"Rate limit triggered on {request.path}")
    return render_template("error.html", code=429,
        message="Too many requests. Your IP has been temporarily blocked. "
                "Please wait 15 minutes and try again."), 429

@app.errorhandler(500)
def server_error(e):
    logger.error("500 on %s: %s", request.path, e)
    return render_template("error.html", code=500,
        message="An unexpected server error occurred. Our team has been notified. "
                "Please try again in a few minutes."), 500


# ================================================================
#  HOME / LOGIN
# ================================================================
@app.route("/")
def index():
    if "user" in session:
        return redirect("/student-dashboard" if session.get("role") == "student"
                        else "/admin-dashboard")
    return render_template("login.html", error=None)


# ================================================================
#  SIGNUP
#  Rate limit: 5 registrations per hour per IP (anti-spam)
# ================================================================
@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def signup():
    if request.method == "POST":
        errors = validate_signup(request.form)
        if errors:
            return render_template("signup.html", error=" | ".join(errors))

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute("SELECT id FROM students WHERE username = %s", (username,))
            if cur.fetchone():
                return render_template("signup.html", error="Username already exists.")
            pw_hash = hash_password(password)
            cur.execute(
                "INSERT INTO students (username, password) VALUES (%s, %s)",
                (username, pw_hash)
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("Signup DB error: %s", exc)
            return render_template("signup.html", error="Registration failed. Please try again.")
        finally:
            cur.close()
            conn.close()

        logger.info("New student registered: %s from %s", username, request.remote_addr)
        log_action(A_STUDENT_REGISTER, actor=username, ip=request.remote_addr)
        return redirect("/")

    return render_template("signup.html", error=None)


# ================================================================
#  STUDENT LOGIN  — 10 attempts / 15 min per IP
# ================================================================
@app.route("/student-login", methods=["POST"])
@limiter.limit("10 per 15 minutes")
def student_login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return render_template("login.html", error="Please enter username and password.")

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT id, password FROM students WHERE username = %s", (username,))
        row = cur.fetchone()
    except Exception as exc:
        logger.error("DB error during student login: %s", exc)
        return render_template("login.html", error="Login unavailable. Please try again.")
    finally:
        cur.close()
        conn.close()

    def _fail():
        logger.warning("Failed student login: username='%s' ip=%s", username, request.remote_addr)
        log_action(A_STUDENT_LOGIN_FAIL, actor=username, ip=request.remote_addr)
        return render_template("login.html", error="Invalid credentials.")

    if not row:
        return _fail()

    stored = row["password"]
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        ok = check_password(password, stored)
    else:
        # Legacy plain-text; upgrade on success
        ok = (password == stored)
        if ok:
            new_hash = hash_password(password)
            try:
                uc = get_db()
                ucur = uc.cursor()
                ucur.execute("UPDATE students SET password=%s WHERE id=%s", (new_hash, row["id"]))
                uc.commit()
                ucur.close()
                uc.close()
            except Exception:
                pass
            logger.info("Upgraded password to bcrypt for '%s'", username)

    if not ok:
        return _fail()

    session.permanent = True
    session["user"] = username
    session["role"] = "student"
    logger.info("Student login ok: '%s' ip=%s", username, request.remote_addr)
    log_action(A_STUDENT_LOGIN_OK, actor=username, ip=request.remote_addr)
    return redirect("/student-dashboard")


# ================================================================
#  ADMIN LOGIN  — 10 attempts / 15 min per IP
# ================================================================
@app.route("/admin-login", methods=["POST"])
@limiter.limit("10 per 15 minutes")
def admin_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")

    user_ok = hmac.compare_digest(username, admin_user)
    pass_ok = hmac.compare_digest(password, admin_pass)

    if not (user_ok and pass_ok):
        logger.warning("Failed admin login from ip=%s", request.remote_addr)
        log_action(A_ADMIN_LOGIN_FAIL, actor=username, ip=request.remote_addr)
        return render_template("login.html", error="Invalid credentials.")

    session.permanent = True
    session["user"] = "admin"
    session["role"] = "admin"
    logger.info("Admin login ok from ip=%s", request.remote_addr)
    log_action(A_ADMIN_LOGIN_OK, actor="admin", ip=request.remote_addr)
    return redirect("/admin-dashboard")


# ================================================================
#  ADMIN RE-AUTH  (for critical actions)
# ================================================================
@app.route("/admin/reauth", methods=["GET", "POST"])
@admin_required
@limiter.limit("10 per 15 minutes")
def admin_reauth():
    if request.method == "POST":
        password = request.form.get("password", "")
        admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")

        if hmac.compare_digest(password, admin_pass):
            import time
            session["reauth_ts"] = time.time()
            log_action(A_REAUTH_OK, actor="admin", ip=request.remote_addr)
            next_url = session.pop("reauth_next", "/admin-dashboard")
            return redirect(next_url)
        else:
            log_action(A_REAUTH_FAIL, actor="admin", ip=request.remote_addr)
            return render_template("reauth.html", error="Incorrect password.")

    return render_template("reauth.html", error=None)


# ================================================================
#  LOGOUT
# ================================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================================================================
#  STUDENT DASHBOARD
# ================================================================
@app.route("/student-dashboard")
@student_required
def student_dashboard():
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT id FROM students WHERE username = %s", (session["user"],))
        student = cur.fetchone()
        if not student:
            return redirect("/logout")
        cur.execute("SELECT * FROM applications WHERE student_id = %s", (student["id"],))
        app_row = cur.fetchone()
    except Exception as exc:
        logger.error("Dashboard DB error: %s", exc)
        return render_template("error.html", code=500, message="Could not load your application."), 500
    finally:
        cur.close()
        conn.close()

    return render_template("student_dashboard.html",
                           application=dict(app_row) if app_row else None)


# ================================================================
#  SUBMIT / UPDATE APPLICATION
#  Rate limit: 20 per hour per IP (prevents rapid spam)
# ================================================================
@app.route("/submit-application", methods=["POST"])
@student_required
@limiter.limit("20 per hour")
def submit_application():
    errors = validate_application(request.form)
    if errors:
        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute("SELECT id FROM students WHERE username=%s", (session["user"],))
            student = cur.fetchone()
            cur.execute("SELECT * FROM applications WHERE student_id=%s", (student["id"],))
            existing = cur.fetchone()
        finally:
            cur.close()
            conn.close()
        return render_template("student_dashboard.html",
                               application=dict(existing) if existing else None,
                               form_errors=errors), 422

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT id FROM students WHERE username=%s", (session["user"],))
        student    = cur.fetchone()
        student_id = student["id"]

        fields = sanitize_application_fields(request.form, student_id)

        cur.execute("SELECT id FROM applications WHERE student_id=%s", (student_id,))
        existing = cur.fetchone()

        if existing:
            action = A_APP_UPDATE
            set_parts = [f"{k} = %s" for k in fields if k != "student_id"]
            values    = [v for k, v in fields.items() if k != "student_id"]
            values.append(student_id)
            cur.execute(
                f"UPDATE applications SET {', '.join(set_parts)}, updated_at = NOW() "
                f"WHERE student_id = %s",
                values
            )
        else:
            action = A_APP_SUBMIT
            cols    = ", ".join(fields.keys())
            holders = ", ".join(["%s"] * len(fields))
            cur.execute(
                f"INSERT INTO applications ({cols}) VALUES ({holders})",
                list(fields.values())
            )

        conn.commit()

        # Get the application id for audit
        cur.execute("SELECT id FROM applications WHERE student_id=%s", (student_id,))
        app_row = cur.fetchone()
        log_action(action, actor=session["user"], ip=request.remote_addr,
                   target_id=app_row["id"] if app_row else None)

    except Exception as exc:
        conn.rollback()
        logger.error("Application submit DB error: %s", exc)
        return render_template("error.html", code=500,
                               message="Could not save application. Please try again."), 500
    finally:
        cur.close()
        conn.close()

    return redirect("/student-dashboard")


# ================================================================
#  ADMIN DASHBOARD
# ================================================================
@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT * FROM applications ORDER BY id DESC")
        rows = [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        logger.error("Admin dashboard DB error: %s", exc)
        rows = []
    finally:
        cur.close()
        conn.close()

    return render_template("admin_dashboard.html", applications=rows)


# ================================================================
#  ADMIN — APPROVE
# ================================================================
@app.route("/approve/<int:app_id>", methods=["POST"])
@admin_required
@limiter.limit("60 per hour")
def approve(app_id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE applications SET status='Approved', rejection_reason=NULL WHERE id=%s",
            (app_id,)
        )
        conn.commit()
        log_action(A_APP_APPROVE, actor="admin", ip=request.remote_addr, target_id=app_id)
        logger.info("Admin approved application #%d", app_id)
    except Exception as exc:
        conn.rollback()
        logger.error("Approve DB error: %s", exc)
    finally:
        cur.close()
        conn.close()
    return redirect("/admin-dashboard")


# ================================================================
#  ADMIN — REJECT
# ================================================================
@app.route("/reject/<int:app_id>", methods=["POST"])
@admin_required
@limiter.limit("60 per hour")
def reject(app_id):
    reason = request.form.get("reason", "").strip()[:500]
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE applications SET status='Rejected', rejection_reason=%s WHERE id=%s",
            (reason, app_id)
        )
        conn.commit()
        log_action(A_APP_REJECT, actor="admin", ip=request.remote_addr,
                   target_id=app_id, detail=f"Reason: {reason[:80]}")
        logger.info("Admin rejected application #%d: %s", app_id, reason[:80])
    except Exception as exc:
        conn.rollback()
        logger.error("Reject DB error: %s", exc)
    finally:
        cur.close()
        conn.close()
    return redirect("/admin-dashboard")


# ================================================================
#  ADMIN — DELETE  (requires re-auth)
# ================================================================
@app.route("/delete/<int:app_id>", methods=["POST"])
@admin_required
@reauth_required
@limiter.limit("30 per hour")
def delete(app_id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM applications WHERE id=%s", (app_id,))
        conn.commit()
        log_action(A_APP_DELETE, actor="admin", ip=request.remote_addr, target_id=app_id)
        logger.info("Admin deleted application #%d", app_id)
    except Exception as exc:
        conn.rollback()
        logger.error("Delete DB error: %s", exc)
    finally:
        cur.close()
        conn.close()
    return redirect("/admin-dashboard")


# ================================================================
#  ADMIN — PREVIEW
# ================================================================
@app.route("/admin/preview/<int:app_id>")
@admin_required
def admin_preview(app_id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT * FROM applications WHERE id=%s", (app_id,))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()
    if not row:
        abort(404)
    return render_template("preview_modal.html", app=dict(row))


# ================================================================
#  ADMIN — EXPORT CSV
#  Rate limit: 10 exports per hour (heavy operation)
#  Sensitive fields masked in export
# ================================================================
@app.route("/admin/export-excel")
@admin_required
@limiter.limit("10 per hour")
def export_excel():
    branch = request.args.get("branch", "").strip()
    gender = request.args.get("gender", "").strip()

    conditions, params = [], []
    if branch:
        conditions.append("a.branch = %s")
        params.append(branch)
    if gender:
        conditions.append("a.gender = %s")
        params.append(gender)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute(f"""
            SELECT
                a.id, s.username, a.full_name, a.email,
                a.branch, a.gender, a.category, a.caste,
                a.student_mobile, a.parent_mobile,
                a.prn_number, a.cet_application_number,
                a.admission_taking_year  AS admission_date,
                a.year_transition, a.admission_receipt,
                a.first_year_credits, a.second_year_credits,
                a.third_year_credits, a.total_credits,
                a.bank_account_number, a.ifsc_code,
                a.local_address, a.permanent_address,
                a.applied_for_scholarship, a.income_certificate_number,
                a.actual_income,
                CASE
                    WHEN a.scholarship_registration_no = 'Other'
                         AND a.custom_scheme_name IS NOT NULL
                    THEN a.custom_scheme_name
                    ELSE a.scholarship_registration_no
                END AS scholarship_scheme_name,
                a.scholarship_reg_year1, a.scholarship_reg_year2,
                a.scholarship_reg_year3,
                a.status, a.rejection_reason, a.created_at
            FROM applications a
            JOIN students s ON s.id = a.student_id
            {where_clause}
            ORDER BY a.id DESC
        """, params)
        rows = cur.fetchall()
    except Exception as exc:
        logger.error("Export DB error: %s", exc)
        abort(500)
    finally:
        cur.close()
        conn.close()

    log_action(A_EXPORT, actor="admin", ip=request.remote_addr,
               detail=f"branch={branch or 'all'} gender={gender or 'all'} rows={len(rows)}")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Username", "Full Name", "Email", "Branch", "Gender",
        "Category", "Caste", "Student Mobile", "Parent Mobile",
        "PRN Number", "CET Application No.", "Admission Date",
        "Year Transition", "Admission Receipt",
        "1st Year Credits", "2nd Year Credits", "3rd Year Credits", "Total Credits",
        # Bank account masked in export — full number not needed for reporting
        "Bank Account (Masked)", "IFSC Code",
        "Local Address", "Permanent Address",
        "Applied for Scholarship", "Income Certificate No.", "Actual Income (Rs)",
        "Scholarship Scheme Name",
        "Scholarship Reg. (Year 1)", "Scholarship Reg. (Year 2)", "Scholarship Reg. (Year 3)",
        "Status", "Rejection Reason", "Submitted On",
    ])

    sv = sanitize_csv_value
    for row in rows:
        writer.writerow([
            sv(row["id"]),          sv(row["username"]),
            sv(row["full_name"]),   sv(row["email"]),
            sv(row["branch"]),      sv(row["gender"]),
            sv(row["category"]),    sv(row["caste"]),
            sv(row["student_mobile"]), sv(row["parent_mobile"]),
            sv(row["prn_number"]),  sv(row["cet_application_number"]),
            sv(row["admission_date"]),
            sv(row["year_transition"]), sv(row["admission_receipt"]),
            sv(row["first_year_credits"]),  sv(row["second_year_credits"]),
            sv(row["third_year_credits"]),  sv(row["total_credits"]),
            # Mask bank account: show only last 4 digits
            sv(mask_bank_account(row["bank_account_number"])),
            sv(row["ifsc_code"]),
            sv(row["local_address"]),       sv(row["permanent_address"]),
            sv(row["applied_for_scholarship"]),
            sv(row["income_certificate_number"]), sv(row["actual_income"]),
            sv(row["scholarship_scheme_name"]),
            sv(row["scholarship_reg_year1"]), sv(row["scholarship_reg_year2"]),
            sv(row["scholarship_reg_year3"]),
            sv(row["status"]),      sv(row["rejection_reason"]),
            sv(str(row["created_at"])[:10] if row["created_at"] else ""),
        ])

    csv_data = output.getvalue()
    output.close()

    parts = ["GCE_Admissions"]
    if branch:
        parts.append(branch.replace(" ", "_")[:20])
    if gender:
        parts.append(gender)
    filename = "_".join(parts) + ".csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8",
            "Cache-Control": "no-store",
        }
    )


# ================================================================
#  ADMIN — AUDIT LOG VIEWER
# ================================================================
@app.route("/admin/audit-log")
@admin_required
def audit_log():
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            SELECT id, timestamp, ip_address, action, actor, target_id, detail
            FROM audit_logs
            ORDER BY timestamp DESC
            LIMIT 500
        """)
        logs = [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()
    return render_template("audit_log.html", logs=logs)


# ================================================================
#  RUN (local dev only)
# ================================================================
if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = not IS_PRODUCTION
    app.run(host="0.0.0.0", port=port, debug=debug)
