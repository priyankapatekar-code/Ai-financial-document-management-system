import sqlite3
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")
# documents table
cursor.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    file_name TEXT NOT NULL
)
""")
conn.commit()