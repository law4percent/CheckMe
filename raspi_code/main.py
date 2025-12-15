from lib.processes import process_a, process_b, process_c
from multiprocessing import Process, Event
from lib.model import models

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
    PRODUCTION_MODE     = True
    SAVE_LOGS           = True
    ANSWER_KEY_PATH     = {"json_path": "answer_keys/json", "image_path": "answer_keys/images"}
    ANSWER_SHEET_PATH   = {"json_path": "answer_sheets/json", "image_path": "answer_sheets/images"}
    status_checker      = Event()
    TEST_TEACHER_UID    = "gbRaC4u7MSRWWRi9LerDQyjVzg22"
    status_checker.set()

    main(
        process_A_args = {
            "TASK_NAME"         : "Process A",
            "IMAGE_EXTENSION"   : "jpg",                        # This is experimental
            "TILE_WIDTH"        : 600,                          # This is experimental for gridding image
            "PRODUCTION_MODE"   : PRODUCTION_MODE,
            "SAVE_LOGS"         : SAVE_LOGS,
            "SHOW_WINDOWS"      : True,
            "PATHS"             : {"answer_key_path": ANSWER_KEY_PATH, "answer_sheet_path": ANSWER_SHEET_PATH},
            "status_checker"    : status_checker,
            "FRAME_DIMENSIONS"  : {"width": 1920, "heght": 1080} # This is experimental
        },
        process_B_args = {
            "TASK_NAME"         : "Process B",
            "BATCH_SIZE"        : 5,
            "TEACHER_UID"       : TEST_TEACHER_UID, # This is for testing but later will get properly via letting the user login here in the system. I will add authentication feature here in the system. And once the user successfully login the system will get the teach_uid with their username credential.
            "status_checker"    : status_checker,
            "PRODUCTION_MODE"   : PRODUCTION_MODE,
            "SAVE_LOGS"         : SAVE_LOGS,
        },
        process_C_args = {
            "task_name"         : "Process C",
            "PRODUCTION_MODE"   : PRODUCTION_MODE,
            "save_logs"         : SAVE_LOGS,
            "status_checker"    : status_checker
        }
    )