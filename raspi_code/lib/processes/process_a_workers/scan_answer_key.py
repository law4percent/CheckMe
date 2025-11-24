import time
import hardware
import display
from enum import Enum

def run(rows: any, cols: any) -> None:
    print("Ready to scan the answer key")
    current_stage, current_display_options = display.initialize_display(module_name="scan_answer_key")

    # while True:
    #     key = hardware.read_keypad(rows, cols)
        
    #     print("=== Option ===\n", current_display_options)

    #     if key != None:
    #         if key == display.ScanAnswerKeyAgreement.YES.value or key == display.ScanAnswerKeyAgreement.NO.value:
    #             current_stage, current_display_options = display.handle_display(key=key, current_stage=current_stage, module_name="scan_answer_key")
         
                # add loop here
    while True:
        time.sleep(0.1)
        key = hardware.read_keypad(rows, cols)
        
        print("=== Option ===")
        print("[1] PRINT")
        print("[2] EXIT")

        if key != None:
            if key == display.ScanAnswerKeyOption.PRINT.value:
                break
            elif key == display.ScanAnswerKeyOption.EXIT.value:
                return