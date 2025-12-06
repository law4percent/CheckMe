# lib/processes/process_a_workers/scan_answer_key.py
import cv2
import time
import json
import os
from . import hardware
from . import display
from lib.services.gemini import GeminiOCREngine
import math
import numpy as np
from datetime import datetime

"""
    Complete Answer Key Scanning Pipeline:
    1. Ask user for number of pages
    2. Ask user if there's an essay
    3. Scan/capture answer key pages one-by-one
    4. If multiple pages, combine them using smart grid algorithm
    5. Send combined image to Gemini for OCR extraction (includes reading assessment UID from paper)
    6. Save extracted answer key as JSON
"""

def _path_existence_checkpoint(target_path) -> dict:
    if not os.path.exists(target_path):
        return {
            "status"    : "error", 
            "message"   : f"{target_path} is not exist. From {__name__}."
        }
    return {"status": "success"}


def _file_existence_checkpoint(file_path) -> dict:
    if not os.path.isfile(file_path):
        return {
            "status"    : "error", 
            "message"   : f"{file_path} file does not exist. From {__name__}."
        }
    return {"status": "success"}


def _smart_grid_auto(collected_images: list, tile_width: int) -> dict:
    """Arrange multiple images into a grid layout."""
    imgs = [cv2.imread(p) for p in collected_images]
    imgs = [img for img in imgs if img is not None]
    n = len(imgs)

    if n == 0:
        return {
            "status"    : "error", 
            "message"   : f"No valid images provided. From {__name__}."
        }

    try:
        # Compute grid dimensions
        grid_size = math.ceil(math.sqrt(n))
        rows = grid_size
        cols = grid_size

        # Compute tile size
        ASPECT_RATIO = 1.4
        tile_height = int(tile_width * ASPECT_RATIO)
        tile_size = (tile_width, tile_height)

        # Resize images to uniform size
        resized_imgs = []
        for img in imgs:
            resized_imgs.append(cv2.resize(img, tile_size))

        # Fill empty slots with white images
        total_slots = rows * cols
        while len(resized_imgs) < total_slots:
            blank = np.full((tile_height, tile_width, 3), 255, dtype=np.uint8)
            resized_imgs.append(blank)

        # Build grid row by row
        row_list = []
        for r in range(rows):
            start = r * cols
            end = start + cols
            row_imgs = resized_imgs[start:end]
            row_list.append(np.hstack(row_imgs))

        # Combine rows vertically
        combined_image = np.vstack(row_list)
        return {
            "status": "success", 
            "frame" : combined_image
        }

    except Exception as e:
        return {
            "status": "error", 
            "message": f"{e}. From {__name__}."
        }


def _combine_images_into_grid(collected_images: list, tile_width: int = 600) -> dict:
    """Combine multiple page images into a single grid image."""
    return _smart_grid_auto(collected_images, tile_width)


def _get_JSON_of_answer_key(image_path: str) -> dict:
    """
        Send image to Gemini API for OCR extraction of answer key.
        Gemini reads the assessment UID directly from the paper.
        
        Args:
            image_path: Path to answer key image
        
        Returns:
            Extracted answer key
    """
    # Step 1: Check file existence
    file_status = _file_existence_checkpoint(image_path)
    if file_status["status"] == "error":
        return file_status
    
    try:
        gemini_engine = GeminiOCREngine()
        JSON_data = gemini_engine.extract_answer_key(image_path)
        
        # Step 2: Check the assessment uid and answer key existence
        assessment_uid_validation_result = _validate_the_assessment_uid_existence(JSON_data)
        if assessment_uid_validation_result["status"] == "error":
            return assessment_uid_validation_result
        
        answer_key_validation_result = _validate_the_answer_key_existence(JSON_data)
        if answer_key_validation_result["status"] == "error":
            return answer_key_validation_result
        
        return {
            "status"    : "success",
            "JSON_data" : JSON_data
        }
    
    except Exception as e:
        return {
            "status"    : "error", 
            "message"   : f"{e}. From {__name__}."
        }


