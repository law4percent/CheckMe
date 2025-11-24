from multiprocessing import Queue
import time
from process_a_workers import scan_answer_key, scan_answer_sheet, settings, shutdown, hardware, display
from enum import Enum

class Options(Enum):
    SCAN_ANSWER_KEY     = '1'
    SCAN_ANSWER_SHEET   = '2'
    SETTINGS            = '3'
    SHUTDOWN            = '4'
    

def process_a(process_A_args: str, queue_frame: Queue):
    print(f"{task_name} is now Running ✅")

    task_name   = process_A_args["task_name"]
    pc_mode     = process_A_args["pc_mode"]
    save_logs   = process_A_args["save_logs"]

    ROW_PINS = [5, 6, 13, 19]    # R1 R2 R3 R4
    COL_PINS = [12, 16, 20]      # C1 C2 C3
    rows, cols = hardware.setup_keypad_pins(pc_mode, ROW_PINS, COL_PINS)

    current_stage, current_display_options = display.initialize_display(module_name="process_a")


    while True:
        if pc_mode:
            print(f"{task_name} PC mode skipping hardwares...")
            time.sleep(1)
            continue

        time.sleep(0.1)

        print("=== Option ===\n", current_display_options)
        key = hardware.read_keypad(rows, cols)

        if key != None:
            if key == display.ProcessMainDirection.UP.value or key == display.ProcessMainDirection.DOWN.value:
                current_stage, current_display_options = display.handle_display(key=key, current_stage=current_stage, module_name="process_a")
            else:
                if key == Options.SCAN_ANSWER_KEY.value:
                    scan_answer_key.run(rows, cols)
                elif key ==  Options.SCAN_ANSWER_SHEET.value:
                    scan_answer_sheet.run()
                elif key ==  Options.SETTINGS.value:
                    settings.run()
                elif key ==  Options.SHUTDOWN.value:
                    shutdown.run()
            
