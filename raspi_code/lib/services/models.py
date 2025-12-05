# lib/services/models.py
import sqlite3
import os

def get_connection(db_path='database'):
    """Create and return a database connection."""
    if not os.path.exists(db_path):
        os.makedirs(db_path)
        print(f"Folder '{db_path}' created.")
    conn = sqlite3.connect(f"{db_path}/checkme.db")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def create_table():
    conn = get_connection()
    cursor = conn.cursor()

    # Table 1: answer_keys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_uid TEXT NOT NULL,
            number_of_pages INTEGER NOT NULL,
            json_path TEXT NOT NULL,
            img_path TEXT NOT NULL,
            has_essay INTEGER NOT NULL,
            saved_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')

    # Table 2: answer_sheets
    # In create_table() function, update answer_sheets table:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_uid TEXT NOT NULL,
            student_id TEXT,
            number_of_pages INTEGER NOT NULL,
            json_file_name TEXT NOT NULL,
            json_path TEXT NOT NULL,
            img_path TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            is_final_score INTEGER DEFAULT 0,
            is_image_uploaded INTEGER DEFAULT 0,
            saved_at TEXT DEFAULT (datetime('now', 'localtime')),
            image_uploaded_at TEXT
        )
    ''')

    conn.commit()
    conn.close()
