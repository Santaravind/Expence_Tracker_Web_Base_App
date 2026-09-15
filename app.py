"""
=============================================================================
 ExpenseFlow - Personal Expense Tracker & Monthly Visual Analytics App
 Built with Flask 3.x, SQLite 3, and Modern Web Design
=============================================================================
"""

import os
import sqlite3
import csv
import io
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, jsonify, Response
)
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask Application
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "expenseflow_super_secret_key_2026_!#*&")
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "expense_tracker.db")

# -----------------------------------------------------------------------------
# Database Helpers & Initialization
# -----------------------------------------------------------------------------
def get_db():
    """Connect to the SQLite database with Row factory."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables and seed initial demo account."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                currency TEXT DEFAULT '₹',
                monthly_budget REAL DEFAULT 50000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Expenses Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                date TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 3. Seed Demo Account if not exists
        cursor.execute("SELECT id FROM users WHERE email = ?", ("demo@example.com",))
        demo_user = cursor.fetchone()
        
        if not demo_user:
            demo_password = generate_password_hash("password123")
            cursor.execute("""
                INSERT INTO users (name, email, password, currency, monthly_budget)
                VALUES (?, ?, ?, ?, ?)
            """, ("Demo User", "demo@example.com", demo_password, "₹", 50000.0))
            
            demo_user_id = cursor.lastrowid
            
            # Seed realistic sample expenses for the demo user
            today = date.today()
            curr_year = today.year
            curr_month = f"{today.month:02d}"

            sample_expenses = [
                ("Apartment Rent", 18000.00, "Rent", "Net Banking", f"{curr_year}-{curr_month}-01", "Monthly house rent transfer"),
                ("Grocery Supermarket", 3450.50, "Shopping", "UPI", f"{curr_year}-{curr_month}-03", "Weekly vegetables and household items"),
                ("Electricity & Water Bill", 2200.00, "Bills", "Net Banking", f"{curr_year}-{curr_month}-05", "Monthly utility payment"),
                ("Weekend Bistro Dinner", 1850.00, "Food", "Credit Card", f"{curr_year}-{curr_month}-07", "Dinner with friends"),
                ("Fuel & Petrol Refill", 2500.00, "Transport", "Debit Card", f"{curr_year}-{curr_month}-09", "Car tank full refill"),
                ("Pharmacy & Health Check", 1200.00, "Health", "UPI", f"{curr_year}-{curr_month}-12", "Vitamins & routine checkup"),
                ("Movie & Popcorn Night", 950.00, "Entertainment", "Credit Card", f"{curr_year}-{curr_month}-15", "Cinema tickets & snacks"),
                ("Online Tech Gadget", 4200.00, "Shopping", "Credit Card", f"{curr_year}-{curr_month}-18", "Wireless mechanical keyboard"),
                ("Cafe Coffee & Snacks", 450.00, "Food", "UPI", f"{curr_year}-{curr_month}-20", "Work from cafe session"),
                ("Broadband Fiber WiFi", 999.00, "Bills", "UPI", f"{curr_year}-{curr_month}-22", "High-speed internet monthly recharge"),
            ]

            for title, amount, category, payment_method, exp_date, notes in sample_expenses:
                cursor.execute("""
                    INSERT INTO expenses (user_id, title, amount, category, payment_method, date, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (demo_user_id, title, amount, category, payment_method, exp_date, notes))

        conn.commit()

# Ensure DB is created on startup
init_db()

# -----------------------------------------------------------------------------
# Authentication Guard Decorator
# -----------------------------------------------------------------------------
def login_required(f):
    """Decorator to require login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access your expense dashboard.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Retrieve current logged in user object from database."""
    if 'user_id' not in session:
        return None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
        return cursor.fetchone()

# -----------------------------------------------------------------------------
# Public & Landing Routes
# -----------------------------------------------------------------------------
@app.route("/")
@app.route("/home")
def home():
    """Landing and Home Page."""
    return render_template("index.html")

