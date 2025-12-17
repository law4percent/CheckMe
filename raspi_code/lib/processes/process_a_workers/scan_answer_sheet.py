# lib/processes/process_a_workers/scan_answer_sheet.py
import cv2
import time
from lib.hardware import camera_contoller as camera
from datetime import datetime
import os
from lib.services import utils, image_combiner
from lib.model import answer_key_model, answer_sheet_model


def _ask_for_number_of_sheets(scan_key, limit: int = 50) -> dict:
    """Ask user for number of answer sheets with multi-digit input support."""
    collected_input = ''
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print("How many answer sheets? [*] Done or [#] Cancel")
        print(f"Current input: {collected_input}")
        # =================================
        key = scan_key()
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


def _ask_for_number_of_pages(scan_key) -> dict:
    """Ask user for number of pages per answer sheet (1-9)."""
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print("How many pages per answer sheet? [1-9] or [#] Cancel")
        # =================================
        key = scan_key()
        if key is None or key not in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            continue

        if key == '#':
            return {"status": "cancelled"}

        total_number_of_pages_per_sheet = int(key)
        return {
                "status"                            : "success",
                "total_number_of_pages_per_sheet"   : total_number_of_pages_per_sheet
            }


def _check_essay_existence_in_db(assessment_uid: str) -> dict:
    """Check if assessment has essay questions."""
    try:
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
        return f"combined_img_DT_{now}.{file_extension}"
    
    if current_sheet_count > 0:
        return f"img_sheet{current_sheet_count}_DT_{now}.{file_extension}"
    
    return f"img{current_page_count}_DT_{now}.{file_extension}"


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
    full_path = save_image["full_path"]
    
    image_file_validation_result =  utils.file_existence_checkpoint(full_path, __name__)
    if image_file_validation_result["status"] == "error":
        return image_file_validation_result

    return {
        "status"   : "success",
        "file_name": file_name,
        "full_path": full_path
    }


def _handle_single_page_answer_sheet_workflow(
        KEY: str, 
        FRAME: any, 
        IMAGE_PATH: str, 
        JSON_PATH: str,
        CURRENT_SHEET_COUNT: int, 
        TOTAL_NUMBER_OF_PAGES_PER_SHEET: int,
        SELECTED_ASSESSMENT_UID: str, 
        ESSAY_EXISTENCE: bool,
        IMAGE_EXTENSION: str
    ) -> dict:
    """Handle single-page answer sheet workflow."""
    # Step 1: Check key input
    if KEY != '*':
        return {"status": "waiting"}
    
    # Step 2: Save in image file format
    image_details = _save_in_image_file(
        frame               = FRAME, 
        target_path         = IMAGE_PATH, 
        current_sheet_count = CURRENT_SHEET_COUNT,
        image_extension     = IMAGE_EXTENSION
    )
    if image_details["status"] == "error":
        return image_details
    
    json_details = {"target_path": JSON_PATH}
    return {
        "status"                            : "success",
        "answer_key_assessment_uid"         : SELECTED_ASSESSMENT_UID,
        "total_number_of_pages_per_sheet"   : TOTAL_NUMBER_OF_PAGES_PER_SHEET,
        "json_details"                      : json_details,
        "image_details"                     : image_details,
        "is_final_score"                    : not ESSAY_EXISTENCE,
    }


