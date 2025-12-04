from .models import get_connection

def create_answer_sheet(answer_key_id, student_id, number_of_pages, json_path, img_path):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO answer_sheets
        (answer_key_id, student_id, number_of_pages, json_path, img_path)
        VALUES (?, ?, ?, ?, ?)
    """, (answer_key_id, student_id, number_of_pages, json_path, img_path))

    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def get_answer_sheet_by_id(sheet_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM answer_sheets WHERE id = ?", (sheet_id,))
    result = cursor.fetchone()

    conn.close()
    return result


def update_score(sheet_id, score, is_final):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE answer_sheets
        SET score = ?, is_final_score = ?
        WHERE id = ?
    """, (score, int(is_final), sheet_id))

    conn.commit()
    conn.close()


def mark_image_uploaded(sheet_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE answer_sheets
        SET is_image_uploaded = 1,
            image_uploaded_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (sheet_id,))

    conn.commit()
    conn.close()


def delete_answer_sheet(sheet_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM answer_sheets WHERE id = ?", (sheet_id,))
    conn.commit()
    conn.close()