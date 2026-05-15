# GCE Kolhapur — Admission Management System
### Flask · PostgreSQL · Production-Hardened · Render-Ready

---

## Project Overview

A full-featured admission management portal for Government College of Engineering, Kolhapur.
Students submit admission applications; admins review, approve, reject, and export data.

---

## Security Features

| Feature | Implementation |
|---|---|
| Password hashing | bcrypt (auto-upgrades legacy plain-text on next login) |
| CSRF protection | Flask-WTF — every POST form carries a `csrf_token` |
| Brute-force protection | Flask-Limiter — 10 attempts / 15 min per IP on all login routes |
| Session security | HttpOnly, SameSite=Lax, Secure (prod), 1-hour lifetime |
| HTTPS enforcement | HTTP → HTTPS 301 redirect via `X-Forwarded-Proto` (Render) |
| Security headers | X-Frame-Options, X-Content-Type-Options, CSP, HSTS, Referrer-Policy, Permissions-Policy |
| No-cache on auth pages | `Cache-Control: no-store` injected on every authenticated response |
| Input validation | Server-side: email, phone, IFSC, bank account, gender, category, branch |
| Mass assignment prevention | Explicit `ALLOWED_APP_COLUMNS` whitelist in `security.py` |
| SQL injection prevention | 100% parameterised `%s` placeholders — no string formatting in queries |
| CSV formula injection | Values starting with `= + - @ \t \r` prefixed with `'` |
| Sensitive field masking | Bank account number shows only last 4 digits in exports |
| Autocomplete restrictions | `autocomplete="off"` on bank account, IFSC, mobile, certificate fields |
| Admin re-authentication | Delete requires re-entry of admin password (5-minute grace window) |
| Route protection | `@admin_required` / `@student_required` / `@reauth_required` decorators |
| Approve/Delete via POST | No state-changing GET requests — CSRF-safe |
| No stack traces in prod | `debug=False` unless `FLASK_ENV=development`; generic error pages |
| Audit trail | Every login, submission, approval, rejection, delete, export logged to `audit_logs` |
| Session expiry warning | JS banner appears 5 minutes before 1-hour session timeout |
| Startup validation | `startup.py` exits with clear message if `SECRET_KEY`/`DATABASE_URL` missing |
| DB retry on connect | psycopg2 retries 3× with back-off (handles Render cold starts) |
| Transaction rollback | Every DB operation wrapped in try/except with explicit rollback |
| Performance indexes | 8 indexes on `applications` and `audit_logs` tables |
| Per-route rate limits | Login: 10/15min · Signup: 5/hr · Submit: 20/hr · Export: 10/hr · Admin: 60/hr |

---

## File Structure

```
gce_admission_pg/
├── app.py                  ← All Flask routes + middleware
├── database.py             ← PostgreSQL connection (retry), schema init, indexes
├── security.py             ← Passwords, validation, sanitisation, whitelisting
├── audit.py                ← Audit trail helpers + action constants
├── startup.py              ← Pre-flight environment validation
│
├── requirements.txt
├── runtime.txt             ← Python 3.11.9 (Render)
├── Procfile                ← gunicorn with production flags
├── .env                    ← Local config (never committed)
├── .gitignore
├── README.md
│
├── static/
│   ├── css/styles.css
│   └── js/
│       ├── admin.js        ← Delete confirm, session expiry warn, search, export URL
│       ├── auth.js         ← Signup client-side validation
│       ├── student.js      ← Year transition, scholarship toggle, IFSC uppercase
│       ├── pdf.js          ← Client-side PDF download
│       └── audit.js        ← Audit log page filter
│
└── templates/
    ├── base.html           ← CSRF meta tag, all CSS, all JS includes
    ├── error.html          ← Generic error page (400/403/404/429/500)
    ├── login.html          ← Student + Admin login panels
    ├── signup.html         ← New student registration
    ├── student_dashboard.html ← Application form (full)
    ├── admin_dashboard.html   ← Applications table + export + audit link
    ├── preview_modal.html     ← Full application read-only view
    ├── audit_log.html         ← Audit event viewer (last 500 events)
    └── reauth.html            ← Admin re-authentication for delete actions
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ Required | Flask session & CSRF secret. Must be 32+ random hex chars. |
| `DATABASE_URL` | ✅ Required | Full PostgreSQL URL (see format below). |
| `ADMIN_USERNAME` | Recommended | Admin login username. Default: `admin` |
| `ADMIN_PASSWORD` | Recommended | Admin login password. Default: `admin123` — **change this!** |
| `FLASK_ENV` | Optional | Set to `development` for local debug mode. Leave unset on Render. |
| `PORT` | Optional | Port to bind. Render sets this automatically. |
| `LIMITER_STORAGE_URI` | Optional | Redis URL for multi-worker rate limiting. Leave blank for single worker. |

**Generate a secure SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**DATABASE_URL formats:**
```
# Local PostgreSQL:
postgresql://postgres:YOUR_PASSWORD@localhost:5432/gce_admission