def _save_image(frame: any, file_name: str, target_path: str) -> dict:
    """Save image frame to disk."""
    path_status = _path_existence_checkpoint(target_path)
    if path_status["status"] == "error":
        return path_status
        
    try:
        full_path = f"{target_path}/{file_name}"
        cv2.imwrite(full_path, frame)
        return {
            "status"    : "success",
            "full_path" : full_path
        }
    except Exception as e:
        return {
            "status"    : "error", 
            "message"   : f"Failed to save image: {str(e)}. From {__name__}."
        }


def _save_in_json_file(JSON_data: dict, target_path: str) -> dict:
    """
        Save extracted answer key as JSON file.
        Uses assessment_uid from the extracted data.
        
        Args:
            answer_key_data: Extracted answer key dictionary (contains assessment_uid)
            credentials_path: Path to credentials folder
        
        Returns:
            Path to saved JSON file, and status dictionary
    """
    # Step 1: Check the path existence
    path_status = _path_existence_checkpoint(target_path)
    if path_status["status"] == "error":
        return path_status
    
    # Step 3: Save into JSON file
    assessment_uid = str(JSON_data["assessment_uid"]).strip()
    json_file_name = f"{assessment_uid}.json"
    try:
        full_path = os.path.join(target_path, json_file_name)
        with open(full_path, 'w') as f:
            json.dump(JSON_data, f, indent=2)
        return {
            "status"        : "success",
            "full_path"     : full_path,
            "file_name"     : json_file_name,
            "assessment_uid": assessment_uid
        }
    except Exception as e:
        return {
            "status"    : "error", 
            "message"   : f"{e}. From {__name__}."
        }


