from multiprocessing import Queue
import time

def process_b(process_B_args: str, queue_frame: Queue):
    task_name   = process_B_args["task_name"]
    pc_mode     = process_B_args["pc_mode"]
    save_logs   = process_B_args["save_logs"]
    
    print(f"{task_name} is now Running ✅")
    while True:
        print(f"{task_name} 💜")
        time.sleep(5)