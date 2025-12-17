# lib/services/answer_sheet_model.py
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
        processed_rtdb: int,
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
            processed_rtdb
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

        rows = cursor.fetchall() # is it fetchall? but student_id cannot be duplicated because it is set unique in DB 
        conn.close()

        # If student_id is already exist and has already entries, then compare images and keep the latest
        if rows:
            collected_same_imgs = [row[0] for row in rows]
            collected_same_imgs.append(img_full_path)

            # Step 1: Determine the newest image
            latest_img = _get_latest_image(collected_same_imgs)

            # Step 2: Overwrite the stored old image for the student and mark again as 1 the processed_score and processed_rtdb
            conn    = get_connection()
            cursor  = conn.cursor()
            cursor.execute('''
                UPDATE answer_sheets
                SET 
                    img_full_path = ?, 
                    processed_score = ?, 
                    processed_rtdb = ?,
                    processed_image_uploaded = ?
                WHERE student_id = ? AND answer_key_assessment_uid = ?
            ''', (
                latest_img, 
                processed_score, 
                processed_rtdb,
                processed_image_uploaded,
                student_id, 
                answer_key_assessment_uid
            ))
            conn.commit()
            conn.close()

            return {"status": "success"}
        
        else:
            # Else then update all the entries where img_full_path is match
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
                        processed_rtdb = ?,
                        processed_image_uploaded = ?
                    WHERE img_full_path = ?
                ''', (
                    json_file_name,
                    json_full_path,
                    student_id,
                    processed_score,
                    processed_rtdb,
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


def update_answer_key_scores_by_image_path() -> dict:
    pass