from multiprocessing import Queue
import time

# Process B will handle:
    # - send images into the Gemini,
    # - wait for the Gemini response
    # - update the SQLite to mark gemini_done as True for the specific image 
    # - update the RTDB Firebase to mark gemini_done as True for the specific image 

def process_b(process_B_args: str):
    task_name   = process_B_args["task_name"]
    pc_mode     = process_B_args["pc_mode"]
    save_logs   = process_B_args["save_logs"]
    exit()
    
    print(f"{task_name} is now Running ✅")
    while True:
        print(f"{task_name} 💜")
        time.sleep(5)