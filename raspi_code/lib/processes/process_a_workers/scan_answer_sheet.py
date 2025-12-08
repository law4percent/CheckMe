# lib/processes/process_a_workers/scan_answer_sheet.py
import cv2
import time
from . import hardware
from . import camera
from . import image_combiner
from datetime import datetime
import os
from lib.services import answer_key_model, answer_sheet_model, utils


def _ask_for_number_of_sheets(keypad_rows_and_cols: list, pc_mode: bool, limit: int = 50) -> dict:
    """Ask user for number of answer sheets with multi-digit input support."""
    rows, cols = keypad_rows_and_cols
    collected_input = ''
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print("How many answer sheets? [*] Done or [#] Cancel")
        print(f"Current input: {collected_input}")
        # =================================
        key = hardware.read_keypad(rows, cols, pc_mode)
        if key is None:
            continue

        if key == '#':
            return {"status": "cancelled"}

        if key.isdigit():
            collected_input += key
            continue

        if key == '*':
            if collected_input == '':
                # ========USE LCD DISPLAY==========
                print("Please enter a valid number.")
                # =================================
                continue

            total_number_of_sheets = int(collected_input)

            if total_number_of_sheets < 1 or total_number_of_sheets > limit:
                # ========USE LCD DISPLAY==========
                print(f"Please enter a number between 1 and {limit}.")
                # =================================
                collected_input = ''
                continue

            return {
                "status"                    : "success",
                "total_number_of_sheets"    : total_number_of_sheets
            }


def _ask_for_number_of_pages(keypad_rows_and_cols: list, pc_mode: bool) -> dict:
    """Ask user for number of pages per answer sheet (1-9)."""
    rows, cols = keypad_rows_and_cols
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print("How many pages per answer sheet? [1-9] or [#] Cancel")
        # =================================
        key = hardware.read_keypad(rows, cols, pc_mode)
        if key is None:
            continue

        if key == '#':
            return {"status": "cancelled"}

        if key not in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            continue

        total_number_of_pages_per_sheet = int(key)
        return {
                "status"                            : "success",
                "total_number_of_pages_per_sheet"   : total_number_of_pages_per_sheet
            }


def _check_essay_existence_in_db(assessment_uid: str) -> dict:
    """Check if assessment has essay questions."""
    try:
        # TODO: Implement database fetching logic
        essay_existence = answer_key_model.get_has_essay_by_assessment_uid(assessment_uid)
        return {
            "status"            : "success",
            "essay_existence"   : essay_existence
        }
    except Exception as e:
        return {
            "status"    : "error",
            "message"   : f"{e}. Source: {__name__}."
        }


