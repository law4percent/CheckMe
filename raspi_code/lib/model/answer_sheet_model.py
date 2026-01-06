# lib/model/answer_sheet_model.py
from .models import get_connection
from datetime import datetime

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


def get_fields_by_empty_student_id(limit: int = 5) -> dict:
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
                - "answer_key_assessment_uid"
                - "json_target_path"
                - "img_full_path"
                - "total_number_of_questions"
        """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                s.answer_key_assessment_uid,
                s.json_target_path,
                s.img_full_path,
                k.total_number_of_questions
            FROM answer_sheets s
            JOIN answer_keys k
                ON s.answer_key_assessment_uid = k.assessment_uid
            WHERE s.student_id IS NULL
            ORDER BY s.saved_at ASC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        sheets = []
        for row in rows:
            sheets.append({
                "answer_key_assessment_uid" : row[0],
                "json_target_path"          : row[1],
                "img_full_path"             : row[2],
                "total_number_of_questions" : row[3]
            })
        
        return {
            "status": "success",
            "sheets": sheets
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch unprocessed sheets. {e}. Source: {__name__}."
        }


def _get_latest_image(files: list[str]) -> str:
    return max(files, key=lambda f: _to_datetime(_extract_datetime(f)))


def _to_datetime(dt_string: str) -> datetime:
    return datetime.strptime(dt_string, "%Y%m%d_%H%M%S")


def _extract_datetime(filename: str) -> str:
    """
        Extracts the datetime string from filename: YYYYMMDD_HHMMSS
    """
    before_ext = filename.rsplit(".", 1)[0]          # remove .jpg
    dt_string = before_ext.rsplit("_DT_", 1)[-1]     # get the part after _DT_
    return dt_string


def update_answer_key_json_path_by_image_path(
        img_full_path: str,
        json_file_name: str,
        json_full_path: str,
        student_id: str,
        answer_key_assessment_uid: str,
        processed_score: int,
        processed_image_uploaded: int
    ) -> dict:
    """
        Update answer key info based on the given image path.

        Args:
            img_full_path
            json_file_name
            json_full_path
            student_id
            answer_key_assessment_uid
            processed_score
            processed_image_uploaded
    """
    try:
        # Step 1: Check for duplication
        conn    = get_connection()
        cursor  = conn.cursor()

        cursor.execute('''
            SELECT img_full_path
            FROM answer_sheets
            WHERE student_id = ? AND answer_key_assessment_uid = ?
        ''', (student_id, answer_key_assessment_uid))

        rows = cursor.fetchall()
        conn.close()

        # If student_id already exists and has entries, compare images and keep the latest
        if rows:
            collected_same_imgs = [row[0] for row in rows]
            collected_same_imgs.append(img_full_path)

            # Step 1: Determine the newest image
            latest_img = _get_latest_image(collected_same_imgs)

            # Step 2: Overwrite the stored old image for the student and mark again as 1
            conn    = get_connection()
            cursor  = conn.cursor()
            cursor.execute('''
                UPDATE answer_sheets
                SET 
                    img_full_path = ?, 
                    processed_score = ?, 
                    processed_image_uploaded = ?
                WHERE student_id = ? AND answer_key_assessment_uid = ?
            ''', (
                latest_img, 
                processed_score,
                processed_image_uploaded,
                student_id, 
                answer_key_assessment_uid
            ))
            conn.commit()
            conn.close()

            return {"status": "success"}
        
        else:
            # Else update all entries where img_full_path matches
            try:
                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE answer_sheets
                    SET 
                        json_file_name = ?,
                        json_full_path = ?,
                        student_id = ?,
                        processed_score = ?,
                        processed_image_uploaded = ?
                    WHERE img_full_path = ?
                ''', (
                    json_file_name,
                    json_full_path,
                    student_id,
                    processed_score,
                    processed_image_uploaded,
                    img_full_path
                ))

                conn.commit()
                conn.close()

                return {"status": "success"}

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to update JSON path and student ID. {e}. Source: {__name__}"
                }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update JSON path and student ID. {e}. Source: {__name__}"
        }


def update_answer_key_scores_by_student_id(score: int, student_id: str, processed_score: int, processed_rtdb: int) -> dict:
    """
        Update score and processing flags for a student's answer sheet
        
        Args:
            score: Student's calculated score
            student_id: Student's unique identifier
            processed_score: Processing status flag (2 = scored)
            processed_rtdb: RTDB upload status flag (1 = ready to upload)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE answer_sheets
            SET 
                score = ?,
                processed_score = ?,
                processed_rtdb = ?
            WHERE student_id = ?
        ''', (
            score,
            processed_score,
            processed_rtdb,
            student_id,
        ))

        conn.commit()
        conn.close()

        return {"status": "success"}

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update scores. {e}. Source: {__name__}"
        }
    

def get_fields_by_processed_score_is_1(limit: int) -> dict:
    """
        Fetch answer sheets that are ready for scoring.

        Criteria:
        - processed_score = 1 (Score is ready to process)

        Args:
            limit: Maximum number of records to fetch.

        Returns:
            Dict: containing a list of answer sheet records with the following keys:

            - "status": Indicates whether the operation was success or error.
            - "sheets": List of answer sheet objects, each containing:
                - "student_id"
                - "score"
                - "answer_key_assessment_uid"
                - "as_json_full_path"
                - "total_number_of_questions"
                - "ak_json_full_path"
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                s.student_id,
                s.score,
                s.answer_key_assessment_uid,
                s.json_full_path,
                k.total_number_of_questions,
                k.json_full_path
            FROM answer_sheets s
            JOIN answer_keys k
                ON s.answer_key_assessment_uid = k.assessment_uid
            WHERE s.processed_score = 1
            ORDER BY s.saved_at ASC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        sheets = []
        for row in rows:
            sheets.append({
                "student_id"                : row[0],
                "score"                     : row[1],
                "answer_key_assessment_uid" : row[2],
                "as_json_full_path"         : row[3],
                "total_number_of_questions" : row[4],
                "ak_json_full_path"         : row[5]
            })
        
        return {
            "status": "success",
            "sheets": sheets
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch unprocessed sheets. {e}. Source: {__name__}."
        }


def get_fields_by_processed_rtdb_is_1(limit: int) -> dict:
    """
        Fetch answer sheets that are ready for Firebase RTDB upload.

        Criteria:
        - processed_rtdb = 1 (Ready to upload to Firebase)

        Args:
            limit: Maximum number of records to fetch.

        Returns:
            Dict containing:
            - "status": Operation status
            - "sheets": List of sheet records with:
                - "student_id"
                - "score"
                - "answer_key_assessment_uid"
                - "is_final_score"
                - "total_number_of_questions"
                - "saved_at"
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                s.student_id,
                s.score,
                s.answer_key_assessment_uid,
                s.is_final_score,
                k.total_number_of_questions,
                s.saved_at
            FROM answer_sheets s
            JOIN answer_keys k
                ON s.answer_key_assessment_uid = k.assessment_uid
            WHERE s.processed_rtdb = 1
            ORDER BY s.saved_at ASC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        sheets = []
        for row in rows:
            sheets.append({
                "student_id"                : row[0],
                "score"                     : row[1],
                "answer_key_assessment_uid" : row[2],
                "is_final_score"            : bool(row[3]),
                "total_number_of_questions" : row[4],
                "saved_at"                  : row[5]
            })
        
        return {
            "status": "success",
            "sheets": sheets
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch sheets ready for Firebase upload. {e}. Source: {__name__}."
        }


def update_processed_rtdb_by_student_id(student_id: str, answer_key_assessment_uid: str, processed_rtdb: int) -> dict:
    """
        Update processed_rtdb status after Firebase upload
        
        Args:
            student_id: Student's unique identifier
            answer_key_assessment_uid: Assessment UID
            processed_rtdb: New status (2 = uploaded to Firebase)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE answer_sheets
            SET processed_rtdb = ?
            WHERE student_id = ? AND answer_key_assessment_uid = ?
        ''', (processed_rtdb, student_id, answer_key_assessment_uid))

        conn.commit()
        conn.close()

        return {"status": "success"}

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update processed_rtdb. {e}. Source: {__name__}"
        }