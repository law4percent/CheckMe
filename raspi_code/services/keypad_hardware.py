"""
Keypad 3x4 Module
Provides a class-based interface for reading input from a 3x4 matrix keypad.

Pin wiring (BCM numbering):
    ALL_PINS = [6, 12, 13, 16, 19, 20, 21]

Key-to-pin mapping (discovered via hardware scan):
    [1] out=20, in=21
    [2] out=19, in=21
    [3] out=12, in=21
    [4] out=6,  in=20
    [5] out=6,  in=19
    [6] out=6,  in=12
    [7] out=13, in=20
    [8] out=13, in=19
    [9] out=12, in=13
    [*] out=16, in=20
    [0] out=16, in=19
    [#] out=12, in=16
"""

import RPi.GPIO as GPIO
import time
from typing import Optional, List, Callable


class KeypadError(Exception):
    """Base exception for keypad errors"""
    pass


class Keypad3x4:
    """
    Interface for 3x4 matrix keypad using GPIO.

    Layout:
        [1] [2] [3]
        [4] [5] [6]
        [7] [8] [9]
        [*] [0] [#]

    Example usage:
        keypad = Keypad3x4()

        # Single key read
        key = keypad.read_key()
        if key:
            print(f"Pressed: {key}")

        # Wait for specific key
        key = keypad.wait_for_key(valid_keys=['1', '2', '3'])

        # Read multi-character input
        code = keypad.read_input(length=8)
    """

    # All GPIO pins used by the keypad (BCM numbering)
    ALL_PINS = [6, 12, 13, 16, 19, 20, 21]

    # Direct mapping: (out_pin, in_pin) -> key character
    # Discovered via hardware scan
    KEYMAP = {
        (20, 21): '1',
        (19, 21): '2',
        (12, 21): '3',
        (6,  20): '4',
        (6,  19): '5',
        (6,  12): '6',
        (13, 20): '7',
        (13, 19): '8',
        (12, 13): '9',
        (16, 20): '*',
        (16, 19): '0',
        (12, 16): '#',
    }

    def __init__(
        self,
        keymap          : dict = None,
        debounce_time   : float = 0.05,
        stability_delay : float = 0.002
    ):
        """
        Initialize keypad interface.

        Args:
            keymap: Custom {(out_pin, in_pin): key} dict. Uses default if None.
            debounce_time: Time to wait after key press (seconds)
            stability_delay: Delay between pin scans (seconds)
        """
        self.keymap          = keymap or self.KEYMAP
        self.debounce_time   = debounce_time
        self.stability_delay = stability_delay

        self._is_setup      = False
        self._last_key      = None
        self._last_key_time = 0

        # Derive unique out/in pins from keymap
        self._out_pins = list(dict.fromkeys(k[0] for k in self.keymap))
        self._in_pins  = list(dict.fromkeys(k[1] for k in self.keymap))

        self.setup()

    def setup(self) -> None:
        """Initialize GPIO pins for the keypad"""
        if self._is_setup:
            return

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Start all pins as INPUT with pull-up
            for pin in self.ALL_PINS:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            self._is_setup = True

        except Exception as e:
            raise KeypadError(f"Failed to setup GPIO: {e}")

    def scan_key(self) -> Optional[str]:
        """
        Scan keypad once and return pressed key.

        Returns:
            str: Key character if pressed, None otherwise
        """
        if not self._is_setup:
            raise KeypadError("Keypad not setup. Call setup() first.")

        for out_pin in self._out_pins:
            # Drive this pin LOW
            GPIO.setup(out_pin, GPIO.OUT)
            GPIO.output(out_pin, GPIO.LOW)
            time.sleep(self.stability_delay)

            # Check all possible in_pins for this out_pin
            for in_pin in self._in_pins:
                if in_pin == out_pin:
                    continue
                GPIO.setup(in_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                if GPIO.input(in_pin) == GPIO.LOW:
                    key = self.keymap.get((out_pin, in_pin))
                    if key:
                        # Restore out_pin before returning
                        GPIO.setup(out_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                        return key

            # Restore out_pin to input
            GPIO.setup(out_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        return None

    def read_key(self, with_debounce: bool = True) -> Optional[str]:
        """
        Read a single key press with optional debouncing.

        Args:
            with_debounce: Apply debounce delay to prevent multiple reads

        Returns:
            str: Pressed key or None
        """
        key = self.scan_key()

        if key and with_debounce:
            current_time = time.time()
            if key == self._last_key and (current_time - self._last_key_time) < self.debounce_time:
                return None

            self._last_key      = key
            self._last_key_time = current_time

            # Wait for key release
            while self.scan_key() is not None:
                time.sleep(0.01)

        return key

    def wait_for_key(
        self,
        valid_keys  : Optional[List[str]] = None,
        timeout     : Optional[float] = None
    ) -> Optional[str]:
        """
        Block until a key is pressed.

        Args:
            valid_keys: List of acceptable keys. If None, accepts any key.
            timeout: Maximum time to wait in seconds. None = wait forever.

        Returns:
            str: Pressed key, or None if timeout
        """
        start_time = time.time()

        while True:
            if timeout and (time.time() - start_time) > timeout:
                return None

            key = self.read_key()

            if key:
                if valid_keys is None or key in valid_keys:
                    return key

            time.sleep(0.05)

    def read_input(
        self,
        length          : int = None,
        valid_keys      : Optional[List[str]] = None,
        end_key         : str = '#',
        cancel_key      : str = '*',
        echo_callback   : Optional[Callable[[str], None]] = None,
        timeout         : Optional[float] = None
    ) -> Optional[str]:
        """
        Read multi-character input from keypad.

        Args:
            length: Maximum input length. None = unlimited until end_key.
            valid_keys: List of acceptable keys (excluding end_key, cancel_key)
            end_key: Key to confirm input (default: '#')
            cancel_key: Key to cancel input (default: '*')
            echo_callback: Function to call for each key press
            timeout: Maximum time to wait in seconds

        Returns:
            str: Input string, or None if cancelled/timeout

        Example:
            # Read 4-digit PIN
            pin = keypad.read_input(
                length=4,
                valid_keys=['0','1','2','3','4','5','6','7','8','9'],
                echo_callback=lambda s: print(f"PIN: {'*' * len(s)}")
            )
        """
        input_buffer = ""
        start_time   = time.time()

        while True:
            if timeout and (time.time() - start_time) > timeout:
                return None

            key = self.read_key()

            if key:
                if key == cancel_key:
                    return None

                if key == end_key:
                    return input_buffer if input_buffer else None

                if valid_keys and key not in valid_keys:
                    continue

                if length and len(input_buffer) >= length:
                    return input_buffer

                input_buffer += key

                if echo_callback:
                    echo_callback(input_buffer)

            time.sleep(0.05)

    def read_numeric(
        self,
        length          : int,
        echo_callback   : Optional[Callable[[str], None]] = None,
        timeout         : Optional[float] = None
    ) -> Optional[str]:
        """
        Read numeric input only (0-9).

        Args:
            length: Exact number of digits required
            echo_callback: Function to call for each digit
            timeout: Maximum time to wait

        Returns:
            str: Numeric string or None
        """
        return self.read_input(
            length          = length,
            valid_keys      = ['0','1','2','3','4','5','6','7','8','9'],
            echo_callback   = echo_callback,
            timeout         = timeout
        )

    def confirm_action(
        self,
        confirm_key : str = '#',
        cancel_key  : str = '*',
        timeout     : Optional[float] = None
    ) -> bool:
        """
        Wait for user confirmation.

        Args:
            confirm_key: Key for yes/confirm (default: '#')
            cancel_key: Key for no/cancel (default: '*')
            timeout: Maximum time to wait

        Returns:
            bool: True if confirmed, False if cancelled/timeout
        """
        key = self.wait_for_key(
            valid_keys=[confirm_key, cancel_key],
            timeout=timeout
        )
        return key == confirm_key

    def cleanup(self) -> None:
        """Cleanup GPIO pins"""
        if self._is_setup:
            GPIO.cleanup()
            self._is_setup = False

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def __repr__(self) -> str:
        return f"Keypad3x4(pins={self.ALL_PINS})"


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    print("="*70)
    print("Example 1: Basic key reading")
    print("="*70)

    keypad = Keypad3x4()

    print("Press any key (Ctrl+C to stop)...")
    try:
        while True:
            key = keypad.read_key()
            if key:
                print(f"Key pressed: {key}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped")


    print("\n" + "="*70)
    print("Example 2: Wait for specific key")
    print("="*70)

    print("Press 1, 2, or 3...")
    key = keypad.wait_for_key(valid_keys=['1', '2', '3'])
    print(f"You pressed: {key}")


    print("\n" + "="*70)
    print("Example 3: Read 4-digit PIN")
    print("="*70)

    def show_pin(pin_so_far):
        masked = '*' * len(pin_so_far)
        print(f"\rPIN: {masked}", end='', flush=True)

    print("Enter 4-digit PIN:")
    pin = keypad.read_numeric(length=4, echo_callback=show_pin)
    print(f"\nYou entered: {pin}")


    print("\n" + "="*70)
    print("Example 4: Read 8-digit temporary code")
    print("="*70)

    def show_code(code):
        print(f"\rCode: {code}", end='', flush=True)

    print("Enter 8-digit code (auto-confirms at 8 digits):")
    code = keypad.read_input(
        length          = 8,
        valid_keys      = ['0','1','2','3','4','5','6','7','8','9'],
        echo_callback   = show_code,
        timeout         = 30
    )

    if code:
        print(f"\nCode entered: {code}")
    else:
        print("\nCancelled or timeout")


    print("\n" + "="*70)
    print("Example 5: Confirmation prompt")
    print("="*70)

    print("Press # to confirm, * to cancel")
    confirmed = keypad.confirm_action()
    print("✅ Confirmed!" if confirmed else "❌ Cancelled")


    print("\n" + "="*70)
    print("Example 6: Read with timeout")
    print("="*70)

    print("Press any key within 5 seconds...")
    key = keypad.wait_for_key(timeout=5)
    print(f"You pressed: {key}" if key else "Timeout!")


    print("\n" + "="*70)
    print("Example 7: Context manager usage")
    print("="*70)

    with Keypad3x4() as kp:
        print("Press a key...")
        key = kp.wait_for_key(timeout=3)
        print(f"Pressed: {key}")


    print("\n" + "="*70)
    print("Example 8: Login flow (8-digit code)")
    print("="*70)

    def login_with_temp_code():
        keypad = Keypad3x4()

        def show_lcd(text):
            masked = '*' * len(text)
            print(f"\rLCD: Enter code: {masked}", end='', flush=True)

        print("\n--- Login Screen ---")
        print("Enter 8-digit temporary code")
        print("Press * to cancel")

        code = keypad.read_input(
            length          = 8,
            valid_keys      = ['0','1','2','3','4','5','6','7','8','9'],
            echo_callback   = show_lcd,
            timeout         = 30
        )

        if code:
            print(f"\n\n✅ Code entered: {code}")
            return code
        else:
            print("\n\n❌ Login cancelled or timeout")
            return None

    result = login_with_temp_code()


    print("\n" + "="*70)
    print("Example 9: Menu navigation")
    print("="*70)

    def show_menu():
        keypad = Keypad3x4()
        menu = """
╔════════════════════════════╗
║        HOME MENU           ║
╠════════════════════════════╣
║  [1] Scan Answer Key       ║
║  [2] Check Answer Sheets   ║
║  [3] Settings              ║
╚════════════════════════════╝
"""
        print(menu)
        print("Press 1, 2, or 3 to select...")

        choice = keypad.wait_for_key(valid_keys=['1', '2', '3'], timeout=30)

        if choice:
            options = {'1': "Scan Answer Key", '2': "Check Answer Sheets", '3': "Settings"}
            print(f"\n✅ Selected: {options[choice]}")
            return choice
        else:
            print("\n⏱ Menu timeout")
            return None

    selection = show_menu()


    print("\n" + "="*70)
    print("Cleanup")
    print("="*70)

    keypad.cleanup()
    print("✅ GPIO cleaned up")

    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)