@app.route("/about")
def about():
    """About ExpenseFlow & Architecture Page."""
    return render_template("about.html")

@app.route("/contect", methods=["GET", "POST"])
@app.route("/contact", methods=["GET", "POST"])
def contect():
    """Contact Us & FAQ Page."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("Please fill in all required contact fields.", "danger")
        else:
            flash(f"Thank you, {name}! Your message regarding '{subject}' has been received.", "success")
            return redirect(url_for("contect"))
            
    return render_template("contect.html")

# -----------------------------------------------------------------------------
# Authentication Flow: Register, Login, Logout
# -----------------------------------------------------------------------------
@app.route("/registation", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def registation():
    """User Registration Route."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        currency = request.form.get("currency", "₹").strip()
        budget = request.form.get("budget", 50000.0)
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        try:
            budget = float(budget)
        except ValueError:
            budget = 50000.0

        if not name or not email or not password:
            flash("Please fill in all mandatory fields.", "danger")
            return render_template("registation.html")

        if password != confirm_password:
            flash("Passwords do not match! Please check and try again.", "danger")
            return render_template("registation.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("registation.html")

        hashed_password = generate_password_hash(password)

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (name, email, password, currency, monthly_budget)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, email, hashed_password, currency, budget))
                conn.commit()

            flash("Account successfully created! Please sign in with your credentials.", "success")
            return redirect(url_for("login", email=email))

        except sqlite3.IntegrityError:
            flash("An account with this email address already exists. Please login.", "warning")
            return redirect(url_for("login", email=email))

    return render_template("registation.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """User Login Route."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['currency'] = user['currency']
            flash(f"Welcome back, {user['name']}!", "success")
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash("Invalid email address or password. Please try again.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    """User Logout and Session Clear."""
    user_name = session.get('user_name', 'User')
    session.clear()
    flash(f"Goodbye, {user_name}! You have been signed out safely.", "info")
    return redirect(url_for("home"))

# -----------------------------------------------------------------------------
# User Dashboard & Expense Management
# -----------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    """User Dashboard with KPI Stats, Expense Filters, and Management."""
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    today = date.today()
    curr_month_str = f"{today.year}-{today.month:02d}"

    with get_db() as conn:
        cursor = conn.cursor()

        # Fetch all expenses of current user (sorted latest first)
        cursor.execute("""
            SELECT * FROM expenses 
            WHERE user_id = ? 
            ORDER BY date DESC, id DESC
        """, (user["id"],))
        expenses = cursor.fetchall()

        # Calculate Monthly Total for current month
        cursor.execute("""
            SELECT SUM(amount) as monthly_sum 
            FROM expenses 
            WHERE user_id = ? AND date LIKE ?
        """, (user["id"], f"{curr_month_str}%"))
        sum_row = cursor.fetchone()
        monthly_total = sum_row["monthly_sum"] or 0.0

        # Category Breakdown for current month
        cursor.execute("""
            SELECT category, SUM(amount) as cat_total 
            FROM expenses 
            WHERE user_id = ? AND date LIKE ?
            GROUP BY category 
            ORDER BY cat_total DESC
        """, (user["id"], f"{curr_month_str}%"))
        cat_rows = cursor.fetchall()

    # Category dictionary for Chart.js
    category_breakdown = {row["category"]: round(row["cat_total"], 2) for row in cat_rows}

    # Top category
    top_category = (cat_rows[0]["category"], cat_rows[0]["cat_total"]) if cat_rows else None

    # Budget Calculations
    monthly_budget = user["monthly_budget"] or 50000.0
    remaining_budget = monthly_budget - monthly_total
    budget_percent = (monthly_total / monthly_budget * 100) if monthly_budget > 0 else 0

    return render_template(
        "dashboard.html",
        user=user,
        expenses=expenses,
        monthly_total=monthly_total,
        monthly_budget=monthly_budget,
        remaining_budget=remaining_budget,
        budget_percent=budget_percent,
        top_category=top_category,
        category_breakdown=category_breakdown,
        current_date=today.strftime("%Y-%m-%d")
    )

@app.route("/add-expense", methods=["POST"])
@login_required
def add_expense():
    """Create a new expense transaction."""
    user_id = session['user_id']
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", 0)
    category = request.form.get("category", "Others").strip()
    payment_method = request.form.get("payment_method", "UPI").strip()
    exp_date = request.form.get("date", "").strip() or date.today().strftime("%Y-%m-%d")
    notes = request.form.get("notes", "").strip()

    try:
        amount = float(amount)
        if amount <= 0:
            flash("Expense amount must be greater than zero.", "danger")
            return redirect(url_for("dashboard"))
    except ValueError:
        flash("Invalid amount value provided.", "danger")
        return redirect(url_for("dashboard"))

    if not title:
        flash("Please enter an expense title / description.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (user_id, title, amount, category, payment_method, date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, amount, category, payment_method, exp_date, notes))
        conn.commit()

    flash(f"Expense '{title}' for {amount:.2f} logged successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/edit-expense/<int:expense_id>", methods=["POST"])
@login_required
def edit_expense(expense_id):
    """Update an existing expense transaction."""
    user_id = session['user_id']
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", 0)
    category = request.form.get("category", "Others").strip()
    payment_method = request.form.get("payment_method", "UPI").strip()
    exp_date = request.form.get("date", "").strip()
    notes = request.form.get("notes", "").strip()

    try:
        amount = float(amount)
        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for("dashboard"))
    except ValueError:
        flash("Invalid amount value.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        cursor = conn.cursor()
        # Verify ownership
        cursor.execute("SELECT id FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
        if not cursor.fetchone():
            flash("Unauthorized action or expense not found.", "danger")
            return redirect(url_for("dashboard"))

        cursor.execute("""
            UPDATE expenses 
            SET title = ?, amount = ?, category = ?, payment_method = ?, date = ?, notes = ?
            WHERE id = ? AND user_id = ?
        """, (title, amount, category, payment_method, exp_date, notes, expense_id, user_id))
        conn.commit()

    flash(f"Expense '{title}' updated successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/delete-expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    """Delete an expense transaction."""
    user_id = session['user_id']

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
        conn.commit()

    flash("Expense record deleted successfully.", "info")
    return redirect(url_for("dashboard"))

@app.route("/update-budget", methods=["POST"])
@login_required
def update_budget():
    """Update user's preferred currency and monthly budget target."""
    user_id = session['user_id']
    currency = request.form.get("currency", "₹").strip()
    monthly_budget = request.form.get("monthly_budget", 50000.0)

    try:
        monthly_budget = float(monthly_budget)
        if monthly_budget < 0:
            monthly_budget = 50000.0
    except ValueError:
        monthly_budget = 50000.0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET currency = ?, monthly_budget = ? WHERE id = ?
        """, (currency, monthly_budget, user_id))
        conn.commit()

    session['currency'] = currency
    flash("Monthly budget settings updated successfully!", "success")
    return redirect(url_for("dashboard"))

# -----------------------------------------------------------------------------
# Monthly Analytics & Reports
# -----------------------------------------------------------------------------
@app.route("/reports")
@login_required
def reports():
    """Monthly Visual Reports, Breakdown Charts & Itemized Ledger."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    today = date.today()
    selected_month = request.args.get("month", f"{today.year}-{today.month:02d}")

    try:
        month_dt = datetime.strptime(selected_month, "%Y-%m")
        month_label = month_dt.strftime("%B %Y")
    except ValueError:
        selected_month = f"{today.year}-{today.month:02d}"
        month_label = today.strftime("%B %Y")

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Month Transactions
        cursor.execute("""
            SELECT * FROM expenses 
            WHERE user_id = ? AND date LIKE ? 
            ORDER BY date DESC, id DESC
        """, (user["id"], f"{selected_month}%"))
        transactions = cursor.fetchall()

        # 2. Total for Selected Month
        cursor.execute("""
            SELECT SUM(amount) as total 
            FROM expenses 
            WHERE user_id = ? AND date LIKE ?
        """, (user["id"], f"{selected_month}%"))
        monthly_total = cursor.fetchone()["total"] or 0.0

        # 3. Category Breakdown
        cursor.execute("""
            SELECT category, SUM(amount) as cat_sum 
            FROM expenses 
            WHERE user_id = ? AND date LIKE ? 
            GROUP BY category 
            ORDER BY cat_sum DESC
        """, (user["id"], f"{selected_month}%"))
        cat_rows = cursor.fetchall()

        # 4. Daily Spending Trend
        cursor.execute("""
            SELECT date, SUM(amount) as day_sum 
            FROM expenses 
            WHERE user_id = ? AND date LIKE ? 
            GROUP BY date 
            ORDER BY date ASC
        """, (user["id"], f"{selected_month}%"))
        daily_rows = cursor.fetchall()

        # 5. Payment Method Breakdown
        cursor.execute("""
            SELECT payment_method, SUM(amount) as pay_sum 
            FROM expenses 
            WHERE user_id = ? AND date LIKE ? 
            GROUP BY payment_method 
            ORDER BY pay_sum DESC
        """, (user["id"], f"{selected_month}%"))
        pay_rows = cursor.fetchall()

    category_breakdown = {row["category"]: round(row["cat_sum"], 2) for row in cat_rows}
    daily_breakdown = {row["date"]: round(row["day_sum"], 2) for row in daily_rows}
    payment_breakdown = {row["payment_method"]: round(row["pay_sum"], 2) for row in pay_rows}

    # Calculations
    active_days_count = len(daily_breakdown) if daily_breakdown else 1
    daily_avg = monthly_total / active_days_count if active_days_count > 0 else 0.0

    highest_day = None
    if daily_rows:
        sorted_days = sorted(daily_rows, key=lambda x: x["day_sum"], reverse=True)
        highest_day = (sorted_days[0]["date"], sorted_days[0]["day_sum"])

    remaining_budget = user["monthly_budget"] - monthly_total

    return render_template(
        "reports.html",
        user=user,
        transactions=transactions,
        selected_month=selected_month,
        month_label=month_label,
        monthly_total=monthly_total,
        daily_avg=daily_avg,
        highest_day=highest_day,
        remaining_budget=remaining_budget,
        category_breakdown=category_breakdown,
        daily_breakdown=daily_breakdown,
        payment_breakdown=payment_breakdown
    )

# -----------------------------------------------------------------------------
# Data Export: CSV Download
# -----------------------------------------------------------------------------
@app.route("/export-csv")
@login_required
def export_csv():
    """Export expenses to CSV spreadsheet file."""
    user_id = session['user_id']
    month_filter = request.args.get("month")

    with get_db() as conn:
        cursor = conn.cursor()
        if month_filter:
            cursor.execute("""
                SELECT date, title, category, payment_method, amount, notes, created_at
                FROM expenses 
                WHERE user_id = ? AND date LIKE ? 
                ORDER BY date DESC
            """, (user_id, f"{month_filter}%"))
            filename = f"expenseflow_report_{month_filter}.csv"
        else:
            cursor.execute("""
                SELECT date, title, category, payment_method, amount, notes, created_at
                FROM expenses 
                WHERE user_id = ? 
                ORDER BY date DESC
            """, (user_id,))
            filename = f"expenseflow_all_expenses_{date.today().strftime('%Y%m%d')}.csv"

        rows = cursor.fetchall()

    # Create in-memory CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Title / Description", "Category", "Payment Method", "Amount", "Notes", "Timestamp"])

    for row in rows:
        writer.writerow([row["date"], row["title"], row["category"], row["payment_method"], row["amount"], row["notes"], row["created_at"]])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# -----------------------------------------------------------------------------
# Application Runner
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("ExpenseFlow Server running at http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)