# Render PostgreSQL (paste from dashboard — Render also provides postgres:// which is auto-fixed):
postgresql://user:pass@dpg-xxxx.oregon-postgres.render.com/gce_admission_xxxx
```

---

## Run Locally

### 1 — Install PostgreSQL and create the database
```bash
# macOS
brew install postgresql && brew services start postgresql

# Ubuntu / Debian
sudo apt install postgresql postgresql-contrib

# Create the database
psql -U postgres -c "CREATE DATABASE gce_admission;"
```

### 2 — Clone / extract and set up virtual environment
```bash
cd gce_admission_pg
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### 4 — Configure .env
Edit `.env` and fill in:
```
SECRET_KEY=<your 32+ char hex string>
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/gce_admission
ADMIN_USERNAME=admin
ADMIN_PASSWORD=choose-a-strong-password
FLASK_ENV=development
```

### 5 — Run
```bash
python app.py
```
Open **http://localhost:5000**

Tables, columns, and indexes are created automatically on every start (idempotent).

---

## Deploy on Render

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial production commit"
git remote add origin https://github.com/YOUR_USERNAME/gce-admission.git
git push -u origin main
```
> `.env` is in `.gitignore` — secrets never reach GitHub.

### Step 2 — Create PostgreSQL on Render
1. Render dashboard → **New → PostgreSQL**
2. Choose a name (e.g. `gce-admission-db`), select free plan, deploy
3. Copy the **Internal Database URL** (use this, not External, for the web service)

### Step 3 — Create Web Service
1. **New → Web Service** → connect your GitHub repo
2. Set:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --workers 2 --threads 2 --timeout 60 --log-level info --access-logfile - --error-logfile - --capture-output`
   - **Python version:** auto-detected from `runtime.txt` (3.11.9)

### Step 4 — Set Environment Variables on Render
In your web service → **Environment** tab:

| Key | Value |
|---|---|
| `SECRET_KEY` | Generated 32+ char hex string |
| `DATABASE_URL` | Internal Database URL from Step 2 |
| `ADMIN_USERNAME` | Your admin username |
| `ADMIN_PASSWORD` | A strong password |

**Do NOT set `FLASK_ENV`** on Render — leaving it unset activates production mode automatically.

> Tip: Render → web service → **Environment** → **Add from Database** links the DB and auto-injects `DATABASE_URL`.

### Step 5 — Deploy
Click **Deploy**. On first boot, tables and indexes are created automatically.

Your app is live at `https://your-service-name.onrender.com`

---

## Database Schema

### `students`
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `username` | VARCHAR(100) | Unique, NOT NULL |
| `password` | VARCHAR(255) | bcrypt hash |
| `created_at` | TIMESTAMPTZ | |

### `applications`
All student form fields. Key columns:

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `student_id` | INTEGER FK | References `students(id)`, CASCADE DELETE |
| `status` | VARCHAR(20) | `Pending` / `Approved` / `Rejected` |
| `rejection_reason` | TEXT | |
| `admission_taking_year` | VARCHAR(20) | Stores selected date (field labelled "Admission Date") |
| `scholarship_registration_no` | VARCHAR(120) | Stores selected scheme name or "Other" |
| `custom_scheme_name` | VARCHAR(255) | Populated when scheme = "Other" |

### `audit_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `timestamp` | TIMESTAMPTZ | Auto-set |
| `ip_address` | VARCHAR(45) | IPv4 or IPv6 |
| `action` | VARCHAR(80) | e.g. `student_login_ok`, `application_approve` |
| `actor` | VARCHAR(100) | Username or `"admin"` |
| `target_id` | INTEGER | Application ID for app-level actions |
| `detail` | TEXT | Extra context (rejection reason, export filters, etc.) |

### Indexes
```sql
idx_apps_student_id, idx_apps_status, idx_apps_email,
idx_apps_branch, idx_apps_created_at,
idx_audit_actor, idx_audit_action, idx_audit_ts
```

---

## Database Migration (upgrading from older version)

These migrations run automatically on every startup via `init_db()`:
```sql
ALTER TABLE applications ADD COLUMN IF NOT EXISTS custom_scheme_name VARCHAR(255);
ALTER TABLE students ALTER COLUMN password TYPE VARCHAR(255);
```

If upgrading from the plain-text password version: no manual migration needed.
Passwords are upgraded to bcrypt automatically the next time each user logs in.

---

## Dependencies

```
Flask==3.0.3
psycopg2-binary==2.9.9
python-dotenv==1.0.1
gunicorn==22.0.0
Flask-WTF==1.2.1
bcrypt==4.1.3
Flask-Limiter==3.7.0
```

---

## Security Notes

- **Rate limiter** uses in-memory storage by default. For multi-worker Render deploys (2+ workers), set `LIMITER_STORAGE_URI` to a Redis URL so limits are shared across workers.
- **Admin password** is compared in env vars using `hmac.compare_digest` (timing-attack safe). Consider storing it bcrypt-hashed in the DB for a future improvement.
- **CSP** allows `unsafe-inline` for styles only (required by Tailwind). All JavaScript is in external `.js` files — no inline script blocks.
- **Session expiry** UI warning fires in the browser 55 minutes after page load. Server-side session lifetime is 60 minutes.
