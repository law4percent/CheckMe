# lib/processes/process_a.py
from multiprocessing import Queue
import time
from .process_a_workers import scan_answer_key, scan_answer_sheet, settings, shutdown, hardware, display
from enum import Enum
import os
from lib.services import answer_key_model
from lib import logger_config
import logging

logger = logger_config.setup_logger(name=__name__, level=logging.DEBUG)

class Options(Enum):
    SCAN_ANSWER_KEY     = '1'
    SCAN_ANSWER_SHEET   = '2'
    SETTINGS            = '3'
    SHUTDOWN            = '4'
    

def _choose_answer_key_from_db(rows: str, cols: str, pc_mode: bool) -> dict:
    """
        Let the user choose an answer key from the database using the keypad.
        Only shows assessment_uid for selection.
        Returns the selected assessment_uid.
    """
    # Fetch only assessment_uid
    list_result = answer_key_model.get_all_answer_keys()
    if list_result["status"] == "error":
        return list_result
    assessment_uids_list = list_result["all_answer_keys"]

    list_length = len(assessment_uids_list)
    if not assessment_uids_list:
        return {
            "status"    : "error",
            "message"   : "No answer keys found in the database."
        }

    index = 0  # start at first key

    while True:
        time.sleep(0.1)
        current_uid = assessment_uids_list[index]
        # Display only assessment_uid
        # ========USE LCD DISPLAY==========
        print(f"\nSelected Assessment UID: {current_uid}")
        print("[*]UP or [#]DOWN | Press 1 to select or 0 to cancel")
        # =================================

        # Read keypad input
        key = hardware.read_keypad(rows=rows, cols=cols, pc_mode=pc_mode)
        if key == '0':
            return {"status": "cancelled"}
        
        if key is None or key not in ['*', '#', '1']:
            continue

        if key == '*':  # UP
            if index > 0:
                index -= 1
        elif key == '#':  # DOWN
            if index < list_length - 1:
                index += 1
        elif key == '1':
            return {
                "status"                    : "success",
                "selected_assessment_uid"   : current_uid
            }


def _check_point(*paths) -> None:
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)


def process_a(**kwargs):
    """
        Main Process A function - Background OCR processing.
        
        Will responsible in getting the answer sheets and answer keys.
        
        Args:
            **kwargs: Must contain 'process_A_args' dict
    """
    process_A_args  = kwargs["process_A_args"]
    task_name       = process_A_args["task_name"]
    image_extension = process_A_args["image_extension"]
    status_checker  = process_A_args["status_checker"]
    pc_mode         = process_A_args["pc_mode"]
    save_logs       = process_A_args["save_logs"]
    camera_index    = process_A_args["camera_index"]
    show_windows    = process_A_args["show_windows"]
    keypad_pins     = process_A_args["keypad_pins"]
    paths           = process_A_args["paths"]
    tile_width      = process_A_args["tile_width"]

    if save_logs:
        logger.info(f"{task_name} is now Running ✅")
    
    _check_point(
        paths["answer_key_path"]["image_path"], 
        paths["answer_sheet_path"]["image_path"], 
        paths["answer_key_path"]["json_path"], 
        paths["answer_sheet_path"]["json_path"]
    )
    current_stage, current_display_options = display.initialize_display()
    rows, cols = hardware.setup_keypad_pins(
        pc_mode, 
        ROW_PINS = keypad_pins["ROWS"], 
        COL_PINS = keypad_pins["COLS"]
    )
    
    while True:
        time.sleep(0.1)
        # ========USE LCD DISPLAY==========
        print(f"{current_display_options[0]}{current_display_options[1]}")
        print("[*]UP or [#]DOWN")
        # =================================
        
        if not status_checker.is_set():
            if save_logs:
                logger.warning(f"{task_name} - Status checker indicates error in another process")
                logger.info(f"{task_name} has stopped")
            exit()
        
        key = hardware.read_keypad(rows, cols, pc_mode)
        if key == None:
            continue

        if key in ['*', '#']:
            current_stage, current_display_options = display.handle_display(key=key, current_stage=current_stage, module_name="process_a")
            continue
        
        if key == '1':
            # Step 1: Scan answer key
            answer_key_data = scan_answer_key.run(
                keypad_rows_and_cols    = [rows, cols], 
                camera_index            = camera_index,
                show_windows            = show_windows, 
                answer_key_paths        = paths["answer_key_path"],
                pc_mode                 = pc_mode,
                image_extension         = image_extension,
                tile_width              = tile_width
            )

            # Step 2: Save results to database
            if answer_key_data["status"] == "success":
                create_result = answer_key_model.create_answer_key(
                    assessment_uid          = answer_key_data["assessment_uid"],
                    total_number_of_pages   = answer_key_data["total_number_of_pages "],
                    json_file_name          = answer_key_data["json_details"]["file_name"],
                    json_full_path          = answer_key_data["json_details"]["full_path"],
                    img_file_name           = answer_key_data["image_details"]["file_name"],
                    img_full_path           = answer_key_data["image_details"]["full_path"],
                    essay_existence         = answer_key_data["essay_existence"]
                )
                if create_result["status"] == "error":
                    if save_logs:
                        logger.error(f"{task_name} - {create_result["message"]}")
            
            # Step 2: Else just display
            elif answer_key_data["status"] == "error":
                if save_logs:
                    logger.error(f"{task_name} - {answer_key_data["message"]}")
                    
            elif answer_key_data["status"] == "cancelled": 
                # ========USE LCD DISPLAY==========
                print(f"{task_name} - {answer_key_data["status"]}")
                time.sleep(3)
                # =================================
        
        
        elif key == '2':
            # Step 1: Choose answer key from database via assessment_uid
            selection_result = _choose_answer_key_from_db(rows, cols, pc_mode)
            if selection_result["status"] == "error":
                continue 
            selected_assessment_uid = selection_result["selected_assessment_uid"]
            
            # Step 2: Scan answer sheets and save to DB
            answer_sheets_data = scan_answer_sheet.run(
                keypad_rows_and_cols    = [rows, cols], 
                camera_index            = camera_index,
                show_windows            = show_windows, 
                answer_sheet_paths      = paths["answer_sheet_path"],
                selected_assessment_uid = selected_assessment_uid,
                pc_mode                 = pc_mode,
                image_extension         = image_extension,
                tile_width              = tile_width
            )

            # Step 3: Just display
            if answer_sheets_data["status"] == "error":
                if save_logs:
                    logger.error(f"{task_name} - {answer_sheets_data["message"]}")


        elif key == '3':
            continue
            # Not yet implement
            settings.run()
            

        elif key == '4':
            continue
            # Not yet implement
            shutdown.run()
            