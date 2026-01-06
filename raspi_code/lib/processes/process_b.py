# lib/processes/process_b.py
"""
Process B: Background OCR Processing Pipeline
Monitors answer_sheets table for unprocessed records and performs OCR + grading

Relative Files:
- lib/model/answer_sheet_model.py : Database interactions for answer_sheets table
- lib/services/gemini.py          : Gemini OCR engine integration
- lib/services/firebase_rtdb.py   : Firebase RTDB upload service
- lib/services/utils.py           : Utility functions for file/path checks
- lib/logger_config.py            : Logger setup and configuration
"""

import time
import json
import os
from datetime import datetime

from lib.services import utils
from lib.services.gemini import GeminiOCREngine
from lib.services.firebase_rtdb import get_firebase_service
from lib import logger_config
import logging

from lib.model import answer_sheet_model, answer_key_model

logger = logger_config.setup_logger(name=__name__, level=logging.DEBUG)


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
            json_data: Extracted answer key dictionary (contains student_id)
            target_path: Directory path to save JSON file
        
        Returns:
            Path to saved JSON file, and status dictionary
    """
    # Step 1: Check the path existence
    path_status = utils.path_existence_checkpoint(target_path, __name__)
    if path_status["status"] == "error":
        return path_status
    
    # Step 2: Save into JSON file
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
        Gemini reads the student ID and answers directly from the paper.
        
        Args:
            sheets: List of answer sheet records from database
            MAX_RETRY: Maximum retry attempts for Gemini API
        
        Returns:
            Dictionary containing success and error lists
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
            # 3. Feed the image to OCR gemini
            gemini_engine = GeminiOCREngine()
            extraction_result = gemini_engine.extract_answer_sheet(
                answer_sheet_img_full_path, 
                total_number_of_questions, 
                MAX_RETRY
            )

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
                "processed_image_uploaded"  : 1
            }
        )
        
    return {
        "error"     : collect_error,
        "success"   : collect_success
    }


def _checking_assessments_by_batch(total_number_of_questions: int, answer_key: dict, as_answer: dict) -> dict:
    """
        Check student answers against answer key
        
        Args:
            total_number_of_questions: Total number of questions
            answer_key: Dictionary of correct answers
            as_answer: Dictionary of student answers
        
        Returns:
            Dictionary with status and score
    """
    if total_number_of_questions != len(as_answer):
        return {
            "status"    : "error",
            "message"   : f"Failed to score. Not the same number of answers or questions. Expected {total_number_of_questions}, got {len(as_answer)}."
        }

    count_check = 0
    for n in range(1, total_number_of_questions + 1):
        student_ans = as_answer.get(f"Q{n}", "").strip()
        correct_ans = answer_key.get(f"Q{n}", "").strip()
        
        if student_ans == correct_ans:
            count_check += 1

    return {
        "status"    : "success",
        "score"     : count_check
    }


def _read_json(json_file_path: str) -> dict:
    """
    Read a JSON file and convert it to a Python dictionary.

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
    Score multiple answer sheets in batch
    
    Arguments:
        sheets:
            - "student_id"
            - "score"
            - "answer_key_assessment_uid"
            - "as_json_full_path"
            - "total_number_of_questions"
            - "ak_json_full_path"
    
    Returns:
        Dictionary with success and error lists
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
    
    # Step 2: Start checking each sheet
    for sheet in sheets:
        student_id                  = str(sheet["student_id"])
        total_number_of_questions   = int(sheet["total_number_of_questions"])
        answer_key_assessment_uid   = str(sheet["answer_key_assessment_uid"])
        answer_sheet_json_path      = str(sheet["as_json_full_path"])
        
        try:
            as_answer = _read_json(answer_sheet_json_path)
        except Exception as e:
            collect_error.append({
                "student_id": student_id,
                "message"   : f"Failed to read answer sheet JSON. {e}. Source: {__name__}",
            })
            continue

        # Step 3: Check assessments
        score_result = _checking_assessments_by_batch(
            total_number_of_questions   = total_number_of_questions, 
            answer_key                  = answer_keys_in_dict[answer_key_assessment_uid]["answers"],
            as_answer                   = as_answer["answers"]
        )
        
        if score_result["status"] == "error":
            collect_error.append({
                "student_id": student_id,
                "message"   : f"{score_result['message']} Please check the {student_id}.json at {answer_sheet_json_path}. Source: {__name__}",
            })
            continue
            
        collect_success.append({
            "score"             : score_result["score"],
            "student_id"        : student_id,
            "processed_score"   : 2,
            "processed_rtdb"    : 1  # Set to 1 as ready to send to RTDB
        })

    return {
        "success"   : collect_success,
        "error"     : collect_error
    }


