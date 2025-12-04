import cv2
import time
from . import hardware
from datetime import datetime
import os
import json
import math
import numpy as np


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


def _naming_the_file(img_path: str, current_count: int) -> str:
    """
    Generate image filename with timestamp and page number.
    
    Format: {img_path}/{timestamp}_img{current_count}.jpg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(img_path, exist_ok=True)
    return f"{img_path}/{now}_img{current_count}.jpg"


def _ask_for_number_of_sheets(keypad_rows_and_cols: list, limit: int = 50) -> list:
    """Ask user for number of answer sheets with multi-digit input support."""
    rows, cols = keypad_rows_and_cols
    number_of_sheets = 1
    collected_input = ''
    while True:
        print("How many answer sheets? [*] Done or [#] Cancel")
        print(f"Current input: {collected_input}")
        time.sleep(0.1)
        key = hardware.read_keypad(rows=rows, cols=cols)
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


def _ask_for_number_of_pages(keypad_rows_and_cols: list) -> list:
    """Ask user for number of pages per answer sheet (1-9)."""
    rows, cols = keypad_rows_and_cols
    number_of_pages_per_sheet = 1
    while True:
        print("How many pages per answer sheet? [1-9] or [#] Cancel")
        time.sleep(0.1)
        key = hardware.read_keypad(rows=rows, cols=cols)
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
        has_essay = False
        return [has_essay, {"status": "success"}]
    except Exception as e:
        return [False, {"status": "error", "message": str(e)}]


def _handle_single_page_answer_sheet(
        capture,
        show_windows: bool,
        answer_sheet_images_path: str,
        sheet_count: int,
        rows: int,
        cols: int
    ) -> dict:
    """Capture and process single-page answer sheet using 4x3 keypad."""
    collected_images = []
    page_count = 1
    
    print(f"📄 Sheet {sheet_count}: Press [2] to capture or [8] to finish")
    
    while True:
        ret, frame = capture.read()
        if not ret:
            return {
                "status": "error",
                "message": "Failed to capture frame"
            }
        
        if show_windows:
            cv2.imshow(f"Sheet {sheet_count} - Press [2] Capture [8] Finish", frame)
        
        key = hardware.read_keypad(rows=rows, cols=cols)
        
        if key == '2':
            # Capture image
            img_path = _naming_the_file(answer_sheet_images_path, sheet_count)
            save_status = _save_image_file(frame, img_path)
            if save_status["status"] == "error":
                return save_status
            collected_images.append(img_path)
            print(f"✅ Captured: {img_path}")
            return {
                "status": "success",
                "images": collected_images,
                "page_count": page_count
            }
        
        elif key == '8':
            return {
                "status": "success",
                "images": collected_images,
                "page_count": page_count
            }
        
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
            return {
                "status": "error",
                "message": "Failed to capture frame"
            }
        
        if show_windows:
            cv2.imshow(f"Sheet {sheet_count} Page {page_count}/{number_of_pages} - [2] Capture [8] Finish", frame)
        
        key = hardware.read_keypad(rows=rows, cols=cols)
        
        if key == '2':
            # Capture image
            img_index = (sheet_count - 1) * number_of_pages + page_count
            img_path = _naming_the_file(answer_sheet_images_path, img_index)
            save_status = _save_image_file(frame, img_path)
            if save_status["status"] == "error":
                return save_status
            collected_images.append(img_path)
            print(f"✅ Captured Page {page_count}: {img_path}")
            page_count += 1
        
        elif key == '8':
            if page_count <= number_of_pages:
                print(f"⚠️  Warning: Only {page_count - 1} pages captured out of {number_of_pages}")
            return {
                "status": "success",
                "images": collected_images,
                "page_count": page_count - 1
            }
        
        time.sleep(0.05)
    
    return {
        "status": "success",
        "images": collected_images,
        "page_count": page_count - 1
    }


def _ask_for_prerequisites(keypad_rows_and_cols: list, assessment_uid: str) -> dict:
    """Ask user for number of sheets and pages per sheet, and check for essay questions."""

    # Step 1: Ask for number of sheets
    number_of_sheets, status = _ask_for_number_of_sheets(keypad_rows_and_cols)
    if status["status"] == "cancelled":
        print("❌ Scanning cancelled by user")
        return status

    # Step 2: Ask for number of pages per answer sheet
    number_of_pages_per_sheet, status = _ask_for_number_of_pages(keypad_rows_and_cols)
    if status["status"] == "cancelled":
        print("❌ Scanning cancelled by user")
        return status

    # Step 3: Check if assessment has essay questions
    has_essay, status = _has_essay(assessment_uid)
    if status["status"] == "error":
        print("❌ Error checking for essay questions")
        return status

    return {
        "number_of_sheets": number_of_sheets,
        "number_of_pages_per_sheet": number_of_pages_per_sheet,
        "has_essay": has_essay,
        "status": "success"
    }


def _cleanup(capture) -> None:
    """Release camera and close all OpenCV windows."""
    capture.release()
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
        task_name: str,
        keypad_rows_and_cols: list,
        camera_index: int,
        save_logs: bool,
        show_windows: bool,
        answer_sheet_images_path: str,
        answer_sheet_jsons_path: str,
        assessment_uid: str,
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
            assessment_uid: Assessment UID for lookup
            pc_mode: Whether running in PC mode
        
        Returns:
            Dictionary with status and results
    """
    rows, cols = keypad_rows_and_cols
    count_sheets = 1
    result = {"status": "waiting"}

    # Step 1: Initialize camera
    capture, camera_status = _initialize_camera(camera_index)
    if camera_status["status"] == "error":
        return camera_status
    
    # Step 2: Ask for prerequisites
    prerequisites = _ask_for_prerequisites(
        keypad_rows_and_cols=keypad_rows_and_cols,
        assessment_uid=assessment_uid
    )
    if prerequisites["status"] != "success":
        _cleanup(capture)
        return prerequisites
    
    number_of_sheets = prerequisites["number_of_sheets"]
    number_of_pages_per_sheet = prerequisites["number_of_pages_per_sheet"]
    has_essay = prerequisites["has_essay"]

    # Step 3: Scan answer sheets based on number of sheets and pages
    while count_sheets <= number_of_sheets:
        # Display menu
        print(f"Sheet {count_sheets}/{number_of_sheets}")
        print("[*] START SCANNING")
        print("[#] EXIT")
        time.sleep(0.1)

        key = hardware.read_keypad(rows=rows, cols=cols)

        if key is None:
            continue

        if key == '#':
            _cleanup(capture)
            return {"status": "cancelled"}

        if key != '*':
            continue

        ret, frame = capture.read()
        if not ret:
            _cleanup(capture)
            return {
                "status": "error",
                "message": "Failed to capture frame"
            }
        
        if show_windows:
            cv2.imshow(f"Scanning Sheet {count_sheets}/{number_of_sheets}", frame)

        # Handle single-page answer sheets
        if number_of_pages_per_sheet == 1:
            result = _handle_single_page_answer_sheet(
                capture=capture,
                show_windows=show_windows,
                answer_sheet_images_path=answer_sheet_images_path,
                sheet_count=count_sheets,
                rows=rows,
                cols=cols
            )

            if result["status"] == "error":
                _cleanup(capture)
                print(f"❌ {result.get('message', 'Unknown error')}")
                return result
            
            if result["status"] == "cancelled":
                _cleanup(capture)
                print("⚠️  Scanning cancelled by user")
                return result
            
            count_sheets += 1

        # Handle multi-page answer sheets
        else:
            result = _handle_multi_page_answer_sheet(
                capture=capture,
                show_windows=show_windows,
                answer_sheet_images_path=answer_sheet_images_path,
                sheet_count=count_sheets,
                number_of_pages=number_of_pages_per_sheet,
                rows=rows,
                cols=cols
            )
        
            if result["status"] == "error":
                _cleanup(capture)
                print(f"❌ {result.get('message', 'Unknown error')}")
                return result
            
            if result["status"] == "cancelled":
                _cleanup(capture)
                print("⚠️  Scanning cancelled by user")
                return result
            
            count_sheets += 1

    # All sheets captured successfully
    _cleanup(capture)
    print("✅ All answer sheets captured successfully")
    return {
        "status": "success",
        "message": "All sheets scanned",
        "number_of_sheets": number_of_sheets,
        "pages_per_sheet": number_of_pages_per_sheet,
        "has_essay": has_essay
    }