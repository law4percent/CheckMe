# lib/processes/process_b.py
"""
    Process B: OCR Processing and Grading
    - Polls database for pending answer sheets (student_id IS NULL)
    - Extracts student_id and answers using Gemini OCR
    - Grades against answer key
    - Updates database with results
    - Operates in FIFO order (oldest first)
"""

import time
import json
import logging
from lib.services import answer_sheet_model, answer_key_model
from lib.services.gemini import GeminiOCREngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Process B - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_answer_key_data(assessment_uid: str, answer_key_json_path: str) -> dict:
    """
        Retrieve answer key data using assessment_uid as filename.
        
        Args:
            assessment_uid: Assessment UID (used as filename)
            answer_key_json_path: Base directory for answer key JSONs
        
        Returns:
            Dict with answer key data or error status
    """
    try:
        # Construct JSON file path using assessment_uid
        json_full_path = f"{answer_key_json_path}/{assessment_uid}.json"
        
        logger.info(f"Loading answer key from {json_full_path}")
        
        try:
            with open(json_full_path, 'r') as f:
                answer_key_data = json.load(f)
            
            # Verify it's the correct assessment
            if answer_key_data.get("assessment_uid") != assessment_uid:
                logger.warning(f"Assessment UID mismatch in JSON file")
            
            return {
                "status": "success",
                "data": answer_key_data
            }
        
        except FileNotFoundError:
            return {
                "status": "error",
                "message": f"Answer key file not found: {json_full_path}"
            }
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "message": f"Invalid JSON format: {str(e)}"
            }
    
    except Exception as e:
        logger.error(f"Error retrieving answer key: {e}")
        return {"status": "error", "message": str(e)}


def _process_single_sheet(sheet: tuple, ocr_engine: GeminiOCREngine, answer_key_json_path: str) -> dict:
    """
    Process a single answer sheet: extract student_id, answers, and grade.
    
    Args:
        sheet: Database row tuple from answer_sheets table
        ocr_engine: Initialized Gemini OCR engine
        answer_key_json_path: Base directory for answer key JSONs
    
    Returns:
        Dict with processing results
    """
    try:
        # Parse sheet data
        sheet_id = sheet[0]
        assessment_uid = sheet[1]
        number_of_pages = sheet[3]
        json_file_name = sheet[4]
        json_path = sheet[5]
        img_path = sheet[6]
        is_final_score = sheet[8]
        
        logger.info(f"Processing sheet ID {sheet_id} for assessment {assessment_uid}")
        
        # Step 1: Extract student answers from image
        logger.info(f"Extracting student answers from {img_path}")
        student_data = ocr_engine.extract_answer_sheet(img_path)
        
        if "error" in student_data:
            return {
                "status": "error",
                "sheet_id": sheet_id,
                "message": f"OCR extraction failed: {student_data.get('error')}"
            }
        
        student_id = student_data.get("student_id", "UNKNOWN")
        student_answers = student_data.get("answers", {})
        
        logger.info(f"Extracted student ID: {student_id}")
        
        # Step 2: Get answer key using assessment_uid
        answer_key_result = _get_answer_key_data(assessment_uid, answer_key_json_path)
        if answer_key_result["status"] == "error":
            return {
                "status": "error",
                "sheet_id": sheet_id,
                "message": answer_key_result["message"]
            }
        
        answer_key_data = answer_key_result["data"]
        
        # Step 3: Grade the student sheet
        logger.info(f"Grading sheet for student {student_id}")
        graded_result = ocr_engine.grade_student_sheet(
            student_answers=student_data,
            answer_key=answer_key_data,
            treat_essay_as_partial=True
        )
        
        score = graded_result["summary"]["correct"]
        total_scorable = graded_result["summary"]["scorable_total"]
        percentage = graded_result["summary"]["percentage"]
        has_partial = graded_result["summary"]["partial"] > 0
        
        logger.info(f"Score: {score}/{total_scorable} ({percentage}%)")
        
        # Step 4: Save graded answers to JSON file
        json_full_path = json_path
        try:
            with open(json_full_path, 'w') as f:
                json.dump({
                    "student_id": student_id,
                    "assessment_uid": assessment_uid,
                    "student_answers": student_answers,
                    "graded_answers": graded_result["graded_answers"],
                    "summary": graded_result["summary"],
                    "has_essay": graded_result["has_essay"]
                }, f, indent=2)
            logger.info(f"Saved graded results to {json_full_path}")
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
            return {
                "status": "error",
                "sheet_id": sheet_id,
                "message": f"Failed to save JSON: {str(e)}"
            }
        
        # Step 5: Update database with results
        try:
            # Update student_id
            answer_sheet_model.update_student_id(sheet_id, student_id)
            
            # Update score (is_final depends on whether there are essays)
            is_final = not has_partial
            answer_sheet_model.update_score(sheet_id, score, is_final)
            
            logger.info(f"✅ Sheet {sheet_id} processed successfully")
            
            return {
                "status": "success",
                "sheet_id": sheet_id,
                "student_id": student_id,
                "score": score,
                "total": total_scorable,
                "percentage": percentage
            }
        
        except Exception as e:
            logger.error(f"Failed to update database: {e}")
            return {
                "status": "error",
                "sheet_id": sheet_id,
                "message": f"Database update failed: {str(e)}"
            }
    
    except Exception as e:
        logger.error(f"Unexpected error processing sheet: {e}")
        return {
            "status": "error",
            "sheet_id": sheet[0] if sheet else "unknown",
            "message": f"Unexpected error: {str(e)}"
        }


