# 📚 Library Management System

A full-featured library management system built with **Python** and **Flask**, offering two interfaces:

- 🖥️ **Command-Line Interface (CLI)** — manage your library through an interactive terminal menu.
- 🌐 **Web Application (UI)** — a modern, responsive dashboard with real-time statistics and search.

Both interfaces share the same SQLite database, so books added in one interface are instantly available in the other.

---

## ✨ Features

### Web UI

- **Dashboard statistics** — live counts of total, available, and issued books.
- **Add books** — quick form to add new titles with author info.
- **Issue / Return books** — one-click actions with status badges.
- **Search** — live client-side filtering by title or author.
- **Toast notifications** — user-friendly feedback for every action.
- **Responsive design** — works on desktop and mobile.
- **XSS protection** — user input is safely escaped.

### Command-Line Interface

- **Add Book** — add a new book to the catalog.
- **View All Books** — display the full catalog with issue status.
- **Issue Book** — mark a book as issued (if available).
- **Return Book** — return an issued book to the shelf.
- **Input validation** — guards against invalid IDs and empty fields.

---

## 🗂️ Project Structure

```
book/
├── app.py               # Flask web application & REST API
├── main.py              # CLI application (also launches the web UI)
├── requirements.txt     # Python dependencies
├── schema.sql           # Database schema (empty placeholder)
├── static/
│   ├── style.css        # Web UI styling
│   └── script.js        # Frontend logic (API calls, search, toasts)
└── templates/
    └── index.html       # Main dashboard template
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.7+**
- **pip**

### Installation

1. **Clone or navigate** to the project directory:

   ```bash
   cd book
   ```

2. **(Optional) Create a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   # .venv\Scripts\activate    # Windows
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

### Run the Command-Line Interface

```bash
python main.py
```

You'll see an interactive menu:

```
=== Library Management System ===
1. Add Book
2. View All Books
3. Issue Book
4. Return Book
5. Exit
```

### Run the Web Application

**Option A** — via the menu entry point:

```bash
python main.py --web
```

**Option B** — run the Flask app directly:

```bash
python app.py
```

Then open **http://localhost:5000** in your browser.

> 💡 The server starts on `0.0.0.0:5000` with debug mode enabled. Use `Ctrl+C` to stop it.

---

## 🔌 REST API

The web app exposes a simple JSON API.

| Method | Endpoint                 | Description            |
| ------ | ------------------------ | ---------------------- |
| GET    | `/api/books`             | List all books         |
| POST   | `/api/books`             | Add a new book         |
| POST   | `/api/books/<id>/issue`  | Issue a book by ID     |
| POST   | `/api/books/<id>/return` | Return a book by ID    |
| GET    | `/api/stats`             | Get library statistics |

### Example — Add a Book

```bash
curl -X POST http://localhost:5000/api/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Pragmatic Programmer", "author": "Andrew Hunt"}'
```

### Example — Get Statistics

```bash
curl http://localhost:5000/api/stats
```

```json
{ "total": 5, "issued": 2, "available": 3 }
```

---

## 🗄️ Database Schema

Data is stored in an SQLite database file (`library.db`), automatically created on first run.

```sql
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    is_issued  INTEGER DEFAULT 0
);
```

| Field       | Type    | Description                   |
| ----------- | ------- | ----------------------------- |
| `id`        | INTEGER | Auto-incrementing primary key |
| `title`     | TEXT    | Book title (required)         |
| `author`    | TEXT    | Book author (required)        |
| `is_issued` | INTEGER | `0` = available, `1` = issued |

---

## 🛠️ Technologies Used

- **[Python 3](https://www.python.org/)** — core language
- **[Flask](https://flask.palletsprojects.com/)** — web framework & REST API
- **[SQLite](https://www.sqlite.org/)** — lightweight embedded database
- **HTML / CSS / JavaScript** — frontend dashboard

---

## 📄 License

This project is open source and available for personal and educational use.
