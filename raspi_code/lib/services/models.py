import sqlite3

def _get_connection(db_name='database/checkme.db'):
    """Create and return a database connection."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    return conn

# answer_key_data {
#          | Column's Name        |  Row's Value |
#             "status"            : "success",
#             "assessment_uid"    : assessment_uid,
#             "pages"             : number_of_sheets,
#             "answer_key"        : answer_key,
#             "saved_path"        : json_path
#         }

def create_table():
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_user(name, age):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (name, age) VALUES (?, ?)', (name, age))
    conn.commit()
    conn.close()

def get_all_users():
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_user_age(name, age):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET age = ? WHERE name = ?', (age, name))
    conn.commit()
    conn.close()

def delete_user(name):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE name = ?', (name,))
    conn.commit()
    conn.close()