def process_b(**kwargs):
    """
    Main Process B loop: Poll for pending sheets and process them.
    
    Args:
        **kwargs: Configuration from main.py (process_B_args)
    """
    process_b_args = kwargs.get("process_B_args", {})
    task_name = process_b_args.get("task_name", "Process B")
    pc_mode = process_b_args.get("pc_mode", False)
    poll_interval = process_b_args.get("poll_interval", 2)
    answer_key_json_path = process_b_args.get("answer_key_json_path", "answer_keys/json")  # Add this
    
    logger.info(f"🔵 {task_name} started - OCR Processing & Grading")
    logger.info(f"Poll interval: {poll_interval}s")
    logger.info(f"Answer key JSON path: {answer_key_json_path}")
    
    # Initialize Gemini OCR Engine
    try:
        ocr_engine = GeminiOCREngine()
        logger.info("✅ Gemini OCR Engine initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OCR engine: {e}")
        return
    
    processed_count = 0
    error_count = 0
    
    try:
        while True:
            try:
                # Get pending sheets (FIFO order - oldest first)
                pending_sheets = answer_sheet_model.get_pending_answer_sheets()
                
                if not pending_sheets:
                    if processed_count > 0:
                        logger.info(f"No pending sheets. Processed: {processed_count}, Errors: {error_count}")
                        logger.info("Waiting for new sheets...")
                        processed_count = 0
                        error_count = 0
                    time.sleep(poll_interval)
                    continue
                
                logger.info(f"Found {len(pending_sheets)} pending sheet(s)")
                
                # Process each pending sheet
                for sheet in pending_sheets:
                    result = _process_single_sheet(sheet, ocr_engine, answer_key_json_path)
                    
                    if result["status"] == "success":
                        processed_count += 1
                        logger.info(
                            f"✅ Processed: Student {result['student_id']}, "
                            f"Score: {result['score']}/{result['total']} ({result['percentage']}%)"
                        )
                    else:
                        error_count += 1
                        logger.error(f"❌ Failed to process sheet {result['sheet_id']}: {result['message']}")
                    
                    time.sleep(0.5)
            
            except KeyboardInterrupt:
                logger.info(f"🔵 {task_name} stopped by user")
                logger.info(f"Final stats - Processed: {processed_count}, Errors: {error_count}")
                break
            
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                error_count += 1
                time.sleep(5)
    
    except Exception as e:
        logger.error(f"❌ Fatal error in {task_name}: {e}")
    
    finally:
        logger.info(f"🔵 {task_name} shutting down")
        logger.info(f"Total processed: {processed_count}, Total errors: {error_count}")


# For testing individually
if __name__ == "__main__":
    process_b(process_B_args={
        "task_name": "Process B",
        "pc_mode": True,
        "save_logs": True,
        "poll_interval": 2
    })