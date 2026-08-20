from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

DATABASE = "library.db"

def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the books table."""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            is_issued INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.route("/")
def index():
    """Render the main dashboard page."""
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    
    # Calculate statistics
    total_books = len(books)
    issued_books = sum(1 for book in books if book["is_issued"])
    available_books = total_books - issued_books
    
    conn.close()
    
    stats = {
        "total": total_books,
        "issued": issued_books,
        "available": available_books
    }
    
    return render_template("index.html", books=books, stats=stats)

@app.route("/api/books", methods=["GET"])
def get_books():
    """API endpoint to get all books."""
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    conn.close()
    
    books_list = [dict(book) for book in books]
    return jsonify(books_list)

@app.route("/api/books", methods=["POST"])
def add_book():
    """API endpoint to add a new book."""
    data = request.get_json()
    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    
    if not title or not author:
        return jsonify({"error": "Title and author are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO books (title, author) VALUES (?, ?)",
        (title, author)
    )
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        "id": book_id,
        "title": title,
        "author": author,
        "is_issued": 0
    }), 201

@app.route("/api/books/<int:book_id>/issue", methods=["POST"])
def issue_book(book_id):
    """API endpoint to issue a book."""
    conn = get_db_connection()
    book = conn.execute("SELECT is_issued FROM books WHERE id = ?", (book_id,)).fetchone()
    
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
def return_book(book_id):
    """API endpoint to return a book."""
    conn = get_db_connection()
    book = conn.execute("SELECT is_issued FROM books WHERE id = ?", (book_id,)).fetchone()
    
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
def get_stats():
    """API endpoint to get library statistics."""
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    
    total_books = len(books)
    issued_books = sum(1 for book in books if book["is_issued"])
    available_books = total_books - issued_books
    
    return jsonify({
        "total": total_books,
        "issued": issued_books,
        "available": available_books
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)