def _handle_multi_page_answer_sheet_workflow(
        KEY: str, 
        FRAME: any,
        IMAGE_PATH: str, 
        JSON_PATH: str,
        CURRENT_COUNT_SHEETS: int, 
        TOTAL_NUMBER_OF_PAGES_PER_SHEET: int,
        SELECTED_ASSESSMENT_UID: str, 
        ESSAY_EXISTENCE: bool,
        CURRENT_COUNT_PAGE: int,
        COLLECTED_IMAGES: list,
        IMAGE_EXTENSION: str,
        TILE_WIDTH: int
    ) -> dict:
    """Handle multi-page answer sheet workflow."""
    # Step 1: Check key input
    if KEY != '*':
        return {
            "status"    : "waiting",
            "next_page" : CURRENT_COUNT_PAGE,
        }
    
    # Step 2: Save individual page
    image_details = _save_in_image_file(
        frame               = FRAME, 
        target_path         = IMAGE_PATH, 
        current_count_page  = CURRENT_COUNT_PAGE,
        image_extension     = IMAGE_EXTENSION
    )
    if image_details["status"] == "error":
        utils.cleanup_temporary_images(COLLECTED_IMAGES)
        return image_details
    
    # Step 3: Collect the remaining pages
    COLLECTED_IMAGES.append(image_details["full_path"])

    # Step 4: Check if all pages are completed
    if CURRENT_COUNT_PAGE < TOTAL_NUMBER_OF_PAGES_PER_SHEET:
        return {
            "status"    : "waiting",
            "next_page" : CURRENT_COUNT_PAGE + 1
        }
    
    # ========USE LCD DISPLAY==========
    print(f"Combining {TOTAL_NUMBER_OF_PAGES_PER_SHEET} pages... please wait")
    time.sleep(3)
    # =================================
    
    # Step 5: All pages collected, combine them
    combined_image_result = image_combiner.combine_images_into_grid(COLLECTED_IMAGES, TILE_WIDTH)
    if combined_image_result["status"] == "error":
        utils.cleanup_temporary_images(COLLECTED_IMAGES)
        return combined_image_result
    
    image_details = _save_in_image_file(
        frame               = combined_image_result["frame"], 
        target_path         = IMAGE_PATH,
        image_extension     = IMAGE_EXTENSION,
        is_combined_image   = True
    )
    if image_details["status"] == "error":
        utils.cleanup_temporary_images(COLLECTED_IMAGES)
        return image_details
    
    json_details = {"target_path": JSON_PATH}
    utils.cleanup_temporary_images(COLLECTED_IMAGES)
    return {
        "status"                            : "success",
        "answer_key_assessment_uid"         : SELECTED_ASSESSMENT_UID,
        "total_number_of_pages_per_sheet"   : TOTAL_NUMBER_OF_PAGES_PER_SHEET,
        "json_details"                      : json_details,
        "image_details"                     : image_details,
        "is_final_score"                    : not ESSAY_EXISTENCE,
        "next_page"                         : 1,  # Reset for next sheet
        "next_sheet"                        : CURRENT_COUNT_SHEETS + 1
    }


def _ask_for_prerequisites(scan_key, ASSESSMENT_UID: str) -> dict:
    """Ask user for number of sheets and pages per sheet, and check for essay questions."""

    # Step 1: Ask for number of sheets
    sheets_result = _ask_for_number_of_sheets(scan_key)
    if sheets_result["status"] == "cancelled":
        return sheets_result

    # Step 2: Ask for number of pages per answer sheet
    pages_result = _ask_for_number_of_pages(scan_key)
    if pages_result["status"] == "cancelled":
        return pages_result

    # Step 3: Check if assessment has essay questions
    essay_result = _check_essay_existence_in_db(ASSESSMENT_UID)
    if essay_result["status"] == "error":
        return essay_result

    return {
        "status"                            : "success",
        "total_number_of_sheets"            : sheets_result["total_number_of_sheets"],
        "total_number_of_pages_per_sheet"   : pages_result["total_number_of_pages_per_sheet"],
        "essay_existence"                   : essay_result["essay_existence"]
    }


