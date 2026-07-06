import sqlite3
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

DB_NAME = "spendly.db"

# Short month names used by the dashboard monthly-spending chart.
_MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def get_db():
    """
    Open a SQLite connection to the database.
    Sets row_factory for dict-like row access and enables foreign key enforcement.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Create the database tables if they don't exist.
    Safe to call multiple times (idempotent).
    """
    conn = get_db()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # Create expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create income table (mirrors expenses; kept separate so existing
    # expense queries/helpers never need to filter by type)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            source TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create unique indexes to handle NULL and user-specific category uniqueness
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_name_null_user 
        ON categories(name) WHERE user_id IS NULL
    ''')
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_name_user 
        ON categories(name, user_id) WHERE user_id IS NOT NULL
    ''')

    # Seed default categories
    default_cats = ["Food", "Shopping", "Bills", "Transport", "Entertainment", "Health", "Education", "Travel", "Other"]
    for cat in default_cats:
        cursor.execute(
            "INSERT OR IGNORE INTO categories (name, user_id) VALUES (?, NULL)",
            (cat,)
        )

    conn.commit()
    conn.close()



def create_user(name, email, password):
    """
    Create a new user with hashed password.
    Returns the new user ID.
    Raises sqlite3.IntegrityError if email already exists.
    """
    conn = get_db()
    cursor = conn.cursor()

    password_hash = generate_password_hash(password)

    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash)
    )

    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return user_id


def get_user_by_email(email):
    """
    Fetch a user by email address.
    Returns a dict-like row (sqlite3.Row) or None if not found.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?",
        (email,)
    )
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    """
    Fetch a user by ID.
    Returns a dict-like row (sqlite3.Row) or None if not found.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,)
    )
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_expenses(user_id, limit=10):
    """
    Fetch expenses for a user, ordered by date descending.
    Returns a list of dict-like rows.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, amount, category, date, description
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (user_id, limit)
    )
    expenses = cursor.fetchall()
    conn.close()
    return expenses


def get_all_user_transactions(user_id):
    """
    Fetch every transaction for a user (no limit), ordered by date descending.

    Each row is a dict with: id, amount, category, date, description, type.
    'type' is either 'expense' or 'income' so the Transactions page (and the
    Dashboard recent list) can render a single combined, chronological feed.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, amount, category, date, description, 'expense' AS type
        FROM expenses
        WHERE user_id = ?
        UNION ALL
        SELECT id, amount, source AS category, date, description, 'income' AS type
        FROM income
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (user_id, user_id)
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "amount": float(row["amount"]),
            "category": row["category"],
            "date": row["date"],
            "description": row["description"] or row["category"],
            "type": row["type"],
        }
        for row in rows
    ]


def create_expense(user_id, amount, category, date, description=None):
    """
    Insert a new expense for a user.
    Returns the new expense's ID.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, category, date, description)
    )
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()
    return expense_id


def create_income(user_id, amount, source, date, description=None):
    """
    Insert a new income entry for a user.
    Returns the new income row's ID.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO income (user_id, amount, source, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, source, date, description)
    )
    conn.commit()
    income_id = cursor.lastrowid
    conn.close()
    return income_id


def get_income_summary(user_id):
    """
    Get summary statistics for a user's income.
    Returns dict with total_income, entry_count.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(amount) as total, COUNT(*) as count FROM income WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return {
        "total_income": row["total"] if row and row["total"] else 0,
        "entry_count": row["count"] if row and row["count"] else 0,
    }


def get_user_categories(user_id):
    """
    Fetch all category names available to a user: the fixed global defaults
    (user_id IS NULL) plus any categories that user has created themselves.
    Returns a sorted list of unique names.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT name FROM categories
        WHERE user_id IS NULL OR user_id = ?
        ORDER BY name
        """,
        (user_id,)
    )
    names = [row["name"] for row in cursor.fetchall()]
    conn.close()
    return names


def create_category(name, user_id):
    """
    Create a new user-specific category if it doesn't already exist
    (case-insensitive match against that user's existing categories, plus
    the global defaults). Returns the final category name to use — either
    the newly created one or an existing match.
    """
    name = name.strip()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name FROM categories
        WHERE (user_id IS NULL OR user_id = ?) AND LOWER(name) = LOWER(?)
        """,
        (user_id, name)
    )
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return existing["name"]

    cursor.execute(
        "INSERT INTO categories (name, user_id) VALUES (?, ?)",
        (name, user_id)
    )
    conn.commit()
    conn.close()
    return name


def get_expense_summary(user_id):
    """
    Get summary statistics for a user's expenses.
    Returns dict with total_spent, transaction_count, top_category.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Total spent and transaction count
    cursor.execute(
        """
        SELECT SUM(amount) as total, COUNT(*) as count
        FROM expenses
        WHERE user_id = ?
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    total_spent = row["total"] if row and row["total"] else 0
    transaction_count = row["count"] if row and row["count"] else 0

    # Top category
    cursor.execute(
        """
        SELECT category, SUM(amount) as cat_total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY cat_total DESC
        LIMIT 1
        """,
        (user_id,)
    )
    top_cat_row = cursor.fetchone()
    top_category = top_cat_row["category"] if top_cat_row else "N/A"

    conn.close()
    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "top_category": top_category
    }


