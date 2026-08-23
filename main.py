import sqlite3
import os

from werkzeug.security import generate_password_hash, check_password_hash

# Default librarian account seeded on first run (must match app.py)
DEFAULT_LIBRARIAN_USERNAME = os.environ.get("LIBRARIAN_USERNAME", "librarian")
DEFAULT_LIBRARIAN_PASSWORD = os.environ.get("LIBRARIAN_PASSWORD", "admin123")


class LibraryManager:

    def __init__(self, db_name="library.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.role = None
        self.username = None
        self.setup_database()

    def setup_database(self):
        """Creates the books and users tables if they don't exist."""
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
        self.conn.commit()

        # Seed a default librarian if no librarian exists
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
                    DEFAULT_LIBRARIAN_USERNAME,
                    generate_password_hash(DEFAULT_LIBRARIAN_PASSWORD),
                    "librarian",
                ),
            )
            self.conn.commit()

    # ---------- Authentication ----------

    def login(self):
        """Prompt for credentials and authenticate against the users table."""
        print("\n=== Login ===")
        identifier = input("Username/Email/School ID: ").strip()
        password = input("Password: ")

        row = self.cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ? OR school_id = ?",
            (identifier, identifier, identifier),
        ).fetchone()

        # row is a plain tuple: (id, school_id, email, username, password_hash, role, created_at)
        if row and check_password_hash(row[4], password):
            self.role = row[5]
            self.username = row[3]
            print(f"Success: Logged in as {self.username} ({self.role}).")
            return True

        print("Error: Invalid credentials.")
        return False

    def is_librarian(self):
        return self.role == "librarian"

    def search_book(self, query):
        """Search by book ID or exact title/author (available to students)."""
        query = query.strip()
        if not query:
            return

        books = []
        if query.isdigit():
            row = self.cursor.execute(
                "SELECT id, title, author, is_issued FROM books WHERE id = ?",
                (int(query),),
            ).fetchone()
            if row:
                books.append(row)

        rows = self.cursor.execute(
            """
            SELECT id, title, author, is_issued FROM books
            WHERE LOWER(title) = LOWER(?) OR LOWER(author) = LOWER(?)
            """,
            (query, query),
        ).fetchall()
        books.extend(rows)

        # Deduplicate
        seen = set()
        unique = []
        for b in books:
            b_id = b[0]
            if b_id not in seen:
                seen.add(b_id)
                unique.append(b)

        if not unique:
            print("\nNo books match your search.")
            return

        print("\n--- Search Results ---")
        for book_id, title, author, is_issued in unique:
            status = "Issued" if is_issued else "Available"
            print(f"ID: {book_id} | Title: {title} | Author: {author} | Status: {status}")
        print("-" * 28)

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
        for book_id, title, author, is_issued in books:
            status = "Issued" if is_issued else "Available"
            print(
                f"ID: {book_id} | Title: {title} | Author: {author} | Status: {status}"
            )
        print("-" * 23)

    def issue_book(self, book_id):
        """Issue a book if it is available."""
        self.cursor.execute(
            "SELECT is_issued FROM books WHERE id = ?", (book_id,)
        )
        result = self.cursor.fetchone()

        if not result:
            print("Error: Book ID not found.")
        elif result[0] == 1:
            print("Notice: Book is already issued.")
        else:
            self.cursor.execute(
                "UPDATE books SET is_issued = 1 WHERE id = ?", (book_id,)
            )
            self.conn.commit()
            print(f"Success: Book ID {book_id} has been issued.")

    def return_book(self, book_id):
        """Return an issued book."""
        self.cursor.execute(
            "SELECT is_issued FROM books WHERE id = ?", (book_id,)
        )
        result = self.cursor.fetchone()

        if not result:
            print("Error: Book ID not found.")
        elif result[0] == 0:
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


def main():
    library = LibraryManager()

    # Authenticate first
    if not library.login():
        library.close()
        return

    if library.is_librarian():
        run_librarian_menu(library)
    else:
        run_student_menu(library)

    library.close()


def run_librarian_menu(library):
    """Librarian gets the full management menu."""
    while True:
        print("\n=== Library Management System (Librarian) ===")
        print("1. Add Book")
        print("2. View All Books")
        print("3. Issue Book")
        print("4. Return Book")
        print("5. Search Book")
        print("6. Logout")

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
            query = input("Enter Book ID or exact title/author: ").strip()
            library.search_book(query)

        elif choice == "6":
            print("Logging out. Goodbye!")
            break

        else:
            print("Error: Invalid choice. Please select 1 through 6.")


def run_student_menu(library):
    """Student gets a search-only menu."""
    while True:
        print("\n=== Library Management System (Student) ===")
        print("1. Search Book (by ID or exact name)")
        print("2. Logout")

        choice = input("Select an option (1-2): ").strip()

        if choice == "1":
            query = input("Enter Book ID or exact title/author: ").strip()
            library.search_book(query)

        elif choice == "2":
            print("Logging out. Goodbye!")
            break

        else:
            print("Error: Invalid choice. Please select 1 or 2.")


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