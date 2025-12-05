# lib/processes/process_b.py
"""
Process B: Background OCR Processing Pipeline
Monitors answer_sheets table for unprocessed records and performs OCR + grading
"""

import time
import json
import os
import logging
from datetime import datetime
from lib.services import answer_key_model, answer_sheet_model
from lib.services.gemini import GeminiOCREngine
from lib.services.firebase_rtdb import get_firebase_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

CONFIG = {
    "POLL_INTERVAL": 5,  # Check database every 5 seconds
    "RETRY_DELAY": 10,   # Wait 10s before retrying failed records
    "MAX_RETRIES": 3,    # Max retry attempts per record
    "BATCH_SIZE": 5      # Process up to 5 records per cycle
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _load_answer_key_from_json(json_path: str) -> dict:
    """Load answer key from JSON file."""
    try:
        if not os.path.exists(json_path):
            return {
                "status": "error",
                "message": f"Answer key JSON not found: {json_path}"
            }
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        return {
            "status": "success",
            "data": data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load answer key JSON: {str(e)}"
        }


def _save_graded_result_to_json(json_path: str, graded_data: dict) -> dict:
    """Save graded results to JSON file."""
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        with open(json_path, 'w') as f:
            json.dump(graded_data, indent=2, fp=f)
        
        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save graded JSON: {str(e)}"
        }


def _process_single_answer_sheet(
        ocr_engine: GeminiOCREngine,
        sheet_record: dict,
        answer_key_data: dict,
        teacher_uid: str,
        firebase_enabled: bool = True
    ) -> dict:
    """
        Process a single answer sheet through OCR and grading.
        
        Args:
            ocr_engine: Initialized GeminiOCREngine
            sheet_record: Answer sheet record from database
            answer_key_data: Answer key data (already loaded)
            teacher_uid: Teacher's Firebase UID
            firebase_enabled: Whether to sync to Firebase
        
        Returns:
            Result dictionary with status and grading info
    """
    try:
        sheet_id = sheet_record["id"]
        img_path = sheet_record["img_path"]
        json_path = sheet_record["json_path"]
        assessment_uid = sheet_record["assessment_uid"]
        
        logger.info(f"Processing answer sheet ID={sheet_id}, UID={assessment_uid}")
        
        # Step 1: Check if image exists
        if not os.path.exists(img_path):
            return {
                "status": "error",
                "message": f"Image file not found: {img_path}"
            }
        
        # Step 2: Extract student answers via OCR
        logger.info(f"Extracting student answers from {img_path}")
        student_answers = ocr_engine.extract_answer_sheet(img_path)
        
        if "error" in student_answers:
            return {
                "status": "error",
                "message": f"OCR extraction failed: {student_answers.get('error')}"
            }
        
        # Step 3: Grade the student sheet
        logger.info(f"Grading student {student_answers.get('student_id', 'UNKNOWN')}")
        has_essay = answer_key_data.get("has_essay", False)
        
        graded_result = ocr_engine.grade_student_sheet(
            student_answers=student_answers,
            answer_key=answer_key_data,
            treat_essay_as_partial=has_essay
        )
        
        # Step 4: Save graded result to JSON
        save_result = _save_graded_result_to_json(json_path, graded_result)
        if save_result["status"] == "error":
            return save_result
        
        # Step 5: Extract results
        student_id = graded_result.get("student_id", "UNKNOWN")
        score = graded_result["summary"]["correct"]
        is_final_score = not graded_result.get("has_essay", False)
        
        # Step 6: Upload to Firebase (if enabled)
        firebase_status = {"status": "skipped"}
        if firebase_enabled and teacher_uid:
            try:
                firebase_service = get_firebase_service()
                firebase_status = firebase_service.upload_graded_result(
                    teacher_uid     = teacher_uid,
                    assessment_uid  = assessment_uid,
                    student_id      = str(student_id),
                    score           = score,
                    is_final_score  = is_final_score,
                    graded_at       = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
                )
                
                if firebase_status["status"] == "success":
                    logger.info(f"✅ Synced to Firebase: {student_id}")
                else:
                    logger.warning(f"⚠️ Firebase sync failed: {firebase_status.get('message')}")
                    
            except Exception as e:
                logger.error(f"Firebase upload error: {e}")
                firebase_status = {"status": "error", "message": str(e)}
        
        return {
            "status": "success",
            "student_id": student_id,
            "score": score,
            "is_final_score": is_final_score,
            "graded_result": graded_result,
            "firebase_status": firebase_status
        }
        
    except Exception as e:
        logger.error(f"Unexpected error processing sheet ID={sheet_record.get('id')}: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }


def _fetch_unprocessed_sheets(batch_size: int = 5) -> list:
    """
        Fetch answer sheets that need processing.
        
        Criteria:
        - student_id IS NULL (not yet processed)
        - is_image_uploaded = 0 (image ready but not OCR'd)
        
        Returns:
            List of answer sheet records
    """
    try:
        sheets = answer_sheet_model.get_unprocessed_sheets(limit=batch_size)
        return sheets
    except Exception as e:
        logger.error(f"Failed to fetch unprocessed sheets: {e}")
        return []


def _update_sheet_with_results(sheet_id: int, result: dict) -> dict:
    """Update answer sheet record with OCR results."""
    try:
        answer_sheet_model.update_answer_sheet_after_ocr(
            sheet_id=sheet_id,
            student_id=result["student_id"],
            score=result["score"],
            is_final_score=result["is_final_score"]
        )
        
        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update database: {str(e)}"
        }


