# ================================================================
#  security.py  —  All security utilities
# ================================================================

import re
import bcrypt

# ── Password hashing ─────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# ── Masking sensitive data ────────────────────────────────────────

def mask_bank_account(account: str) -> str:
    """Return only the last 4 digits, padded with asterisks."""
    if not account:
        return ""
    s = str(account).strip()
    if len(s) <= 4:
        return s
    return "*" * (len(s) - 4) + s[-4:]

# ── Validation patterns ───────────────────────────────────────────

_RE_EMAIL    = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
_RE_PHONE    = re.compile(r'^[6-9][0-9]{9}$')
_RE_IFSC     = re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$')
_RE_ACCOUNT  = re.compile(r'^[0-9]{9,18}$')
_RE_USERNAME = re.compile(r'^[a-zA-Z0-9_]{3,50}$')

VALID_GENDERS    = {"Male", "Female", "Other"}
VALID_CATEGORIES = {"Open", "SC", "ST", "OBC", "EWS"}
VALID_BRANCHES   = {
    "Computer Engineering",
    "Artificial Intelligence And Data Science Engineering",
    "Mechanical Engineering",
    "Electrical Engineering",
    "Electronics Engineering",
}
VALID_TRANSITIONS  = {"1st to 2nd", "2nd to 3rd", "3rd to 4th"}
VALID_SCHOLARSHIP  = {"Yes", "No"}
VALID_SCHEMES = {
    "Post Matric Scholarship Scheme (Government of India)",
    "Tuition Fee & Exam Fee for Tribal Students (Freeship)",
    "Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC)",
    "Scholarship for students of minority communities pursuing Higher and Professional courses (DTE)",
    "Payment of Maintenance Allowance to VJNT and SBC Students Studying in Professional Courses and Living in Hostel Attached to Professional Colleges",
    "Payment of Tuition Fees and Examination Fees to OBC Girls Pursuing Professional Courses",
    "Post Matric Scholarship to OBC Students",
    "Post Matric Scholarship to SBC Students",
    "Post Matric Scholarship to the Girls Belonging to Other Backward Classes taking admission in Professional Courses",
    "Post Matric Scholarship to VJNT Students",
    "Tuition Fees and Examination Fees to OBC Students",
    "Tuition Fees and Examination Fees to SBC Students",
    "Tuition Fees and Examination Fees to VJNT Students",
    "Government of India Post-Matric Scholarship",
    "Maintenance Allowance for student Studying in professional courses",
    "Post-Matric Scholarship for persons with disability",
    "Post-Matric Tuition Fee and Examination Fee (Freeship)",
    "Other",
}

def validate_signup(form) -> list:
    errors = []
    username = form.get("username", "").strip()
    password = form.get("password", "")
    confirm  = form.get("confirm_password", "")
    if not _RE_USERNAME.match(username):
        errors.append("Username: 3–50 chars, letters/numbers/underscores only.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors

def validate_application(form) -> list:
    errors = []
    if not form.get("full_name", "").strip():
        errors.append("Full name is required.")
    if not form.get("prn_number", "").strip():
        errors.append("PRN number is required.")
    email = form.get("email", "")
    if not _RE_EMAIL.match(email.strip()):
        errors.append("A valid email address is required.")
    if form.get("branch", "") not in VALID_BRANCHES:
        errors.append("Please select a valid branch.")
    if form.get("category", "") not in VALID_CATEGORIES:
        errors.append("Please select a valid category.")
    if form.get("gender", "") not in VALID_GENDERS:
        errors.append("Please select a valid gender.")
    if form.get("year_transition", "") not in VALID_TRANSITIONS:
        errors.append("Please select a valid year of transition.")
    sm = form.get("student_mobile", "").strip()
    pm = form.get("parent_mobile", "").strip()
    if sm and not _RE_PHONE.match(sm):
        errors.append("Student mobile must be a valid 10-digit Indian number.")
    if pm and not _RE_PHONE.match(pm):
        errors.append("Parent mobile must be a valid 10-digit Indian number.")
    acct = form.get("bank_account_number", "").strip()
    ifsc = form.get("ifsc_code", "").strip().upper()
    if acct and not _RE_ACCOUNT.match(acct):
        errors.append("Bank account number must be 9–18 digits.")
    if ifsc and not _RE_IFSC.match(ifsc):
        errors.append("IFSC code format is invalid (e.g. SBIN0001234).")
    for fn in ("first_year_credits", "second_year_credits", "third_year_credits", "total_credits"):
        v = form.get(fn, "").strip()
        if v:
            try:
                if int(v) < 0:
                    raise ValueError
            except ValueError:
                errors.append(f"{fn.replace('_', ' ').title()} must be a non-negative integer.")
    applied = form.get("applied_for_scholarship", "No")
    if applied not in VALID_SCHOLARSHIP:
        errors.append("Invalid scholarship option.")
    if applied == "Yes":
        scheme = form.get("scholarship_registration_no", "")
        if scheme not in VALID_SCHEMES:
            errors.append("Please select a valid scholarship scheme.")
        if scheme == "Other" and not form.get("custom_scheme_name", "").strip():
            errors.append("Please enter the custom scholarship scheme name.")
    return errors

# ── Whitelisted columns (mass-assignment prevention) ─────────────

ALLOWED_APP_COLUMNS = {
    "full_name", "email", "bank_account_number", "ifsc_code",
    "branch", "caste", "category", "gender",
    "student_mobile", "parent_mobile", "local_address", "permanent_address",
    "cet_application_number", "prn_number", "admission_taking_year",
    "year_transition", "admission_receipt",
    "first_year_credits", "second_year_credits", "third_year_credits", "total_credits",
    "applied_for_scholarship", "income_certificate_number", "actual_income",
    "scholarship_registration_no", "scholarship_reg_year1",
    "scholarship_reg_year2", "scholarship_reg_year3",
    "custom_scheme_name",
}
INT_COLUMNS = {"first_year_credits", "second_year_credits", "third_year_credits", "total_credits"}

def sanitize_application_fields(raw_form, student_id: int) -> dict:
    fields = {}
    for key in ALLOWED_APP_COLUMNS:
        val = raw_form.get(key, "").strip()
        if val == "":
            fields[key] = None
        elif key in INT_COLUMNS:
            try:
                fields[key] = int(val)
            except ValueError:
                fields[key] = None
        else:
            fields[key] = val
    if fields.get("ifsc_code"):
        fields["ifsc_code"] = fields["ifsc_code"].upper()
    fields["student_id"] = student_id
    return fields

# ── CSV formula injection prevention ─────────────────────────────

_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

def sanitize_csv_value(value) -> str:
    s = str(value) if value is not None else ""
    if s and s[0] in _INJECTION_PREFIXES:
        return "'" + s
    return s
