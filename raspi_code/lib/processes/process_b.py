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

from lib.model import answer_sheet_model

logger = logger_config.setup_logger(name=__name__, level=logging.DEBUG)


# @dataclass
# class ProcessingMetrics:
#     """Track processing statistics."""
#     total_processed: int = 0
#     total_failed: int = 0
#     total_cycles: int = 0
#     start_time: float = 0.0
    
#     def record_success(self):
#         self.total_processed += 1
    
#     def record_failure(self):
#         self.total_failed += 1
    
#     def get_uptime(self) -> float:
#         return time.time() - self.start_time


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


def _get_JSON_of_answer_sheet(sheets: list, MAX_RETRY: int) -> dict:
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
        time.sleep(5)
        json_data = {}
        # 1. Get data
        total_number_of_questions   = int(sheet["total_number_of_questions"])
        answer_sheet_img_full_path  = str(sheet["img_full_path"])
        

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
            extraction_result = gemini_engine.extract_answer_sheet(answer_sheet_img_full_path, total_number_of_questions, MAX_RETRY)

            # 4. Verify the result
            if extraction_result["status"] == "error":
                collect_error.append(
                    {
                        "img_file"  : answer_sheet_img_full_path,
                        "message"   : extraction_result["message"],
                    }
                )
                continue
            json_data = extraction_result["result"]

        except Exception as e:
            collect_error.append(
                {
                    "img_file"  : answer_sheet_img_full_path,
                    "message"   : f"Failed to extract with Gemini OCR. {e}. Source: {__name__}",
                }
            )
            continue
            
        # 5. Save as json file
        save_result         = {}
        json_target_path    = str(sheet["json_target_path"])
        save_result         = _save_in_json_file(json_data=json_data, target_path=json_target_path)
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
                "answer_key_assessment_uid" : str(sheet["answer_key_assessment_uid"]),
                "processed_score"           : 1,
                "processed_image_uploaded"  : 1 # WIP: Need to finalize
            }
        )
        
    return {
        "error"     : collect_error,
        "success"   : collect_success
    }


def _checking_assessments_by_batch(total_number_of_questions: int, answer_key: str, as_answer: dict) -> dict:
    if total_number_of_questions != len(as_answer):
        return {
        "status"    : "error",
        "message"   : f"Failed to score. Not the same number of answers or questions."
    }

    count_check = 0
    for n in range(1, total_number_of_questions+1):
        if as_answer.get(f"Q{n}").strip() == answer_key.get(f"Q{n}").strip():
            count_check += 1

    return {
        "status"                    : "success",
        "score"                     : count_check
    }


