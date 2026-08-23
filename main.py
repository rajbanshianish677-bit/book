import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


class LibraryManager:

    def __init__(self, db_name="library.db"):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        """Creates the books table and users table if they don't exist."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                is_issued INTEGER DEFAULT 0
            )
        """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('librarian', 'student')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        # Seed a default librarian if none exists
        existing = self.cursor.execute(
            "SELECT 1 FROM users WHERE role = 'librarian' LIMIT 1"
        ).fetchone()
        if not existing:
            self.cursor.execute(
                """
                INSERT INTO users (school_id, email, username, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "LIB-1",
                    "librarian@library.local",
                    "librarian",
                    generate_password_hash("admin123"),
                    "librarian",
                ),
            )
        self.conn.commit()

    # ---------- Authentication ----------
    def authenticate(self, identifier, password):
        """Return a user row dict if credentials are valid, else None."""
        row = self.cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ? OR school_id = ?",
            (identifier, identifier, identifier),
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            return row
        return None

    # ---------- Book operations ----------
    def add_book(self, title, author):
        """Add a new book to the library."""
        self.cursor.execute(
            "INSERT INTO books (title, author) VALUES (?, ?)", (title, author)
        )
        self.conn.commit()
        print(f"Success: '{title}' by {author} added to the library.")

    def view_books(self):
        """Display all books and their current status."""
        self.cursor.execute("SELECT * FROM books")
        books = self.cursor.fetchall()

        if not books:
            print("\nNo books found in the library database.")
            return

        print("\n--- Library Catalog ---")
        for b in books:
            status = "Issued" if b["is_issued"] else "Available"
            print(
                f"ID: {b['id']} | Title: {b['title']} | Author: {b['author']} | Status: {status}"
            )
        print("-" * 23)

    def search_books(self, query):
        """Search by book ID or exact title/author. Returns matching rows."""
        results = []
        if query.isdigit():
            row = self.cursor.execute(
                "SELECT * FROM books WHERE id = ?", (int(query),)
            ).fetchone()
            if row:
                results.append(row)

        rows = self.cursor.execute(
            "SELECT * FROM books WHERE LOWER(title) = LOWER(?) OR LOWER(author) = LOWER(?)",
            (query, query),
        ).fetchall()
        results.extend(rows)

        # De-duplicate by id
        seen = set()
        unique = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)
        return unique

    def issue_book(self, book_id):
        """Issue a book if it is available."""
        result = self.cursor.execute(
            "SELECT is_issued FROM books WHERE id = ?", (book_id,)
        ).fetchone()

        if not result:
            print("Error: Book ID not found.")
        elif result["is_issued"] == 1:
            print("Notice: Book is already issued.")
        else:
            self.cursor.execute(
                "UPDATE books SET is_issued = 1 WHERE id = ?", (book_id,)
            )
            self.conn.commit()
            print(f"Success: Book ID {book_id} has been issued.")

    def return_book(self, book_id):
        """Return an issued book."""
        result = self.cursor.execute(
            "SELECT is_issued FROM books WHERE id = ?", (book_id,)
        ).fetchone()

        if not result:
            print("Error: Book ID not found.")
        elif result["is_issued"] == 0:
            print("Notice: Book was not issued.")
        else:
            self.cursor.execute(
                "UPDATE books SET is_issued = 0 WHERE id = ?", (book_id,)
            )
            self.conn.commit()
            print(f"Success: Book ID {book_id} returned successfully.")

    def close(self):
        """Close the database connection."""
        self.conn.close()


def login_flow():
    """Prompt for credentials and return a user row (or None)."""
    library = LibraryManager()
    print("\n=== Library Management System - Login ===")
    print("(Log in with username, email, or school ID)")

    identifier = input("Username / Email / School ID: ").strip()
    import getpass
    password = getpass.getpass("Password: ")

    user = library.authenticate(identifier, password)
    if user is None:
        print("\nError: Invalid credentials.")
        library.close()
        return None
    print(f"\nWelcome, {user['username']} ({user['role']})!")
    return library, user


def run_librarian(library):
    """Librarian menu - full control."""
    while True:
        print("\n=== Librarian Menu ===")
        print("1. Add Book")
        print("2. View All Books")
        print("3. Issue Book")
        print("4. Return Book")
        print("5. Search Book")
        print("6. Log Out")

        choice = input("Select an option (1-6): ").strip()

        if choice == "1":
            title = input("Enter book title: ").strip()
            author = input("Enter author name: ").strip()
            if title and author:
                library.add_book(title, author)
            else:
                print("Error: Title and author cannot be empty.")

        elif choice == "2":
            library.view_books()

        elif choice == "3":
            try:
                book_id = int(input("Enter Book ID to issue: "))
                library.issue_book(book_id)
            except ValueError:
                print("Error: Please enter a valid numerical ID.")

        elif choice == "4":
            try:
                book_id = int(input("Enter Book ID to return: "))
                library.return_book(book_id)
            except ValueError:
                print("Error: Please enter a valid numerical ID.")

        elif choice == "5":
            query = input("Enter book ID or exact title/author: ").strip()
            results = library.search_books(query)
            if not results:
                print("\nNo matching book found.")
            else:
                print("\n--- Search Results ---")
                for b in results:
                    status = "Issued" if b["is_issued"] else "Available"
                    print(
                        f"ID: {b['id']} | Title: {b['title']} | Author: {b['author']} | Status: {status}"
                    )

        elif choice == "6":
            print("Logging out. Goodbye!")
            return

        else:
            print("Error: Invalid choice. Please select 1 through 6.")


def run_student(library):
    """Student menu - search only."""
    while True:
        print("\n=== Student Menu ===")
        print("1. Search Book")
        print("2. Log Out")

        choice = input("Select an option (1-2): ").strip()

        if choice == "1":
            query = input("Enter book ID or exact title/author: ").strip()
            results = library.search_books(query)
            if not results:
                print("\nNo matching book found.")
                print("(Students can only search by book ID or exact title/author.)")
            else:
                print("\n--- Search Results ---")
                for b in results:
                    status = "Issued" if b["is_issued"] else "Available"
                    print(
                        f"ID: {b['id']} | Title: {b['title']} | Author: {b['author']} | Status: {status}"
                    )

        elif choice == "2":
            print("Logging out. Goodbye!")
            return

        else:
            print("Error: Invalid choice. Please select 1 or 2.")


def main():
    session = login_flow()
    if session is None:
        return
    library, user = session
    try:
        if user["role"] == "librarian":
            run_librarian(library)
        else:
            run_student(library)
    finally:
        library.close()


def run_web():
    """Run the web UI version."""
    import subprocess
    import sys
    import os

    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, 'app.py')

    print("Starting Library Management Web UI...")
    print("Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop the server")

    try:
        subprocess.run([sys.executable, app_path], cwd=script_dir)
    except KeyboardInterrupt:
        print("\nWeb server stopped.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--web':
        run_web()
    else:
        main()
