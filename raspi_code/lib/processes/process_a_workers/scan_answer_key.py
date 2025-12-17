# lib/processes/process_a_workers/scan_answer_key.py
import cv2
import time
import json
import os
from datetime import datetime

from lib.hardware import camera_contoller as camera
from lib.services.gemini import GeminiOCREngine
from lib.services import utils, image_combiner

"""
    Complete Answer Key Scanning Pipeline:
    1. Ask user for number of pages
    2. Ask user if there's an essay
    3. Scan/capture answer key pages one-by-one
    4. If multiple pages, combine them using smart grid algorithm
    5. Send combined image to Gemini for OCR extraction (includes reading assessment UID from paper)
    6. Save extracted answer key as JSON
"""

def _get_JSON_of_answer_key(image_path: str, MAX_RETRY: int) -> dict:
    """
        Send image to Gemini API for OCR extraction of answer key.
        Gemini reads the assessment UID directly from the paper.
        
        Args:
            image_path: Path to answer key image
        
        Returns:
            Extracted JSON data of answer key
    """
    # Step 1: Check file existence
    file_status = utils.file_existence_checkpoint(image_path, __name__)
    if file_status["status"] == "error":
        return file_status
    
    try:
        gemini_engine = GeminiOCREngine()
        extraction_result = gemini_engine.extract_answer_key(image_path, MAX_RETRY)
        
        # Step 2: Check the status
        if extraction_result["status"] == "error":
            return extraction_result

        return {
            "status"    : "success",
            "JSON_data" : extraction_result["result"]
        }
    
    except Exception as e:
        return {
            "status"    : "error", 
            "message"   : f"{e}. Source: {__name__}."
        }


def _save_image(frame: any, file_name: str, target_path: str) -> dict:
    """Save image frame to disk."""
    path_status = utils.path_existence_checkpoint(target_path, __name__)
    if path_status["status"] == "error":
        return path_status
        
    try:
        full_path = utils.join_path_with_os_adaptability(
            TARGET_PATH = target_path,
            FILE_NAME   = file_name,
            SOURCE      = __name__,
            create_one  = False
        )
        cv2.imwrite(full_path, frame)
        return {
            "status"    : "success",
            "full_path" : full_path
        }
    except Exception as e:
        return {
            "status"    : "error", 
            "message"   : f"Failed to save image: {str(e)}. Source: {__name__}."
        }


