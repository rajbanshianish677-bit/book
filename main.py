import os
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

# Default librarian account (kept in sync with app.py)
DEFAULT_LIBRARIAN_USERNAME = os.environ.get("LIBRARIAN_USERNAME", "librarian")
DEFAULT_LIBRARIAN_PASSWORD = os.environ.get("LIBRARIAN_PASSWORD", "admin123")


def require_confirmation(prompt):
    """Ask for a yes/no confirmation."""
    answer = input(prompt + " (y/n): ").strip().lower()
    return answer in ("y", "yes")


class User:
    def __init__(self, user_id, username, email, school_id, role):
        self.id = user_id
        self.username = username
        self.email = email
        self.school_id = school_id
        self.role = role

    def is_librarian(self):
        return self.role == "librarian"


class LibraryManager:

    def __init__(self, db_name="library.db"):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
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
                role TEXT NOT NULL CHECK (role IN ('librarian', 'student')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.conn.commit()

        # Seed the default librarian if no librarian exists
        librarian = self.cursor.execute(
            "SELECT * FROM users WHERE role = 'librarian' LIMIT 1"
        ).fetchone()
        if not librarian:
            self.cursor.execute(
                """
                INSERT INTO users (school_id, email, username, password_hash, role)
                VALUES (?, ?, ?, ?, 'librarian')
                """,
                (
                    "LIB-1",
                    "librarian@library.local",
                    DEFAULT_LIBRARIAN_USERNAME,
                    generate_password_hash(DEFAULT_LIBRARIAN_PASSWORD),
                ),
            )
            self.conn.commit()
            print(
                "[Setup] Default librarian created: "
                f"username='{DEFAULT_LIBRARIAN_USERNAME}', "
                f"password='{DEFAULT_LIBRARIAN_PASSWORD}'"
            )

    def login(self, identifier, password):
        """Authenticate a user by username, email, or school ID."""
        row = self.cursor.execute(
            """
            SELECT * FROM users
            WHERE username = ? OR email = ? OR school_id = ?
            LIMIT 1
            """,
            (identifier, identifier, identifier),
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            return User(row["id"], row["username"], row["email"], row["school_id"], row["role"])
        return None

    def register(self, school_id, email, username, password, role="student"):
        """Create a new user account."""
        existing = self.cursor.execute(
            "SELECT id FROM users WHERE username = ? OR email = ? OR school_id = ?",
            (username, email, school_id),
        ).fetchone()
        if existing:
            return False, "Username, email, or school ID already exists."
        self.cursor.execute(
            """
            INSERT INTO users (school_id, email, username, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (school_id, email, username, generate_password_hash(password), role),
        )
        self.conn.commit()
        return True, "Account created successfully."

    def add_book(self, title, author):
        """Add a new book to the library. (Librarian only)"""
        self.cursor.execute(
            "INSERT INTO books (title, author) VALUES (?, ?)", (title, author)
        )
        self.conn.commit()
        print(f"Success: '{title}' by {author} added to the library.")

    def search_book(self, query):
        """Search books by ID or exact title/author. (Available to everyone)"""
        rows = []
        if query.isdigit():
            row = self.cursor.execute(
                "SELECT * FROM books WHERE id = ?", (int(query),)
            ).fetchone()
            if row:
                rows.append(dict(row))
        for row in self.cursor.execute(
            "SELECT * FROM books WHERE LOWER(title) = LOWER(?) OR LOWER(author) = LOWER(?)",
            (query, query),
        ).fetchall():
            rows.append(dict(row))

        # De-duplicate by id
        seen = set()
        unique = []
        for row in rows:
            if row["id"] not in seen:
                seen.add(row["id"])
                unique.append(row)
        return unique

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


def auth_menu(library):
    """Handle login or signup, returning the authenticated user."""
    while True:
        print("\n=== Library Management System ===")
        print("1. Login")
        print("2. Create Account")
        print("3. Exit")

        choice = input("Select an option (1-3): ").strip()

        if choice == "1":
            identifier = input("Username / Email / School ID: ").strip()
            password = input("Password: ").strip()

            user = library.login(identifier, password)
            if user:
                role_label = "Librarian" if user.is_librarian() else "Student"
                print(f"\nWelcome, {user.username}! You are logged in as {role_label}.")
                return user
            else:
                print("Error: Invalid credentials. Please try again.")

        elif choice == "2":
            school_id = input("School ID Number: ").strip()
            email = input("Email: ").strip()
            username = input("Username: ").strip()
            password = input("Password: ").strip()

            print("\nRole options:")
            print("1. Student (search books only)")
            print("2. Librarian (full control)")
            role_choice = input("Select role (1-2): ").strip()
            role = "librarian" if role_choice == "2" else "student"

            if role == "librarian":
                if not require_confirmation(
                    "Librarians can add, issue, and return books. Continue?"
                ):
                    print("Account creation cancelled.")
                    continue

            if school_id and email and username and password:
                ok, message = library.register(
                    school_id, email, username, password, role
                )
                print(message)
            else:
                print("Error: All fields are required.")

        elif choice == "3":
            library.close()
            print("Exiting system. Goodbye!")
            exit(0)

        else:
            print("Error: Invalid choice. Please select 1 through 3.")


def librarian_menu(library, user):
    """Full menu for librarians."""
    while True:
        print("\n=== Library Management System - Librarian ===")
        print("1. Add Book")
        print("2. View All Books")
        print("3. Issue Book")
        print("4. Return Book")
        print("5. Search Books")
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
            query = input("Enter book ID or exact title/author to search: ").strip()
            display_search_results(library, query)

        elif choice == "6":
            print("Logged out.")
            return

        else:
            print("Error: Invalid choice. Please select 1 through 6.")


def student_menu(library, user):
    """Search-only menu for students."""
    while True:
        print("\n=== Library Management System - Student ===")
        print("1. Search Books")
        print("2. View Available Books")
        print("3. Logout")

        choice = input("Select an option (1-3): ").strip()

        if choice == "1":
            query = input(
                "Enter a book ID or the exact title/author to search: "
            ).strip()
            display_search_results(library, query)

        elif choice == "2":
            library.cursor.execute("SELECT * FROM books WHERE is_issued = 0")
            books = library.cursor.fetchall()
            if not books:
                print("\nNo available books right now.")
            else:
                print("\n--- Available Books ---")
                for row in books:
                    print(
                        f"ID: {row['id']} | Title: {row['title']} | "
                        f"Author: {row['author']} | Status: Available"
                    )
                print("-" * 23)

        elif choice == "3":
            print("Logged out.")
            return

        else:
            print("Error: Invalid choice. Please select 1 through 3.")


def display_search_results(library, query):
    """Print the results of a book search."""
    if not query:
        print("Error: Search query cannot be empty.")
        return

    results = library.search_book(query)

    if not results:
        print("\nNo matching book found. Check the ID or exact title/author.")
        return

    print("\n--- Search Results ---")
    for row in results:
        status = "Issued" if row["is_issued"] else "Available"
        print(
            f"ID: {row['id']} | Title: {row['title']} | "
            f"Author: {row['author']} | Status: {status}"
        )
    print("-" * 23)


def main():
    library = LibraryManager()

    # Users must log in (or create an account) first
    user = auth_menu(library)

    # Role-based menu loop
    if user.is_librarian():
        librarian_menu(library, user)
    else:
        student_menu(library, user)

    library.close()
    print("Exiting system. Goodbye!")


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