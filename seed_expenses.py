import sqlite3
import random
import sys
from datetime import datetime, timedelta

DB_NAME = "spendly.db"


def get_db():
    """Open a SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Category definitions with Indian context
CATEGORIES = {
    "Food": {"min": 50, "max": 800, "weight": 25, "descriptions": [
        "Lunch at office canteen", "Street food", "Dinner at restaurant",
        "Morning chai and snacks", "Family dinner", "Order from Zomato",
        "Breakfast at mess", "Weekend brunch", "Coffee at Cafe Coffee Day",
        "Biryani takeaway", "South Indian thali", "North Indian thali"
    ]},
    "Transport": {"min": 20, "max": 500, "weight": 15, "descriptions": [
        "Metro card recharge", "Auto rickshaw fare", "Uber ride",
        "Bus pass monthly", "Fuel refill", "Ola cab",
        "Train ticket", "Parking fee", "Bike maintenance"
    ]},
    "Bills": {"min": 200, "max": 3000, "weight": 12, "descriptions": [
        "Electricity bill", "Water bill", "Internet bill",
        "Mobile recharge", "DTH subscription", "Cooking gas refill",
        "Maintenance charges", "Society maintenance"
    ]},
    "Health": {"min": 100, "max": 2000, "weight": 8, "descriptions": [
        "Pharmacy medicines", "Doctor consultation", "Gym membership",
        "Health checkup", "Dental visit", "Eye test",
        "Vitamins supplements", "Physiotherapy session"
    ]},
    "Entertainment": {"min": 100, "max": 1500, "weight": 10, "descriptions": [
        "Movie tickets", "Netflix subscription", "Amazon Prime",
        "Concert entry", "Bowling night", "Escape room",
        "Gaming zone", "Amusement park"
    ]},
    "Shopping": {"min": 200, "max": 5000, "weight": 18, "descriptions": [
        "New clothes", "Festival shopping", "Electronics purchase",
        "Home decor", "Kitchen items", "Shoes and accessories",
        "Birthday gift", "Wedding gift", "Furniture item"
    ]},
    "Other": {"min": 50, "max": 1000, "weight": 12, "descriptions": [
        "Miscellaneous", "Donation", "Stationery",
        "Gift wrapping", "Photocopy and print", "Courier charges",
        "Pet expenses", "Plant purchase"
    ]}
}


def parse_args():
    """Parse command line arguments."""
    if len(sys.argv) != 4:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
        count = int(sys.argv[2])
        months = int(sys.argv[3])
        return user_id, count, months
    except ValueError:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)


def verify_user(conn, user_id):
    """Verify that the user exists in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        print(f"No user found with id {user_id}.")
        sys.exit(1)
    return row["name"]


def select_category():
    """Select a category based on weights."""
    categories = list(CATEGORIES.keys())
    weights = [CATEGORIES[cat]["weight"] for cat in categories]
    return random.choices(categories, weights=weights, k=1)[0]


def generate_expense(user_id, start_date, end_date):
    """Generate a single random expense."""
    category = select_category()
    cat_data = CATEGORIES[category]

    amount = random.randint(cat_data["min"], cat_data["max"])
    description = random.choice(cat_data["descriptions"])

    # Generate random date within range
    days_range = (end_date - start_date).days
    random_days = random.randint(0, days_range)
    expense_date = start_date + timedelta(days=random_days)

    return (
        user_id,
        amount,
        category,
        expense_date.strftime("%Y-%m-%d"),
        description
    )


def seed_expenses(user_id, count, months):
    """Generate and insert expenses for the given user."""
    conn = get_db()

    # Calculate date range (approximate months as 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)

    # Generate all expenses
    expenses = []
    for _ in range(count):
        expenses.append(generate_expense(user_id, start_date, end_date))

    # Insert all expenses in a single transaction
    cursor = conn.cursor()
    try:
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inserting expenses: {e}")
        conn.close()
        sys.exit(1)

    # Fetch some sample records for display
    cursor.execute(
        "SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 5",
        (user_id,)
    )
    samples = cursor.fetchall()

    conn.close()

    # Print confirmation
    print(f"Successfully inserted {count} expenses!")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("\nSample expenses:")
    for sample in samples:
        print(f"  - ID {sample['id']}: Rs. {sample['amount']} ({sample['category']}) - {sample['description']} on {sample['date']}")


if __name__ == "__main__":
    user_id, count, months = parse_args()

    conn = get_db()
    user_name = verify_user(conn, user_id)
    conn.close()

    print(f"Seeding {count} expenses for {user_name} (user_id={user_id}) across {months} months...")
    seed_expenses(user_id, count, months)
