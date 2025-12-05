from multiprocessing import Queue
import time

# Process C will handle:
    # - checking if there is a gemini_done = False
    # - Then if the step 1 is true, overwrite the the student answer sheet with the real answer
    # - Then upload to the Google Drive
    # - Repeat the process

def process_c(**kwargs):
    process_C_args  = kwargs.get("process_C_args", {})
    task_name   = process_C_args["task_name"]
    pc_mode     = process_C_args["pc_mode"]
    save_logs   = process_C_args["save_logs"]
    exit()
    
    print(f"{task_name} is now Running ✅")
    while True:
        print(f"{task_name} 💜")
        time.sleep(3)