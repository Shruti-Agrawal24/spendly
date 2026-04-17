import sqlite3
import random
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_NAME = "spendly.db"


def get_db():
    """Open a SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Common Indian first names (mixed gender)
FIRST_NAMES = [
    "Aarav", "Vihaan", "Aditya", "Sai", "Reyansh", "Aryan", "Krishna", "Ishaan",
    "Diya", "Saanvi", "Ananya", "Priya", "Meera", "Kavya", "Riya", "Neha",
    "Rahul", "Arjun", "Karan", "Rohan", "Vikram", "Sameer", "Ajay", "Sanjay",
    "Pooja", "Sneha", "Divya", "Deepika", "Anjali", "Nisha", "Usha", "Rekha",
    "Arjun", "Vivaan", "Ayaan", "Krishiv", "Reyansh", "Shaurya", "Pranav", "Neel"
]

# Common Indian surnames from various regions
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Agarwal", "Singh", "Kumar", "Yadav", "Patel",
    "Reddy", "Rao", "Nair", "Pillai", "Menon", "Iyer", "Iyengar", "Naidu",
    "Chatterjee", "Banerjee", "Mukherjee", "Ganguly", "Das", "Bose", "Sarkar",
    "Joshi", "Pandey", "Tiwari", "Mishra", "Shukla", "Srivastava", "Dubey",
    "Naik", "Desai", "Joshi", "Kulkarni", "Patil", "Shinde", "Jadhav", "Pawar"
]


def generate_unique_email(conn):
    """Generate a unique email that doesn't exist in the database."""
    max_attempts = 50

    for _ in range(max_attempts):
        first_name = random.choice(FIRST_NAMES).lower()
        last_name = random.choice(LAST_NAMES).lower()
        suffix = random.randint(10, 999)

        email = f"{first_name}.{last_name}{suffix}@gmail.com"

        # Check if email already exists
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone() is None:
            return email, f"{first_name.capitalize()} {last_name.capitalize()}"

    # Fallback with timestamp-based suffix
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    first_name = random.choice(FIRST_NAMES).lower()
    last_name = random.choice(LAST_NAMES).lower()
    email = f"{first_name}.{last_name}{timestamp}@gmail.com"
    return email, f"{first_name.capitalize()} {last_name.capitalize()}"


def seed_user():
    """Generate and insert a realistic Indian user into the database."""
    conn = get_db()

    # Generate unique email and name
    email, name = generate_unique_email(conn)

    # Hash the password
    password_hash = generate_password_hash("password123")

    # Get current datetime for created_at
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert the user
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, created_at)
    )

    # Get the inserted user's ID
    user_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Print confirmation
    print(f"User created successfully!")
    print(f"  id: {user_id}")
    print(f"  name: {name}")
    print(f"  email: {email}")


if __name__ == "__main__":
    seed_user()
