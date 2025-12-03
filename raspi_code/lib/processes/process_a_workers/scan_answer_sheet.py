import cv2
import time
from . import hardware
from datetime import datetime
import os
import json
import math
import numpy as np
from lib.services.gemini import GeminiOCREngine


def _smart_grid_auto(collected_images: list, tile_width: int):
    """Arrange multiple images into a grid layout."""
    imgs = [cv2.imread(p) for p in collected_images]
    imgs = [img for img in imgs if img is not None]
    n = len(imgs)
    
    # if n == 0: <==== for investigation
    #     raise ValueError("No valid images provided.")
    
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


def _get_JSON_of_answer_key(image_path: str):
    """
        Send image to Gemini API for OCR extraction of answer key.
        Gemini reads the assessment UID directly from the paper.
        
        Args:
            image_path: Path to answer key image
        
        Returns:
            Extracted answer key as dictionary (includes assessment_uid read from paper)
    """
    try:
        gemini_engine = GeminiOCREngine()
        answer_key = gemini_engine.extract_answer_key(image_path)
        
        return answer_key
    
    except Exception as e:
        print(f"Error extracting answer key: {e}")
        return {"error": str(e)}


def _save_image_file(frame, img_full_path: str):
    """Save image frame to disk."""
    # os.makedirs(os.path.dirname(img_full_path), exist_ok=True) <- Need to investigate
    cv2.imwrite(img_full_path, frame)


def _save_answer_key_json(answer_key_data: dict, answer_key_json_path: str):
    """
        Save extracted answer key as JSON file.
        Uses assessment_uid from the extracted data.
        
        Args:
            answer_key_data: Extracted answer key dictionary (contains assessment_uid)
            credentials_path: Path to credentials folder
        
        Returns:
            Path to saved JSON file or None if assessment_uid not found
    """
    assessment_uid = answer_key_data.get("assessment_uid")
    
    if not assessment_uid:
        print("❌ Error: assessment_uid not found in extracted data")
        return None
    
    # os.makedirs(answer_key_json_path, exist_ok=True) <- Need to investigate
    json_path = os.path.join(answer_key_json_path, f"{assessment_uid}.json")
    
    with open(json_path, 'w') as f:
        json.dump(answer_key_data, f, indent=2)
    
    print(f"Answer key saved to: {json_path}")
    return json_path


def _naming_the_file(img_path: str, current_count: int) -> str:
    """
        Generate image filename with timestamp and page number.
        
        Format: {img_path}/{timestamp}_img{current_count}.jpg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    # os.makedirs(img_path, exist_ok=True) <- Need to investigate
    return f"{img_path}/{now}_img{current_count}.jpg"


def _ask_for_number_of_sheets(key: str, is_answered_number_of_sheets: bool, number_of_sheets: int) -> int:
    if is_answered_number_of_sheets:
        return [number_of_sheets, True]
    
    collect_input = ''
    print("How many answer sheets? [*] Done or [#] Cancel")
    while True:
        time.sleep(0.1)
        key = hardware.read_keypad()
        if key == None:
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
            print(f"Number of answer sheets set to {number_of_sheets}.")
            return [number_of_sheets, True]

        elif key == '#':
            print("Cancelled entering number of answer sheets.")
            return [0, False]


def _ask_for_number_of_pages(key: str, is_answered_number_of_pages: bool, number_of_pages: int) -> int:
    if is_answered_number_of_pages:
        return [number_of_pages, True]
    
    print("How many pages per answer sheets? [1-9]")
    if not key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
        return [1, False]
    
    number_of_pages = int(key)
    return [number_of_pages, True]


def _has_essay(assessmen_uid: str) -> bool:
    # will handle db fetching later
    return False


def _handle_single_page_answer_sheet(capture, show_windows: bool, answer_sheet_images_path: str, answer_sheet_jsons_path: str, sheet_count: int, page_count: int) -> dict:
    pass


def _handle_multi_page_answer_sheet(capture, show_windows: bool, answer_sheet_images_path: str, answer_sheet_jsons_path: str, sheet_count: int, page_count: int) -> dict:
    pass



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

    rows, cols                      = keypad_rows_and_cols
    capture                         = cv2.VideoCapture(camera_index)

    number_of_sheets                = 1
    count_sheets                    = 1
    is_answered_number_of_sheets    = False

    number_of_pages                 = 1
    is_answered_number_of_pages     = False

    essay_existence                 = _has_essay("dummy_assessment_uid") # to be replaced with real assessment_uid
    result                          = {"status": "waiting"}

    if not capture.isOpened():
        print("Error - Cannot open camera")
        return {"error": "Camera not accessible", "status": "error"}
    
    while True:
        time.sleep(0.1) # <-- Reduce CPU usage and debounce keypad inpud but still experimental

        key = hardware.read_keypad(rows=rows, cols=cols)
        if key == None:
            continue

        # Step 1: Ask for number of sheets
        number_of_sheets, is_answered_number_of_sheets = _ask_for_number_of_sheets(key, is_answered_number_of_sheets, number_of_sheets)
        if not is_answered_number_of_sheets:
            continue

        # ✅ Step 2: Ask for number of pages per answer sheet
        number_of_pages, is_answered_number_of_pages = _ask_for_number_of_pages(key, is_answered_number_of_pages, number_of_pages)
        if not is_answered_number_of_pages:
            continue


        # Step 3: Scan answer sheets based on number of sheets and pages
        if count_sheets <= number_of_sheets:
            count_pages = 1
            while count_pages <= number_of_pages:
                ret, frame = capture.read()
                if not ret:
                    print("Error - Failed to capture image")
                    capture.release()
                    cv2.destroyAllWindows()
                    return {"error": "Failed to capture image", "status": "error"}
                cv2.imshow("Capture Preview - Press 'c' to capture", frame)

                # Handle single-page answer sheet
                if number_of_pages == 1:
                    pass

                # Handle multi-page answer sheet
                else:
                    pass
                
                if result["status"] != "success":
                    capture.release()
                    cv2.destroyAllWindows()
                    break
                
                count_pages += 1

            # Save to database can be handled here if needed

            count_sheets += 1
        else:
            break