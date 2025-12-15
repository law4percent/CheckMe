# lib/processes/process_b.py
"""
Process B: Background OCR Processing Pipeline
Monitors answer_sheets table for unprocessed records and performs OCR + grading
"""

import time
import json
import os
from datetime import datetime
from dataclasses import dataclass

from lib.services import utils
from lib.services.gemini import GeminiOCREngine
from lib.services.firebase_rtdb import get_firebase_service
from lib import logger_config
import logging

from raspi_code.lib.models import answer_key_model, answer_sheet_model

logger = logger_config.setup_logger(name=__name__, level=logging.DEBUG)


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




def _group_sheets_by_assessment_uid(sheets: list[dict]) -> dict:
    sheets_by_uid = {}
    for sheet in sheets:
        uid = sheet["answer_key_assessment_uid"]
        if uid not in sheets_by_uid:
            sheets_by_uid[uid] = []
        sheets_by_uid[uid].append(sheet)
    return sheets_by_uid


def _save_in_json_file(json_data: dict, target_path: str) -> dict:
    """
        Save extracted answer key as JSON file.
        Uses student_id from the extracted data.
        
        Args:
            answer_key_data: Extracted answer key dictionary (contains student_id)
        
        Returns:
            Path to saved JSON file, and status dictionary
    """
    # Step 1: Check the path existence
    path_status = utils.path_existence_checkpoint(target_path, __name__)
    if path_status["status"] == "error":
        return path_status
    
    # Step 3: Save into JSON file
    student_id = str(json_data["student_id"]).strip()
    json_file_name = f"{student_id}.json"
    try:
        full_path = os.path.join(target_path, json_file_name)
        with open(full_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        json_file_validation_result = utils.file_existence_checkpoint(full_path, __name__)
        if json_file_validation_result["status"] == "error":
            return json_file_validation_result
        
        return {
            "status"        : "success",
            "full_path"     : full_path,
            "file_name"     : json_file_name,
            "student_id"    : student_id
        }
    except Exception as e:
        return {
            "status"    : "error", 
            "message"   : f"{e}. Source: {__name__}."
        }


def _validate_the_json_result(JSON_data: dict, total_number_of_questions: int) -> dict:
    if "student_id" not in JSON_data or "answer_key" not in JSON_data:
        return {
            "status"    : "error",
            "message"   : f"assessment_uid or answer_key does not exist. Something problem in the prompt or weak prompt. Source: {__name__}"
        }
        
    student_id = JSON_data.get("student_id")
    if not student_id or str(student_id).strip() == "":
        return {
            "status"    : "error",
            "message"   : (
                f"student_id not found in the paper. Source: {__name__}\n"
                "==================== POSSIBLE REASONS =======================\n"
                "[1] Prompt Quality: The prompt sent to Gemini may be unclear.\n"
                "[2] Image Quality: The image might be blurry.\n"
                "[3] Font Size: The text may be too small.\n"
                "[4] Font Style: The font might be difficult to read.\n"
                "[5] Instructions: The paper instructions may be unclear.\n"
                "[6] Formatting: The answer key may be poorly formatted.\n"
                "============================================================\n\n"
                "++++++++++++++++++++++++ JSON DATA +++++++++++++++++++++++++\n"
                f"{JSON_data}\n"
                "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            )
        }
    
    answers = JSON_data.get("answers")
    for n in range(1, total_number_of_questions + 1):
        if f"Q{n}" not in answers:
            return {
                "status"    : "error",
                "message"   : f"Missing: Q{n}. Source: {__name__}."
            }
        
    return {
        "status"    : "success",
        "student_id": str(student_id).strip()
    }


def _get_JSON_of_answer_sheet(sheets: list, delay: int = 5) -> dict:
    """
        Send image to Gemini API for OCR extraction of answer sheet.
        Gemini reads the assessment UID directly from the paper.
        
        Args:
            image_path: Path to answer key image
        
        Returns:
            Extracted JSON data of answer key
    """
    collect_error = []
    collect_success = []
    for sheet in sheets:
        time.sleep(delay)
        # 1. Get data
        total_number_of_questions   = int(sheet["total_number_of_questions"])
        answer_sheet_img_full_path  = sheet["img_full_path"]
        

        # 2. Verify the image file existence
        file_result = utils.file_existence_checkpoint(answer_sheet_img_full_path, __name__)
        if file_result["status"] == "error":
            collect_error.append(
                {
                    "img_file"  : answer_sheet_img_full_path,
                    "message"   : file_result["message"],
                }
            )
            continue

        try:
            # 3. feed the image to OCR gemini
            gemini_engine = GeminiOCREngine()
            JSON_data = gemini_engine.extract_answer_sheet(answer_sheet_img_full_path, total_number_of_questions)
        except Exception as e:
            collect_error.append(
                {
                    "img_file"  : answer_sheet_img_full_path,
                    "message"   : f"Failed to extract with Gemini OCR. {e}. Source: {__name__}",
                }
            )
            continue
            
        # 4. Verify the result
        keys_result = _validate_the_json_result(JSON_data, total_number_of_questions)
        if keys_result["status"] == "error":
            collect_error.append(
                {
                    "img_file"  : answer_sheet_img_full_path,
                    "message"   : keys_result["message"],
                }
            )
            continue
        
        # 5. Save into json file
        save_result = {}
        json_target_path = str(sheet["json_target_path"])
        save_result = _save_in_json_file(json_data=JSON_data, target_path=json_target_path)
        if save_result["status"] == "error":
            collect_error.append(
                {
                    "img_file"  : answer_sheet_img_full_path,
                    "message"   : save_result["message"],
                }
            )
            continue
        
        # 6. Collect success student_id to update DB later
        collect_success.append(
            {
                "json_file_name"            : save_result["file_name"],
                "json_full_path"            : save_result["full_path"],
                "student_id"                : save_result["student_id"],
                "img_full_path"             : answer_sheet_img_full_path,
                "json_data"                 : JSON_data,
                "answer_key_assessment_uid" : sheet["answer_key_assessment_uid"]
            }
        )
        
    return {
        "error"     : collect_error,
        "success"   : collect_success
    }


def _grade_it(json_full_path) -> dict:
    # Step 1: check json existence
    json_restult = utils.file_existence_checkpoint(json_full_path, __name__)
    if json_restult["status"] == "error":
        return json_restult
    
    # Step 2: Get json and convert it into dict like this:
    # {
    #     "assessment_uid": "XXXX1234",
    #     "answers": {
    #         "Q1": "A",
    #         "Q2": "CPU",
    #         "Q3": "unreadable",
    #         ...
    #         "Qn": "no_answer", <-- if blank or no any answer
    #     }
    # }
    
    # Step 3: Get the answers value and initialize it to answer_sheet
    
    
    # Step 4: Get the answer 
    
    # Step 5: Start checking by counting the check
    
    count_check = 0
    for n in range(1, total_number_of_questions+1):
        if answer_sheet.get(f"Q{n}").strip() == answer_key.get(f"Q{n}").strip():
            count_check += 1
            

    return {
        "status"                    : "success",
        "score"                     : count_check,
        "is_final_score"            : is_final_score, # This can be done with check the assessment uid of the answer_key DB table
        "answer_key_assessment_uid" : answer_key_assessment_uid
    }


def _score_batch(batch_size: int) -> dict:
    pass
    # Step 1: fetch those sheets that have processed_score is 1
    
    # Step 2: Group with assessment_uid
    _group_sheets_by_assessment_uid()
    
    # Step 3: _grade_it()
    
    
    # Step 4: update the score, is_final_score, and processed_score by answer_key_assessment_uid and student_id
    result = answer_sheet_model.update_answer_key_scores_by_image_path(
        score                       = score,
        is_final_score              = is_final_score,
        answer_key_assessment_uid   = answer_key_assessment_uid,
        student_id                  = student_id
    )
    if result["status"] == "error":
        return result
    

def _update_firebase_rtdb(batch_size) -> dict:
    # Step 1: fetch those sheets that have processed_rtdb is 1
    return {
        
    }
    
    
    
# ============================================================
# MAIN PROCESS B FUNCTION
# ============================================================

def process_b(**kwargs):
    """
        Main Process B function - Background OCR processing.
        
        Continuously monitors answer_sheets table and processes unprocessed records with Gemini OCR.
        
        Args:
            **kwargs: Must contain 'process_B_args' dict
    """
    process_B_args      = kwargs["process_B_args"]
    task_name           = process_B_args["task_name"],
    poll_interval       = process_B_args["poll_interval"],
    retry_delay         = process_B_args["retry_delay"],
    max_retries         = process_B_args["max_retries"],
    batch_size          = process_B_args["batch_size"],
    teacher_uid         = process_B_args["teacher_uid"],
    firebase_enabled    = process_B_args["firebase_enabled"],
    status_checker      = process_B_args["status_checker"],
    pc_mode             = process_B_args["pc_mode"]
    save_logs           = process_B_args["save_logs"]

    if save_logs:
        logger.info(f"{task_name} is now Running ✅")
        if firebase_enabled and teacher_uid:
            logger.info(f"Firebase sync enabled for teacher: {teacher_uid}")
        else:
            logger.info("Firebase sync disabled")
    
    # Initialize metrics
    metrics = ProcessingMetrics(start_time=time.time())
    
    # Main processing loop
    running = True
    
    while running:
        time.sleep(poll_interval)
        # Check if other processes signaled to stop
        if not status_checker.is_set():
            if save_logs:
                logger.warning(f"{task_name} - Status checker indicates error in another process")
                logger.info(f"{task_name} has stopped")
            running = False
            break
        
        metrics.total_cycles += 1
        if save_logs:
            logger.info(f"=== Processing Cycle {metrics.total_cycles} ===")
        
        # Step 1: Fetch data from db
        sheets_result = answer_sheet_model.get_unprocessed_sheets(limit=batch_size)
        if sheets_result["status"] == "error":
            if save_logs:
                logger.error(f"{task_name} - {sheets_result["message"]}")
            continue
        sheets = sheets_result["sheets"]

        # Step 2: Extract one batch images to text to json with gemini OCR
        json_results = _get_JSON_of_answer_sheet(sheets, batch_size)
        
        # Step 3: Update database json path and student id by image_full_path
        json_success = json_results["success"]
        for success in json_success:
            update_db_result = answer_sheet_model.update_answer_key_json_path_by_image_path(
                img_full_path               = success["img_full_path"],
                json_file_name              = success["json_file_name"],
                json_full_path              = success["json_full_path"],
                student_id                  = success["student_id"],
                answer_key_assessment_uid   = success["answer_key_assessment_uid"]
            )
            if update_db_result["status"] == "error" and save_logs:
                logger.error(f"{task_name} - {update_db_result["message"]}")
            
        if save_logs:
            json_error = json_results["error"]
            for error in json_error:
                logger.error(f"{task_name} - {error["message"]}")
        
        
        # Step 4. scoring
        _score_batch(batch_size)
        
        _update_firebase_rtdb(batch_size)
        # Step 5: Save to firebase
            # assessmentUid: "QWER1234"
            # isPartialScore: false
            # scannedAt: "11/25/2025 11:22:34"
            # score: 23
            # studentId: 2352352
        
