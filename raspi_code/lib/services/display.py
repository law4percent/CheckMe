from enum import Enum

class Stage(Enum):
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

class Direction(Enum):
    UP      = '*'
    DOWN    = '#'



def handle_display(key: str, current_stage: int):
    current_display_options = []

    if key == Direction.UP.value:
        if current_stage > 1:
            current_stage -= 1 
    elif key == Direction.DOWN.value:
        if current_stage < 3:
            current_stage += 1  

    if current_stage == 1:
        current_display_options = Stage.STAGE_1.value
    elif current_stage == 2:
        current_display_options = Stage.STAGE_2.value
    elif current_stage == 3:
        current_display_options = Stage.STAGE_3.value

    return [current_stage, current_display_options]


def initialize_display(current_stage: int = 1, current_display_options: list = Stage.STAGE_1.value):
    current_stage = current_stage
    current_display_options = current_display_options
    return [current_stage, current_display_options]

