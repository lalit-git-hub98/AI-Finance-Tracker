import sqlite3
from datetime import date, datetime
# Database connection
def get_conn():
    return sqlite3.connect("utils/expense_tracker.db", check_same_thread=False)

# Initialize database
def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                recurring BOOLEAN DEFAULT 0,
                location TEXT,
                payment_method TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS budget_settings (
                setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                monthly_budget REAL DEFAULT 0,
                savings_goal REAL DEFAULT 0,
                actual_savings REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        conn.commit()

# User authentication functions
def register_user(first, last, email, password):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
                        (first, last, email, password))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(email, password):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, first_name, last_name FROM users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()
        return user  # (user_id, first_name, last_name)

# Budget and savings functions
def get_budget_settings(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT monthly_budget, savings_goal, actual_savings FROM budget_settings WHERE user_id = ?", (user_id,))
        result = cur.fetchone()

        if result:
            return result
        else:
            cur.execute("INSERT INTO budget_settings (user_id, monthly_budget, savings_goal, actual_savings) VALUES (?, 0, 0, 0)", (user_id,))
            conn.commit()
            return (0, 0, 0)

def update_budget_settings(user_id, monthly_budget, savings_goal, actual_savings):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE budget_settings 
            SET monthly_budget = ?, savings_goal = ?, actual_savings = ?
            WHERE user_id = ?
        """, (monthly_budget, savings_goal, actual_savings, user_id))

        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO budget_settings (user_id, monthly_budget, savings_goal, actual_savings)
                VALUES (?, ?, ?, ?)
            """, (user_id, monthly_budget, savings_goal, actual_savings))
        conn.commit()

def get_total_expenses(user_id):
    current_date = datetime.now()
    current_month = current_date.strftime("%Y-%m")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT SUM(amount) FROM expenses 
            WHERE user_id = ? AND date LIKE ?
        """, (user_id, f"{current_month}%"))
        result = cur.fetchone()
        return result[0] if result[0] else 0
    
def add_expense(user_id, amount, category, date, description, recurring, location, payment_method):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO expenses (user_id, amount, category, date, description, recurring, location, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, amount, category, date, description, recurring, location, payment_method))
        conn.commit()

def get_all_expenses(user_id, limit=50):
    """Get all expenses for a user with limit"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT expense_id, amount, category, date, description, recurring, location, payment_method
            FROM expenses 
            WHERE user_id = ?
            ORDER BY date DESC, expense_id DESC
            LIMIT ?
        """, (user_id, limit))
        return cur.fetchall()

############################ Get Weekly Updates ############################
def get_weekly_expenses(user_id):
    """Get expenses from the last 7 days"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT expense_id, amount, category, date, description, location, payment_method
            FROM expenses 
            WHERE user_id = ? AND date >= ? AND date <= ?
            ORDER BY date DESC
        """, (user_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        return cur.fetchall()

def get_weekly_category_summary(user_id):
    """Get category-wise expense summary for the last 7 days"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT category, SUM(amount) as total_amount, COUNT(*) as count
            FROM expenses 
            WHERE user_id = ? AND date >= ? AND date <= ?
            GROUP BY category
            ORDER BY total_amount DESC
            LIMIT 5
        """, (user_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        return cur.fetchall()

def get_top_weekly_expenses(user_id, limit=2):
    """Get top expenses from the last 7 days by amount"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT amount, category, date, description, location
            FROM expenses 
            WHERE user_id = ? AND date >= ? AND date <= ?
            ORDER BY amount DESC
            LIMIT ?
        """, (user_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), limit))
        return cur.fetchall()