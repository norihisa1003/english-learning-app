import sqlite3
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE = "english_coach.db"

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn=None):
    close_after = conn is None  # 自分でopenした場合だけcloseする
    if conn is None:
        conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            reading_level TEXT,
            listening_level TEXT,
            speaking_level TEXT,
            writing_level TEXT,
            weak_points TEXT,
            goal TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            menu TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS writing_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_text TEXT NOT NULL,
            feedback TEXT NOT NULL,
            error_types TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            login_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            user_answer TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            error_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # Insert default user profile (skipped if already exists due to UNIQUE constraint on email)
    conn.execute("""
        INSERT OR IGNORE INTO users (name, email, reading_level, listening_level, speaking_level, writing_level, weak_points, goal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        os.getenv("DEFAULT_USER_NAME"),
        os.getenv("DEFAULT_USER_EMAIL"),
        "C2", "C2", "B2", "B2",
        "article, tense",
        "work overseas"
    ))
    conn.commit()
    if close_after:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")