def _update_firebase_rtdb(batch_size: int, teacher_uid: str) -> dict:
    """
    Upload scored answer sheets to Firebase RTDB
    
    Args:
        batch_size: Number of records to process
        teacher_uid: Teacher's unique identifier
    
    Returns:
        Dictionary with status and results
    """
    # Step 1: Fetch sheets that are ready to upload (processed_rtdb = 1)
    sheets_result = answer_sheet_model.get_fields_by_processed_rtdb_is_1(batch_size)
    
    if sheets_result["status"] == "error":
        return sheets_result
    
    sheets = sheets_result["sheets"]
    
    if not sheets:
        return {
            "status": "success",
            "message": "No sheets ready to upload to Firebase"
        }
    
    # Step 2: Group sheets by assessment_uid
    grouped_by_assessment = _group_sheets_by_assessment_uid(sheets)
    
    # Step 3: Get Firebase service
    firebase_service = get_firebase_service()
    
    all_uploaded = []
    all_failed = []
    
    # Step 4: Upload each assessment group
    for assessment_uid, assessment_sheets in grouped_by_assessment.items():
        # Prepare student records for upload
        student_records = []
        
        for sheet in assessment_sheets:
            student_records.append({
                "student_id": sheet["student_id"],
                "score": sheet["score"],
                "perfect_score": sheet["total_number_of_questions"],
                "is_partial_score": not sheet["is_final_score"],
                "scanned_at": sheet.get("saved_at", datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
            })
        
        # Upload to Firebase
        upload_result = firebase_service.upload_student_scores(
            teacher_uid=teacher_uid,
            assessment_uid=assessment_uid,
            student_records=student_records
        )
        
        if upload_result["status"] == "success":
            # Update DB to mark as uploaded (processed_rtdb = 2)
            for sheet in assessment_sheets:
                update_result = answer_sheet_model.update_processed_rtdb_by_student_id(
                    student_id=sheet["student_id"],
                    answer_key_assessment_uid=sheet["answer_key_assessment_uid"],
                    processed_rtdb=2
                )
                
                if update_result["status"] == "success":
                    all_uploaded.append(sheet["student_id"])
                else:
                    all_failed.append(sheet["student_id"])
        
        elif upload_result["status"] == "partial":
            # Some uploaded, some failed - update only successful ones
            uploaded_ids = [r["student_id"] for r in student_records[:upload_result["uploaded_count"]]]
            
            for student_id in uploaded_ids:
                update_result = answer_sheet_model.update_processed_rtdb_by_student_id(
                    student_id=student_id,
                    answer_key_assessment_uid=assessment_uid,
                    processed_rtdb=2
                )
                
                if update_result["status"] == "success":
                    all_uploaded.append(student_id)
                else:
                    all_failed.append(student_id)
            
            all_failed.extend([r["student_id"] for r in student_records[upload_result["uploaded_count"]:]])
        
        else:
            # All failed
            all_failed.extend([sheet["student_id"] for sheet in assessment_sheets])
    
    return {
        "status": "success" if len(all_failed) == 0 else "partial",
        "uploaded_count": len(all_uploaded),
        "failed_count": len(all_failed),
        "uploaded_ids": all_uploaded,
        "failed_ids": all_failed
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
    TASK_NAME       = process_B_args["TASK_NAME"]
    BATCH_SIZE      = process_B_args["BATCH_SIZE"]
    TEACHER_UID     = process_B_args["TEACHER_UID"]
    status_checker  = process_B_args["status_checker"]
    PRODUCTION_MODE = process_B_args["PRODUCTION_MODE"]
    SAVE_LOGS       = process_B_args["SAVE_LOGS"]
    MAX_RETRY       = process_B_args["MAX_RETRY"]

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
                    logger.error(f"{TASK_NAME} - {sheets_result['message']}")
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
                        logger.error(f"{TASK_NAME} - {update_db_result['message']}")
                
                # Step 4: Save error in logs
                if SAVE_LOGS:
                    error_sheets = extraction_results["error"]
                    if len(error_sheets) > 0:
                        logger.error(f"{TASK_NAME} - Processing {len(error_sheets)} failed sheets from batch of {BATCH_SIZE}")
                        for error_sheet in error_sheets:
                            logger.error(f"{TASK_NAME} - {error_sheet['message']}")
            
            
            # ========== PROCESS SCORING ==========
            # Step 1: Fetch data from db
            sheets_result = answer_sheet_model.get_fields_by_processed_score_is_1(BATCH_SIZE)
            if sheets_result["status"] == "error":
                if SAVE_LOGS:
                    logger.error(f"{TASK_NAME} - {sheets_result['message']}")
            else:
                # Step 2: Score it!
                scoring_result = _scoring_by_batch(sheets_result["sheets"])

                # Step 3: Update database
                success_sheets = scoring_result["success"]
                for success_sheet in success_sheets:
                    update_db_result = answer_sheet_model.update_answer_key_scores_by_student_id(
                        score           = success_sheet["score"],
                        student_id      = success_sheet["student_id"],
                        processed_score = success_sheet["processed_score"],
                        processed_rtdb  = success_sheet["processed_rtdb"]
                    )
                    if update_db_result["status"] == "error" and SAVE_LOGS:
                        logger.error(f"{TASK_NAME} - {update_db_result['message']}")
                
                # Step 4: Log errors
                if SAVE_LOGS:
                    error_sheets = scoring_result["error"]
                    if len(error_sheets) > 0:
                        logger.error(f"{TASK_NAME} - Scoring failed for {len(error_sheets)} sheets")
                        for error_sheet in error_sheets:
                            logger.error(f"{TASK_NAME} - {error_sheet['message']}")
            
            
            # ========== PROCESS RTDB UPDATE ==========
            rtdb_result = _update_firebase_rtdb(BATCH_SIZE, TEACHER_UID)
            
            if rtdb_result["status"] == "error" and SAVE_LOGS:
                logger.error(f"{TASK_NAME} - Firebase upload failed: {rtdb_result.get('message', 'Unknown error')}")
            elif rtdb_result["status"] == "partial" and SAVE_LOGS:
                logger.warning(f"{TASK_NAME} - Partial Firebase upload: {rtdb_result['uploaded_count']} success, {rtdb_result['failed_count']} failed")
            elif rtdb_result["status"] == "success" and SAVE_LOGS and rtdb_result.get("uploaded_count", 0) > 0:
                logger.info(f"{TASK_NAME} - Firebase upload successful: {rtdb_result['uploaded_count']} records")
        
        except Exception as e:
            if SAVE_LOGS:
                logger.error(f"{TASK_NAME} - Unexpected error: {e}. Source: {__name__}")