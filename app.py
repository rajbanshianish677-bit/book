from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3
import os
from functools import wraps

from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
    UserMixin,
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret key for sessions - for production set via env var
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."

DATABASE = "library.db"

# Default librarian account seeded on first run
DEFAULT_LIBRARIAN_USERNAME = os.environ.get("LIBRARIAN_USERNAME", "librarian")
DEFAULT_LIBRARIAN_PASSWORD = os.environ.get("LIBRARIAN_PASSWORD", "admin123")


def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with books and users tables."""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            is_issued INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('librarian', 'student')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Seed a default librarian if no librarian exists
    existing = conn.execute(
        "SELECT 1 FROM users WHERE role = 'librarian' LIMIT 1"
    ).fetchone()
    if not existing:
        conn.execute(
            """
            INSERT INTO users (school_id, email, username, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "LIB-1",
                "librarian@library.local",
                DEFAULT_LIBRARIAN_USERNAME,
                generate_password_hash(DEFAULT_LIBRARIAN_PASSWORD),
                "librarian",
            ),
        )
        conn.commit()
    conn.close()


# Initialize database on startup
init_db()


# ---------- User loader for Flask-Login ----------
class User(UserMixin):
    def __init__(self, id, username, email, school_id, role):
        self.id = id
        self.username = username
        self.email = email
        self.school_id = school_id
        self.role = role

    def is_librarian(self):
        return self.role == "librarian"


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return User(row["id"], row["username"], row["email"], row["school_id"], row["role"])


def role_required(role):
    """Decorator restricting a route to a specific role."""
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role != role:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Forbidden: insufficient permissions"}), 403
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------- Auth routes ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ? OR school_id = ?",
            (identifier, identifier, identifier),
        ).fetchone()
        conn.close()

        if row and check_password_hash(row["password_hash"], password):
            user = User(row["id"], row["username"], row["email"], row["school_id"], row["role"])
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("index"))
        flash("Invalid credentials. Please try again.", "error")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        school_id = request.form.get("school_id", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "student").strip()

        if not (school_id and email and username and password):
            flash("All fields are required.", "error")
        elif role not in ("librarian", "student"):
            flash("Invalid role selected.", "error")
        else:
            conn = get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users (school_id, email, username, password_hash, role)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (school_id, email, username,
                     generate_password_hash(password), role),
                )
                conn.commit()
                user_id = cursor.lastrowid
                row = conn.execute(
                    "SELECT * FROM users WHERE id = ?", (user_id,)
                ).fetchone()
                conn.close()
                user = User(row["id"], row["username"], row["email"],
                            row["school_id"], row["role"])
                login_user(user)
                flash("Account created successfully!", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                conn.close()
                flash("School ID, email, or username already exists.", "error")

    return render_template("signup.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------- Main dashboard ----------
@app.route("/")
@login_required
def index():
    """Render dashboard - view depends on role."""
    conn = get_db_connection()

    if current_user.is_librarian():
        # Librarian: full catalog + stats
        books = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
        total_books = len(books)
        issued_books = sum(1 for b in books if b["is_issued"])
        stats = {
            "total": total_books,
            "issued": issued_books,
            "available": total_books - issued_books,
        }
        role = "librarian"
    else:
        # Student: empty catalog initially - students search instead
        books = []
        stats = {"total": 0, "issued": 0, "available": 0}
        role = "student"

    conn.close()
    return render_template("index.html", books=books, stats=stats, role=role)


# ---------- Book API ----------
@app.route("/api/books", methods=["GET"])
@role_required("librarian")
def get_books():
    """API: list all books (librarian only)."""
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(b) for b in books])


@app.route("/api/books", methods=["POST"])
@role_required("librarian")
def add_book():
    """API: add a book (librarian only)."""
    data = request.get_json()
    title = data.get("title", "").strip()
    author = data.get("author", "").strip()

    if not title or not author:
        return jsonify({"error": "Title and author are required"}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO books (title, author) VALUES (?, ?)", (title, author)
    )
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()

    return jsonify({"id": book_id, "title": title,
                    "author": author, "is_issued": 0}), 201


@app.route("/api/books/search", methods=["GET"])
@login_required
def search_books():
    """API: search by book ID or exact title/author.

    Available to all logged-in users (both librarian and student).
    """
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    conn = get_db_connection()
    books = []
    # If the query is a number, match by ID first
    if query.isdigit():
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (int(query),)
        ).fetchone()
        if row:
            books.append(dict(row))

    # Also match by exact title or author (case-insensitive)
    rows = conn.execute(
        "SELECT * FROM books WHERE LOWER(title) = LOWER(?) OR LOWER(author) = LOWER(?)",
        (query, query),
    ).fetchall()
    books.extend(dict(r) for r in rows)
    conn.close()

    # De-duplicate by id
    seen = set()
    unique = []
    for b in books:
        if b["id"] not in seen:
            seen.add(b["id"])
            unique.append(b)
    return jsonify(unique)


@app.route("/api/books/<int:book_id>/issue", methods=["POST"])
@role_required("librarian")
def issue_book(book_id):
    """API: issue a book (librarian only)."""
    conn = get_db_connection()
    book = conn.execute(
        "SELECT is_issued FROM books WHERE id = ?", (book_id,)
    ).fetchone()

    if not book:
        conn.close()
        return jsonify({"error": "Book not found"}), 404

    if book["is_issued"]:
        conn.close()
        return jsonify({"error": "Book is already issued"}), 400

    conn.execute("UPDATE books SET is_issued = 1 WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Book issued successfully", "is_issued": 1})


@app.route("/api/books/<int:book_id>/return", methods=["POST"])
@role_required("librarian")
def return_book(book_id):
    """API: return a book (librarian only)."""
    conn = get_db_connection()
    book = conn.execute(
        "SELECT is_issued FROM books WHERE id = ?", (book_id,)
    ).fetchone()

    if not book:
        conn.close()
        return jsonify({"error": "Book not found"}), 404

    if not book["is_issued"]:
        conn.close()
        return jsonify({"error": "Book was not issued"}), 400

    conn.execute("UPDATE books SET is_issued = 0 WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Book returned successfully", "is_issued": 0})


@app.route("/api/stats", methods=["GET"])
@role_required("librarian")
def get_stats():
    """API: library statistics (librarian only)."""
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()

    total_books = len(books)
    issued_books = sum(1 for b in books if b["is_issued"])
    return jsonify({
        "total": total_books,
        "issued": issued_books,
        "available": total_books - issued_books,
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)