def get_category_breakdown(user_id):
    """
    Get expense breakdown by category for a user.
    Returns list of dicts with name, amount, percentage.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get total spent
    cursor.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id = ?",
        (user_id,)
    )
    total = cursor.fetchone()["total"] or 0

    # Get per-category totals
    cursor.execute(
        """
        SELECT category, SUM(amount) as cat_total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY cat_total DESC
        """,
        (user_id,)
    )
    categories = cursor.fetchall()
    conn.close()

    breakdown = []
    for cat in categories:
        percentage = int((cat["cat_total"] / total * 100)) if total > 0 else 0
        breakdown.append({
            "name": cat["category"],
            "amount": cat["cat_total"],
            "percentage": percentage
        })

    return breakdown


def get_income_category_breakdown(user_id):
    """
    Get income breakdown by source for a user (the income-side mirror of
    get_category_breakdown). Returns list of dicts with name, amount, percentage.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get total income
    cursor.execute(
        "SELECT SUM(amount) as total FROM income WHERE user_id = ?",
        (user_id,)
    )
    total = cursor.fetchone()["total"] or 0

    # Get per-source totals
    cursor.execute(
        """
        SELECT source, SUM(amount) as source_total
        FROM income
        WHERE user_id = ?
        GROUP BY source
        ORDER BY source_total DESC
        """,
        (user_id,)
    )
    sources = cursor.fetchall()
    conn.close()

    breakdown = []
    for src in sources:
        percentage = int((src["source_total"] / total * 100)) if total > 0 else 0
        breakdown.append({
            "name": src["source"],
            "amount": src["source_total"],
            "percentage": percentage
        })

    return breakdown


def get_monthly_spending(user_id, months=6):
    """
    Get total spending per month for the last N months (including the current one),
    oldest to newest. Months with no expenses are returned as zero so the chart
    always has the full window.

    Returns a list of dicts: [{"label": "Jan", "amount": 1234.5}, ...]
    """
    today = datetime.now()
    # Start of the first month in the window. We compute year/month pairs and
    # normalize by going through each calendar month, then backfill totals.
    months_indexed = []  # list of (year, month_index_0based)
    cursor_year, cursor_month = today.year, today.month
    for _ in range(months):
        months_indexed.append((cursor_year, cursor_month))
        cursor_month -= 1
        if cursor_month == 0:
            cursor_month = 12
            cursor_year -= 1
    months_indexed.reverse()  # oldest -> newest

    first_year, first_month = months_indexed[0]
    # First day of the first month in the window, formatted as YYYY-MM-DD.
    cutoff = f"{first_year:04d}-{first_month:02d}-01"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT strftime('%Y-%m', date) AS ym, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ? AND date >= ?
        GROUP BY ym
        ORDER BY ym
        """,
        (user_id, cutoff)
    )
    rows = cursor.fetchall()
    conn.close()

    totals = {row["ym"]: row["total"] or 0 for row in rows}

    result = []
    for year, month in months_indexed:
        key = f"{year:04d}-{month:02d}"
        result.append({
            "label": _MONTH_LABELS[month - 1],
            "amount": float(totals.get(key, 0)),
        })
    return result


def get_monthly_income(user_id, months=6):
    """
    Get total income per month for the last N months (the income-side mirror of
    get_monthly_spending). Months with no income are returned as zero so the
    chart always has the full window.

    Returns a list of dicts: [{"label": "Jan", "amount": 1234.5}, ...]
    """
    today = datetime.now()
    months_indexed = []  # list of (year, month_index_0based)
    cursor_year, cursor_month = today.year, today.month
    for _ in range(months):
        months_indexed.append((cursor_year, cursor_month))
        cursor_month -= 1
        if cursor_month == 0:
            cursor_month = 12
            cursor_year -= 1
    months_indexed.reverse()  # oldest -> newest

    first_year, first_month = months_indexed[0]
    cutoff = f"{first_year:04d}-{first_month:02d}-01"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT strftime('%Y-%m', date) AS ym, SUM(amount) AS total
        FROM income
        WHERE user_id = ? AND date >= ?
        GROUP BY ym
        ORDER BY ym
        """,
        (user_id, cutoff)
    )
    rows = cursor.fetchall()
    conn.close()

    totals = {row["ym"]: row["total"] or 0 for row in rows}

    result = []
    for year, month in months_indexed:
        key = f"{year:04d}-{month:02d}"
        result.append({
            "label": _MONTH_LABELS[month - 1],
            "amount": float(totals.get(key, 0)),
        })
    return result


def seed_db():
    """
    Insert sample data for development.
    Checks for existing data to prevent duplicate inserts.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Check if users table already has data
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count > 0:
        conn.close()
        return  # Data already exists, skip seeding

    # Create demo user
    demo_password_hash = generate_password_hash("demo123")
    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", demo_password_hash)
    )

    # Get the demo user's ID
    cursor.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",))
    demo_user_id = cursor.fetchone()[0]

    # Insert 8 sample expenses across different categories
    # Dates spread across April 2026
    sample_expenses = [
        (demo_user_id, 45.50, "Food", "2026-04-01", "Lunch at cafe"),
        (demo_user_id, 15.00, "Transport", "2026-04-02", "Bus pass"),
        (demo_user_id, 120.00, "Bills", "2026-04-03", "Electricity bill"),
        (demo_user_id, 35.00, "Health", "2026-04-05", "Pharmacy"),
        (demo_user_id, 50.00, "Entertainment", "2026-04-07", "Movie tickets"),
        (demo_user_id, 89.99, "Shopping", "2026-04-08", "New shirt"),
        (demo_user_id, 25.00, "Other", "2026-04-09", "Miscellaneous"),
        (demo_user_id, 65.00, "Food", "2026-04-10", "Dinner with friends"),
    ]

    cursor.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        sample_expenses
    )

    conn.commit()
    conn.close()
