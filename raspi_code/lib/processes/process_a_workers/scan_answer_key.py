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
        
        Format: {img_path}/{timestamp}_img{current_count}.jpeg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    # os.makedirs(img_path, exist_ok=True) <- Need to investigate
    return f"{img_path}/{now}_img{current_count}.jpeg"


def run(
        task_name: str,
        keypad_rows_and_cols: list,
        camera_index: int, 
        save_logs: bool, 
        show_windows: bool, 
        answer_key_path: str,
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
    capture                         = cv2.VideoCapture(camera_index)
    collected_image_names           = []
    number_of_sheets                = 1
    count_page                      = 1
    is_answered_number_of_sheets    = False
    essay_existence                 = False
    is_answered_essay_existence     = False

    if not capture.isOpened():
        print("Error - Cannot open camera")
        return {"error": "Camera not accessible"}

    while True:
        time.sleep(3)

        key = '1' # hardware.read_keypad(rows=rows, cols=cols)

        # Step 1: Ask for number of sheets
        if not is_answered_number_of_sheets:
            print("How many pages? [1-9]")
            if key and key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                number_of_sheets                = int(key)
                is_answered_number_of_sheets    = True
                continue
            continue

        # Step 2: Ask for essay existence
        if not is_answered_essay_existence:
            print("Is there an essay? [1]Y/[2]N")
            if key and key in ['1', '2']:
                essay_existence             = (key == '1')
                is_answered_essay_existence = True
                print("================")
                print("Analyzing data...")
                print(f"Number of pages: {number_of_sheets}")
                print(f"Has essay: {essay_existence}")
                print("================")
                time.sleep(2)
                continue
            continue
    
        # Capture frame from camera
        ret, frame = capture.read()
        if not ret:
            print("Error - Check the camera")
            continue

        # Display menu
        print("[1] SCAN")
        print("[2] EXIT")

        if show_windows:
            cv2.imshow("CheckMe-ScanAnswerSheet", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # ========== SINGLE PAGE WORKFLOW ==========
        if number_of_sheets == 1:
            if key and key in ['1', '2']:
                if key == display.ScanAnswerKeyOption.SCAN.value:
                    img_full_path = _naming_the_file(
                        img_path        = answer_key_path,
                        current_count   = count_page
                    )
                    _save_image_file(frame=frame, img_full_path=img_full_path)
                    print(f"✅ Scanned single page: {img_full_path}")
                    
                    # Extract answer key using Gemini (includes assessment_uid from paper)
                    print("Extracting answer key with Gemini OCR...")
                    answer_key = _get_JSON_of_answer_key(image_path="answer_keys/images/answer_key.docx_page-0001.jpg") #img_full_path)
                    
                    if "error" not in answer_key:
                        # Verify assessment_uid was extracted
                        assessment_uid = answer_key.get("assessment_uid")
                        if not assessment_uid:
                            print("❌ Extraction failed: assessment_uid not found on paper")
                            capture.release()
                            if show_windows:
                                cv2.destroyAllWindows()
                            return {"error": "assessment_uid not found on paper"}
                        
                        # Add essay flag
                        answer_key["has_essay"] = essay_existence
                        
                        # Save JSON result
                        json_path = _save_answer_key_json(
                            answer_key_data         = answer_key,
                            answer_key_json_path    = answer_key_json_path
                        )
                        
                        if json_path:
                            print("✅ Successfully scanned and extracted answer key!")
                            capture.release()
                            if show_windows:
                                cv2.destroyAllWindows()
                            return {
                                "status"            : "success",
                                "assessment_uid"    : assessment_uid,
                                "answer_key"        : answer_key,
                                "saved_path"        : json_path
                            }
                        else:
                            return {"error": "Failed to save answer key JSON"}
                    else:
                        print(f"❌ Extraction failed: {answer_key.get('error')}")
                        capture.release()
                        if show_windows:
                            cv2.destroyAllWindows()
                        return {"error": answer_key.get('error')}
                
                elif key == display.ScanAnswerKeyOption.EXIT.value:
                    capture.release()
                    if show_windows:
                        cv2.destroyAllWindows()
                    return {"status": "cancelled"}
        
        # ========== MULTIPLE PAGES WORKFLOW ==========
        elif number_of_sheets > 1:
            # Generate ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
            ordinal_map = {1: 'st', 2: 'nd', 3: 'rd'}
            extension = ordinal_map.get(count_page, 'th')
            print(f"Put the {count_page}{extension} page.")

            if key and key in ['1', '2']:
                if key == display.ScanAnswerKeyOption.SCAN.value:
                    img_full_path = _naming_the_file(
                        img_path        = answer_key_path,
                        current_count   = count_page
                    )
                    collected_image_names.append(img_full_path)
                    _save_image_file(frame=frame, img_full_path=img_full_path)
                    print(f"✅ Scanned {count_page}{extension} page at {img_full_path}")
                    
                    # Check if all pages collected
                    if count_page == number_of_sheets:
                        print(f"Combining {count_page} pages... please wait")
                        
                        # Combine images
                        combined_image = _combine_images_into_grid(collected_image_names)
                        now = datetime.now().strftime("%Y%m%d_%H%M%S")
                        combined_path = os.path.join(answer_key_path, f"{now}_combined_grid.jpg")
                        _save_image_file(frame=combined_image, img_full_path=combined_path)
                        print("✅ Pages combined successfully")
                        
                        # Extract answer key from combined image (includes assessment_uid from paper)
                        print("Extracting answer key with Gemini OCR...")
                        answer_key = _get_JSON_of_answer_key(image_path=combined_path)
                        
                        if "error" not in answer_key:
                            # Verify assessment_uid was extracted
                            assessment_uid = answer_key.get("assessment_uid")
                            if not assessment_uid:
                                print("❌ Extraction failed: assessment_uid not found on paper")
                                capture.release()
                                if show_windows:
                                    cv2.destroyAllWindows()
                                return {"error": "assessment_uid not found on paper"}
                            
                            # Add metadata
                            answer_key["has_essay"]     = essay_existence
                            answer_key["total_pages"]   = number_of_sheets
                            
                            # Save JSON result
                            json_path = _save_answer_key_json(
                                answer_key_data     = answer_key,
                                answer_key_json_path    = answer_key_json_path
                            )
                            
                            if json_path:
                                print("✅ Successfully scanned and extracted answer key!")
                                capture.release()
                                if show_windows:
                                    cv2.destroyAllWindows()
                                return {
                                    "status"            : "success",
                                    "assessment_uid"    : assessment_uid,
                                    "pages"             : number_of_sheets,
                                    "answer_key"        : answer_key,
                                    "saved_path"        : json_path
                                }
                            else:
                                return {"error": "Failed to save answer key JSON"}
                        else:
                            print(f"❌ Extraction failed: {answer_key.get('error')}")
                            capture.release()
                            if show_windows:
                                cv2.destroyAllWindows()
                            return {"error": answer_key.get('error')}
                    
                    count_page += 1
                
                elif key == display.ScanAnswerKeyOption.EXIT.value:
                    print(f"❌ Scanning cancelled at page {count_page}/{number_of_sheets}")
                    capture.release()
                    if show_windows:
                        cv2.destroyAllWindows()
                    return {"status": "cancelled"}
    
    capture.release()
    if show_windows:
        cv2.destroyAllWindows()
    
    return {"status": "exited"}