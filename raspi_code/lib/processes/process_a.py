from multiprocessing import Queue
import time
from lib.services import hardware
from process_a_workers import scan_answer_key, scan_answer_sheet, settings, shutdown
from lib.services import display

def process_a(process_A_args: str, queue_frame: Queue):
    print(f"{task_name} is now Running ✅")

    task_name   = process_A_args["task_name"]
    pc_mode     = process_A_args["pc_mode"]
    save_logs   = process_A_args["save_logs"]

    ROW_PINS = [5, 6, 13, 19]    # R1 R2 R3 R4
    COL_PINS = [12, 16, 20]      # C1 C2 C3
    rows, cols = hardware.setup_keypad_pins(pc_mode, ROW_PINS, COL_PINS)

    current_stage, current_display_options = display.initialize_display()


    while True:
        if pc_mode:
            print(f"{task_name} PC mode skipping hardwares...")
            time.sleep(1)
            continue

        time.sleep(0.1)

        print("=== Option ===\n", current_display_options)
        key = hardware.read_keypad(rows, cols)

        if key != None:
            if key == display.Direction.UP.value or key == display.Direction.DOWN.value:
                current_stage, current_display_options = display.handle_display(key, current_stage)
            else:
                if key == '1':
                    scan_answer_key.run()
                elif key == '2':
                    scan_answer_sheet.run()
                elif key == '3':
                    settings.run()
                elif key == '4':
                    shutdown.run()
            
