import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "spendly.db"


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
        "SELECT id, name, email FROM users WHERE id = ?",
        (user_id,)
    )
    user = cursor.fetchone()
    conn.close()
    return user


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
