import sqlite3

import sqlite3

def get_connection(db_name='database/checkme.db'):
    """Create and return a database connection."""
    conn = sqlite3.connect(db_name)
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_key_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            number_of_pages INTEGER NOT NULL,
            json_path TEXT NOT NULL,
            img_path TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            is_final_score INTEGER DEFAULT 0,
            is_image_uploaded INTEGER DEFAULT 0,
            saved_at TEXT DEFAULT (datetime('now', 'localtime')),
            image_uploaded_at TEXT,
            FOREIGN KEY (answer_key_id)
                REFERENCES answer_keys(id)
                ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
