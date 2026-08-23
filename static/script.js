/* ========================================
   Library Management System - JavaScript
   ======================================== */

// DOM Elements
const booksTbody = document.getElementById('books-tbody');
const searchInput = document.getElementById('search-input');
const emptyState = document.getElementById('empty-state');
const toastContainer = document.getElementById('toast-container');

// Role is injected from the server as a data attribute on <body>
const userRole = document.body.dataset.role || 'student';
const IS_LIBRARIAN = userRole === 'librarian';

// Librarian-only DOM elements
const addBookForm = document.getElementById('add-book-form');
const bookTitleInput = document.getElementById('book-title');
const bookAuthorInput = document.getElementById('book-author');

// Stat elements
const statTotal = document.getElementById('stat-total');
const statAvailable = document.getElementById('stat-available');
const statIssued = document.getElementById('stat-issued');

// API Base URL
const API_BASE = '/api';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    if (IS_LIBRARIAN) {
        loadBooks();
        loadStats();
    }
});

// Event Listeners
function setupEventListeners() {
    if (IS_LIBRARIAN && addBookForm) {
        // Add book form submission (librarian only)
        addBookForm.addEventListener('submit', handleAddBook);
        // Event delegation for action buttons (librarian only)
        booksTbody.addEventListener('click', handleActionClick);
    }
    // Search input - librarian searches client-side, student searches server-side
    if (searchInput) {
        if (IS_LIBRARIAN) {
            searchInput.addEventListener('input', debounce(handleSearch, 300));
        } else {
            searchInput.addEventListener('input', debounce(handleStudentSearch, 300));
        }
    }
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" aria-label="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
    `;

    toastContainer.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => removeToast(toast), 5000);

    // Close button
    toast.querySelector('.toast-close').addEventListener('click', () => removeToast(toast));
}

function removeToast(toast) {
    toast.classList.add('removing');
    toast.addEventListener('animationend', () => toast.remove());
}

// Set button loading state
function setButtonLoading(button, loading) {
    if (loading) {
        button.classList.add('loading');
        button.disabled = true;
    } else {
        button.classList.remove('loading');
        button.disabled = false;
    }
}

// API Calls
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const response = await fetch(url, { ...defaultOptions, ...options });
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || 'An error occurred');
    }

    return data;
}

// Load all books (librarian)
async function loadBooks() {
    try {
        const books = await apiCall('/books');
        renderBooks(books);
    } catch (error) {
        console.error('Failed to load books:', error);
        showToast('Failed to load books', 'error');
    }
}

// Load statistics (librarian)
async function loadStats() {
    try {
        const stats = await apiCall('/stats');
        updateStats(stats);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Update stats display
function updateStats(stats) {
    if (statTotal) statTotal.textContent = stats.total;
    if (statAvailable) statAvailable.textContent = stats.available;
    if (statIssued) statIssued.textContent = stats.issued;
}

// Render books in table
function renderBooks(books) {
    if (!booksTbody) return;

    if (books.length === 0) {
        booksTbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'flex';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';

    booksTbody.innerHTML = books.map(book => `
        <tr data-id="${book.id}">
            <td>${book.id}</td>
            <td>${escapeHtml(book.title)}</td>
            <td>${escapeHtml(book.author)}</td>
            <td>
                <span class="status-badge ${book.is_issued ? 'status-issued' : 'status-available'}">
                    ${book.is_issued ? 'Issued' : 'Available'}
                </span>
            </td>
            ${IS_LIBRARIAN ? `
            <td>
                <div class="action-buttons">
                    ${book.is_issued
                        ? `<button class="btn btn-sm btn-return" data-id="${book.id}" title="Return Book">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                                <path d="M3 3v5h5"/>
                            </svg>
                          </button>`
                        : `<button class="btn btn-sm btn-issue" data-id="${book.id}" title="Issue Book">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                            </svg>
                          </button>`
                    }
                </div>
            </td>`
            : ''}
        </tr>
    `).join('');
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Handle add book form submission (librarian)
async function handleAddBook(event) {
    event.preventDefault();

    const title = bookTitleInput.value.trim();
    const author = bookAuthorInput.value.trim();

    if (!title || !author) {
        showToast('Please enter both title and author', 'error');
        return;
    }

    const submitBtn = addBookForm.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true);

    try {
        await apiCall('/books', {
            method: 'POST',
            body: JSON.stringify({ title, author })
        });

        showToast(`"${title}" by ${author} added successfully`, 'success');
        addBookForm.reset();
        loadBooks();
        loadStats();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

// Handle action button clicks (issue/return) - librarian only
async function handleActionClick(event) {
    const button = event.target.closest('button');
    if (!button) return;

    const bookId = parseInt(button.dataset.id);
    if (!bookId) return;

    const isIssue = button.classList.contains('btn-issue');
    const isReturn = button.classList.contains('btn-return');

    if (!isIssue && !isReturn) return;

    setButtonLoading(button, true);

    try {
        if (isIssue) {
            await apiCall(`/books/${bookId}/issue`, { method: 'POST' });
            showToast('Book issued successfully', 'success');
        } else if (isReturn) {
            await apiCall(`/books/${bookId}/return`, { method: 'POST' });
            showToast('Book returned successfully', 'success');
        }

        loadBooks();
        loadStats();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        setButtonLoading(button, false);
    }
}

// Handle client-side search (librarian)
function handleSearch(event) {
    const query = event.target.value.toLowerCase();
    const rows = booksTbody.querySelectorAll('tr');

    let visibleCount = 0;

    rows.forEach(row => {
        const title = row.cells[1].textContent.toLowerCase();
        const author = row.cells[2].textContent.toLowerCase();

        if (title.includes(query) || author.includes(query)) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    // Show/hide empty state based on search results
    if (emptyState) {
        if (visibleCount === 0 && query) {
            emptyState.style.display = 'flex';
            emptyState.querySelector('p').textContent = 'No matching books found';
            emptyState.querySelector('span').textContent = 'Try a different search term';
        } else if (visibleCount === 0 && !query) {
            emptyState.style.display = 'flex';
            emptyState.querySelector('p').textContent = 'No books in the library yet';
            emptyState.querySelector('span').textContent = 'Add your first book using the form above';
        } else {
            emptyState.style.display = 'none';
        }
    }
}

// Handle server-side search (student) - by book ID or exact title/author
async function handleStudentSearch(event) {
    const query = event.target.value.trim();

    if (!query) {
        renderBooks([]);
        return;
    }

    try {
        const books = await apiCall(`/books/search?q=${encodeURIComponent(query)}`);
        renderStudentResults(books, query);
    } catch (error) {
        console.error('Failed to search books:', error);
        showToast('Failed to search books', 'error');
    }
}

// Render student search results
function renderStudentResults(books, query) {
    if (!booksTbody) return;

    if (books.length === 0) {
        booksTbody.innerHTML = '';
        if (emptyState) {
            emptyState.style.display = 'flex';
            emptyState.querySelector('p').textContent = 'No matching book found';
            emptyState.querySelector('span').textContent = `No book matches "${query}". Check the ID or exact title.`;
        }
        return;
    }

    if (emptyState) emptyState.style.display = 'none';

    booksTbody.innerHTML = books.map(book => `
        <tr data-id="${book.id}">
            <td>${book.id}</td>
            <td>${escapeHtml(book.title)}</td>
            <td>${escapeHtml(book.author)}</td>
            <td>
                <span class="status-badge ${book.is_issued ? 'status-issued' : 'status-available'}">
                    ${book.is_issued ? 'Issued' : 'Available'}
                </span>
            </td>
        </tr>
    `).join('');
}
