from enum import Enum

class ProcessMainStage(Enum):
    STAGE_1 = [
        '[1] Scan Answer Key      \n',
        '[2] Scan Answer Sheet  🔽\n'
    ]
    STAGE_2 = [
        '[2] Scan Answer Sheet  🔼\n',
        '[3] Settings           🔽\n',
    ]
    STAGE_3 = [
        '[3] Settings           🔼\n',
        '[4] Shutdown           \n'
    ]


class ProcessMainDirection(Enum):
    UP      = '*'
    DOWN    = '#'


class ScanAnswerKeyOption(Enum):
    PRINT = '1'
    EXIT  = '0'




def handle_display(key: str, current_stage: int, module_name: str) -> list:
    current_display_options = []

    if module_name == "process_a":
        if key == ProcessMainDirection.UP.value:
            if current_stage > 1:
                current_stage -= 1 
        elif key == ProcessMainDirection.DOWN.value:
            if current_stage < 3:
                current_stage += 1  

        if current_stage == 1:
            current_display_options = ProcessMainStage.STAGE_1.value
        elif current_stage == 2:
            current_display_options = ProcessMainStage.STAGE_2.value
        elif current_stage == 3:
            current_display_options = ProcessMainStage.STAGE_3.value

        return [current_stage, current_display_options]
    
    if module_name == "scan_answer_key":
        if key == ScanAnswerKeyOption.PRINT.value:
            pass
        elif key == ScanAnswerKeyOption.EXIT.value:
            pass


def initialize_display(module_name: str, current_stage: int = 1) -> list:
    if module_name == "process_a":
        current_stage           = current_stage
        current_display_options = current_display_options
        return [current_stage, current_display_options]
    
    if module_name == "scan_answer_key":
        pass 

