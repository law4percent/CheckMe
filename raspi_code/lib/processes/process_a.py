from multiprocessing import Queue
import time
from .process_a_workers import scan_answer_key, scan_answer_sheet, settings, shutdown, hardware, display
from enum import Enum
import os
from lib.services import answer_key_model, answer_sheet_model

class Options(Enum):
    SCAN_ANSWER_KEY     = '1'
    SCAN_ANSWER_SHEET   = '2'
    SETTINGS            = '3'
    SHUTDOWN            = '4'
    

def _choose_answer_key_from_db(cols: str, rows: str, pc_mode: bool) -> str:
    """
        Let the user choose an answer key from the database using the keypad.
        Only shows assessment_uid for selection.
        Returns the selected assessment_uid.
    """
    # Fetch only assessment_uid
    keys = answer_key_model.get_all_answer_keys()

    if not keys:
        print("No answer keys found in the database.")
        return None

    index = 0  # start at first key

    while True:
        time.sleep(0.1)

        # Display only assessment_uid
        current_uid = keys[index]
        print(f"\nSelected Assessment UID: {current_uid}")
        print("[*]UP or [#]DOWN | Press 1 to select")

        # Read keypad input
        key = hardware.read_keypad(rows=rows, cols=cols, pc_mode=pc_mode)
        if key is None:
            continue

        if key == '*':  # UP
            index = (index - 1) % len(keys)
        elif key == '#':  # DOWN
            index = (index + 1) % len(keys)
        elif key == 1:
            # Any other key selects the current assessment_uid
            print(f"Selected assessment_uid: {current_uid}")
            return current_uid


def _check_point(*paths) -> None:
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Folder '{path}' created.")


def process_a(process_A_args: str, queue_frame: Queue):

    task_name       = process_A_args["task_name"]
    pc_mode         = process_A_args["pc_mode"]
    save_logs       = process_A_args["save_logs"]
    camera_index    = process_A_args["camera_index"]
    show_windows    = process_A_args["show_windows"]
    keypad_pins     = process_A_args["keypad_pins"]
    answer_key_image_path       = process_A_args["answer_key_image_path"]
    answer_key_json_path        = process_A_args["answer_key_json_path"]
    answer_sheet_images_path    = process_A_args["answer_sheet_images_path"]
    answer_sheet_jsons_path     = process_A_args["answer_sheet_jsons_path"]

    print(f"{task_name} is now Running ✅")
    _check_point(answer_key_image_path, answer_sheet_images_path, answer_key_json_path, answer_sheet_jsons_path)
    current_stage, current_display_options = display.initialize_display()
    rows, cols = hardware.setup_keypad_pins(
                    pc_mode, 
                    ROW_PINS = keypad_pins["ROWS"], 
                    COL_PINS = keypad_pins["COLS"]
                )
    
    while True:
        time.sleep(0.1)

        print(f"{current_display_options[0]}{current_display_options[1]}")
        print("[*]UP or [#]DOWN")
        
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
                answer_key_image_path   = answer_key_image_path, 
                answer_key_json_path    = answer_key_json_path,
                pc_mode                 = pc_mode
            )

            # Step 2: Save results to database
            if answer_key_data["status"] == "success":
                answer_key_model.create_answer_key(
                    assessment_uid  = answer_sheets_data["assessment_uid"],
                    number_of_pages = answer_sheets_data["number_of_pages"],
                    json_path       = answer_sheets_data["json_path"],
                    img_path        = answer_sheets_data["img_path"],
                    has_essay       = answer_sheets_data["has_essay"]
                )
            
            elif answer_key_data["status"] == "error":
                if save_logs:
                    pass
                print(f"{task_name} - Error: {answer_key_data["message"]}")

            elif answer_key_data["status"] == "cancelled": 
                if save_logs:
                    pass
                print(f"{task_name} - {answer_key_data["status"]}")
        
        
        elif key == '2':
            # Step 1: Choose answer key from database via assessment_uid
            target_assessment_uid = _choose_answer_key_from_db(cols, rows, pc_mode)

            # Step 2: Scan answer sheets
            answer_sheets_data = scan_answer_sheet.run(
                keypad_rows_and_cols        = [rows, cols], 
                camera_index                = camera_index, 
                save_logs                   = save_logs, 
                show_windows                = show_windows, 
                answer_sheet_images_path    = answer_sheet_images_path, 
                answer_sheet_json_path      = answer_sheet_jsons_path,
                assessment_uid              = target_assessment_uid,  # to be replaced with real assessment_uid
                pc_mode                     = pc_mode
            )

            # Step 3: Save results to database
            if answer_sheets_data["status"] == "success":
                pass

            elif answer_sheets_data["status"] == "error":
                print(f"{task_name} - Error: {answer_sheets_data["error"]}")

            elif answer_sheets_data["status"] == "cancelled": 
                print(f"{task_name} - {answer_sheets_data["status"]}")


        elif key == '3':
            settings.run()
            

        elif key == '4':
            shutdown.run()
            