def _read_json(json_file_path: str) -> dict:
    """
    Read a student answer JSON file and convert it to a Python dictionary.

    Args:
        json_file_path (str): Full path to the JSON file

    Returns:
        dict: Parsed JSON content as a Python dictionary
    """
    
    with open(json_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data


def _scoring_by_batch(sheets: list) -> dict:
    """
    Arguments:
        sheets:
            - "student_id"
            - "score"
            - "answer_key_assessment_uid"
            - "as_json_full_path"
            - "total_number_of_questions"
            - "ak_json_full_path"
    """
    # Step 1: Get the JSON file and extract to dict
    organized_sheets    = _group_sheets_by_assessment_uid(sheets)
    answer_keys_in_dict = {}

    for key in organized_sheets.keys():
        org_sheet               = organized_sheets[key]
        first_index             = org_sheet[0]
        answer_key_json_path    = str(first_index["ak_json_full_path"])
        answer_keys_in_dict[key]= _read_json(answer_key_json_path)

    collect_success = []
    collect_error   = []
    # Step 2: Start checking
    for sheet in sheets:
        student_id                  = str(sheet["student_id"])
        score                       = int(sheet["score"])
        total_number_of_questions   = int(sheet["total_number_of_questions"])
        answer_key_assessment_uid   = str(sheet["answer_key_assessment_uid"])
        answer_sheet_json_path      = str(sheet["as_json_full_path"])
        as_answer                   = _read_json(answer_sheet_json_path)

        # Step 2: Checking assessments
        score = _checking_assessments_by_batch(
            total_number_of_questions   = total_number_of_questions, 
            answer_key                  = answer_keys_in_dict[answer_key_assessment_uid],
            as_answer                   = as_answer["answers"]
        )
        if score["status"] == "error":
            collect_error.append({
                "student_id": student_id,
                "message"   : f"{score["message"]} Please check the {student_id}.json at {answer_sheet_json_path}. Source: {__name__}",
            })
            continue
        collect_success.append({
            "score"             : score,
            "student_id"        : student_id,
            "processed_score"   : 2,
            "processed_rtdb"    : 1 # set this to 1 as ready to send to RTDB
        })

    return {
        "success"   : collect_success,
        "error"     : collect_error
    }

        # Step X: attach the correction in the image 
        # ======================== WIP: This will be done in process_c.py ========================
        # img_full_path = 
        # if img_full_path["status"] == "error":
        #     collect_error.append(
        #         {
        #             "student_id": student_id,
        #             "message"   : f"Failed to extract with Gemini OCR. {e}. Source: {__name__}",
        #         }
        #     )
        #     continue



        
    

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
    process_B_args  = kwargs["process_B_args"]
    TASK_NAME       = process_B_args["TASK_NAME"],
    BATCH_SIZE      = process_B_args["BATCH_SIZE"],
    TEACHER_UID     = process_B_args["TEACHER_UID"],
    status_checker  = process_B_args["status_checker"],
    PRODUCTION_MODE = process_B_args["PRODUCTION_MODE"]
    SAVE_LOGS       = process_B_args["SAVE_LOGS"]
    MAX_RETRY       = process_B_args["MAX_RETRY"]

    # retry_delay         = process_B_args["retry_delay"],
    # max_retries         = process_B_args["max_retries"],

    if SAVE_LOGS:
        logger.info(f"{TASK_NAME} is now Running ✅")
    
    while True:
        try:
            time.sleep(5)
            # Check if other processes signaled to stop
            if not status_checker.is_set():
                if SAVE_LOGS:
                    logger.warning(f"{TASK_NAME} - Status checker indicates error in another process")
                    logger.info(f"{TASK_NAME} has stopped")
                break
            
            # ========== PROCESS EXTRACTION WITH GEMINI OCR AND SAVE TO JSON FILE ==========
            # Step 1: Fetch data from db
            sheets_result = answer_sheet_model.get_fields_by_empty_student_id(limit=BATCH_SIZE)
            if sheets_result["status"] == "error":
                if SAVE_LOGS:
                    logger.error(f"{TASK_NAME} - {sheets_result["message"]}")
            else:
                # Step 2: OCR Extraction with Gemini
                extraction_results = _get_JSON_of_answer_sheet(sheets_result["sheets"], MAX_RETRY)
                
                # Step 3: Update database
                success_sheets = extraction_results["success"]
                for success_sheet in success_sheets:
                    update_db_result = answer_sheet_model.update_answer_key_json_path_by_image_path(
                        img_full_path               = success_sheet["img_full_path"],
                        json_file_name              = success_sheet["json_file_name"],
                        json_full_path              = success_sheet["json_full_path"],
                        student_id                  = success_sheet["student_id"],
                        answer_key_assessment_uid   = success_sheet["answer_key_assessment_uid"],
                        processed_score             = success_sheet["processed_score"],
                        processed_image_uploaded    = success_sheet["processed_image_uploaded"]
                    )
                    if update_db_result["status"] == "error" and SAVE_LOGS:
                        logger.error(f"{TASK_NAME} - {update_db_result["message"]}")
                
                # Step 4: Save error in logs
                if SAVE_LOGS:
                    error_sheets = extraction_results["error"]
                    if len(error_sheets) > 0:
                        logger.error(f"{TASK_NAME} - {BATCH_SIZE} sheets")
                        for error_sheet in error_sheets:
                            logger.error(f"{TASK_NAME} - {error_sheet["message"]}")
            
            
            # ========== PROCESS SCORING ==========
            # Step 1: Fetch data from db
            sheets_result = answer_sheet_model.get_fields_by_processed_score_is_1(BATCH_SIZE)
            if sheets_result["status"] == "error":
                if SAVE_LOGS:
                    logger.error(f"{TASK_NAME} - {sheets_result["message"]}")
            else:
                # Step 2: Score it!
                scoring_result = _scoring_by_batch(sheets_result["sheets"])

                # Step 3: Update database
                success_sheets = scoring_result["success"]
                for success_sheet in success_sheets:
                    update_db_result = answer_sheet_model.update_answer_key_scores_by_image_path(
                        score           = scoring_result["score"],
                        student_id      = scoring_result["student_id"],
                        processed_score = scoring_result["processed_score"],
                        processed_rtdb  = scoring_result["processed_rtdb"]
                    )
                    if update_db_result["status"] == "error" and SAVE_LOGS:
                        logger.error(f"{TASK_NAME} - {update_db_result["message"]}")

            
            # ========== PROCESS RTDB UPDATE ==========
            _update_firebase_rtdb(BATCH_SIZE)
            # Step 4: Save to firebase
                # assessmentUid: "QWER1234"
                # isPartialScore: false
                # scannedAt: "11/25/2025 11:22:34"
                # score: 23
                # studentId: 2352352
        
        except Exception as e:
            if SAVE_LOGS:
                logger.warning(f"{TASK_NAME} - {e} Source: {__name__}")
        
