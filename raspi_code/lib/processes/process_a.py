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
    

def check_point(*paths) -> None:
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
    answer_key_image_path     = process_A_args["answer_key_image_path"]
    answer_sheets_image_path  = process_A_args["answer_sheets_image_path"]
    answer_key_txt_path     = process_A_args["answer_key_txt_path"]
    answer_sheets_txt_path  = process_A_args["answer_sheets_txt_path"]

    print(f"{task_name} is now Running ✅")
    check_point(answer_key_image_path, answer_sheets_image_path, answer_key_txt_path, answer_sheets_txt_path)
    current_stage, current_display_options = display.initialize_display()
    rows, cols = hardware.setup_keypad_pins(
                    pc_mode, 
                    ROW_PINS = keypad_pins["ROWS"], 
                    COL_PINS = keypad_pins["COLS"]
                )
    
    # ========= TEST KEYS =========
    pc_key = '1' # REMOVE LATER
    # =============================
    
    while True:
        time.sleep(1.5)

        print(f"{current_display_options[0]}{current_display_options[1]}")
        print("[*]UP or [#]DOWN")
        
        if pc_mode:
            if pc_key != None and pc_key in ['*', '#', '1', '2', '3', '4']:
                if pc_key in ['*', '#']:
                    current_stage, current_display_options = display.handle_display(key=pc_key, current_stage=current_stage)
                else:
                    if pc_key == '1':
                        scan_answer_key.run(
                            task_name               = task_name,
                            keypad_rows_and_cols    = [rows, cols], 
                            camera_index            = camera_index, 
                            save_logs               = save_logs, 
                            show_windows            = show_windows, 
                            answer_key_path         = answer_key_image_path, 
                            pc_mode                 = pc_mode
                        )
                    elif pc_key == '2':
                        scan_answer_sheet.run()
                    elif pc_key == '3':
                        settings.run()
                    elif pc_key == '4':
                        shutdown.run()
                continue

        key = hardware.read_keypad(rows = rows, cols = cols)
        if key != None and key in ['*', '#', '1', '2', '3', '4']:
            if key in ['*', '#']:
                current_stage, current_display_options = display.handle_display(key=key, current_stage=current_stage, module_name="process_a")
            else:
                if pc_key == '1':
                    scan_answer_key.run([rows, cols], camera_index, save_logs, show_windows, answer_key_image_path, test_mode)
                elif pc_key == '2':
                    scan_answer_sheet.run()
                elif pc_key == '3':
                    settings.run()
                elif pc_key == '4':
                    shutdown.run()
            