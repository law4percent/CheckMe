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

def _smart_grid_auto(collected_images: list, tile_width: int) -> list:
    """Arrange multiple images into a grid layout."""
    imgs = [cv2.imread(p) for p in collected_images]
    imgs = [img for img in imgs if img is not None]
    n = len(imgs)
    
    if n == 0:
        return [
            '',
            {"status": "error", "message": "No valid images to combine"}
        ]
    
    # Compute grid dimensions
    grid_size = math.ceil(math.sqrt(n))
    rows = grid_size
    cols = grid_size

    # Compute tile size
    tile_height = int(tile_width * 1.4)
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
    return [
        combined_image,
        {"status": "success"}
    ]


def _combine_images_into_grid(collected_images: list, tile_width: int = 600):
    """Combine multiple page images into a single grid image."""
    return _smart_grid_auto(collected_images, tile_width)


def _get_JSON_of_answer_key(image_path: str) -> list:
    """
        Send image to Gemini API for OCR extraction of answer key.
        Gemini reads the assessment UID directly from the paper.
        
        Args:
            image_path: Path to answer key image
        
        Returns:
            Extracted answer key dictionary and status dictionary
    """
    answer_key = {}
    try:
        gemini_engine = GeminiOCREngine()
        answer_key = gemini_engine.extract_answer_key(image_path)
        
        return [
            answer_key, 
            {"status": "success"}
        ]
    
    except Exception as e:
        print(f"Error extracting answer key: {e}")
        return [
            answer_key, 
            {"status": "error", "message": str(e)}
        ]


def _save_image_file(frame, img_full_path: str) -> dict:
    """Save image frame to disk."""
    try:
        os.makedirs(os.path.dirname(img_full_path), exist_ok=True)
        cv2.imwrite(img_full_path, frame)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save image: {str(e)}"}


def _save_answer_key_json(answer_key_data: dict, answer_key_json_path: str, assessment_uid: str) -> list:
    """
        Save extracted answer key as JSON file.
        Uses assessment_uid from the extracted data.
        
        Args:
            answer_key_data: Extracted answer key dictionary (contains assessment_uid)
            credentials_path: Path to credentials folder
        
        Returns:
            Path to saved JSON file, and status dictionary
    """
    try:
        os.makedirs(answer_key_json_path, exist_ok=True)
        json_path = os.path.join(answer_key_json_path, f"{assessment_uid}.json")
        
        with open(json_path, 'w') as f:
            json.dump(answer_key_data, f, indent=2)
        
        return [
            json_path,
            {"status": "success"}
        ]
    except Exception as e:
        return [
            "",
            {"status": "error", "message": f"Failed to save JSON: {str(e)}"}
        ]


