import hashlib
import hmac
import math
import re
import time
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session

from database.db import (
    get_db, init_db, seed_db,
    create_user, get_user_by_email, get_user_by_id,
    get_user_expenses, get_expense_summary, get_category_breakdown,
    get_monthly_spending,
)
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-key-change-in-production"


# ------------------------------------------------------------------ #
# Category icons used by the dashboard recent-transactions list.      #
# ------------------------------------------------------------------ #

CATEGORY_ICONS = {
    "Food": "🍔",
    "Transport": "🚗",
    "Bills": "📄",
    "Health": "💊",
    "Entertainment": "🎬",
    "Shopping": "🛍",
    "Other": "📦",
}


def category_icon(name):
    """Return an emoji for a category, falling back to a generic package."""
    return CATEGORY_ICONS.get(name, "📦")


# ------------------------------------------------------------------ #
# Time-based greeting (used on the dashboard)                         #
# ------------------------------------------------------------------ #

def get_greeting():
    """Return a greeting based on the current local hour."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    if 12 <= hour < 17:
        return "Good Afternoon"
    return "Good Evening"


# ------------------------------------------------------------------ #
# Pie chart geometry — pure SVG, no JS                                #
# ------------------------------------------------------------------ #

def _polar_to_cartesian(cx, cy, r, angle_deg):
    """Convert polar coordinates to SVG x/y."""
    rad = math.radians(angle_deg - 90)  # rotate so 0° is at the top
    return (cx + r * math.cos(rad), cy + r * math.sin(rad))


def _arc_path(cx, cy, r, start_deg, end_deg):
    """Build an SVG path 'd' string for an arc slice."""
    if end_deg - start_deg >= 359.999:
        # Full circle — draw two arcs to avoid the SVG "move" gotcha.
        large_arc = 1
        x1, y1 = _polar_to_cartesian(cx, cy, r, 0)
        x2, y2 = _polar_to_cartesian(cx, cy, r, 180)
        return (
            f"M {cx} {cy} "
            f"L {x1:.2f} {y1:.2f} "
            f"A {r} {r} 0 {large_arc} 1 {x2:.2f} {y2:.2f} "
            f"A {r} {r} 0 {large_arc} 1 {x1:.2f} {y1:.2f} Z"
        )
    large_arc = 1 if (end_deg - start_deg) > 180 else 0
    x1, y1 = _polar_to_cartesian(cx, cy, r, start_deg)
    x2, y2 = _polar_to_cartesian(cx, cy, r, end_deg)
    return (
        f"M {cx} {cy} "
        f"L {x1:.2f} {y1:.2f} "
        f"A {r} {r} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z"
    )


def build_pie_slices(breakdown):
    """Convert a category breakdown into a list of SVG arc descriptors."""
    slices = []
    cumulative = 0.0
    total = sum(cat["percentage"] for cat in breakdown) or 1
    for cat in breakdown:
        # Map this slice's percentage of the *whole* pie (not 100%) to degrees.
        span = (cat["percentage"] / total) * 360
        start = cumulative
        end = cumulative + span
        cumulative = end
        slices.append({
            "path_d": _arc_path(100, 100, 80, start, end),
            "css_class": "pie-slice--" + cat["name"].lower(),
            "label": cat["name"],
            "percentage": cat["percentage"],
            "amount": cat["amount"],
        })
    return slices


def generate_csrf_token():
    """Generate a CSRF token for the current session."""
    expires = int(time.time()) + 3600  # 1 hour
    payload = f"{expires}"
    signature = hmac.new(
        app.config["SECRET_KEY"].encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:10]
    return f"{expires}-{signature}"


def validate_csrf_token(token):
    """Validate a CSRF token."""
    try:
        expires, signature = token.rsplit("-", 1)
        expected_signature = hmac.new(
            app.config["SECRET_KEY"].encode(),
            expires.encode(),
            hashlib.sha256
        ).hexdigest()[:10]
        if not hmac.compare_digest(signature, expected_signature):
            return False
        if int(expires) < int(time.time()):
            return False
        return True
    except (ValueError, AttributeError):
        return False


@app.context_processor
def inject_csrf():
    """Make csrf_token() available in all templates."""
    return dict(csrf_token=generate_csrf_token)


@app.context_processor
def inject_user():
    """Make logged_in state and current user available in all templates."""
    from database.db import get_user_by_id
    user_id = session.get("user_id")
    if user_id:
        user = get_user_by_id(user_id)
        return dict(logged_in=True, current_user=user)
    return dict(logged_in=False, current_user=None)


@app.context_processor
def inject_helpers():
    """Expose dashboard helpers (greeting, category_icon) to all templates."""
    return dict(greeting=get_greeting(), category_icon=category_icon)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Redirect if already logged in
    if session.get("user_id"):
        flash("Already logged in", "error")
        return redirect(url_for("landing"))

    if request.method == "POST":
        # Validate CSRF token
        csrf_token = request.form.get("csrf_token", "")
        if not validate_csrf_token(csrf_token):
            flash("Invalid or expired session. Please try again.", "error")
            return render_template("register.html")

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Validate required fields
        if not name:
            flash("Name is required", "error")
            return render_template("register.html")

        if not email:
            flash("Email is required", "error")
            return render_template("register.html")

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash("Invalid email format", "error")
            return render_template("register.html")

        if not password:
            flash("Password is required", "error")
            return render_template("register.html")

        # Validate password length
        if len(password) < 6:
            flash("Password must be at least 6 characters", "error")
            return render_template("register.html")

        # Check for duplicate email
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        conn.close()

        if existing_user:
            flash("Email already registered", "error")
            return render_template("register.html")

        # Create user
        try:
            create_user(name, email, password)
            flash("Registration successful! Please sign in.", "success")
            return redirect(url_for("login"))
        except Exception:
            flash("Registration failed. Please try again.", "error")
            return render_template("register.html")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Redirect if already logged in
    if session.get("user_id"):
        flash("Already logged in", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        # Validate CSRF token
        csrf_token = request.form.get("csrf_token", "")
        if not validate_csrf_token(csrf_token):
            flash("Invalid or expired session. Please try again.", "error")
            return render_template("login.html")

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Validate required fields
        if not email:
            flash("Email is required", "error")
            return render_template("login.html")

        if not password:
            flash("Password is required", "error")
            return render_template("login.html")

        # Fetch user by email
        user = get_user_by_email(email)

        # Verify password
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid credentials", "error")
            return render_template("login.html")

        # Successful login - store user_id in session
        session["user_id"] = user["id"]
        flash("Welcome back!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    # Redirect if not logged in
    if not session.get("user_id"):
        flash("Please log in to access this page", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = get_user_by_id(user_id)

    # Personal info shown on the Account & Settings page. Phone and country are
    # not in the users table yet — defaults keep the page rendering until a
    # future step adds the columns and wires them through this dict.
    user_info = {
        "name": user["name"],
        "email": user["email"],
        "member_since": user["created_at"][:10] if user["created_at"] else "Recently",
        "phone": "",
        "country": "India",
        "currency": "INR (₹)",
        "language": "English (US)",
        "timezone": "Asia/Kolkata (IST)",
        "theme": "Light",
    }

    return render_template("profile.html", user_info=user_info)


@app.route("/dashboard")
def dashboard():
    # Auth gate — Dashboard is the post-login landing page.
    if not session.get("user_id"):
        flash("Please log in to access this page", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = get_user_by_id(user_id)

    # User initials for the greeting avatar (e.g. "Ankit Kumar" -> "AK").
    name_parts = [p for p in (user["name"] or "").split() if p]
    if len(name_parts) >= 2:
        initials = (name_parts[0][0] + name_parts[-1][0]).upper()
    elif name_parts:
        initials = name_parts[0][:2].upper()
    else:
        initials = "??"

    # Money totals. The schema has no income table yet, so total_income is
    # hard-coded to 0.00 — the layout is forward-compatible with future income.
    summary = get_expense_summary(user_id)
    total_income = 0.00
    total_expenses = summary["total_spent"] or 0.00
    balance = total_income - total_expenses

    # Recent transactions (top 5) — uses existing helper with a lower limit.
    recent = []
    for exp in get_user_expenses(user_id, limit=5):
        recent.append({
            "name": exp["description"] or exp["category"],
            "category": exp["category"],
            "category_class": exp["category"].lower(),
            "date": exp["date"][:10] if exp["date"] else "",
            "amount": f"₹{exp['amount']:.2f}",
        })

    # Pie chart data (overall category breakdown) + monthly bar series.
    breakdown = get_category_breakdown(user_id)
    pie_slices = build_pie_slices(breakdown)

    monthly = get_monthly_spending(user_id, months=6)
    max_amount = max((m["amount"] for m in monthly), default=0) or 1
    for entry in monthly:
        entry["height_pct"] = int(round((entry["amount"] / max_amount) * 100))

    # Static example insights for the v1 dashboard. Real computation comes later.
    top_category = summary.get("top_category") or "—"
    ai_insights = [
        f"Your top spending category is {top_category}.",
        "Weekend spending tends to be higher than weekday spending.",
        "Cutting ₹500 from Food could noticeably improve your monthly savings.",
    ]

    return render_template(
        "dashboard.html",
        user=user,
        initials=initials,
        balance=balance,
        total_income=total_income,
        total_expenses=total_expenses,
        recent=recent,
        pie_slices=pie_slices,
        monthly=monthly,
        ai_insights=ai_insights,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