def _naming_image_file(file_extension: str, is_combined_image: bool, current_sheet_count: int, current_page_count: int) -> str:
    """
        Generate image filename with timestamp and page number.
        
        Format: {timestamp}_img{current_count}.jpg
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    if is_combined_image:
        return f"combined_img_{now}.{file_extension}"
    
    if current_sheet_count > 0:
        return f"img_sheet{current_sheet_count}_{now}.{file_extension}"
    
    return f"img{current_page_count}_{now}.{file_extension}"


def _save_image(frame: any, file_name: str, target_path: str) -> dict:
    """Save image frame to disk."""
    path_status = utils.path_existence_checkpoint(target_path)
    if path_status["status"] == "error":
        return path_status
        
    try:
        full_path = os.path.join(target_path, file_name)
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


def _save_in_image_file(frame: any, target_path: str, image_extension: str, is_combined_image: bool = False, current_sheet_count: int = 0, current_page_count: int = 0) -> dict:
    file_name = _naming_image_file(
        current_sheet_count = current_sheet_count,
        current_page_count  = current_page_count, 
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


def _handle_single_page_answer_sheet_workflow(
        key: str, 
        frame: any, 
        answer_sheet_image_path: str, 
        answer_sheet_json_path: str,
        current_sheet_count: int, 
        total_number_of_pages_per_sheet: int,
        selected_assessment_uid: str, 
        essay_existence: bool,
        image_extension: str
    ) -> dict:
    """Handle single-page answer sheet workflow."""
    # Step 1: Check key input
    if key != '*':
        return {"status": "waiting"}
    
    # Step 2: Save in image file format
    image_details = _save_in_image_file(
        frame               = frame, 
        target_path         = answer_sheet_image_path, 
        current_sheet_count = current_sheet_count,
        image_extension     = image_extension
    )
    if image_details["status"] == "error":
        return image_details
    
    json_details = {"target_path": answer_sheet_json_path}
    return {
        "status"                            : "success",
        "answer_key_assessment_uid"         : selected_assessment_uid,
        "total_number_of_pages_per_sheet"   : total_number_of_pages_per_sheet,
        "json_details"                      : json_details,
        "image_details"                     : image_details,
        "is_final_score"                    : not essay_existence,
    }


def _handle_multi_page_answer_sheet_workflow(
        key: str, 
        frame: any,
        answer_sheet_image_path: str, 
        answer_sheet_json_path: str,
        current_count_sheets: int, 
        total_number_of_pages_per_sheet: int,
        selected_assessment_uid: str, 
        essay_existence: bool,
        current_count_page: int,
        collected_image_names: list,
        image_extension: str,
        tile_width: int
    ) -> dict:
    """Handle multi-page answer sheet workflow."""
    # Step 1: Check key input
    if key != '*':
        return {
            "status"    : "waiting",
            "next_page" : current_count_page,
        }
    
    # Step 2: Save individual page
    image_details = _save_in_image_file(
        frame               = frame, 
        target_path         = answer_sheet_image_path, 
        current_count_page  = current_count_page,
        image_extension     = image_extension
    )
    if image_details["status"] == "error":
        return image_details
    
    # Step 3: Collect the remaining pages
    collected_image_names.append(image_details["full_path"])

    # Step 4: Check if all pages are completed
    if current_count_page < total_number_of_pages_per_sheet:
        return {
            "status"    : "waiting",
            "next_page" : current_count_page + 1
        }
    
    # ========USE LCD DISPLAY==========
    print(f"Combining {total_number_of_pages_per_sheet} pages... please wait")
    time.sleep(3)
    # =================================
    
    # Step 5: All pages collected, combine them
    combined_image_result = image_combiner.combine_images_into_grid(collected_image_names, tile_width)
    if combined_image_result["status"] == "error":
        return combined_image_result
    
    
    image_details = _save_in_image_file(
        frame               = combined_image_result["frame"], 
        target_path         = answer_sheet_image_path,
        image_extension     = image_extension,
        is_combined_image   = True
    )
    if image_details["status"] == "error":
        return image_details
    
    json_details = {"target_path": answer_sheet_json_path}
    return {
        "status"                            : "success",
        "answer_key_assessment_uid"         : selected_assessment_uid,
        "total_number_of_pages_per_sheet"   : total_number_of_pages_per_sheet,
        "json_details"                      : json_details,
        "image_details"                     : image_details,
        "is_final_score"                    : not essay_existence,
        "next_page"                         : 1,  # Reset for next sheet
        "next_sheet"                        : current_count_sheets + 1
    }


def _ask_for_prerequisites(keypad_rows_and_cols: list, assessment_uid: str, pc_mode: bool) -> dict:
    """Ask user for number of sheets and pages per sheet, and check for essay questions."""

    # Step 1: Ask for number of sheets
    sheets_result = _ask_for_number_of_sheets(keypad_rows_and_cols, pc_mode)
    if sheets_result["status"] == "cancelled":
        return sheets_result

    # Step 2: Ask for number of pages per answer sheet
    pages_result = _ask_for_number_of_pages(keypad_rows_and_cols, pc_mode)
    if pages_result["status"] == "cancelled":
        return pages_result

    # Step 3: Check if assessment has essay questions
    essay_result = _check_essay_existence_in_db(assessment_uid)
    if essay_result["status"] == "error":
        return essay_result

    return {
        "status"                            : "success",
        "total_number_of_sheets"            : sheets_result["total_number_of_sheets"],
        "total_number_of_pages_per_sheet"   : pages_result["total_number_of_pages_per_sheet"],
        "essay_existence"                   : essay_result["essay_existence"]
    }


def run(
        keypad_rows_and_cols: list,
        camera_index: int,
        show_windows: bool,
        answer_sheet_paths: dict,
        selected_assessment_uid: str,
        pc_mode: bool,
        image_extension: str,
        tile_width: int
    ) -> dict:
    """
        Main function to capture and process answer sheets.
        
        Args:
            keypad_rows_and_cols: List containing [rows, cols] for keypad matrix
            camera_index: Index of camera device (0 for default)
            show_windows: Whether to display camera preview windows
            ...
        
        Returns:
            dict: {
                "status": "success" | "error" | "cancelled",
                "message": str (if error),
                ...
            }
    """
    answer_sheet_image_path = answer_sheet_paths["image_path"]
    answer_sheet_json_path  = answer_sheet_paths["json_path"]
    rows, cols              = keypad_rows_and_cols
    count_sheets            = 1
    count_page_per_sheet    = 1
    collected_image_names   = []
    result                  = {"status": "waiting"}

    # Step 1: Initialize camera
    camera_result = camera.initialize_camera(camera_index)
    if camera_result["status"] == "error":
        return camera_result
    capture = camera_result["capture"]
    
    # Step 2: Ask for prerequisites
    prerequisites = _ask_for_prerequisites(
        keypad_rows_and_cols    = keypad_rows_and_cols,
        assessment_uid          = selected_assessment_uid,
        pc_mode                 = pc_mode
    )
    if prerequisites["status"] == "cancelled":
        return prerequisites
    
    total_number_of_sheets          = prerequisites["total_number_of_sheets"]
    total_number_of_pages_per_sheet = prerequisites["total_number_of_pages_per_sheet"]
    essay_existence                 = prerequisites["essay_existence"]

    # Step 3: Scan answer sheets based on number of sheets and pages
    while count_sheets <= total_number_of_sheets:
        time.sleep(0.1)
        progress = f"[{count_sheets}/{total_number_of_sheets}]"
        
        if total_number_of_pages_per_sheet > 1:
            # ========USE LCD DISPLAY==========
            print(f"\n{progress} Sheet {count_sheets} - Page {count_page_per_sheet}/{total_number_of_pages_per_sheet}")
            # =================================
        else:
            # ========USE LCD DISPLAY==========
            print(f"\n{progress} Sheet {count_sheets}")
            # =================================
        
        # ========USE LCD DISPLAY==========
        print(f"{progress} Press [*] to CAPTURE or [#] to EXIT")
        # =================================

        ret, frame = capture.read()
        if not ret:
            result = {
                "status"    : "error",
                "message"   : f"Failed to capture frame. Source: {__name__}."
            }
            break
        
        if show_windows:
            cv2.imshow("Answer Sheet Scanner", frame)
            cv2.waitKey(1)

        key = hardware.read_keypad(rows, cols, pc_mode)

        if key is None or key not in ['*', '#']:
            continue

        if key == '#':
            result = {"status": "cancelled"}
            break

        # Handle single-page answer sheets
        if total_number_of_pages_per_sheet == 1:
            result = _handle_single_page_answer_sheet_workflow(
                key                             = key,
                frame                           = frame,
                answer_sheet_image_path         = answer_sheet_image_path,
                answer_sheet_json_path          = answer_sheet_json_path, 
                current_sheet_count             = count_sheets,
                total_number_of_pages_per_sheet = total_number_of_pages_per_sheet,
                selected_assessment_uid         = selected_assessment_uid,
                essay_existence                 = essay_existence,
                image_extension                 = image_extension
            )
            if result["status"] == "waiting":
                continue
            
            elif result["status"] == "success":
                create_result = answer_sheet_model.create_answer_sheet(
                    answer_key_assessment_uid       = result["answer_key_assessment_uid"],
                    total_number_of_pages_per_sheet = result["total_number_of_pages_per_sheet"],
                    json_target_path                = result["json_details"]["target_path"],
                    img_file_name                   = result["image_details"]["file_name"],
                    img_full_path                   = result["image_details"]["full_path"],
                    is_final_score                  = result["is_final_score"]
                )
                if create_result["status"] == "error":
                    result = create_result
                    break
                # ========USE LCD DISPLAY==========
                print(f"✅ Sheet {count_sheets}/{total_number_of_sheets} saved")
                time.sleep(3)
                # =================================
                count_sheets += 1

            elif result["status"] == "error":
                break

        # Handle multi-page answer sheets
        else:
            result = _handle_multi_page_answer_sheet_workflow(
                key                             = key,
                frame                           = frame,
                answer_sheet_image_path         = answer_sheet_image_path,
                answer_sheet_json_path          = answer_sheet_json_path,
                current_count_sheets            = count_sheets,
                total_number_of_pages_per_sheet = total_number_of_pages_per_sheet,
                selected_assessment_uid         = selected_assessment_uid,
                essay_existence                 = essay_existence,
                current_count_page              = count_page_per_sheet,
                collected_image_names           = collected_image_names,
                image_extension                 = image_extension,
                tile_width                      = tile_width
            )
            
            if result["status"] == "waiting":
                count_page_per_sheet = result["next_page"]
                continue
            
            elif result["status"] == "success":
                create_result = answer_sheet_model.create_answer_sheet(
                    answer_key_assessment_uid       = result["answer_key_assessment_uid"],
                    total_number_of_pages_per_sheet = result["total_number_of_pages_per_sheet"],
                    json_target_path                = result["json_details"]["target_path"],
                    img_file_name                   = result["image_details"]["file_name"],
                    img_full_path                   = result["image_details"]["full_path"],
                    is_final_score                  = result["is_final_score"]
                )
                if create_result["status"] == "error":
                    result = create_result
                    break
                
                # ========USE LCD DISPLAY==========
                print(f"✅ Sheet {count_sheets}/{total_number_of_sheets} completed and saved")
                time.sleep(3)
                # =================================
                count_sheets            = result["next_sheet"]
                count_page_per_sheet    = result["next_page"]
                collected_image_names.clear()
            
            elif result["status"] == "error":
                break

    camera.cleanup(capture, show_windows)    
    return result