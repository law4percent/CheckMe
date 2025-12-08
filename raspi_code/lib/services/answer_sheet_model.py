# lib/services/answer_sheet_model.py
"""
Database model for answer_sheets table
"""

import sqlite3
from .models import get_connection


def create_answer_sheet(
        answer_key_assessment_uid: str,
        total_number_of_pages_per_sheet: int,
        json_target_path: str,
        img_file_name: str,
        img_full_path: str,
        is_final_score: bool
    ) -> dict:
    """
        Create a new answer sheet record.
        
        Args:
            answer_key_assessment_uid: Answer key that used to
            total_number_of_pages_per_sheet: Number of pages in the answer sheet
            json_target_path: JSON path
            img_file_name: Full name of image file
            img_full_path: Full path to image file
            is_final_score: Whether this is the final score (no essay)
        
        Returns:
            Dictionary with status and inserted ID
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO answer_sheets (
                answer_key_assessment_uid,
                total_number_of_pages_per_sheet,
                json_target_path,
                img_file_name,
                img_full_path,
                is_final_score
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            answer_key_assessment_uid,
            total_number_of_pages_per_sheet,
            json_target_path,
            img_file_name,
            img_full_path,
            1 if is_final_score else 0
        ))
        
        conn.commit()
        sheet_id = cursor.lastrowid
        conn.close()
        
        return {
            "status": "success",
            "id": sheet_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create answer sheet. {e}. Source: {__name__}."
        }


def get_unprocessed_sheets(limit: int = 5) -> dict:
    """
        Fetch answer sheets that have not been processed yet.

        Criteria:
        - student_id IS NULL (OCR has not extracted the student ID yet)

        Args:
            limit: Maximum number of records to fetch.

        Returns:
            Dict: containing a list of answer sheet records with the following keys:

            - "status": Indicates whether the operation was successful or resulted in an error.
            - "sheets": List of answer sheet objects, each containing:
                - "id"
                - "answer_key_assessment_uid"
                - "json_file_name"
                - "json_full_path"
                - "json_target_path"
                - "img_full_path"
                - "is_final_score"
                - "student_id"
                - "score"
                - "saved_at"
        """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                s.id,
                s.answer_key_assessment_uid,
                s.json_file_name,
                s.json_full_path,
                s.json_target_path,
                s.img_full_path,
                s.is_final_score,
                s.student_id,
                s.score,
                s.saved_at,
                k.total_number_of_questions
            FROM answer_sheets s
            JOIN answer_keys k
                ON s.answer_key_assessment_uid = k.assessment_uid
            WHERE student_id IS NULL
            ORDER BY saved_at ASC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        sheets = []
        for row in rows:
            sheets.append({
                "id"                        : row[0],
                "answer_key_assessment_uid" : row[1],
                "json_file_name"            : row[2],
                "json_full_path"            : row[3],
                "json_target_path"          : row[4],
                "img_full_path"             : row[5],
                "is_final_score"            : row[6],
                "student_id"                : row[7],
                "score"                     : row[8],
                "saved_at"                  : row[9],
                "total_number_of_questions" : row[10]
            })
        
        return {
            "status": "success",
            "sheets": sheets
        }
    except Exception as e:
        return {
            "status": "error",
            "sheets": [],
            "message": f"Failed to fetch unprocessed sheets. {e}. Source: {__name__}."
        }


def get_answer_sheet_by_id(sheet_id: int) -> Optional[Dict]:
    """
    Fetch a single answer sheet by ID.
    
    Args:
        sheet_id: Answer sheet ID
    
    Returns:
        Answer sheet record or None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                assessment_uid,
                student_id,
                number_of_pages,
                json_file_name,
                json_path,
                img_path,
                score,
                is_final_score,
                is_image_uploaded,
                saved_at,
                image_uploaded_at
            FROM answer_sheets
            WHERE id = ?
        ''', (sheet_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "assessment_uid": row[1],
            "student_id": row[2],
            "number_of_pages": row[3],
            "json_file_name": row[4],
            "json_path": row[5],
            "img_path": row[6],
            "score": row[7],
            "is_final_score": row[8],
            "is_image_uploaded": row[9],
            "saved_at": row[10],
            "image_uploaded_at": row[11]
        }
    except Exception as e:
        print(f"Error fetching sheet by ID: {e}")
        return None


def update_answer_sheet_after_ocr(
    sheet_id: int,
    student_id: str,
    score: int,
    is_final_score: bool
) -> dict:
    """
    Update answer sheet after OCR processing.
    
    Args:
        sheet_id: Answer sheet ID
        student_id: Extracted student ID
        score: Calculated score
        is_final_score: Whether this is the final score
    
    Returns:
        Status dictionary
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE answer_sheets
            SET 
                student_id = ?,
                score = ?,
                is_final_score = ?,
                is_image_uploaded = 1,
                image_uploaded_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (
            student_id,
            score,
            1 if is_final_score else 0,
            sheet_id
        ))
        
        conn.commit()
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def get_all_sheets_by_assessment(assessment_uid: str) -> List[Dict]:
    """
    Get all answer sheets for a specific assessment.
    
    Args:
        assessment_uid: Assessment identifier
    
    Returns:
        List of answer sheet records
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                assessment_uid,
                student_id,
                number_of_pages,
                json_file_name,
                json_path,
                img_path,
                score,
                is_final_score,
                is_image_uploaded,
                saved_at,
                image_uploaded_at
            FROM answer_sheets
            WHERE assessment_uid = ?
            ORDER BY saved_at DESC
        ''', (assessment_uid,))
        
        rows = cursor.fetchall()
        conn.close()
        
        sheets = []
        for row in rows:
            sheets.append({
                "id": row[0],
                "assessment_uid": row[1],
                "student_id": row[2],
                "number_of_pages": row[3],
                "json_file_name": row[4],
                "json_path": row[5],
                "img_path": row[6],
                "score": row[7],
                "is_final_score": row[8],
                "is_image_uploaded": row[9],
                "saved_at": row[10],
                "image_uploaded_at": row[11]
            })
        
        return sheets
    except Exception as e:
        print(f"Error fetching sheets by assessment: {e}")
        return []