def _save_in_json_file(json_data: dict, target_path: str) -> dict:
    """
        Save extracted answer key as JSON file.
        Uses assessment_uid from the extracted data.
        
        Args:
            answer_key_data: Extracted answer key dictionary (contains assessment_uid)
        
        Returns:
            Path to saved JSON file, and status dictionary
    """
    # Step 1: Check the path existence
    path_status = utils.path_existence_checkpoint(target_path, __name__)
    if path_status["status"] == "error":
        return path_status
    
    # Step 3: Save into JSON file
    assessment_uid = str(json_data["assessment_uid"]).strip()
    json_file_name = f"{assessment_uid}.json"
    try:
        full_path = utils.join_path_with_os_adaptability(
            TARGET_PATH = target_path,
            FILE_NAME   = json_file_name,
            SOURCE      = __name__,
            create_one  = False
        )
        with open(full_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        json_file_validation_result = utils.file_existence_checkpoint(full_path, __name__)
        if json_file_validation_result["status"] == "error":
            return json_file_validation_result
        
        return {
            "status"        : "success",
            "full_path"     : full_path,
            "file_name"     : json_file_name,
            "assessment_uid": assessment_uid
        }
    except Exception as e:
        return {
            "status"    : "error", 
            "message"   : f"{e}. Source: {__name__}."
        }


def _naming_image_file(file_extension: str, is_combined_image: bool, current_count: int) -> str:
    """
        Generate image filename with timestamp and page number.
        
        Format: {timestamp}_img{current_count}.jpg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    if is_combined_image:
        return f"combined_img_DT_{now}.{file_extension}"
    return f"img{current_count}_DT_{now}.{file_extension}"


def _ask_for_number_of_pages(scan_key) -> dict:
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print("How many pages? [1-9] or [#] Cancel")
        # =================================
        key = scan_key()
        if key is None or key in ['0', '*']:
            continue

        if key == '#':
            return {"status": "cancelled"}

        total_number_of_pages = int(key)
        return {
            "total_number_of_pages" : total_number_of_pages, 
            "status"                : "success"
        }


def _ask_for_essay_existence(scan_key) -> dict:
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print("Is there an essay? [*] YES or [#] NO")
        # =================================

        key = scan_key()
        if key is None or key not in ['#', '*']:
            continue

        if key == '#':
            return {
                "status"            : "success",
                "essay_existence"   : False, 
            }
        
        if key == '*':
            return {
                "status"            : "success",
                "essay_existence"   : True 
            }


def _save_in_image_file(frame: any, target_path: str, image_extension: str, is_combined_image: bool = False, current_page_count: int = 0) -> dict:
    file_name = _naming_image_file(
        current_count       = current_page_count, 
        file_extension      = image_extension,
        is_combined_image   = is_combined_image
    )
    save_image = _save_image(
        frame           = frame, 
        file_name       = file_name,
        target_path     = target_path
    )
    if save_image["status"] == "error":
        return save_image
    full_path = save_image["full_path"]

    image_file_validation_result = utils.file_existence_checkpoint(full_path, __name__)
    if image_file_validation_result["status"] == "error":
        return image_file_validation_result

    return {
        "status"   : "success",
        "file_name": file_name,
        "full_path": full_path
    }


def _handle_single_page_workflow(
        KEY: str,
        FRAME: any,
        IMAGE_PATH: str,
        JSON_PATH: str,
        ESSAY_EXISTENCE: bool,
        TOTAL_NUMBER_OF_PAGES: int,
        IMAGE_EXTENSION: str,
        MAX_RETRY: int
    ) -> dict:
    # ========USE LCD DISPLAY==========
    print(f"Put the answer key.")
    # =================================
    
    # Step 1: Check the key
    if KEY != '*':
        return {"status": "waiting"}

    # Step 2: Save in image file format
    image_details = _save_in_image_file(
        frame               = FRAME, 
        target_path         = IMAGE_PATH, 
        current_page_count  = TOTAL_NUMBER_OF_PAGES,
        image_extension     = IMAGE_EXTENSION
    )
    if image_details["status"] == "error":
        return image_details
    
    # Step 3: Get the JSON of answer key with Gemini OCR
    JSON_of_answer_key = _get_JSON_of_answer_key(
        image_path  = image_details["full_path"], 
        MAX_RETRY   = MAX_RETRY
    )
    if JSON_of_answer_key["status"] == "error":
        return JSON_of_answer_key
    JSON_data = JSON_of_answer_key["JSON_data"]

    # Step 4: Save in JSON file format
    json_details = _save_in_json_file(
        json_data   = JSON_data,
        target_path = JSON_PATH
    )
    if json_details["status"] == "error":
        return json_details
    
    return {
        "status"                    : "success",
        "assessment_uid"            : json_details["assessment_uid"],
        "total_number_of_pages"     : TOTAL_NUMBER_OF_PAGES,
        "json_details"              : json_details,
        "image_details"             : image_details,
        "essay_existence"           : ESSAY_EXISTENCE,
        "total_number_of_questions" : len(JSON_data["answers"])
    }


def _handle_multiple_pages_workflow(
        KEY: str,
        FRAME: any,
        IMAGE_PATH: str,
        JSON_PATH: str,
        ESSAY_EXISTENCE: bool,
        CURRENT_PAGE_COUNT: int,
        TOTAL_NUMBER_OF_PAGES: int,
        COLLECTED_IMAGES: list,
        IMAGE_EXTENSION: str,
        TILE_WIDTH: int,
        MAX_RETRY: int
    ) -> dict:
    # ========USE LCD DISPLAY==========
    ordinal_map = {1: 'st', 2: 'nd', 3: 'rd'}
    extension = ordinal_map.get(CURRENT_PAGE_COUNT, 'th')
    print(f"Put the {CURRENT_PAGE_COUNT}{extension} page.")
    # =================================
    
    # Step 1: Check the key
    if KEY != '*':
        return {
            "status"    : "waiting", 
            "next_page" : CURRENT_PAGE_COUNT
        }
        
    # Step 2: Save in image file format
    image_details = _save_in_image_file(
        frame               = FRAME, 
        target_path         = IMAGE_PATH, 
        current_page_count  = CURRENT_PAGE_COUNT,
        image_extension     = IMAGE_EXTENSION
    )
    if image_details["status"] == "error":
        utils.cleanup_temporary_images(COLLECTED_IMAGES)
        return image_details
    COLLECTED_IMAGES.append(image_details["full_path"])
    
    # Step 3: Check if the page count is still less than to total pages else proceed to combined all collected images
    if CURRENT_PAGE_COUNT < TOTAL_NUMBER_OF_PAGES:
        return {
            "status"    : "waiting", 
            "next_page" : CURRENT_PAGE_COUNT + 1
        }
    
    # ========USE LCD DISPLAY==========
    print(f"Combining {CURRENT_PAGE_COUNT} pages... please wait")
    time.sleep(3)
    # =================================
    
    # Step 4: Combine images
    combined_image_result = image_combiner.combine_images_into_grid(COLLECTED_IMAGES, TILE_WIDTH)
    if combined_image_result["status"] == "error":
        utils.cleanup_temporary_images(COLLECTED_IMAGES)
        return combined_image_result
    
    # Step 5: Save in image file format
    image_details = _save_in_image_file(
        frame               = combined_image_result["frame"], 
        target_path         = IMAGE_PATH,
        image_extension     = IMAGE_EXTENSION,
        is_combined_image   = True
    )
    if image_details["status"] == "error":
        utils.cleanup_temporary_images(COLLECTED_IMAGES)
        return image_details
    
    # Step 6: Get the JSON of answer key with Gemini OCR]
    JSON_of_answer_key = _get_JSON_of_answer_key(
        image_path  = image_details["full_path"], 
        MAX_RETRY   = MAX_RETRY
    )
    if JSON_of_answer_key["status"] == "error":
        utils.cleanup_temporary_images(COLLECTED_IMAGES)
        return JSON_of_answer_key
    JSON_data = JSON_of_answer_key["JSON_data"]

    # Step 7: Save in JSON file format    
    json_details = _save_in_json_file(
        json_data   = JSON_data,
        target_path = JSON_PATH
    )
    if json_details["status"] == "error":
        utils.cleanup_temporary_images(COLLECTED_IMAGES)
        return json_details
    
    # Step 8: Cleanup temporary individual page images
    utils.cleanup_temporary_images(COLLECTED_IMAGES)
    
    return {
        "status"                    : "success",
        "assessment_uid"            : json_details["assessment_uid"],
        "total_number_of_pages"     : TOTAL_NUMBER_OF_PAGES,
        "json_details"              : json_details,
        "image_details"             : image_details,
        "essay_existence"           : ESSAY_EXISTENCE,
        "total_number_of_questions" : len(JSON_data["answers"])
    }


def _ask_for_prerequisites(scan_key) -> dict:
    # Ask for number of pages
    pages_result = _ask_for_number_of_pages(scan_key)
    if pages_result["status"] == "cancelled":
        return pages_result

    # Ask for essay existence
    essay_result = _ask_for_essay_existence(scan_key)
    if essay_result["status"] == "cancelled":
        return essay_result
    
    return {
        "status"                    : "success",
        "total_number_of_pages"     : pages_result["total_number_of_pages"],
        "essay_existence"           : essay_result["essay_existence"]
    }


def run(
        scan_key,
        SHOW_WINDOWS: bool, 
        PATHS: dict,
        PRODUCTION_MODE: bool,
        IMAGE_EXTENSION: str,
        TILE_WIDTH: int,
        FRAME_DIMENSIONS: dict,
        MAX_RETRY: int
    ) -> dict:
    """
        Main scanning workflow for answer key.
        Assessment UID is read from the paper by Gemini.
        
        Args:
            scan_key: scan_key() function
            SHOW_WINDOWS: Whether to display camera feed
            PATHS: Path to save scanned images of answer keys
            PRODUCTION_MODE: Testing mode or for production mode
            IMAGE_EXTENSION: Image file extension (e.g., 'jpg', 'png').
            TILE_WIDTH: Grid dimension
        
        Returns:
            dict: A dictionary containing:
                - "status": Operation status ("success" or "error" or "cancelled").
                - "assessment_uid": Extracted assessment UID from Gemini.
                - "total_number_of_pages": Number of scanned pages.
                - "json_details": Metadata extracted from the answer key
                                (contains keys "full_path" and "file_name").
                - "image_details": Information about saved image files
                                (contains keys "full_path" and "file_name").
                - "essay_existence": Boolean indicating if the assessment contains an essay section.
                - "total_number_of_questions": Number of questions in a questionnaire
                - "message": Error message (if failed).
    """
    IMAGE_PATH      = PATHS["image_path"]
    JSON_PATH       = PATHS["json_path"]
    collected_images= []
    count_page      = 1
    result          = {"status": "waiting"}

    # Step 1: Initialize Camera & start camera
    config_result = camera.config_camera(FRAME_DIMENSIONS)
    if config_result["status"] == "error":
        return config_result
    capture = config_result["capture"]
    capture.start()
    
    # Step 2: Get prerequisites
    prerequisites = _ask_for_prerequisites(scan_key)
    if prerequisites["status"] == "cancelled":
        camera.cleanup_camera(capture)
        return prerequisites
    total_number_of_pages   = prerequisites["total_number_of_pages"]
    essay_existence         = prerequisites["essay_existence"]

    try:
        while True:
            time.sleep(0.1)
            # ========USE LCD DISPLAY==========
            print("[*] SCAN | [#] CANCEL")
            # =================================
            frame = capture.capture_array()
            frame = cv2.resize(frame, (FRAME_DIMENSIONS["width"], FRAME_DIMENSIONS["height"]))
            
            if SHOW_WINDOWS:
                cv2.imshow("Answer Key Scanner", frame)
                cv2.waitKey(1)

            key = scan_key()

            if key is None or key not in ['*', '#']:
                continue

            if key == '#':
                result = {"status": "cancelled"}
                if len(collected_images) > 0:
                    utils.cleanup_temporary_images(collected_images)
                break

            # Step 3: Process according to number of pages
            # ========== SINGLE PAGE WORKFLOW ==========
            if total_number_of_pages == 1:
                result = _handle_single_page_workflow(
                    KEY                     = key,
                    FRAME                   = frame,
                    IMAGE_PATH              = IMAGE_PATH,
                    JSON_PATH               = JSON_PATH, 
                    ESSAY_EXISTENCE         = essay_existence,
                    TOTAL_NUMBER_OF_PAGES   = total_number_of_pages,
                    IMAGE_EXTENSION         = IMAGE_EXTENSION,
                    MAX_RETRY               = MAX_RETRY
                )
                if result["status"] == "waiting":
                    continue
                break
            
            # ========== MULTIPLE PAGES WORKFLOW ==========
            else:
                result = _handle_multiple_pages_workflow(
                    KEY                     = key,
                    FRAME                   = frame,
                    IMAGE_PATH              = IMAGE_PATH,
                    JSON_PATH               = JSON_PATH,
                    ESSAY_EXISTENCE         = essay_existence,
                    CURRENT_PAGE_COUNT      = count_page,
                    TOTAL_NUMBER_OF_PAGES   = total_number_of_pages,
                    COLLECTED_IMAGES        = collected_images,
                    IMAGE_EXTENSION         = IMAGE_EXTENSION,
                    TILE_WIDTH              = TILE_WIDTH,
                    MAX_RETRY               = MAX_RETRY
                )
                if result["status"] == "waiting":
                    count_page = result["next_page"]
                    continue
                break

    except Exception as e:
        camera.cleanup_camera(capture)
        return {
            "status"    : "error",
            "message"   : f"{e} Source: {__name__}"
        }

    finally:
        camera.cleanup_camera(capture)
        return result