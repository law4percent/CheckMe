# lib/processes/process_a_workers/scan_answer_sheet.py
import cv2
import time
from . import hardware
from datetime import datetime
import os
import json
import math
import numpy as np
from lib.services import answer_key_model, answer_sheet_model


def _smart_grid_auto(collected_images: list, tile_width: int) -> list:
    """Arrange multiple images into a grid layout."""
    imgs = [cv2.imread(p) for p in collected_images]
    imgs = [img for img in imgs if img is not None]
    n = len(imgs)
    
    if n == 0:
        return [
            None,
            {"status": "error", "message": "No valid images provided."}
        ]
    
    try:
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
    
    except Exception as e:
        return [
            None,
            {"status": "error", "message": f"Failed to combine images: {str(e)}"}
        ]


def _combine_images_into_grid(collected_images: list, tile_width: int = 600) -> list:
    """Combine multiple page images into a single grid image."""
    return _smart_grid_auto(collected_images, tile_width)


def _save_image_file(frame, img_full_path: str) -> dict:
    """Save image frame to disk with error handling."""
    try:
        os.makedirs(os.path.dirname(img_full_path), exist_ok=True)
        cv2.imwrite(img_full_path, frame)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save image: {str(e)}"}


def _naming_the_file(img_path: str, current_count: int) -> list:
    """
    Generate image filename with timestamp and page number.
    
    Format: {img_path}/{timestamp}_img{current_count}.jpg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(img_path, exist_ok=True)
    file_name = f"{now}_img{current_count}"
    return [
        f"{img_path}/{file_name}.jpg", 
        file_name
    ]


def _ask_for_number_of_sheets(keypad_rows_and_cols: list, pc_mode: bool, limit: int = 50) -> list:
    """Ask user for number of answer sheets with multi-digit input support."""
    rows, cols = keypad_rows_and_cols
    number_of_sheets = 1
    collected_input = ''
    while True:
        print("How many answer sheets? [*] Done or [#] Cancel")
        print(f"Current input: {collected_input}")
        time.sleep(0.1)
        key = hardware.read_keypad(rows, cols, pc_mode)
        if key is None:
            continue

        if key == '#':
            print("Cancelled entering number of answer sheets.")
            return [number_of_sheets, {"status": "cancelled"}]

        if key.isdigit():
            collected_input += key
            continue

        if key == '*':
            if collected_input == '':
                print("Please enter a valid number.")
                continue

            number_of_sheets = int(collected_input)

            if number_of_sheets < 1 or number_of_sheets > limit:
                print(f"Please enter a number between 1 and {limit}.")
                collected_input = ''
                continue

            return [number_of_sheets, {"status": "success"}]


def _ask_for_number_of_pages(keypad_rows_and_cols: list, pc_mode: bool) -> list:
    """Ask user for number of pages per answer sheet (1-9)."""
    rows, cols = keypad_rows_and_cols
    number_of_pages_per_sheet = 1
    while True:
        print("How many pages per answer sheet? [1-9] or [#] Cancel")
        time.sleep(0.1)
        key = hardware.read_keypad(rows, cols, pc_mode)
        if key is None:
            continue

        if key == '#':
            print("❌ Scanning cancelled by user")
            return [number_of_pages_per_sheet, {"status": "cancelled"}]

        if key not in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            continue

        number_of_pages_per_sheet = int(key)
        return [number_of_pages_per_sheet, {"status": "success"}]


def _has_essay(assessment_uid: str) -> list:
    """Check if assessment has essay questions (to be implemented with DB)."""
    try:
        # TODO: Implement database fetching logic
        has_essay = answer_key_model.get_has_essay_by_assessment_uid(assessment_uid)
        return [has_essay, {"status": "success"}]
    except Exception as e:
        return [False, {"status": "error", "message": str(e)}]


def _save_to_db(result: dict) -> dict:
    """Save answer sheet record to database."""
    try:
        answer_sheet_model.create_answer_sheet(
            assessment_uid  = result["assessment_uid"],
            number_of_pages = result["number_of_pages"],
            json_file_name  = result["json_file_name"],
            json_path       = result["json_path"],
            img_path        = result["img_path"],
            is_final_score  = result["is_final_score"]
        )
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": f"Database save failed: {str(e)}"}


def _handle_single_page_answer_sheet_workflow(
        key: str, 
        frame: any, 
        answer_sheet_image_path: str, 
        answer_sheet_json_path: str,
        current_count_sheets: int, 
        number_of_pages_per_sheet: int,
        assessment_uid: str, 
        has_essay: bool
    ) -> dict:
    """Handle single-page answer sheet workflow."""
    # Step 1: Check key input
    if key != '*':
        return {"status": "waiting"}
    
    # Step 2: Save captured frame
    img_full_path, file_name = _naming_the_file(
        img_path        = answer_sheet_image_path,
        current_count   = current_count_sheets
    )
    save_image_file_status = _save_image_file(
        frame           = frame,
        img_full_path   = img_full_path,
    )
    if save_image_file_status["status"] == "error":
        return save_image_file_status
    
    json_full_path = f"{answer_sheet_json_path}/{file_name}.json"
    return {
        "status"            : "success",
        "assessment_uid"    : assessment_uid,
        "number_of_pages"   : number_of_pages_per_sheet,
        "json_file_name"    : f"{file_name}.json",
        "json_path"         : json_full_path,
        "img_path"          : img_full_path,
        "is_final_score"    : not has_essay,
    }


def _handle_multi_page_answer_sheet_workflow(
        key: str, 
        frame: any,
        answer_sheet_image_path: str, 
        answer_sheet_json_path: str,
        current_count_sheets: int, 
        number_of_pages_per_sheet: int,
        assessment_uid: str, 
        has_essay: bool,
        current_count_page: int,
        collected_image_names: list
    ) -> dict:
    """Handle multi-page answer sheet workflow."""
    # Step 1: Check key input
    if key != '*':
        return {"status": "waiting"}
    
    # Step 2: Save individual page
    page_img_full_path, _ = _naming_the_file(
        img_path        = answer_sheet_image_path,
        current_count   = f"{current_count_sheets}_page{current_count_page}"
    )
    save_image_file_status = _save_image_file(
        frame           = frame,
        img_full_path   = page_img_full_path,
    )
    if save_image_file_status["status"] == "error":
        return save_image_file_status
    
    collected_image_names.append(page_img_full_path)
    print(f"✅ Page {current_count_page}/{number_of_pages_per_sheet} captured")

    # Step 3: Check if all pages are collected
    if current_count_page < number_of_pages_per_sheet:
        # More pages to scan for this sheet
        return {
            "status"    : "waiting",
            "next_page" : current_count_page + 1,
            "next_sheet": current_count_sheets
        }
    
    # All pages collected, combine them
    print(f"Combining {number_of_pages_per_sheet} pages... please wait")

    combined_image, combined_images_status = _combine_images_into_grid(collected_image_names)
    if combined_images_status["status"] == "error":
        return combined_images_status
    
    # Save combined image
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{now}_combined_img{current_count_sheets}"
    combined_img_full_path = os.path.join(answer_sheet_image_path, f"{file_name}.jpg")
    
    save_combined_status = _save_image_file(
        frame           = combined_image, 
        img_full_path   = combined_img_full_path
    )
    if save_combined_status["status"] == "error":
        return save_combined_status
    
    json_full_path = f"{answer_sheet_json_path}/{file_name}.json"
    
    # Return result with database info
    return {
        "status"            : "success",
        "assessment_uid"    : assessment_uid,
        "number_of_pages"   : number_of_pages_per_sheet,
        "json_file_name"    : f"{file_name}.json",
        "json_path"         : json_full_path,
        "img_path"          : combined_img_full_path,
        "is_final_score"    : not has_essay,
        "next_page"         : 1,  # Reset for next sheet
        "next_sheet"        : current_count_sheets + 1
    }


def _ask_for_prerequisites(keypad_rows_and_cols: list, assessment_uid: str, pc_mode: bool) -> dict:
    """Ask user for number of sheets and pages per sheet, and check for essay questions."""

    # Step 1: Ask for number of sheets
    number_of_sheets, number_of_sheets_status = _ask_for_number_of_sheets(keypad_rows_and_cols, pc_mode)
    if number_of_sheets_status["status"] == "cancelled":
        return number_of_sheets_status

    # Step 2: Ask for number of pages per answer sheet
    number_of_pages_per_sheet, number_of_pages_per_sheet_status = _ask_for_number_of_pages(keypad_rows_and_cols, pc_mode)
    if number_of_pages_per_sheet_status["status"] == "cancelled":
        return number_of_pages_per_sheet_status

    # Step 3: Check if assessment has essay questions
    has_essay, has_essay_status = _has_essay(assessment_uid)
    if has_essay_status["status"] == "error":
        return has_essay_status

    return {
        "status"                    : "success",
        "number_of_sheets"          : number_of_sheets,
        "number_of_pages_per_sheet" : number_of_pages_per_sheet,
        "has_essay"                 : has_essay
    }


def _cleanup(capture: any, show_windows: bool) -> None:
    """Release camera and close all OpenCV windows."""
    capture.release()
    if show_windows:
        cv2.destroyAllWindows()


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


def run(
        keypad_rows_and_cols: list,
        camera_index: int,
        show_windows: bool,
        answer_sheet_image_path: str,
        answer_sheet_json_path: str,
        assessment_uid: str,
        pc_mode: bool = False
    ) -> dict:
    """
        Main function to capture and process answer sheets.
        
        Args:
            keypad_rows_and_cols: [rows, cols] for keypad
            camera_index: Camera device index
            show_windows: Whether to display preview windows
            answer_sheet_image_path: Path to save answer sheet images
            answer_sheet_json_path: Path to save answer sheet JSON files
            assessment_uid: Assessment UID for lookup
            pc_mode: Whether running in PC mode
        
        Returns:
            Dictionary with status and results
    """
    rows, cols              = keypad_rows_and_cols
    count_sheets            = 1
    count_page_per_sheet    = 1
    collected_image_names   = []
    result = {"status": "waiting"}

    # Step 1: Initialize camera
    capture, camera_status = _initialize_camera(camera_index)
    if camera_status["status"] == "error":
        return camera_status
    
    # Step 2: Ask for prerequisites
    prerequisites = _ask_for_prerequisites(
        keypad_rows_and_cols    = keypad_rows_and_cols,
        assessment_uid          = assessment_uid,
        pc_mode                 = pc_mode
    )
    if prerequisites["status"] != "success":
        _cleanup(capture, show_windows)
        return prerequisites
    
    number_of_sheets            = prerequisites["number_of_sheets"]
    number_of_pages_per_sheet   = prerequisites["number_of_pages_per_sheet"]
    has_essay                   = prerequisites["has_essay"]

    # Step 3: Scan answer sheets based on number of sheets and pages
    while count_sheets <= number_of_sheets:
        progress = f"[{count_sheets}/{number_of_sheets}]"
        
        if number_of_pages_per_sheet > 1:
            print(f"\n{progress} Sheet {count_sheets} - Page {count_page_per_sheet}/{number_of_pages_per_sheet}")
        else:
            print(f"\n{progress} Sheet {count_sheets}")
        
        print(f"{progress} [*] CAPTURE IMAGE")
        print(f"{progress} [#] EXIT")
        time.sleep(0.1)

        key = hardware.read_keypad(rows, cols, pc_mode)

        if key is None or key not in ['*', '#']:
            ret, frame = capture.read()
            if ret and show_windows:
                cv2.imshow(f"Scanning Sheet {count_sheets}/{number_of_sheets}", frame)
            continue

        if key == '#':
            result = {"status": "cancelled"}
            break

        ret, frame = capture.read()
        if not ret:
            result = {
                "status"    : "error",
                "message"   : "Failed to capture frame"
            }
            break
        
        if show_windows:
            cv2.imshow(f"Scanning Sheet {count_sheets}/{number_of_sheets}", frame)
            cv2.waitKey(1)

        # Handle single-page answer sheets
        if number_of_pages_per_sheet == 1:
            result = _handle_single_page_answer_sheet_workflow(
                key                         = key,
                frame                       = frame,
                answer_sheet_image_path     = answer_sheet_image_path,
                answer_sheet_json_path      = answer_sheet_json_path,
                current_count_sheets        = count_sheets,
                number_of_pages_per_sheet   = number_of_pages_per_sheet,
                assessment_uid              = assessment_uid,
                has_essay                   = has_essay
            )
            
            if result["status"] == "waiting":
                continue
            
            elif result["status"] == "success":
                save_status = _save_to_db(result)
                if save_status["status"] == "error":
                    result = save_status
                    break
                
                print(f"✅ Sheet {count_sheets}/{number_of_sheets} saved")
                count_sheets += 1

            elif result["status"] == "error":
                break

        # Handle multi-page answer sheets
        else:
            result = _handle_multi_page_answer_sheet_workflow(
                key                         = key,
                frame                       = frame,
                answer_sheet_image_path     = answer_sheet_image_path,
                answer_sheet_json_path      = answer_sheet_json_path,
                current_count_sheets        = count_sheets,
                number_of_pages_per_sheet   = number_of_pages_per_sheet,
                assessment_uid              = assessment_uid,
                has_essay                   = has_essay,
                current_count_page          = count_page_per_sheet,
                collected_image_names       = collected_image_names
            )
            
            if result["status"] == "waiting":
                count_page_per_sheet = result["next_page"]
                continue
            
            elif result["status"] == "success":
                save_status = _save_to_db(result)
                if save_status["status"] == "error":
                    result = save_status
                    break
                
                print(f"✅ Sheet {count_sheets}/{number_of_sheets} completed and saved")
                count_sheets = result["next_sheet"]
                count_page_per_sheet = result["next_page"]
                collected_image_names.clear()
            
            elif result["status"] == "error":
                break

    _cleanup(capture, show_windows)
    
    if result["status"] == "success" or (result["status"] == "waiting" and count_sheets > number_of_sheets):
        print("✅ All answer sheets captured successfully")
        return {"status": "success", "message": "All sheets processed"}
    
    return result