def delete_answer_sheet(sheet_id: int) -> dict:
    """
    Delete an answer sheet record.
    
    Args:
        sheet_id: Answer sheet ID
    
    Returns:
        Status dictionary
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM answer_sheets WHERE id = ?', (sheet_id,))
        
        conn.commit()
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def get_processing_stats() -> Dict:
    """
    Get statistics about answer sheet processing.
    
    Returns:
        Dictionary with processing statistics
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total sheets
        cursor.execute('SELECT COUNT(*) FROM answer_sheets')
        total = cursor.fetchone()[0]
        
        # Processed sheets
        cursor.execute('SELECT COUNT(*) FROM answer_sheets WHERE student_id IS NOT NULL')
        processed = cursor.fetchone()[0]
        
        # Unprocessed sheets
        cursor.execute('SELECT COUNT(*) FROM answer_sheets WHERE student_id IS NULL')
        unprocessed = cursor.fetchone()[0]
        
        # Sheets with final scores
        cursor.execute('SELECT COUNT(*) FROM answer_sheets WHERE is_final_score = 1')
        final_scores = cursor.fetchone()[0]
        
        # Sheets needing manual grading (has essay)
        cursor.execute('SELECT COUNT(*) FROM answer_sheets WHERE is_final_score = 0 AND student_id IS NOT NULL')
        needs_manual = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total": total,
            "processed": processed,
            "unprocessed": unprocessed,
            "final_scores": final_scores,
            "needs_manual_grading": needs_manual
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {
            "total": 0,
            "processed": 0,
            "unprocessed": 0,
            "final_scores": 0,
            "needs_manual_grading": 0
        }