def _process_batch(ocr_engine: GeminiOCREngine, teacher_uid: str, firebase_enabled: bool) -> dict:
    """
        Process one batch of unprocessed answer sheets.
        
        Returns:
            Summary of batch processing
    """
    # Step 1: Fetch unprocessed sheets
    sheets = _fetch_unprocessed_sheets(batch_size=CONFIG["BATCH_SIZE"])
    exit()
    
    if not sheets:
        return {
            "status"    : "idle",
            "processed" : 0,
            "message"   : "No sheets to process"
        }
    
    logger.info(f"Found {len(sheets)} unprocessed sheet(s)")
    
    processed_count = 0
    failed_count    = 0
    
    # Step 2: Group sheets by assessment_uid to load answer keys efficiently
    sheets_by_uid = {}
    for sheet in sheets:
        uid = sheet["assessment_uid"]
        if uid not in sheets_by_uid:
            sheets_by_uid[uid] = []
        sheets_by_uid[uid].append(sheet)
    
    # Step 3: Process each group
    for assessment_uid, sheet_group in sheets_by_uid.items():
        logger.info(f"Processing {len(sheet_group)} sheet(s) for UID={assessment_uid}")
        
        # Load answer key once per group
        answer_key_record = answer_key_model.get_answer_key_by_uid(assessment_uid)
        
        if not answer_key_record:
            logger.error(f"No answer key found for UID={assessment_uid}")
            failed_count += len(sheet_group)
            continue
        
        # Load answer key JSON
        answer_key_json = _load_answer_key_from_json(answer_key_record["json_path"])
        if answer_key_json["status"] == "error":
            logger.error(f"Failed to load answer key JSON: {answer_key_json['message']}")
            failed_count += len(sheet_group)
            continue
        
        answer_key_data = answer_key_json["data"]
        answer_key_data["has_essay"] = bool(answer_key_record["has_essay"])
        
        # Process each sheet in this group
        for sheet in sheet_group:
            sheet_id = sheet["id"]
            
            # Process the sheet
            result = _process_single_answer_sheet(
                ocr_engine          = ocr_engine,
                sheet_record        = sheet,
                answer_key_data     = answer_key_data,
                teacher_uid         = teacher_uid,
                firebase_enabled    = firebase_enabled
            )
            
            if result["status"] == "success":
                # Update database
                update_result = _update_sheet_with_results(sheet_id, result)
                
                if update_result["status"] == "success":
                    logger.info(f"✅ Sheet ID={sheet_id} processed successfully")
                    processed_count += 1
                else:
                    logger.error(f"Failed to update sheet ID={sheet_id}: {update_result['message']}")
                    failed_count += 1
            else:
                logger.error(f"Failed to process sheet ID={sheet_id}: {result['message']}")
                failed_count += 1
            
            # Small delay to avoid rate limiting
            time.sleep(1)
    
    return {
        "status": "success",
        "processed": processed_count,
        "failed": failed_count,
        "total": len(sheets)
    }


