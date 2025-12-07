from lib.processes import process_a, process_b, process_c
from multiprocessing import Process, Event
from lib.services import models

def main(**kargs):
    models.create_table()
    task_a = Process(
        target  = process_a.process_a,
        kwargs  = {"process_A_args": kargs["process_A_args"]}
    )
    task_b = Process(
        target  = process_b.process_b, 
        kwargs  = {"process_B_args": kargs["process_B_args"]}
    )
    task_c = Process(
        target  = process_c.process_c, 
        kwargs  = {"process_C_args": kargs["process_C_args"]}
    )
    
    task_a.start()
    task_b.start()
    task_c.start()
    
    task_a.join()
    task_b.join()
    task_c.join()
    

if __name__ == "__main__":
    PC_MODE             = True
    SAVE_LOGS           = True
    ANSWER_KEY_PATH     = {"json_path": "answer_keys/json", "image_path": "answer_keys/images"}
    ANSWER_SHEET_PATH   = {"json_path": "answer_sheets/json", "image_path": "answer_sheets/images"}
    status_checker  = Event()
    status_checker.set()
    main(
        process_A_args = {
            "task_name"         : "Process A",
            "image_extension"   : "jpg",    # This is experimental
            "tile_width"        : 600,      # This is experimental for gridding image
            "pc_mode"           : PC_MODE,
            "save_logs"         : SAVE_LOGS,
            "camera_index"      : 0,
            "show_windows"      : True,
            "keypad_pins"       : {"ROWS": [5, 6, 13, 19], "COLS": [12, 16, 20]},
            "paths"             : {"answer_key_path": ANSWER_KEY_PATH, "answer_sheet_path": ANSWER_SHEET_PATH},
            "status_checker"    : status_checker,
        },
        process_B_args = {
            "task_name"         : "Process B",
            "pc_mode"           : PC_MODE,
            "save_logs"         : SAVE_LOGS,
            "poll_interval"     : 5,
            "paths"             : {"answer_key_path": ANSWER_KEY_PATH, "answer_sheet_path": ANSWER_SHEET_PATH},
            "status_checker"    : status_checker,
            "teacher_uid"       : "gbRaC4u7MSRWWRi9LerDQyjVzg22",
            "firebase_enabled"  : True
        },
        process_C_args = {
            "task_name"         : "Process C",
            "pc_mode"           : PC_MODE,
            "save_logs"         : SAVE_LOGS,
            "status_checker"    : status_checker
        }
    )