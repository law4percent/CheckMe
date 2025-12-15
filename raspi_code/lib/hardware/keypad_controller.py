import RPi.GPIO as GPIO
import time

# Default configuration
ROW_PINS = [19, 21, 20, 16]
COL_PINS = [12, 13, 6]

MATRIX = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#']
]

def setup_keypad(row_pins=ROW_PINS, col_pins=COL_PINS) -> None:
    """
        Initialize GPIO pins for the keypad.
    """
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for r in row_pins:
        GPIO.setup(r, GPIO.OUT)
        GPIO.output(r, GPIO.HIGH)

    for c in col_pins:
        GPIO.setup(c, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def scan_key(matrix=MATRIX, row_pins=ROW_PINS, col_pins=COL_PINS) -> str | None:
    """
        Scan the keypad and return the pressed key.
        Returns None if no key is pressed.
    """
    for i, r in enumerate(row_pins):
        GPIO.output(r, GPIO.LOW)
        time.sleep(0.002)  # Stability delay

        for j, c in enumerate(col_pins):
            if GPIO.input(c) == GPIO.LOW:
                GPIO.output(r, GPIO.HIGH)
                return matrix[i][j]

        GPIO.output(r, GPIO.HIGH)
    
    return None