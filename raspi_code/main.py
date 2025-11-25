from lib.processes import process_a, process_b, process_c
from multiprocessing import Process, Queue, Event

def main(**kargs):
    queue_frame = Queue(maxsize=1)
    
    task_a = Process(
        target  =   process_a.process_a,
        kwargs  =   {
            "process_A_args"    : kargs["process_A_args"],
            "queue_frame"       : queue_frame
        }
    )
    task_b = Process(
        target  =   process_b.process_b, 
        kwargs  =   {
            "process_B_args"    : kargs["process_B_args"],
            "queue_frame"       : queue_frame
        }
    )
    task_c = Process(
        target  =   process_c.process_c, 
        kwargs  =   {
            "process_C_args"    : kargs["process_C_args"]
        }
    )
    
    task_a.start()
    task_b.start()
    task_c.start()
    
    task_a.join()
    task_b.join()
    task_c.join()
    

if __name__ == "__main__":
    pc_mode  = True
    save_logs   = False
    
    main(
        process_A_args = {
            "task_name"     : "Process A",
            "pc_mode"       : pc_mode,
            "save_logs"     : save_logs,
            "camera_index"  : 0,
            "show_windows"  : True
        },
        process_B_args = {
            "task_name"     : "Process B",
            "pc_mode"       : pc_mode,
            "save_logs"     : save_logs,
        },
        process_C_args = {
            "task_name"     : "Process C",
            "pc_mode"       : pc_mode,
            "save_logs"     : save_logs,
        }
    )