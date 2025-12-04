import cv2
import time
from . import hardware
from datetime import datetime
import os
import json
import math
import numpy as np


def _smart_grid_auto(collected_images: list, tile_width: int):
    """Arrange multiple images into a grid layout."""
    imgs = [cv2.imread(p) for p in collected_images]
    imgs = [img for img in imgs if img is not None]
    n = len(imgs)
    
    if n == 0:
        raise ValueError("No valid images provided.")
    
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
    return combined_image


def _combine_images_into_grid(collected_images: list, tile_width: int = 600):
    """Combine multiple page images into a single grid image."""
    combined_image = _smart_grid_auto(collected_images, tile_width)
    return combined_image


def _save_image_file(frame, img_full_path: str):
    """Save image frame to disk."""
    os.makedirs(os.path.dirname(img_full_path), exist_ok=True)
    cv2.imwrite(img_full_path, frame)


def _naming_the_file(img_path: str, current_count: int) -> str:
    """
    Generate image filename with timestamp and page number.
    
    Format: {img_path}/{timestamp}_img{current_count}.jpg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(img_path, exist_ok=True)
    return f"{img_path}/{now}_img{current_count}.jpg"


def _ask_for_number_of_sheets(key: str, is_answered_number_of_sheets: bool, number_of_sheets: int, limit: int = 50) -> list:
    if is_answered_number_of_sheets:
        return [number_of_sheets, True]
    
    collect_input = ''
    print("How many answer sheets? [*] Done or [#] Cancel")
    while True:
        time.sleep(0.1)
        key = hardware.read_keypad()
        if key is None:
            continue

        if key.isdigit():
            collect_input += key
            print(f"Current input: {collect_input}")
            continue

        if key == '*':
            if collect_input == '':
                print("Please enter a valid number.")
                continue

            number_of_sheets = int(collect_input)
            if number_of_sheets < 1 or number_of_sheets > limit:
                print(f"Please enter a number between 1 and {limit}.")
                collect_input = ''
                continue

            print(f"Number of answer sheets set to {number_of_sheets}.")
            return [number_of_sheets, True]

        elif key == '#':
            print("Cancelled entering number of answer sheets.")
            return [0, False]


def _ask_for_number_of_pages(key: str, is_answered_number_of_pages_per_sheet: bool, number_of_pages_per_sheet: int) -> list:
    if is_answered_number_of_pages_per_sheet:
        return [number_of_pages_per_sheet, True]
    
    print("How many pages per answer sheets? [1-9]")
    if key not in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
        return [number_of_pages_per_sheet, False]
    
    number_of_pages_per_sheet = int(key)
    return [number_of_pages_per_sheet, True]


def _has_essay(assessment_uid: str) -> bool:
    """Check if assessment has essay questions (to be implemented with DB)."""
    # will handle db fetching later
    return False


def _handle_single_page_answer_sheet(
        capture, 
        show_windows: bool, 
        answer_sheet_images_path: str, 
        sheet_count: int, 
        page_count: int,
        rows: int,
        cols: int
    ) -> dict:
    """Capture and process single-page answer sheet using 4x3 keypad."""
    collected_images = []
    
    print(f"📄 Sheet {sheet_count}: Press [*] to capture or [#] to finish")
    
    while True:
        ret, frame = capture.read()
        if not ret:
            return {
                "status": "error", 
                "message": "Failed to capture frame"
            }
        
        if show_windows:
            cv2.imshow(f"Sheet {sheet_count}", frame)
        
        key = hardware.read_keypad(rows=rows, cols=cols)
        
        if key == '2':
            # Capture image
            img_path = _naming_the_file(answer_sheet_images_path, page_count)
            _save_image_file(frame, img_path)
            collected_images.append(img_path)
            print(f"✅ Captured: {img_path}")
            return {"status": "success", "images": collected_images}
        
        elif key == '8':
            return {"status": "cancelled", "images": collected_images}
        
        time.sleep(0.05)


def _handle_multi_page_answer_sheet(
        capture, 
        show_windows: bool, 
        answer_sheet_images_path: str, 
        sheet_count: int, 
        number_of_pages: int,
        rows: int,
        cols: int
    ) -> dict:
    """Capture and process multi-page answer sheet using 4x3 keypad."""
    collected_images = []
    page_count = 1
    
    while page_count <= number_of_pages:
        print(f"📄 Sheet {sheet_count} Page {page_count}/{number_of_pages}: Press [2] to capture or [8] to finish")
        
        ret, frame = capture.read()
        if not ret:
            return {"status": "error", "message": "Failed to capture frame"}
        
        if show_windows:
            cv2.imshow(f"Sheet {sheet_count} Page {page_count}/{number_of_pages} - [2] Capture [8] Finish", frame)
        
        key = hardware.read_keypad(rows=rows, cols=cols)
        
        if key == '2':
            # Capture image
            img_path = _naming_the_file(answer_sheet_images_path, (sheet_count - 1) * number_of_pages + page_count)
            _save_image_file(frame, img_path)
            collected_images.append(img_path)
            print(f"✅ Captured Page {page_count}: {img_path}")
            page_count += 1
        
        elif key == '8':
            if page_count <= number_of_pages:
                print(f"⚠️  Warning: Only {page_count - 1} pages captured out of {number_of_pages}")
            return {"status": "success", "images": collected_images}
        
        time.sleep(0.05)
    
    return {"status": "success", "images": collected_images}


def _ask_for_prerequisites(rows: int, cols: int, number_of_sheets, is_answered_number_of_sheets, number_of_pages_per_sheet, is_answered_number_of_pages_per_sheet) -> None:
    while True:
        time.sleep(0.1)  # Reduce CPU usage and debounce keypad input

        key = hardware.read_keypad(rows=rows, cols=cols)
        if key is None:
            continue

        # Step 1: Ask for number of sheets
        number_of_sheets, is_answered_number_of_sheets = _ask_for_number_of_sheets(
            key                             = key, 
            is_answered_number_of_sheets    = is_answered_number_of_sheets, 
            number_of_sheets                = number_of_sheets
        )
        if not is_answered_number_of_sheets:
            continue

        # Step 2: Ask for number of pages per answer sheet
        number_of_pages_per_sheet, is_answered_number_of_pages_per_sheet = _ask_for_number_of_pages(
            key                                     = key, 
            is_answered_number_of_pages_per_sheet   = is_answered_number_of_pages_per_sheet, 
            number_of_pages_per_sheet               = number_of_pages_per_sheet
        )
        if not is_answered_number_of_pages_per_sheet:
            continue

        return {
            "number_of_sheets"                      : number_of_sheets, 
            "is_answered_number_of_sheets"          : is_answered_number_of_sheets, 
            "number_of_pages_per_sheet"             : number_of_pages_per_sheet, 
            "is_answered_number_of_pages_per_sheet" : is_answered_number_of_pages_per_sheet
        }


def run(
        task_name: str,
        keypad_rows_and_cols: list,
        camera_index: int, 
        save_logs: bool, 
        show_windows: bool, 
        answer_sheet_images_path: str,
        answer_sheet_jsons_path: str,
        pc_mode: bool = False
    ) -> dict:
    """
    Main function to capture and process answer sheets.
    
    Args:
        task_name: Name of the task
        keypad_rows_and_cols: [rows, cols] for keypad
        camera_index: Camera device index
        save_logs: Whether to save logs
        show_windows: Whether to display preview windows
        answer_sheet_images_path: Path to save answer sheet images
        answer_sheet_jsons_path: Path to save answer sheet JSON files
        pc_mode: Whether running in PC mode
    
    Returns:
        Dictionary with status and results
    """
    rows, cols                              = keypad_rows_and_cols
    capture                                 = cv2.VideoCapture(camera_index)

    number_of_sheets                        = 1
    count_sheets                            = 1
    is_answered_number_of_sheets            = False

    number_of_pages_per_sheet               = 1
    is_answered_number_of_pages_per_sheet   = False

    essay_existence                         = _has_essay("dummy_assessment_uid")  # to be replaced with real assessment_uid
    result                                  = {"status": "waiting"}

    if not capture.isOpened():
        print("❌ Error - Cannot open camera")
        return {
            "error": "Camera not accessible", 
            "status": "error"
        }
    
    print("🎯 Answer Sheet Scanner Started")
    # Step 1 & 2: Ask for number of sheets and pages per sheet
    prerequisites = _ask_for_prerequisites(
        rows, 
        cols, 
        number_of_sheets, 
        is_answered_number_of_sheets, 
        number_of_pages_per_sheet, 
        is_answered_number_of_pages_per_sheet
    )
    number_of_sheets                        = prerequisites["number_of_sheets"]
    is_answered_number_of_sheets            = prerequisites["is_answered_number_of_sheets"]
    number_of_pages_per_sheet               = prerequisites["number_of_pages_per_sheet"]
    is_answered_number_of_pages_per_sheet   = prerequisites["is_answered_number_of_pages_per_sheet"]

    # Step 3: Scan answer sheets based on number of sheets and pages
    while count_sheets <= number_of_sheets:
        
        if number_of_pages_per_sheet == 1:
            result = _handle_single_page_answer_sheet(
                capture, 
                show_windows, 
                answer_sheet_images_path, 
                count_sheets, 
                count_sheets,
                rows,
                cols
            )
        else:
            result = _handle_multi_page_answer_sheet(
                capture, 
                show_windows, 
                answer_sheet_images_path, 
                count_sheets, 
                number_of_pages_per_sheet,
                rows,
                cols
            )
        
        if result["status"] == "error":
            capture.release()
            cv2.destroyAllWindows()
            print(f"❌ {result.get('message', 'Unknown error')}")
            return result
        
        if result["status"] == "cancelled":
            print("⚠️  Scanning cancelled by user")
            capture.release()
            cv2.destroyAllWindows()
            return {"status": "cancelled", "sheets_completed": count_sheets - 1}
        
        count_sheets += 1

    # All sheets captured successfully
    capture.release()
    cv2.destroyAllWindows()
    print("✅ All answer sheets captured successfully")
    return {
        "status": "success",
        "sheets_count": number_of_sheets,
        "pages_per_sheet": number_of_pages_per_sheet,
        "total_images": number_of_sheets * number_of_pages_per_sheet
    }