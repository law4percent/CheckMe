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
    SCAN = '1'
    EXIT  = '2'


def display_the_options():
    print("=== Option ===")
    print("[1] SCAN")
    print("[2] EXIT")


def handle_display(key: str, current_stage: int) -> list:
    current_display_options = []

    if key == ProcessMainDirection.UP.value:
        if current_stage > 1:
            current_stage -= 1 
    elif key == ProcessMainDirection.DOWN.value:
        if current_stage < 3:
            current_stage += 1
    else:
        return [current_stage, current_display_options]

    if current_stage == 1:
        current_display_options = ProcessMainStage.STAGE_1.value
    elif current_stage == 2:
        current_display_options = ProcessMainStage.STAGE_2.value
    elif current_stage == 3:
        current_display_options = ProcessMainStage.STAGE_3.value
    else:
        return [current_stage, current_display_options]

    return [current_stage, current_display_options]


def initialize_display(current_stage: int = 1) -> list:
    current_stage           = current_stage
    current_display_options = ProcessMainStage.STAGE_1.value
    return [current_stage, current_display_options]

