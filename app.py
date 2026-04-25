import hashlib
import hmac
import re
import time

from flask import Flask, render_template, request, redirect, url_for, flash, session

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, get_user_by_id, get_user_expenses, get_expense_summary, get_category_breakdown
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-key-change-in-production"


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
        return redirect(url_for("landing"))

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
        return redirect(url_for("profile"))

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

    # User info from database
    user_info = {
        "name": user["name"],
        "email": user["email"],
        "member_since": user["created_at"][:10] if user["created_at"] else "Recently"
    }

    # Expense summary from database
    summary = get_expense_summary(user_id)
    summary_stats = {
        "total_spent": f"₹{summary['total_spent']:,.2f}" if summary['total_spent'] else "₹0.00",
        "transaction_count": str(summary['transaction_count']),
        "top_category": summary['top_category']
    }

    # Recent transactions from database
    expenses = get_user_expenses(user_id, limit=10)
    transactions = []
    for exp in expenses:
        transactions.append({
            "date": exp["date"][:10] if exp["date"] else "",
            "description": exp["description"] or exp["category"],
            "category": exp["category"],
            "category_class": exp["category"].lower(),
            "amount": f"₹{exp['amount']:.2f}"
        })

    # Category breakdown from database
    breakdown = get_category_breakdown(user_id)
    category_breakdown = []
    for cat in breakdown:
        category_breakdown.append({
            "name": cat["name"],
            "amount": f"₹{cat['amount']:.2f}",
            "percentage": cat["percentage"]
        })

    return render_template(
        "profile.html",
        user_info=user_info,
        summary_stats=summary_stats,
        transactions=transactions,
        category_breakdown=category_breakdown
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