# ============================================================
# MAIN PROCESS B FUNCTION
# ============================================================

def process_b(**kwargs):
    """
        Main Process B function - Background OCR processing.
        
        Continuously monitors answer_sheets table and processes unprocessed records.
    """
    process_B_args  = kwargs.get("process_B_args", {})
    task_name       = process_B_args.get("task_name")
    poll_interval   = process_B_args.get("poll_interval", 5)
    status_checker  = process_B_args.get("status_checker")
    
    # Override config with args from main.py
    CONFIG["POLL_INTERVAL"] = poll_interval
    
    logger.info(f"{task_name} is now Running ✅")
    
    # Initialize OCR engine
    try:
        ocr_engine = GeminiOCREngine()
        logger.info("Gemini OCR Engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OCR engine: {e}")
        print(f"{task_name} - Error: OCR engine initialization failed {e}")
        status_checker.clear() # This will stop all the processes a and c
        exit()
    
    # Main processing loop
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            logger.info(f"=== Processing Cycle {cycle_count} ===")
            
            # Process one batch
            batch_result = _process_batch(ocr_engine)
            
            if batch_result["status"] == "idle":
                # logger.info("No sheets to process. Waiting...")
                print(f"{task_name} - No sheets to process. Waiting...")
            elif batch_result["status"] == "success":
                # logger.info(
                #     f"Batch complete: {batch_result['processed']} processed, "
                #     f"{batch_result['failed']} failed out of {batch_result['total']}"
                # )
                print(
                    f"Batch complete: {batch_result['processed']} processed, "
                    f"{batch_result['failed']} failed out of {batch_result['total']}"
                )
            
            # Wait before next cycle
            time.sleep(CONFIG["POLL_INTERVAL"])
            
        except KeyboardInterrupt:
            logger.info(f"{task_name} stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in processing loop: {e}")
            time.sleep(CONFIG["RETRY_DELAY"])
    
    return {"status": "stopped", "message": f"{task_name} terminated"}


# ============================================================
# MANUAL PROCESSING FUNCTION (FOR TESTING)
# ============================================================

def process_single_sheet_manual(sheet_id: int) -> dict:
    """
    Manually process a single answer sheet by ID (for testing).
    
    Args:
        sheet_id: Answer sheet ID from database
    
    Returns:
        Processing result
    """
    logger.info(f"Manual processing of sheet ID={sheet_id}")
    
    # Initialize OCR engine
    ocr_engine = GeminiOCREngine()
    
    # Fetch sheet record
    sheet = answer_sheet_model.get_answer_sheet_by_id(sheet_id)
    if not sheet:
        return {"status": "error", "message": f"Sheet ID={sheet_id} not found"}
    
    # Fetch answer key
    answer_key_record = answer_key_model.get_answer_key_by_uid(sheet["assessment_uid"])
    if not answer_key_record:
        return {"status": "error", "message": "Answer key not found"}
    
    # Load answer key JSON
    answer_key_json = _load_answer_key_from_json(answer_key_record["json_path"])
    if answer_key_json["status"] == "error":
        return answer_key_json
    
    answer_key_data = answer_key_json["data"]
    answer_key_data["has_essay"] = bool(answer_key_record["has_essay"])
    
    # Process
    result = _process_single_answer_sheet(
        ocr_engine=ocr_engine,
        sheet_record=sheet,
        answer_key_data=answer_key_data
    )
    
    if result["status"] == "success":
        update_result = _update_sheet_with_results(sheet_id, result)
        if update_result["status"] == "success":
            logger.info(f"✅ Sheet ID={sheet_id} processed successfully")
            return result
        else:
            return update_result
    else:
        return result


if __name__ == "__main__":
    # Test single sheet processing
    # process_single_sheet_manual(sheet_id=1)
    
    # Or run full process
    process_b(process_B_args={"task_name": "Process B - OCR Worker"})