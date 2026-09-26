# database.py
import sqlite3
from datetime import date

def init_db():
    conn = sqlite3.connect("notices.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            thread_id INTEGER,
            tag TEXT,
            title TEXT,
            comment TEXT,
            due_date TEXT,
            weekday TEXT,
            reminded INTEGER DEFAULT 0,
            reminded_24h INTEGER DEFAULT 0,
            reminded_12h INTEGER DEFAULT 0
        )
    """)
    # পুরনো ডেটাবেস থাকলে কলাম আপডেট করে নেবে
    cursor.execute("PRAGMA table_info(notices)")
    columns = [col[1] for col in cursor.fetchall()]
    if "weekday" not in columns:
        cursor.execute("ALTER TABLE notices ADD COLUMN weekday TEXT")
    if "comment" not in columns:
        cursor.execute("ALTER TABLE notices ADD COLUMN comment TEXT")
    if "reminded_24h" not in columns:
        cursor.execute("ALTER TABLE notices ADD COLUMN reminded_24h INTEGER DEFAULT 0")
    if "reminded_12h" not in columns:
        cursor.execute("ALTER TABLE notices ADD COLUMN reminded_12h INTEGER DEFAULT 0")
        
    conn.commit()
    conn.close()

def fetch_notices(chat_id: int, tag: str = None):
    conn = sqlite3.connect("notices.db")
    cursor = conn.cursor()
    today_str = date.today().strftime("%Y-%m-%d")
    
    if tag:
        cursor.execute(
            "SELECT id, tag, title, comment, due_date, weekday FROM notices WHERE chat_id = ? AND tag = ? AND due_date >= ? ORDER BY due_date ASC",
            (chat_id, tag, today_str)
        )
    else:
        cursor.execute(
            "SELECT id, tag, title, comment, due_date, weekday FROM notices WHERE chat_id = ? AND due_date >= ? ORDER BY due_date ASC",
            (chat_id, today_str)
        )
    rows = cursor.fetchall()
    conn.close()
    return rows