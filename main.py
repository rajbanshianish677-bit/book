import sqlite3


class LibraryManager:

    def __init__(self, db_name="library.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        """Creates the books table if it doesn't exist."""
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
        self.conn.commit()

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

    while True:
        print("\n=== Library Management System ===")
        print("1. Add Book")
        print("2. View All Books")
        print("3. Issue Book")
        print("4. Return Book")
        print("5. Exit")

        choice = input("Select an option (1-5): ").strip()

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
            library.close()
            print("Exiting system. Goodbye!")
            break

        else:
            print("Error: Invalid choice. Please select 1 through 5.")


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