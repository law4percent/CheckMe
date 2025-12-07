# lib/processes/process_b.py
"""
Process B: Background OCR Processing Pipeline
Monitors answer_sheets table for unprocessed records and performs OCR + grading
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from lib.services import answer_key_model, answer_sheet_model
from lib.services.gemini import GeminiOCREngine
from lib.services.firebase_rtdb import get_firebase_service
from lib import logger_config
import logging

logger = logger_config.setup_logger(name=__name__, level=logging.DEBUG)


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class ProcessBConfig:
    """Configuration for Process B."""
    task_name: str
    poll_interval: int = 5
    retry_delay: int = 10
    max_retries: int = 3
    batch_size: int = 5
    teacher_uid: Optional[str] = None
    firebase_enabled: bool = False
    status_checker: Optional[Any] = None


@dataclass
class ProcessingMetrics:
    """Track processing statistics."""
    total_processed: int = 0
    total_failed: int = 0
    total_cycles: int = 0
    start_time: float = 0.0
    
    def record_success(self):
        self.total_processed += 1
    
    def record_failure(self):
        self.total_failed += 1
    
    def get_uptime(self) -> float:
        return time.time() - self.start_time


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _validate_config(args: dict) -> Dict[str, Any]:
    """Validate required configuration arguments."""
    required_keys = ["task_name", "poll_interval", "status_checker"]
    
    missing = [key for key in required_keys if key not in args]
    if missing:
        return {
            "status": "error",
            "message": f"Missing config: {', '.join(missing)}"
        }
    
    return {"status": "success"}


def _load_answer_key_from_json(json_path: str) -> Dict[str, Any]:
    """Load answer key from JSON file."""
    try:
        if not os.path.exists(json_path):
            return {
                "status": "error",
                "message": f"Answer key JSON not found: {json_path}"
            }
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            "status": "success",
            "data": data
        }
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON format: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load answer key JSON: {str(e)}"
        }


def _construct_json_path(json_target_path: str, student_id: str) -> str:
    """
    Construct the full JSON path for graded results.
    
    Format: {json_target_path}/{student_id}.json
    Example: answer_sheets/json/4201400.json
    """
    json_file_name = f"{student_id}.json"
    return os.path.join(json_target_path, json_file_name)


def _save_graded_result_to_json(json_full_path: str, graded_data: dict) -> Dict[str, Any]:
    """Save graded results to JSON file."""
    try:
        # Ensure directory exists
        dir_path = os.path.dirname(json_full_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Save with proper formatting
        with open(json_full_path, 'w', encoding='utf-8') as f:
            json.dump(graded_data, f, indent=2, ensure_ascii=False)
        
        return {"status": "success"}
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save graded JSON: {str(e)}"
        }


def _format_datetime_for_firebase(dt: datetime) -> str:
    """
    Format datetime for Firebase RTDB.
    
    Format: MM/DD/YYYY HH:MM:SS
    Example: 11/25/2025 11:22:34
    """
    return dt.strftime("%m/%d/%Y %H:%M:%S")


def _upload_to_firebase(
        teacher_uid: str,
        assessment_uid: str,
        student_id: str,
        score: int,
        is_final_score: bool,
        scanned_at: str
    ) -> Dict[str, Any]:
    """
    Upload graded result to Firebase RTDB.
    
    Structure:
    {
        "teacherUid": {
            "assessmentUid": {
                "studentId": {
                    "assessmentUid": "...",
                    "isPartialScore": true/false,
                    "scannedAt": "MM/DD/YYYY HH:MM:SS",
                    "score": 23,
                    "studentId": 2352352,
                    "uploadedtoGdriveAt": "MM/DD/YYYY HH:MM:SS"
                }
            }
        }
    }
    """
    try:
        firebase_service = get_firebase_service()
        
        # Prepare data matching the exact Firebase structure
        firebase_data = {
            "assessmentUid": assessment_uid,
            "isPartialScore": not is_final_score,  # Inverse of is_final_score
            "scannedAt": scanned_at,
            "score": score,
            "studentId": int(student_id) if student_id.isdigit() else student_id,
            "uploadedtoGdriveAt": _format_datetime_for_firebase(datetime.now())
        }
        
        # Upload to path: {teacherUid}/{assessmentUid}/{studentId}
        result = firebase_service.upload_graded_result(
            teacher_uid=teacher_uid,
            assessment_uid=assessment_uid,
            student_id=student_id,
            data=firebase_data
        )
        
        if result["status"] == "success":
            logger.info(f"✅ Synced to Firebase: {teacher_uid}/{assessment_uid}/{student_id}")
        else:
            logger.warning(f"⚠️ Firebase sync failed: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Firebase upload error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def _process_single_answer_sheet(
        ocr_engine: GeminiOCREngine,
        sheet_record: dict,
        answer_key_data: dict,
        config: ProcessBConfig
    ) -> Dict[str, Any]:
    """
    Process a single answer sheet through OCR and grading.
    
    Args:
        ocr_engine: Initialized GeminiOCREngine
        sheet_record: Answer sheet record from database
        answer_key_data: Answer key data (already loaded)
        config: Process B configuration
    
    Returns:
        Result dictionary with status and grading info
    """
    try:
        sheet_id = sheet_record["id"]
        img_full_path = sheet_record["img_full_path"]
        json_target_path = sheet_record["json_target_path"]
        assessment_uid = sheet_record["answer_key_assessment_uid"]
        is_final_score = bool(sheet_record["is_final_score"])
        saved_at = sheet_record["saved_at"]  # Original scan timestamp from DB
        
        logger.info(f"Processing answer sheet ID={sheet_id}, UID={assessment_uid}")
        
        # Step 1: Check if image exists
        if not os.path.exists(img_full_path):
            return {
                "status": "error",
                "message": f"Image file not found: {img_full_path}"
            }
        
        # Step 2: Extract student answers via OCR
        logger.info(f"Extracting student answers from {img_full_path}")
        student_answers = ocr_engine.extract_answer_sheet(img_full_path)
        
        if not student_answers or "error" in student_answers:
            return {
                "status": "error",
                "message": f"OCR extraction failed: {student_answers.get('error', 'Unknown error')}"
            }
        
        # Validate student_id was extracted
        student_id = student_answers.get("student_id")
        if not student_id:
            return {
                "status": "error",
                "message": "Student ID not found in extracted data"
            }
        
        # Convert student_id to string for consistency
        student_id = str(student_id)
        
        # Step 3: Grade the student sheet
        logger.info(f"Grading student {student_id}")
        has_essay = answer_key_data.get("has_essay", False)
        
        graded_result = ocr_engine.grade_student_sheet(
            student_answers=student_answers,
            answer_key=answer_key_data,
            treat_essay_as_partial=has_essay
        )
        
        # Step 4: Construct JSON path and save graded results locally
        json_full_path = _construct_json_path(json_target_path, student_id)
        json_file_name = os.path.basename(json_full_path)
        
        save_result = _save_graded_result_to_json(json_full_path, graded_result)
        if save_result["status"] == "error":
            return save_result
        
        # Step 5: Extract results
        score = graded_result.get("summary", {}).get("correct", 0)
        
        # Step 6: Format scanned_at timestamp for Firebase
        # Parse saved_at from SQLite format (YYYY-MM-DD HH:MM:SS)
        # and convert to Firebase format (MM/DD/YYYY HH:MM:SS)
        try:
            saved_dt = datetime.strptime(saved_at, "%Y-%m-%d %H:%M:%S")
            scanned_at_firebase = _format_datetime_for_firebase(saved_dt)
        except Exception as e:
            logger.warning(f"Could not parse saved_at timestamp: {e}, using current time")
            scanned_at_firebase = _format_datetime_for_firebase(datetime.now())
        
        # Step 7: Upload to Firebase (if enabled)
        firebase_status = {"status": "skipped"}
        if config.firebase_enabled and config.teacher_uid:
            firebase_status = _upload_to_firebase(
                teacher_uid=config.teacher_uid,
                assessment_uid=assessment_uid,
                student_id=student_id,
                score=score,
                is_final_score=is_final_score,
                scanned_at=scanned_at_firebase
            )
        
        return {
            "status": "success",
            "student_id": student_id,
            "score": score,
            "is_final_score": is_final_score,
            "json_file_name": json_file_name,
            "json_full_path": json_full_path,
            "scanned_at": scanned_at_firebase,
            "graded_result": graded_result,
            "firebase_status": firebase_status
        }
        
    except Exception as e:
        logger.exception(f"Unexpected error processing sheet ID={sheet_record.get('id')}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }


def _fetch_unprocessed_sheets(batch_size: int = 5) -> List[dict]:
    """
    Fetch answer sheets that need processing.
    
    Criteria:
    - student_id IS NULL (not yet processed)
    
    Returns:
        List of answer sheet records
    """
    try:
        sheets = answer_sheet_model.get_unprocessed_sheets(limit=batch_size)
        return sheets if sheets else []
    except Exception as e:
        logger.error(f"Failed to fetch unprocessed sheets: {e}")
        return []


def _update_sheet_with_results(sheet_id: int, result: dict) -> Dict[str, Any]:
    """
    Update answer sheet record with OCR results.
    
    Updates fields:
    - student_id
    - score
    - json_file_name
    - json_full_path
    
    Note: is_final_score is already set during scanning (process_a),
    no need to update it here.
    """
    try:
        answer_sheet_model.update_answer_sheet_after_ocr(
            sheet_id=sheet_id,
            student_id=result["student_id"],
            score=result["score"],
            json_file_name=result["json_file_name"],
            json_full_path=result["json_full_path"]
        )
        
        return {"status": "success"}
    except Exception as e:
        logger.exception(f"Failed to update sheet ID={sheet_id}")
        return {
            "status": "error",
            "message": f"Failed to update database: {str(e)}"
        }


def _process_batch(
        ocr_engine: GeminiOCREngine,
        config: ProcessBConfig,
        metrics: ProcessingMetrics
    ) -> Dict[str, Any]:
    """
        Process one batch of unprocessed answer sheets.
        
        Returns:
            Summary of batch processing
    """
    # Step 1: Fetch unprocessed sheets
    sheets = _fetch_unprocessed_sheets(batch_size=config.batch_size)
    
    if not sheets:
        return {
            "status": "idle",
            "processed": 0,
            "message": "No sheets to process"
        }
    
    # logger.info(f"Found {len(sheets)} unprocessed sheet(s)")
    
    processed_count = 0
    failed_count    = 0
    
    # Step 2: Group sheets by assessment_uid to load answer keys efficiently
    sheets_by_uid = {}
    for sheet in sheets:
        uid = sheet["answer_key_assessment_uid"]
        if uid not in sheets_by_uid:
            sheets_by_uid[uid] = []
        sheets_by_uid[uid].append(sheet)
    
    # Step 3: Process each group
    for assessment_uid, sheet_group in sheets_by_uid.items():
        # logger.info(f"Processing {len(sheet_group)} sheet(s) for UID={assessment_uid}")
        
        # Load answer key once per group
        try:
            answer_key_record = answer_key_model.get_answer_key_json_path_by_uid(assessment_uid)
        except Exception as e:
            logger.error(f"Database error fetching answer key for UID={assessment_uid}: {e}")
            failed_count += len(sheet_group)
            metrics.total_failed += len(sheet_group)
            continue
        
        # What this mean? it's unclear
        if not answer_key_record:
            logger.error(f"No answer key found for UID={assessment_uid}")
            failed_count += len(sheet_group)
            metrics.total_failed += len(sheet_group)
            continue
        
        # Load answer key JSON
        json_path = answer_key_record["json_full_path"]
        if not json_path:
            logger.error(f"Answer key JSON path is missing for UID={assessment_uid}")
            failed_count += len(sheet_group)
            metrics.total_failed += len(sheet_group)
            continue
        
        answer_key_json = _load_answer_key_from_json(json_path)
        if answer_key_json["status"] == "error":
            logger.error(f"Failed to load answer key JSON: {answer_key_json['message']}")
            failed_count += len(sheet_group)
            metrics.total_failed += len(sheet_group)
            continue
        
        answer_key_data = answer_key_json["data"]
        # Use correct column name: essay_existence
        answer_key_data["has_essay"] = bool(answer_key_record.get("essay_existence", 0))
        
        # Process each sheet in this group
        for sheet in sheet_group:
            sheet_id = sheet["id"]
            
            try:
                # Process the sheet
                result = _process_single_answer_sheet(
                    ocr_engine=ocr_engine,
                    sheet_record=sheet,
                    answer_key_data=answer_key_data,
                    config=config
                )
                
                if result["status"] == "success":
                    # Update database
                    update_result = _update_sheet_with_results(sheet_id, result)
                    
                    if update_result["status"] == "success":
                        logger.info(
                            f"✅ Sheet ID={sheet_id} processed successfully "
                            f"(Student: {result['student_id']}, Score: {result['score']})"
                        )
                        processed_count += 1
                        metrics.record_success()
                    else:
                        logger.error(f"Failed to update sheet ID={sheet_id}: {update_result['message']}")
                        failed_count += 1
                        metrics.record_failure()
                else:
                    logger.error(f"Failed to process sheet ID={sheet_id}: {result['message']}")
                    failed_count += 1
                    metrics.record_failure()
                
            except Exception as e:
                logger.exception(f"Unexpected error processing sheet ID={sheet_id}")
                failed_count += 1
                metrics.record_failure()
            
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

def process_b(**kwargs) -> Dict[str, Any]:
    """
        Main Process B function - Background OCR processing.
        
        Continuously monitors answer_sheets table and processes unprocessed records.
        
        Args:
            **kwargs: Must contain 'process_B_args' dict with configuration
        
        Returns:
            dict: Status dictionary
    """
    # Extract and validate configuration
    process_B_args = kwargs.get("process_B_args", {})
    
    validation = _validate_config(process_B_args)
    if validation["status"] == "error":
        logger.error(validation["message"])
        return validation
    
    try:
        config = ProcessBConfig(
            task_name           = process_B_args["task_name"],
            poll_interval       = process_B_args.get("poll_interval", 5),
            retry_delay         = process_B_args.get("retry_delay", 10),
            max_retries         = process_B_args.get("max_retries", 3),
            batch_size          = process_B_args.get("batch_size", 5),
            teacher_uid         = process_B_args.get("teacher_uid"),
            firebase_enabled    = process_B_args.get("firebase_enabled", False),
            status_checker      = process_B_args.get("status_checker")
        )
    except TypeError as e:
        error_msg = f"Invalid configuration: {e}"
        logger.error(error_msg)
        if config.status_checker:
            config.status_checker.clear()  # Signal other processes to stop
            exit()
    
    logger.info(f"{config.task_name} is now Running ✅")
    print(f"{config.task_name} is now Running ✅")
    
    # Log Firebase status
    if config.firebase_enabled and config.teacher_uid:
        logger.info(f"Firebase sync enabled for teacher: {config.teacher_uid}")
    else:
        logger.info("Firebase sync disabled")
    
    # Initialize metrics
    metrics = ProcessingMetrics(start_time=time.time())
    
    # Initialize OCR engine
    try:
        ocr_engine = GeminiOCREngine()
        logger.info("Gemini OCR Engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OCR engine: {e}")
        print(f"{config.task_name} - Error: OCR engine initialization failed: {e}")
        
        if config.status_checker:
            config.status_checker.clear()  # Signal other processes to stop
            exit()
    
    # Main processing loop
    running = True
    
    try:
        while running:
            # Check if other processes signaled to stop
            if config.status_checker and not config.status_checker.is_set():
                logger.warning("Status checker indicates error in another process")
                running = False
                break
            
            metrics.total_cycles += 1
            logger.info(f"=== Processing Cycle {metrics.total_cycles} ===")
            
            try:
                # Process one batch
                batch_result = _process_batch(ocr_engine, config, metrics)
                
                if batch_result["status"] == "idle":
                    print(f"{config.task_name} - No sheets to process. Waiting...")
                    
                elif batch_result["status"] == "success":
                    print(
                        f"{config.task_name} - Batch complete: "
                        f"{batch_result['processed']} processed, "
                        f"{batch_result['failed']} failed out of {batch_result['total']}"
                    )
                
            except Exception as e:
                logger.exception("Error processing batch")
                print(f"{config.task_name} - Batch processing error: {e}")
                time.sleep(config.retry_delay)
                continue
            
            # Wait before next cycle
            time.sleep(config.poll_interval)
        
    except KeyboardInterrupt:
        logger.info(f"{config.task_name} stopped by user")
        print(f"\n{config.task_name} stopped by user")
        
    except Exception as e:
        logger.exception(f"Unexpected error in {config.task_name}")
        print(f"{config.task_name} - Fatal error: {e}")
        
        if config.status_checker:
            config.status_checker.clear()
        
        return {
            "status": "error",
            "message": f"Fatal error: {str(e)}"
        }
    
    finally:
        # Log final statistics
        logger.info(
            f"{config.task_name} shutting down. "
            f"Stats: Cycles={metrics.total_cycles}, "
            f"Processed={metrics.total_processed}, "
            f"Failed={metrics.total_failed}, "
            f"Uptime={metrics.get_uptime():.1f}s"
        )
        
        print(f"\n{config.task_name} stopped.")
        print(f"Statistics:")
        print(f"  - Cycles completed: {metrics.total_cycles}")
        print(f"  - Sheets processed: {metrics.total_processed}")
        print(f"  - Sheets failed: {metrics.total_failed}")
        print(f"  - Uptime: {metrics.get_uptime():.1f} seconds")
    
    return {
        "status": "stopped",
        "message": f"{config.task_name} terminated normally",
        "metrics": {
            "cycles": metrics.total_cycles,
            "processed": metrics.total_processed,
            "failed": metrics.total_failed,
            "uptime": metrics.get_uptime()
        }
    }







# ============================================================
# MANUAL PROCESSING FUNCTION (FOR TESTING)
# ============================================================

def process_single_sheet_manual(
        sheet_id: int,
        teacher_uid: Optional[str] = None,
        firebase_enabled: bool = False
    ) -> Dict[str, Any]:
    """
        Manually process a single answer sheet by ID (for testing).
        
        Args:
            sheet_id: Answer sheet ID from database
            teacher_uid: Teacher's Firebase UID (optional)
            firebase_enabled: Whether to sync to Firebase
        
        Returns:
            Processing result
    """
    logger.info(f"Manual processing of sheet ID={sheet_id}")
    
    # Initialize OCR engine
    try:
        ocr_engine = GeminiOCREngine()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to initialize OCR engine: {e}"
        }
    
    # Fetch sheet record
    try:
        sheet = answer_sheet_model.get_answer_sheet_by_id(sheet_id)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database error: {e}"
        }
    
    if not sheet:
        return {
            "status": "error",
            "message": f"Sheet ID={sheet_id} not found"
        }
    
    # Fetch answer key
    assessment_uid = sheet["answer_key_assessment_uid"]
    try:
        answer_key_record = answer_key_model.get_answer_key_json_path_by_uid(assessment_uid)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database error fetching answer key: {e}"
        }
    
    if not answer_key_record:
        return {
            "status": "error",
            "message": f"Answer key not found for UID={assessment_uid}"
        }
    
    # Load answer key JSON
    answer_key_json = _load_answer_key_from_json(answer_key_record["json_full_path"])
    if answer_key_json["status"] == "error":
        return answer_key_json
    
    answer_key_data = answer_key_json["data"]
    answer_key_data["has_essay"] = bool(answer_key_record.get("essay_existence", 0))
    
    # Create config for processing
    config = ProcessBConfig(
        task_name="Manual Processing",
        teacher_uid=teacher_uid,
        firebase_enabled=firebase_enabled
    )
    
    # Process
    result = _process_single_answer_sheet(
        ocr_engine=ocr_engine,
        sheet_record=sheet,
        answer_key_data=answer_key_data,
        config=config
    )
    
    if result["status"] == "success":
        update_result = _update_sheet_with_results(sheet_id, result)
        if update_result["status"] == "success":
            logger.info(f"✅ Sheet ID={sheet_id} processed successfully")
            print(f"\n✅ Processing complete!")
            print(f"  - Student ID: {result['student_id']}")
            print(f"  - Score: {result['score']}")
            print(f"  - Final Score: {'Yes' if result['is_final_score'] else 'No (has essay)'}")
            print(f"  - JSON saved: {result['json_full_path']}")
            print(f"  - Firebase: {result['firebase_status']['status']}")
            return result
        else:
            return update_result
    else:
        return result


if __name__ == "__main__":
    # Test single sheet processing
    # result = process_single_sheet_manual(
    #     sheet_id=1,
    #     teacher_uid="gbRaC4u7MSRWWRi9LerDQyjVzg22",
    #     firebase_enabled=True
    # )
    # print(json.dumps(result, indent=2))
    
    # Or run full process
    process_b(process_B_args={
        "task_name": "Process B - OCR Worker",
        "poll_interval": 5,
        "teacher_uid": "gbRaC4u7MSRWWRi9LerDQyjVzg22",
        "firebase_enabled": True,
        "status_checker": None  # Replace with actual multiprocessing.Event()
    })