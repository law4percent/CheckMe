from multiprocessing import Queue
import time

def process_a(process_A_args: str, queue_frame: Queue):
    task_name   = process_A_args["task_name"]
    pc_mode     = process_A_args["pc_mode"]
    save_logs   = process_A_args["save_logs"]
    
    print(f"{task_name} is now Running ✅")
    while True:
        print(f"{task_name} 💜")
        time.sleep(1)