def run(
        scan_key,
        SHOW_WINDOWS: bool,
        PATHS: dict,
        SELECTED_ASSESSMENT_UID: str,
        PRODUCTION_MODE: bool,
        IMAGE_EXTENSION: str,
        TILE_WIDTH: int,
        FRAME_DIMENSIONS: dict
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
    IMAGE_PATH          = PATHS["image_path"]
    JSON_PATH           = PATHS["json_path"]
    count_sheets        = 1
    count_page_per_sheet= 1
    collected_images    = []
    result              = {"status": "waiting"}

    # Step 1: Initialize Camera & start camera
    config_result = camera.config_camera(FRAME_DIMENSIONS)
    if config_result["status"] == "error":
        return config_result
    capture = config_result["capture"]
    capture.start()
    
    # Step 2: Ask for prerequisites
    prerequisites = _ask_for_prerequisites(
        keypad_rows_and_cols    = scan_key,
        ASSESSMENT_UID          = SELECTED_ASSESSMENT_UID
    )
    if prerequisites["status"] == "cancelled":
        camera.cleanup_camera(capture)
        return prerequisites
    
    TOTAL_NUMBER_OF_SHEETS          = prerequisites["total_number_of_sheets"]
    TOTAL_NUMBER_OF_PAGES_PER_SHEET = prerequisites["total_number_of_pages_per_sheet"]
    ESSAY_EXISTENCE                 = prerequisites["essay_existence"]

    try:
        # Step 3: Scan answer sheets based on number of sheets and pages
        while count_sheets <= TOTAL_NUMBER_OF_SHEETS:
            time.sleep(0.1)
            progress = f"[{count_sheets}/{TOTAL_NUMBER_OF_SHEETS}]"
            
            if TOTAL_NUMBER_OF_PAGES_PER_SHEET > 1:
                # ========USE LCD DISPLAY==========
                print(f"\n{progress} Sheet {count_sheets} - Page {count_page_per_sheet}/{TOTAL_NUMBER_OF_PAGES_PER_SHEET}")
                # =================================
            else:
                # ========USE LCD DISPLAY==========
                print(f"\n{progress} Sheet {count_sheets}")
                # =================================
            
            # ========USE LCD DISPLAY==========
            print(f"{progress} Press [*] to CAPTURE or [#] to EXIT")
            # =================================

            frame = capture.capture_array()
            frame = cv2.resize(frame, (FRAME_DIMENSIONS["width"], FRAME_DIMENSIONS["height"]))
            
            if SHOW_WINDOWS:
                cv2.imshow("Answer Sheet Scanner", frame)
                cv2.waitKey(1)

            key = scan_key()

            if key is None or key not in ['*', '#']:
                continue

            if key == '#':
                result = {"status": "cancelled"}
                if len(collected_images) > 0:
                    utils.cleanup_temporary_images(collected_images)
                break

            # Handle single-page answer sheets
            if TOTAL_NUMBER_OF_PAGES_PER_SHEET == 1:
                result = _handle_single_page_answer_sheet_workflow(
                    KEY                             = key,
                    FRAME                           = frame,
                    IMAGE_PATH                      = IMAGE_PATH,
                    JSON_PATH                       = JSON_PATH, 
                    CURRENT_SHEET_COUNT             = count_sheets,
                    TOTAL_NUMBER_OF_PAGES_PER_SHEET = TOTAL_NUMBER_OF_PAGES_PER_SHEET,
                    SELECTED_ASSESSMENT_UID         = SELECTED_ASSESSMENT_UID,
                    ESSAY_EXISTENCE                 = ESSAY_EXISTENCE,
                    IMAGE_EXTENSION                 = IMAGE_EXTENSION
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
                    print(f"✅ Sheet {count_sheets}/{TOTAL_NUMBER_OF_SHEETS} saved")
                    time.sleep(3)
                    # =================================
                    count_sheets += 1

                elif result["status"] == "error":
                    break

            # Handle multi-page answer sheets
            else:
                result = _handle_multi_page_answer_sheet_workflow(
                    KEY                             = key,
                    FRAME                           = frame,
                    IMAGE_PATH                      = IMAGE_PATH,
                    JSON_PATH                       = JSON_PATH,
                    CURRENT_COUNT_SHEETS            = count_sheets,
                    TOTAL_NUMBER_OF_PAGES_PER_SHEET = TOTAL_NUMBER_OF_PAGES_PER_SHEET,
                    SELECTED_ASSESSMENT_UID         = SELECTED_ASSESSMENT_UID,
                    ESSAY_EXISTENCE                 = ESSAY_EXISTENCE,
                    CURRENT_COUNT_PAGE              = count_page_per_sheet,
                    COLLECTED_IMAGES                = collected_images,
                    IMAGE_EXTENSION                 = IMAGE_EXTENSION,
                    TILE_WIDTH                      = TILE_WIDTH
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
                    print(f"✅ Sheet {count_sheets}/{TOTAL_NUMBER_OF_SHEETS} completed and saved")
                    time.sleep(3)
                    # =================================
                    count_sheets            = result["next_sheet"]
                    count_page_per_sheet    = result["next_page"]
                    collected_images.clear()
                
                elif result["status"] == "error":
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