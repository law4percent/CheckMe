from gpiozero import DigitalOutputDevice, DigitalInputDevice
from time import sleep

# BCM pin numbers

KEYS = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["*", "0", "#"]
]


def setup_keypad_pins(pc_mode: bool, ROW_PINS: list, COL_PINS: list) -> list | None:
    if pc_mode:
        print("Skipping the setup_keypad_pins()...")
        return None

    # Setup rows (output)
    rows = [DigitalOutputDevice(pin, active_high=False, initial_value=True) for pin in ROW_PINS]

    # Setup columns (input)
    cols = [DigitalInputDevice(pin, pull_up=True) for pin in COL_PINS]
    return [rows, cols]


def read_keypad(rows: list, cols: list) -> str | None:
    for r, row in enumerate(rows):
        row.off()    # active-low → set row LOW to enable

        for c, col in enumerate(cols):
            if not col.value:   # LOW = pressed
                key = KEYS[r][c]

                # Wait until key is released
                while not col.value:
                    sleep(0.01)

                row.on()
                return key

        row.on()

    return None