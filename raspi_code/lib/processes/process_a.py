from multiprocessing import Queue
import time
from .process_a_workers import scan_answer_key, scan_answer_sheet, settings, shutdown, hardware, display
from enum import Enum
import os

class Options(Enum):
    SCAN_ANSWER_KEY     = '1'
    SCAN_ANSWER_SHEET   = '2'
    SETTINGS            = '3'
    SHUTDOWN            = '4'
    

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
    answer_sheets_image_path    = process_A_args["answer_sheets_image_path"]
    answer_key_json_path        = process_A_args["answer_key_json_path"]
    answer_sheets_json_path     = process_A_args["answer_sheets_json_path"]

    print(f"{task_name} is now Running ✅")
    _check_point(answer_key_image_path, answer_sheets_image_path, answer_key_json_path, answer_sheets_json_path)
    current_stage, current_display_options = display.initialize_display()
    rows, cols = hardware.setup_keypad_pins(
                    pc_mode, 
                    ROW_PINS = keypad_pins["ROWS"], 
                    COL_PINS = keypad_pins["COLS"]
                )
    
    while True:
        time.sleep(1.5)

        print(f"{current_display_options[0]}{current_display_options[1]}")
        print("[*]UP or [#]DOWN")
        
        key = hardware.read_keypad(rows = rows, cols = cols)
        if key == None:
            continue

        if key in ['*', '#']:
            current_stage, current_display_options = display.handle_display(key=key, current_stage=current_stage, module_name="process_a")
            continue
        
        if key == '1':
            answer_key_data = scan_answer_key.run(
                task_name               = task_name,
                keypad_rows_and_cols    = [rows, cols], 
                camera_index            = camera_index, 
                save_logs               = save_logs, 
                show_windows            = show_windows, 
                answer_key_path         = answer_key_image_path, 
                answer_key_json_path    = answer_key_json_path,
                pc_mode                 = pc_mode
            )

            if answer_key_data["status"] == "success":
                # save the json path and answer key UID into SQLite
                # answer_key_data {
                #             "status"            : "success",
                #             "assessment_uid"    : assessment_uid,
                #             "pages"             : number_of_sheets,
                #             "answer_key"        : answer_key,
                #             "saved_path"        : json_path
                #         }
                pass
            
            elif answer_key_data["status"] == "error":
                print(f"{task_name} - Error: {answer_key_data["error"]}")

            elif answer_key_data["status"] == "cancelled": 
                print(f"{task_name} - {answer_key_data["status"]}")
        
        
        elif key == '2':
            answer_sheets_data = scan_answer_sheet.run(
                task_name               = task_name,
                keypad_rows_and_cols    = [rows, cols], 
                camera_index            = camera_index, 
                save_logs               = save_logs, 
                show_windows            = show_windows, 
                answer_key_path         = answer_key_image_path, 
                answer_key_json_path    = answer_key_json_path,
                pc_mode                 = pc_mode
            )

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
            