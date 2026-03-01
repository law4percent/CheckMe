import RPi.GPIO as GPIO
import time

CANDIDATE_PINS = [6, 12, 13, 16, 19, 20, 21]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

print("Press and HOLD a key, then watch the output.")
print("Ctrl+C to stop.\n")

try:
    while True:
        for out_pin in CANDIDATE_PINS:
            # Set one pin as OUTPUT LOW
            GPIO.setup(out_pin, GPIO.OUT)
            GPIO.output(out_pin, GPIO.LOW)

            # Check all others as INPUT
            for in_pin in CANDIDATE_PINS:
                if in_pin == out_pin:
                    continue
                GPIO.setup(in_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                if GPIO.input(in_pin) == GPIO.LOW:
                    print(f"Key detected! out_pin={out_pin} ? in_pin={in_pin}")
                    time.sleep(0.3)

            # Reset out_pin back to input
            GPIO.setup(out_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        time.sleep(0.05)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\nDone.")