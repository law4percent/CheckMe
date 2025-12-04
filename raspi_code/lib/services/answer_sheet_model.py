# lib/services/answer_sheet_model.py
from .models import get_connection

def create_answer_sheet(assessment_uid, number_of_pages, json_file_name, json_path, img_path, is_final_score):
    """Create a new answer sheet record."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO answer_sheets
        (assessment_uid, number_of_pages, json_file_name, json_path, img_path, is_final_score)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (assessment_uid, number_of_pages, json_file_name, json_path, img_path, int(is_final_score)))

    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def get_answer_sheet_by_id(sheet_id):
    """Get answer sheet by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM answer_sheets WHERE id = ?", (sheet_id,))
    result = cursor.fetchone()

    conn.close()
    return result


def get_pending_answer_sheets():
    """Get all answer sheets where student_id is NULL (pending OCR processing)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM answer_sheets 
        WHERE student_id IS NULL 
        ORDER BY saved_at ASC
    """)
    results = cursor.fetchall()

    conn.close()
    return results


def get_unuploaded_answer_sheets():
    """Get all answer sheets where is_image_uploaded = 0 (pending upload)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM answer_sheets 
        WHERE is_image_uploaded = 0 
        ORDER BY saved_at ASC
    """)
    results = cursor.fetchall()

    conn.close()
    return results


def update_student_id(sheet_id, student_id):
    """Update student_id after OCR extraction (for process_b)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE answer_sheets
        SET student_id = ?
        WHERE id = ?
    """, (student_id, sheet_id))

    conn.commit()
    conn.close()


def update_score(sheet_id, score, is_final):
    """Update score and final score status."""
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
    """Mark image as uploaded to cloud storage (for process_c)."""
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


def get_answer_sheets_by_assessment(assessment_uid):
    """Get all answer sheets for a specific assessment."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM answer_sheets 
        WHERE assessment_uid = ?
        ORDER BY saved_at DESC
    """, (assessment_uid,))
    results = cursor.fetchall()

    conn.close()
    return results


def delete_answer_sheet(sheet_id):
    """Delete an answer sheet record."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM answer_sheets WHERE id = ?", (sheet_id,))
    conn.commit()
    conn.close()