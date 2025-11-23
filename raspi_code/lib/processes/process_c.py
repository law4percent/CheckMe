from multiprocessing import Queue
import time

def process_c(process_C_args: str):
    task_name   = process_C_args["task_name"]
    pc_mode     = process_C_args["pc_mode"]
    save_logs   = process_C_args["save_logs"]
    
    print(f"{task_name} is now Running ✅")
    while True:
        print(f"{task_name} 💜")
        time.sleep(3)