# lib/services/answer_key_model.py
from typing import Optional, List, Dict
from .models import get_connection


def create_answer_key(
        assessment_uid: str,
        total_number_of_pages: int,
        json_file_name: str,
        json_full_path: str,
        img_file_name: str,
        img_full_path: str,
        essay_existence: bool,
        total_number_of_questions: int
    ) -> dict:
    """
        Creates a new answer key record in the database.

        Args:
            assessment_uid (str): Unique identifier of the assessment.
            total_number_of_pages (int): Total number of scanned pages.
            json_file_name (str): File name of the generated JSON details.
            json_full_path (str): Full path to the JSON details file.
            img_file_name (str): File name of the saved answer key image.
            img_full_path (str): Full path to the saved image file.
            essay_existence (bool): Indicates whether the assessment includes an essay section.

        Returns:
            dict: A dictionary containing:
                - "status": Operation status ("success" or "error").
                - "id": Inserted record ID (if successful).
                - "message": Error message (if failed).
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO answer_keys (
                assessment_uid,
                total_number_of_pages,
                json_file_name,
                json_full_path,
                img_file_name,
                img_full_path,
                essay_existence,
                total_number_of_questions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            assessment_uid,
            total_number_of_pages,
            json_file_name,
            json_full_path,
            img_file_name,
            img_full_path,
            1 if essay_existence else 0,
            total_number_of_questions
        ))
        
        conn.commit()
        key_id = cursor.lastrowid
        conn.close()
        
        return {
            "status": "success",
            "id": key_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"{e}. Source: {__name__}."
        }


def get_all_answer_keys() -> dict:
    """
        Fetch all assessment UIDs from answer_keys table.
        
        Returns:
            List of assessment UIDs
    """
    try:
        conn    = get_connection()
        cursor  = conn.cursor()
        
        cursor.execute('SELECT assessment_uid FROM answer_keys ORDER BY saved_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "status"            : "success",
            "all_answer_keys"   : [row[0] for row in rows]
        }
    except Exception as e:
        return {
            "status"    : "error",
            "message"   : f"{e}. Source: {__name__}"
        }


def get_answer_key_json_path_by_uid(assessment_uid: str) -> Optional[Dict]:
    """
        Fetch answer key record by assessment UID.
        
        Args:
            assessment_uid: Assessment identifier
        
        Returns:
            Answer key record or None
    """
    try:
        conn    = get_connection()
        cursor  = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                assessment_uid,
                json_full_path
            FROM answer_keys
            WHERE assessment_uid = ?
        ''', (assessment_uid,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id"                : row[0],
            "assessment_uid"    : row[1],
            "json_full_path"    : row[2],
        }
    except Exception as e:
        print(f"Error fetching answer key by UID: {e}")
        return None


def get_has_essay_by_assessment_uid(assessment_uid: str) -> bool:
    """
        Check if an assessment has essay questions.
        
        Args:
            assessment_uid: Assessment identifier
        
        Returns:
            True if has essay, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT has_essay 
            FROM answer_keys 
            WHERE assessment_uid = ?
        ''', (assessment_uid,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False
        
        return bool(row[0])
    
    except Exception as e:
        print(f"Error checking essay status: {e}")
        return False


def get_answer_key_by_id(key_id: int) -> Optional[Dict]:
    """
        Fetch answer key record by ID.
        
        Args:
            key_id: Answer key ID
        
        Returns:
            Answer key record or None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                assessment_uid,
                number_of_pages,
                json_path,
                img_path,
                has_essay,
                saved_at
            FROM answer_keys
            WHERE id = ?
        ''', (key_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "assessment_uid": row[1],
            "number_of_pages": row[2],
            "json_path": row[3],
            "img_path": row[4],
            "has_essay": row[5],
            "saved_at": row[6]
        }
    except Exception as e:
        print(f"Error fetching answer key by ID: {e}")
        return None


def update_answer_key(
        key_id: int,
        assessment_uid: Optional[str] = None,
        number_of_pages: Optional[int] = None,
        json_path: Optional[str] = None,
        img_path: Optional[str] = None,
        has_essay: Optional[bool] = None
    ) -> dict:
    """
    Update an answer key record.
    
    Args:
        key_id: Answer key ID
        assessment_uid: New assessment UID (optional)
        number_of_pages: New number of pages (optional)
        json_path: New JSON path (optional)
        img_path: New image path (optional)
        has_essay: New essay status (optional)
    
    Returns:
        Status dictionary
    """
    try:
        # Build dynamic update query
        updates = []
        values = []
        
        if assessment_uid is not None:
            updates.append("assessment_uid = ?")
            values.append(assessment_uid)
        
        if number_of_pages is not None:
            updates.append("number_of_pages = ?")
            values.append(number_of_pages)
        
        if json_path is not None:
            updates.append("json_path = ?")
            values.append(json_path)
        
        if img_path is not None:
            updates.append("img_path = ?")
            values.append(img_path)
        
        if has_essay is not None:
            updates.append("has_essay = ?")
            values.append(1 if has_essay else 0)
        
        if not updates:
            return {"status": "error", "message": "No fields to update"}
        
        values.append(key_id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = f"UPDATE answer_keys SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        
        conn.commit()
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def delete_answer_key(key_id: int) -> dict:
    """
        Delete an answer key record.
        
        Args:
            key_id: Answer key ID
        
        Returns:
            Status dictionary
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM answer_keys WHERE id = ?', (key_id,))
        
        conn.commit()
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def delete_answer_key_by_uid(assessment_uid: str) -> dict:
    """
        Delete an answer key by assessment UID.
        
        Args:
            assessment_uid: Assessment identifier
        
        Returns:
            Status dictionary
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM answer_keys WHERE assessment_uid = ?', (assessment_uid,))
        
        conn.commit()
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def get_all_answer_keys_full() -> List[Dict]:
    """
        Fetch all answer key records with full details.
        
        Returns:
            List of answer key records
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                assessment_uid,
                number_of_pages,
                json_path,
                img_path,
                has_essay,
                saved_at
            FROM answer_keys
            ORDER BY saved_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        keys = []
        for row in rows:
            keys.append({
                "id": row[0],
                "assessment_uid": row[1],
                "number_of_pages": row[2],
                "json_path": row[3],
                "img_path": row[4],
                "has_essay": row[5],
                "saved_at": row[6]
            })
        
        return keys
    except Exception as e:
        print(f"Error fetching all answer keys: {e}")
        return []