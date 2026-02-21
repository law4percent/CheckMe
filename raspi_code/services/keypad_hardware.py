"""
Keypad 3x4 Module
Provides a class-based interface for reading input from a 3x4 matrix keypad.
"""

import RPi.GPIO as GPIO
import time
from typing import Optional, List, Callable
from enum import Enum


class KeypadMode(Enum):
    """Keypad operation modes"""
    NUMERIC         = "numeric"       # 0-9 only
    ALPHANUMERIC    = "alphanumeric"  # 0-9, *, #
    CUSTOM          = "custom"         # Custom matrix


class KeypadError(Exception):
    """Base exception for keypad errors"""
    pass


class Keypad3x4:
    """
    Interface for 3x4 matrix keypad using GPIO.
    
    Default Layout:
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
        code = keypad.read_input(length=8, uppercase=True)
    """
    
    # Default GPIO pin configuration (BCM numbering)
    DEFAULT_ROW_PINS = [19, 21, 20, 16]
    DEFAULT_COL_PINS = [12, 13, 6]
    
    # Default key matrix layout
    DEFAULT_MATRIX = [
        ['1', '2', '3'],
        ['4', '5', '6'],
        ['7', '8', '9'],
        ['*', '0', '#']
    ]
    
    def __init__(
        self,
        row_pins: List[int] = None,
        col_pins: List[int] = None,
        matrix: List[List[str]] = None,
        debounce_time: float = 0.05,
        stability_delay: float = 0.002
    ):
        """
        Initialize keypad interface.
        
        Args:
            row_pins: GPIO pins for rows (BCM numbering)
            col_pins: GPIO pins for columns (BCM numbering)
            matrix: Key layout matrix (4 rows x 3 columns)
            debounce_time: Time to wait after key press (seconds)
            stability_delay: Delay between row scans (seconds)
        """
        self.row_pins = row_pins or self.DEFAULT_ROW_PINS
        self.col_pins = col_pins or self.DEFAULT_COL_PINS
        self.matrix = matrix or self.DEFAULT_MATRIX
        self.debounce_time = debounce_time
        self.stability_delay = stability_delay
        
        self._is_setup = False
        self._last_key = None
        self._last_key_time = 0
        
        # Validate configuration
        self._validate_configuration()
        
        # Setup GPIO
        self.setup()
    
    def _validate_configuration(self) -> None:
        """Validate pin configuration and matrix layout"""
        if len(self.row_pins) != 4:
            raise KeypadError("Exactly 4 row pins required")
        
        if len(self.col_pins) != 3:
            raise KeypadError("Exactly 3 column pins required")
        
        if len(self.matrix) != 4 or any(len(row) != 3 for row in self.matrix):
            raise KeypadError("Matrix must be 4x3 (4 rows, 3 columns)")
    
    def setup(self) -> None:
        """Initialize GPIO pins for the keypad"""
        if self._is_setup:
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup row pins as outputs (HIGH by default)
            for pin in self.row_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.HIGH)
            
            # Setup column pins as inputs with pull-up resistors
            for pin in self.col_pins:
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
        
        for i, row_pin in enumerate(self.row_pins):
            # Pull row LOW
            GPIO.output(row_pin, GPIO.LOW)
            time.sleep(self.stability_delay)
            
            # Check each column
            for j, col_pin in enumerate(self.col_pins):
                if GPIO.input(col_pin) == GPIO.LOW:
                    # Key pressed
                    GPIO.output(row_pin, GPIO.HIGH)
                    return self.matrix[i][j]
            
            # Pull row back HIGH
            GPIO.output(row_pin, GPIO.HIGH)
        
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
            # Debounce: ignore if same key pressed within debounce time
            current_time = time.time()
            if key == self._last_key and (current_time - self._last_key_time) < self.debounce_time:
                return None
            
            self._last_key = key
            self._last_key_time = current_time
            
            # Wait for key release
            while self.scan_key() is not None:
                time.sleep(0.01)
        
        return key
    
    def wait_for_key(
        self,
        valid_keys: Optional[List[str]] = None,
        timeout: Optional[float] = None
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
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            key = self.read_key()
            
            if key:
                # Check if key is valid
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
            echo_callback: Function to call for each key (e.g., lcd.show)
            timeout: Maximum time to wait in seconds
        
        Returns:
            str: Input string, or None if cancelled/timeout
        
        Example:
            # Read 4-digit PIN
            pin = keypad.read_input(
                length=4,
                valid_keys=['0','1','2','3','4','5','6','7','8','9'],
                echo_callback=lambda s: lcd.show(f"PIN: {s}")
            )
            
            # Read 8-digit code
            code = keypad.read_input(
                length=8,
                valid_keys=['0','1','2','3','4','5','6','7','8','9']
            )
        """
        input_buffer = ""
        start_time = time.time()
        
        while True:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            key = self.read_key()
            
            if key:
                # Check for cancel
                if key == cancel_key:
                    return None
                
                # Check for end/confirm
                if key == end_key:
                    return input_buffer if input_buffer else None
                
                # Check if key is valid
                if valid_keys and key not in valid_keys:
                    continue
                
                # Check length limit
                if length and len(input_buffer) >= length:
                    # Auto-confirm when length reached
                    return input_buffer
                
                # Add key to buffer
                input_buffer += key
                
                # Echo callback
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
        valid_keys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        return self.read_input(
            length          = length,
            valid_keys      = valid_keys,
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
    
    def get_matrix(self) -> List[List[str]]:
        """Get current key matrix layout"""
        return self.matrix
    
    def set_matrix(self, matrix: List[List[str]]) -> None:
        """
        Set custom key matrix layout.
        
        Args:
            matrix: 4x3 matrix of key characters
        """
        if len(matrix) != 4 or any(len(row) != 3 for row in matrix):
            raise KeypadError("Matrix must be 4x3")
        self.matrix = matrix
    
    def cleanup(self) -> None:
        """Cleanup GPIO pins"""
        if self._is_setup:
            GPIO.cleanup()
            self._is_setup = False
    
    def __enter__(self):
        """Context manager entry"""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
    
    def __repr__(self) -> str:
        return f"Keypad3x4(rows={self.row_pins}, cols={self.col_pins})"


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
        """Simulate LCD display"""
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
    
    print("Enter 8-digit code:")
    print("(will auto-confirm when 8 digits entered)")
    
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
    
    if confirmed:
        print("✅ Confirmed!")
    else:
        print("❌ Cancelled")
    
    
    print("\n" + "="*70)
    print("Example 6: Read with timeout")
    print("="*70)
    
    print("Press any key within 5 seconds...")
    key = keypad.wait_for_key(timeout=5)
    
    if key:
        print(f"You pressed: {key}")
    else:
        print("Timeout!")
    
    
    print("\n" + "="*70)
    print("Example 7: Context manager usage")
    print("="*70)
    
    with Keypad3x4() as kp:
        print("Press a key...")
        key = kp.wait_for_key(timeout=3)
        print(f"Pressed: {key}")
    # GPIO automatically cleaned up
    
    
    print("\n" + "="*70)
    print("Example 8: Custom matrix layout")
    print("="*70)
    
    # Example: Alphabetic keypad
    custom_matrix = [
        ['A', 'B', 'C'],
        ['D', 'E', 'F'],
        ['G', 'H', 'I'],
        ['*', '0', '#']
    ]
    
    keypad_custom = Keypad3x4(matrix=custom_matrix)
    print("Custom layout set")
    print("Matrix:", keypad_custom.get_matrix())
    
    
    print("\n" + "="*70)
    print("Example 9: Login flow integration (8-digit code)")
    print("="*70)
    
    def login_with_temp_code():
        """Simulate login with 8-digit temporary code from mobile app"""
        keypad = Keypad3x4()
        
        def show_lcd(text):
            """Simulate LCD display"""
            masked = '*' * len(text)  # Mask for security
            print(f"\rLCD: Enter code: {masked}", end='', flush=True)
        
        print("\n--- Login Screen ---")
        print("Enter 8-digit temporary code")
        print("Format: 12345678 (8 numbers)")
        print("Press * to cancel")
        print("(auto-confirms when 8 digits entered)")
        
        code = keypad.read_input(
            length          = 8,
            valid_keys      = ['0','1','2','3','4','5','6','7','8','9'],
            echo_callback   = show_lcd,
            timeout         = 30  # 30 second timeout
        )
        
        if code:
            print(f"\n\n✅ Code entered successfully")
            print("Validating with Firebase...")
            # In real system: auth.login_with_temp_code(code)
            return code
        else:
            print("\n\n❌ Login cancelled or timeout")
            return None
    
    # Run login flow
    result = login_with_temp_code()
    
    
    print("\n" + "="*70)
    print("Example 10: Menu navigation")
    print("="*70)
    
    def show_menu():
        """Display menu and get selection"""
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
        
        choice = keypad.wait_for_key(
            valid_keys=['1', '2', '3'],
            timeout=30
        )
        
        if choice:
            options = {
                '1': "Scan Answer Key",
                '2': "Check Answer Sheets",
                '3': "Settings"
            }
            print(f"\n✅ Selected: {options[choice]}")
            return choice
        else:
            print("\n⏱ Menu timeout")
            return None
    
    # Show menu
    selection = show_menu()
    
    
    print("\n" + "="*70)
    print("Cleanup")
    print("="*70)
    
    keypad.cleanup()
    print("✅ GPIO cleaned up")
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)