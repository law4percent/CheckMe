from .models import get_connection

def create_answer_key(assessment_uid: str, number_of_pages: int, json_path: str, img_path: str, has_essay: bool) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO answer_keys 
        (assessment_uid, number_of_pages, json_path, img_path, has_essay)
        VALUES (?, ?, ?, ?, ?)
    """, (assessment_uid, number_of_pages, json_path, img_path, int(has_essay)))

    conn.commit()
    conn.close()


def get_has_essay_by_assessment_uid(assessment_uid):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT has_essay FROM answer_keys WHERE assessment_uid = ?",
        (assessment_uid,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0]  # return the actual value of has_essay (0 or 1)
    return None  # not found


def get_all_answer_keys() -> list:
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch only assessment_uid column
    cursor.execute("SELECT assessment_uid FROM answer_keys ORDER BY id ASC")
    result = cursor.fetchall()  # returns list of tuples: [('MATH-2025-Q1',), ('ENG-2025-Q1',), ...]

    conn.close()
    return [row[0] for row in result]  # convert to simple list of strings


def delete_answer_key(key_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM answer_keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()