def _naming_the_file(img_path: str, current_count: int) -> str:
    """
        Generate image filename with timestamp and page number.
        
        Format: {img_path}/{timestamp}_img{current_count}.jpg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{img_path}/{now}_img{current_count}.jpg"


def _ask_for_number_of_pages(keypad_rows_and_cols: list) -> list:
    rows, cols = keypad_rows_and_cols
    number_of_pages = 1
    while True:
        print("How many pages does? [1-9] or [#] Cancel")
        time.sleep(0.1)  # Reduce CPU usage and debounce keypad input
        key = hardware.read_keypad(rows=rows, cols=cols)
        if key is None:
            continue

        if key == '#':
            print("❌ Scanning cancelled by user")
            return [number_of_pages, {"status": "cancelled"}]
        

        if key not in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            continue

        number_of_pages = int(key)
        return [number_of_pages, {"status": "success"}]


def _ask_for_essay_existence(keypad_rows_and_cols) -> list:
    rows, cols = keypad_rows_and_cols
    while True:
        print("Is there an essay? [*] YES or [#] NO")
        time.sleep(0.1)  # Reduce CPU usage and debounce keypad input
        key = hardware.read_keypad(rows=rows, cols=cols)
        if key is None:
            continue

        if key == '#':
            print("Essay existence: NO")
            return [False, {"status": "success"}]
        
        if key == '*':
            print("Essay existence: YES")
            return [True, {"status": "success"}]


def _handle_single_page_workflow(
        key: str,
        frame: any,
        answer_key_image_path: str,
        answer_key_json_path: str,
        essay_existence: bool,
        number_of_pages: int
    ) -> dict:
    if key != '*':
        return {"status": "waiting"}

    img_full_path = _naming_the_file(
        img_path        = answer_key_image_path,
        current_count   = number_of_pages
    )
    save_image_file_status = _save_image_file(
        frame           = frame, 
        img_full_path   = img_full_path
    )
    if save_image_file_status["status"] == "error":
        return save_image_file_status
    
    answer_key_data, answer_key_data_status = _get_JSON_of_answer_key(image_path=img_full_path)
    if answer_key_data_status["status"] == "error":
        return answer_key_data_status

    assessment_uid = answer_key_data.get("assessment_uid")
    if not assessment_uid:
        return {
            "status"    : "error",
            "message"   : "assessment_uid not found on paper"
        }
    
    answer_key_data["has_essay"]    = essay_existence
    answer_key_data["total_pages"]  = number_of_pages
    json_path, json_path_status = _save_answer_key_json(
        answer_key_data         = answer_key_data,
        answer_key_json_path    = answer_key_json_path,
        assessment_uid          = assessment_uid
    )
    if json_path_status["status"] == "error":
        return json_path_status
    
    return {
        "status"                : "success",
        "assessment_uid"        : assessment_uid,
        "pages"                 : number_of_pages,
        "answer_key_data"       : answer_key_data,
        "answer_key_json_path"  : json_path
    }


def _handle_multiple_pages_workflow(
        key: str,
        frame: any,
        answer_key_image_path: str,
        answer_key_json_path: str,
        essay_existence: bool,
        count_page: int,
        number_of_pages: int,
        collected_image_names: list
    ) -> dict:

    # Generate ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
    ordinal_map = {1: 'st', 2: 'nd', 3: 'rd'}
    extension = ordinal_map.get(count_page, 'th')
    print(f"Put the {count_page}{extension} page.")
    if key != '*':
        return {
            "status"    : "waiting", 
            "next_page" : count_page
        }

    img_full_path = _naming_the_file(
        img_path        = answer_key_image_path,
        current_count   = count_page
    )
    collected_image_names.append(img_full_path)
    save_image_file_status = _save_image_file(
        frame           = frame, 
        img_full_path   = img_full_path
    )
    if save_image_file_status["status"] == "error":
        return save_image_file_status
    
    if count_page == number_of_pages:
        print(f"Combining {count_page} pages... please wait")
        
        # Combine images
        combined_image, combined_images_status = _combine_images_into_grid(collected_image_names)
        if combined_images_status["status"] == "error":
            return combined_images_status
        now             = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_path   = os.path.join(answer_key_image_path, f"{now}_combined_img.jpg")
        _save_image_file(
            frame           = combined_image, 
            img_full_path   = combined_path
        )
        answer_key_data, answer_key_data_status = _get_JSON_of_answer_key(image_path=combined_path)
        if answer_key_data_status["status"] == "error":
            return answer_key_data_status

        assessment_uid = answer_key_data.get("assessment_uid")
        if not assessment_uid:
            return {
                "status"    : "error",
                "message"   : "assessment_uid not found on paper"
            }
        
        answer_key_data["has_essay"]    = essay_existence
        answer_key_data["total_pages"]  = number_of_pages
        json_path, json_path_status = _save_answer_key_json(
            answer_key_data         = answer_key_data,
            answer_key_json_path    = answer_key_json_path,
            assessment_uid          = assessment_uid
        )
        if json_path_status["status"] == "error":
            return json_path_status
        
        print("✅ Successfully scanned and extracted answer key!")
        return {
            "status"                : "success",
            "assessment_uid"        : assessment_uid,
            "pages"                 : number_of_pages,
            "answer_key_data"       : answer_key_data,
            "answer_key_json_path"  : json_path
        }

    return {
        "status"    : "waiting", 
        "next_page" : count_page + 1
    }


def _ask_for_prerequisites(keypad_rows_and_cols: list) -> dict:
    # Step 1: Ask for number of pages
    number_of_pages, number_of_pages_status = _ask_for_number_of_pages(keypad_rows_and_cols)
    if number_of_pages_status["status"] == "cancelled":
        return number_of_pages_status

    # Step 2: Ask for essay existence
    essay_existence, essay_existence_status = _ask_for_essay_existence(keypad_rows_and_cols)
    if essay_existence_status["status"] == "cancelled":
        return essay_existence_status
    
    return {
        "number_of_pages"   : number_of_pages,
        "essay_existence"   : essay_existence,
        "status"            : "success"
    }


def _initialize_camera(camera_index: int) -> list:
    """Initialize camera capture."""
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        return [
            capture,
            {"status": "error", "message": "Cannot open camera"}
        ]
    return [
        capture,
        {"status": "success"}
    ]


def _cleanup_camera(capture: any, show_windows: bool) -> None:
    """Release camera resources."""
    capture.release()
    if show_windows:
        cv2.destroyAllWindows()


def run(
        task_name: str,
        keypad_rows_and_cols: list,
        camera_index: int, 
        save_logs: bool, 
        show_windows: bool, 
        answer_key_image_path: str,
        answer_key_json_path: str,
        pc_mode: bool = False
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

    rows, cols                      = keypad_rows_and_cols
    collected_image_names           = []
    count_page                      = 1
    result                          = {"status": "waiting"}

    capture, camera_status = _initialize_camera(camera_index)
    if camera_status["status"] == "error":
        _cleanup_camera(capture, show_windows)
        return camera_status
    
    # Step 1 & 2: Get prerequisites
    prerequisites = _ask_for_prerequisites(keypad_rows_and_cols)
    if prerequisites["status"] == "cancelled":
        _cleanup_camera(capture, show_windows)
        return prerequisites
    number_of_pages = prerequisites["number_of_pages"]
    essay_existence = prerequisites["essay_existence"]

    while True:
        # Display menu
        print("[*] SCAN")
        print("[#] EXIT")
        time.sleep(0.1) # <-- Reduce CPU usage and debounce keypad inpud but still experimental

        key = hardware.read_keypad(rows=rows, cols=cols)

        if key == None or key not in ['*', '#']:
            result = {"status": "waiting"}
            continue

        if key == '#':
            result = {"status": "cancelled"}
            break
        
        # Capture frame from camera
        ret, frame = capture.read()
        if not ret:
            result = {
                "status"    : "error",
                "message"   : "Failed to capture image"
            }
            break

        if show_windows:
            cv2.imshow(f"Scanning Answer Key {count_page}/{number_of_pages}", frame)

        # Step 3: Process according to number of pages
        # ========== SINGLE PAGE WORKFLOW ==========
        if number_of_pages == 1:
            result = _handle_single_page_workflow(
                key                     = key,
                frame                   = frame,
                answer_key_image_path   = answer_key_image_path,
                answer_key_json_path    = answer_key_json_path,
                essay_existence         = essay_existence,
                number_of_pages         = number_of_pages
            )
            if result.get("status") == "waiting":
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
                count_page              = count_page,
                number_of_pages         = number_of_pages,
                collected_image_names   = collected_image_names
            )
            if result.get("status") == "waiting":
                count_page = result["next_page"]
                continue
            break

    _cleanup_camera(capture, show_windows)
    return result