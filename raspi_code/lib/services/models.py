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
            assessment_uid TEXT NOT NULL UNIQUE,
            total_number_of_pages INTEGER NOT NULL,
            json_file_name TEXT NOT NULL,
            json_full_path TEXT NOT NULL,
            img_file_name TEXT NOT NULL,
            img_full_path TEXT NOT NULL,
            essay_existence INTEGER NOT NULL,
            total_number_of_questions INTEGER NOT NULL, 
            saved_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')

    # Table 2: answer_sheets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_key_assessment_uid TEXT NOT NULL,
            total_number_of_pages_per_sheet INTEGER NOT NULL,
            json_file_name TEXT,                                -- will adjust later by process_b() : file format [4201400.json == {student_id}.json] and will not save to RTDB
            json_full_path TEXT,                                -- will adjust later by process_b() : path format [{json_target_path}/{json_file_name} == answer_keys/json/4201400.json] and will not save to RTDB
            json_target_path TEXT NOT NULL, 
            img_file_name TEXT NOT NULL,
            img_full_path TEXT NOT NULL,
            is_final_score INTEGER NOT NULL,                    -- will fetch later by process_b() and will save to RTDB as isPartialScore
            student_id TEXT,                                    -- will adjust later by process_b() : format [4201400] and will save to RTDB
            score INTEGER DEFAULT 0,                            -- will adjust later by process_b() and will save to RTDB
            is_image_uploaded INTEGER DEFAULT 0,                -- will adjust later by process_c()
            saved_at TEXT DEFAULT (datetime('now', 'localtime')), -- will fetch later by process_b() and will save to RTDB as scannedAt
            image_uploaded_at TEXT,                              -- will adjust later by process_c()
            FOREIGN KEY (answer_key_assessment_uid) REFERENCES answer_keys(assessment_uid)
        )
    ''')

    conn.commit()
    conn.close()