def _naming_image_file(file_extension: str, is_combined_image: bool, current_count: int) -> str:
    """
        Generate image filename with timestamp and page number.
        
        Format: {timestamp}_img{current_count}.jpg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    if is_combined_image:
        return f"combined_img_{now}.{file_extension}"
    return f"img{current_count}_{now}.{file_extension}"


def _ask_for_number_of_pages(keypad_rows_and_cols: list, pc_mode: bool) -> dict:
    rows, cols = keypad_rows_and_cols
    number_of_pages = 1
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print("How many pages? [1-9] or [#] Cancel")
        # =================================
        key = hardware.read_keypad(rows, cols, pc_mode)
        if key is None:
            continue

        if key == '#':
            return {
                "number_of_pages"   : number_of_pages, 
                "status"            : "cancelled"
            }
        
        if key not in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            continue

        number_of_pages = int(key)
        return {
            "number_of_pages"   : number_of_pages, 
            "status"            : "success"
        }


def _ask_for_essay_existence(keypad_rows_and_cols: list, pc_mode: bool) -> dict:
    rows, cols = keypad_rows_and_cols
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print("Is there an essay? [*] YES or [#] NO")
        # =================================
        key = hardware.read_keypad(rows, cols, pc_mode)
        if key is None:
            continue

        if key == '#':
            return {
                "has_essay" : False, 
                "status"    : "success"
            }
        
        if key == '*':
            return {
                "status"          : "success",
                "essay_existence" : True 
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
    return {
        "status"   : "success",
        "file_name": file_name,
        "full_path": save_image["full_path"]
    }


def _validate_the_assessment_uid_existence(JSON_data: dict) -> dict:
    assessment_uid = JSON_data.get("assessment_uid")
    if not assessment_uid or str(assessment_uid).strip() == "":
        return {
            "status"    : "error",
            "message"   : (
                f"assessment_uid not found in the paper. Source: {__name__}\n"
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
        
    return {
        "status"        : "success",
        "assessment_uid": str(assessment_uid).strip()
    }
    

def _validate_the_answer_key_existence(JSON_data: dict) -> dict:
    answer_key = JSON_data.get("answer_key")
    if not answer_key or str(answer_key).strip() == "":
        return {
            "status"    : "error",
            "message"   : (
                f"answer_key not found in the paper. Source: {__name__}\n"
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
        
    return {
        "status"        : "success",
        "answer_key"    : str(answer_key).strip()
    }


def _handle_single_page_workflow(
        key: str,
        frame: any,
        answer_key_image_path: str,
        answer_key_json_path: str,
        essay_existence: bool,
        total_number_of_pages: int,
        image_extension: str
    ) -> dict:
    # ========USE LCD DISPLAY==========
    print(f"Put the answer key.")
    # =================================
    
    # Step 1: Check the key
    if key != '*':
        return {"status": "waiting"}

    # Step 2: Save in image file format
    image_details = _save_in_image_file(
        frame               = frame, 
        target_path         = answer_key_image_path, 
        current_page_count  = total_number_of_pages,
        image_extension     = image_extension
    )
    if image_details["status"] == "error":
        return image_details
    
    # Step 3: Get the JSON of answer key with Gemini OCR
    JSON_of_answer_key = _get_JSON_of_answer_key(image_path=image_details["full_path"])
    if JSON_of_answer_key["status"] == "error":
        return JSON_of_answer_key
    
    # Step 4: Save in JSON file format
    json_details = _save_in_json_file(
        JSON_data   = JSON_of_answer_key["JSON_data"],
        target_path = answer_key_json_path
    )
    if json_details["status"] == "error":
        return json_details
    
    return {
        "status"                : "success",
        "assessment_uid"        : json_details["assessment_uid"],
        "total_number_of_pages" : total_number_of_pages,
        "json_details"          : json_details,
        "image_details"         : image_details,
        "has_essay"             : essay_existence
    }


def _handle_multiple_pages_workflow(
        key: str,
        frame: any,
        answer_key_image_path: str,
        answer_key_json_path: str,
        essay_existence: bool,
        current_page_count: int,
        total_number_of_pages: int,
        collected_image_names: list,
        image_extension: str
    ) -> dict:
    # ========USE LCD DISPLAY==========
    ordinal_map = {1: 'st', 2: 'nd', 3: 'rd'}
    extension = ordinal_map.get(current_page_count, 'th')
    print(f"Put the {current_page_count}{extension} page.")
    # =================================
    
    # Step 1: Check the key
    if key != '*':
        return {
            "status"    : "waiting", 
            "next_page" : current_page_count
        }
        
    # Step 2: Save in image file format
    image_details = _save_in_image_file(
        frame               = frame, 
        target_path         = answer_key_image_path, 
        current_page_count  = current_page_count,
        image_extension     = image_extension
    )
    if image_details["status"] == "error":
        return image_details
    collected_image_names.append(image_details["full_path"])
    
    # Step 3: Check if the page count is still less than to total pages else proceed to combined all collected images
    if current_page_count < total_number_of_pages:
        return {
            "status"    : "waiting", 
            "next_page" : current_page_count + 1
        }
    
    # ========USE LCD DISPLAY==========
    print(f"Combining {current_page_count} pages... please wait")
    time.sleep(3)
    # =================================
    
    # Step 4: Combine images
    combined_image_details = _combine_images_into_grid(collected_image_names)
    if combined_image_details["status"] == "error":
        return combined_image_details
    
    # Step 5: Save in image file format
    image_details = _save_in_image_file(
        frame               = combined_image_details["frame"], 
        target_path         = answer_key_image_path,
        image_extension     = image_extension,
        is_combined_image   = True
    )
    if image_details["status"] == "error":
        return image_details
    
    # Step 6: Get the JSON of answer key with Gemini OCR
    JSON_of_answer_key = _get_JSON_of_answer_key(image_path=image_details["full_path"])
    if JSON_of_answer_key["status"] == "error":
        return JSON_of_answer_key

    # Step 7: Save in JSON file format    
    json_details = _save_in_json_file(
        JSON_data   = JSON_of_answer_key["JSON_data"],
        target_path = answer_key_json_path
    )
    if json_details["status"] == "error":
        return json_details
    
    return {
        "status"                : "success",
        "assessment_uid"        : json_details["assessment_uid"],
        "total_number_of_pages" : total_number_of_pages,
        "json_details"          : json_details,
        "image_details"         : image_details,
        "has_essay"             : essay_existence
    }


def _ask_for_prerequisites(keypad_rows_and_cols: list, pc_mode: bool) -> dict:
    # Ask for number of pages
    pages_result = _ask_for_number_of_pages(keypad_rows_and_cols, pc_mode)
    if pages_result["status"] == "cancelled":
        return pages_result

    # Ask for essay existence
    essay_result = _ask_for_essay_existence(keypad_rows_and_cols, pc_mode)
    if essay_result["status"] == "cancelled":
        return essay_result
    
    return {
        "status"            : "success",
        "number_of_pages"   : pages_result["number_of_pages"],
        "essay_existence"   : essay_result["essay_existence"]
    }


def _initialize_camera(camera_index: int) -> dict:
    """Initialize camera capture."""
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        return {
            "status"    : "error", 
            "message"   : f"Cannot open camera. From {__name__}."
        }
    return {
        "status"    : "success", 
        "capture"   : capture
    }


def _cleanup_camera(capture: any, show_windows: bool) -> None:
    """Release camera resources."""
    capture.release()
    if show_windows:
        cv2.destroyAllWindows()


def run(
        keypad_rows_and_cols: list,
        camera_index: int,
        show_windows: bool, 
        answer_key_paths: dict,
        pc_mode: bool,
        image_extension: str
    ) -> dict:

    """
        Main scanning workflow for answer key.
        Assessment UID is read from the paper by Gemini.
        
        Args:
            task_name: Name of the task
            keypad_rows_and_cols: [rows, cols] for keypad
            camera_index: Camera device index
            save_logs: Whether to save logs
            show_windows: Whether to display camera feed
            answer_key_path: Path to save scanned images
            credentials_path: Path to save JSON results
            pc_mode: Testing mode for development
        
        Returns:
            Dictionary with extraction results or error status
    """
    answer_key_image_path   = answer_key_paths["image_path"]
    answer_key_json_path    = answer_key_paths["json_path"]
    rows, cols              = keypad_rows_and_cols
    collected_image_names   = []
    count_page              = 1
    result                  = {"status": "waiting"}

    # Step 1: Initialize Camera
    camera_status = _initialize_camera(camera_index)
    if camera_status["status"] == "error":
        return camera_status
    capture = camera_status["capture"]
    
    # Step 2: Get prerequisites
    prerequisites = _ask_for_prerequisites(keypad_rows_and_cols, pc_mode)
    if prerequisites["status"] == "cancelled":
        _cleanup_camera(capture, show_windows)
        return prerequisites
    number_of_pages = prerequisites["number_of_pages"]
    essay_existence = prerequisites["essay_existence"]

    while True:
        time.sleep(0.1) # <-- Reduce CPU usage and debounce keypad inpud but still experimental
        # ========USE LCD DISPLAY==========
        print("[*] SCAN | [#] CANCEL")
        # =================================

        ret, frame = capture.read()
        if not ret:
            result = {
                "status"    : "error",
                "message"   : f"Failed to capture frame. From {__name__}."
            }
            break
        
        if show_windows:
            cv2.imshow(f"Scanning Sheet {count_page}/{number_of_pages}", frame)
            cv2.waitKey(1)

        key = hardware.read_keypad(rows, cols, pc_mode)

        if key is None or key not in ['*', '#']:
            continue

        if key == '#':
            result = {"status": "cancelled"}
            break

        # Step 3: Process according to number of pages
        # ========== SINGLE PAGE WORKFLOW ==========
        if number_of_pages == 1:
            result = _handle_single_page_workflow(
                key                     = key,
                frame                   = frame,
                answer_key_image_path   = answer_key_image_path,
                answer_key_json_path    = answer_key_json_path, 
                essay_existence         = essay_existence,
                total_number_of_pages   = number_of_pages,
                image_extension         = image_extension
            )
            if result["status"] == "waiting":
                continue
            break
        
        # ========== MULTIPLE PAGES WORKFLOW ==========
        else:
            result = _handle_multiple_pages_workflow(
                key                     = key,
                frame                   = frame,
                answer_key_image_path   = answer_key_image_path,
                answer_key_json_path    = answer_key_json_path,
                essay_existence         = essay_existence,
                current_page_count      = count_page,
                total_number_of_pages   = number_of_pages,
                collected_image_names   = collected_image_names,
                image_extension         = image_extension
            )
            if result["status"] == "waiting":
                count_page = result["next_page"]
                continue
            break

    _cleanup_camera(capture, show_windows)
    return result