"""
LCD I2C Module
Provides a class-based interface for I2C character LCD displays (16x2, 20x4).
Uses PCF8574 I2C backpack.
"""

import smbus2
import time
from typing import List, Optional, Tuple
from enum import Enum


class LCDSize(Enum):
    """Standard LCD sizes"""
    LCD_16x2 = (16, 2)
    LCD_20x4 = (20, 4)


class LCDError(Exception):
    """Base exception for LCD errors"""
    pass


class LCDConnectionError(LCDError):
    """Raised when LCD connection fails"""
    pass


class LCD_I2C:
    """
    Interface for I2C character LCD displays.
    
    Supports:
    - 16x2 LCD (16 columns, 2 rows)
    - 20x4 LCD (20 columns, 4 rows)
    
    Default Layout (20x4):
        Row 0: [                    ]  (20 chars)
        Row 1: [                    ]
        Row 2: [                    ]
        Row 3: [                    ]
    
    Example usage:
        lcd = LCD_I2C(address=0x27, size=LCDSize.LCD_20x4)
        
        ### Simple text
        lcd.show("Hello, World!")
        
        ### Multi-line
        lcd.show([
            "Line 1",
            "Line 2",
            "Line 3"
        ])
        
        ### Clear after 3 seconds
        lcd.show("Temporary message", duration=3)
        
        ### Position text
        lcd.write_at(0, 0, "Top Left")
        lcd.write_at(10, 1, "Mid Right")
        
        ### Scrollable list (more lines than LCD rows)
        lcd.show_scrollable([
            "Option 1",
            "Option 2",
            "Option 3",
            "Option 4",
            "Option 5",
        ], scroll_up_key='2', scroll_down_key='8')
    """
    
    # LCD Commands
    LCD_CLEARDISPLAY    = 0x01
    LCD_RETURNHOME      = 0x02
    LCD_ENTRYMODESET    = 0x04
    LCD_DISPLAYCONTROL  = 0x08
    LCD_CURSORSHIFT     = 0x10
    LCD_FUNCTIONSET     = 0x20
    LCD_SETCGRAMADDR    = 0x40
    LCD_SETDDRAMADDR    = 0x80
    
    # Flags for display entry mode
    LCD_ENTRYRIGHT  = 0x00
    LCD_ENTRYLEFT   = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00
    
    # Flags for display on/off control
    LCD_DISPLAYON   = 0x04
    LCD_DISPLAYOFF  = 0x00
    LCD_CURSORON    = 0x02
    LCD_CURSOROFF   = 0x00
    LCD_BLINKON     = 0x01
    LCD_BLINKOFF    = 0x00
    
    # Flags for display/cursor shift
    LCD_DISPLAYMOVE = 0x08
    LCD_CURSORMOVE  = 0x00
    LCD_MOVERIGHT   = 0x04
    LCD_MOVELEFT    = 0x00
    
    # Flags for function set
    LCD_8BITMODE  = 0x10
    LCD_4BITMODE  = 0x00
    LCD_2LINE     = 0x08
    LCD_1LINE     = 0x00
    LCD_5x10DOTS  = 0x04
    LCD_5x8DOTS   = 0x00
    
    # Flags for backlight control
    LCD_BACKLIGHT   = 0x08
    LCD_NOBACKLIGHT = 0x00
    
    # Enable bit
    En = 0b00000100
    Rw = 0b00000010
    Rs = 0b00000001
    
    def __init__(
        self,
        address   : int     = 0x27,
        bus       : int     = 1,
        size      : LCDSize = LCDSize.LCD_20x4,
        backlight : bool    = True
    ):
        """
        Initialize LCD display.
        
        Args:
            address: I2C address (usually 0x27 or 0x3F)
            bus: I2C bus number (1 for Raspberry Pi)
            size: LCD size (16x2 or 20x4)
            backlight: Enable backlight by default
        """
        self.address    = address
        self.bus_number = bus
        self.cols, self.rows = size.value
        self.backlight_state = LCD_I2C.LCD_BACKLIGHT if backlight else LCD_I2C.LCD_NOBACKLIGHT
        
        # Row address offsets for different LCD sizes
        if self.rows == 2:
            self.row_offsets = [0x00, 0x40]
        elif self.rows == 4:
            self.row_offsets = [0x00, 0x40, 0x14, 0x54]
        else:
            self.row_offsets = [0x00, 0x40, 0x14, 0x54]
        
        try:
            self.bus = smbus2.SMBus(self.bus_number)
        except Exception as e:
            raise LCDConnectionError(f"Failed to open I2C bus: {e}")
        
        # Initialize display
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize LCD in 4-bit mode"""
        try:
            # Wait for LCD to power up
            time.sleep(0.05)
            
            # Put LCD into 4-bit mode
            self._write_four_bits(0x03 << 4)
            time.sleep(0.005)
            
            self._write_four_bits(0x03 << 4)
            time.sleep(0.005)
            
            self._write_four_bits(0x03 << 4)
            time.sleep(0.00015)
            
            self._write_four_bits(0x02 << 4)
            
            # Function set: 4-bit mode, 2 lines, 5x8 dots
            self._write_command(
                self.LCD_FUNCTIONSET |
                self.LCD_4BITMODE |
                self.LCD_2LINE |
                self.LCD_5x8DOTS
            )
            
            # Display control: display on, cursor off, blink off
            self._write_command(
                self.LCD_DISPLAYCONTROL |
                self.LCD_DISPLAYON |
                self.LCD_CURSOROFF |
                self.LCD_BLINKOFF
            )
            
            # Clear display
            self.clear()
            
            # Entry mode: left to right, no shift
            self._write_command(
                self.LCD_ENTRYMODESET |
                self.LCD_ENTRYLEFT |
                self.LCD_ENTRYSHIFTDECREMENT
            )
            
        except Exception as e:
            raise LCDError(f"LCD initialization failed: {e}")
    
    def _write_four_bits(self, data: int) -> None:
        """Write 4 bits to LCD"""
        try:
            self.bus.write_byte(self.address, data | self.backlight_state)
            self._pulse_enable(data)
        except Exception as e:
            raise LCDConnectionError(f"I2C write failed: {e}")
    
    def _pulse_enable(self, data: int) -> None:
        """Pulse the enable bit"""
        self.bus.write_byte(self.address, data | self.En | self.backlight_state)
        time.sleep(0.0005)
        self.bus.write_byte(self.address, (data & ~self.En) | self.backlight_state)
        time.sleep(0.0001)
    
    def _write_command(self, cmd: int) -> None:
        """Write command to LCD"""
        self._write_four_bits(cmd & 0xF0)
        self._write_four_bits((cmd << 4) & 0xF0)
    
    def _write_data(self, data: int) -> None:
        """Write data to LCD"""
        self._write_four_bits(self.Rs | (data & 0xF0))
        self._write_four_bits(self.Rs | ((data << 4) & 0xF0))
    
    def clear(self) -> None:
        """Clear the display"""
        self._write_command(self.LCD_CLEARDISPLAY)
        time.sleep(0.002)
    
    def home(self) -> None:
        """Return cursor to home position"""
        self._write_command(self.LCD_RETURNHOME)
        time.sleep(0.002)
    
    def set_cursor(self, col: int, row: int) -> None:
        """
        Set cursor position.
        
        Args:
            col: Column (0 to cols-1)
            row: Row (0 to rows-1)
        """
        if row < 0 or row >= self.rows:
            raise ValueError(f"Row must be 0-{self.rows-1}")
        if col < 0 or col >= self.cols:
            raise ValueError(f"Column must be 0-{self.cols-1}")
        
        self._write_command(self.LCD_SETDDRAMADDR | (col + self.row_offsets[row]))
    
    def write(self, text: str) -> None:
        """
        Write text at current cursor position.
        
        Args:
            text: Text to write
        """
        for char in text:
            self._write_data(ord(char))
    
    def write_at(self, col: int, row: int, text: str) -> None:
        """
        Write text at specific position.
        
        Args:
            col: Column position
            row: Row position
            text: Text to write
        """
        self.set_cursor(col, row)
        self.write(text)
    
    def show(
        self,
        content: str | List[str],
        duration: Optional[float] = None,
        clear_first: bool = True,
        center: bool = False
    ) -> None:
        """
        Display content on LCD.
        
        Args:
            content: Single string or list of strings (one per row)
            duration: Auto-clear after N seconds (None = no auto-clear)
            clear_first: Clear display before writing
            center: Center text on each row
        
        Examples:
            # Single line
            lcd.show("Hello!")
            
            # Multi-line
            lcd.show(["Line 1", "Line 2", "Line 3"])
            
            # Temporary message
            lcd.show("Please wait...", duration=2)
            
            # Centered text
            lcd.show("MENU", center=True)
        """
        if clear_first:
            self.clear()
        
        # Convert single string to list
        if isinstance(content, str):
            lines = [content]
        else:
            lines = content
        
        # Display each line
        for i, line in enumerate(lines[:self.rows]):  # Max rows
            if center:
                # Center text
                padding = (self.cols - len(line)) // 2
                line = " " * padding + line
            
            # Truncate if too long
            line = line[:self.cols]
            
            self.write_at(0, i, line)
        
        # Auto-clear after duration
        if duration:
            time.sleep(duration)
            self.clear()

    # -------------------------------------------------------------------------
    # SCROLLABLE DISPLAY
    # -------------------------------------------------------------------------

    def _render_scroll_view(
        self,
        lines       : List[str],
        offset      : int,
        title       : Optional[str] = None,
        show_scroll_indicator : bool = True,
    ) -> None:
        """
        Internal helper – renders one 'page' of a scrollable list.

        Layout (20x4 with title):
            Row 0  →  title (fixed header)
            Row 1-3 →  content lines [offset … offset+visible_rows-1]

        Layout (20x4 without title):
            Row 0-3 →  content lines [offset … offset+3]

        A small scroll indicator is written at the far-right of the first and
        last content rows so the user knows there is more content above/below.
        """
        self.clear()

        content_start_row = 0
        if title is not None:
            self.write_at(0, 0, title[:self.cols].center(self.cols))
            content_start_row = 1

        visible_rows = self.rows - content_start_row
        total        = len(lines)

        for i in range(visible_rows):
            line_index = offset + i
            if line_index >= total:
                break

            line = lines[line_index][:self.cols]

            # Scroll indicators (^ at top content row when scrollable up,
            # v at bottom content row when scrollable down)
            indicator = " "
            if show_scroll_indicator:
                if i == 0 and offset > 0:
                    indicator = "^"
                elif i == visible_rows - 1 and (offset + visible_rows) < total:
                    indicator = "v"

            # Reserve last character for indicator; pad line to fill the rest
            display_line = f"{line:<{self.cols - 1}}{indicator}"
            self.write_at(0, content_start_row + i, display_line)

    def show_scrollable(
        self,
        lines             : List[str],
        title             : Optional[str] = None,
        scroll_up_key     : str  = "2",
        scroll_down_key   : str  = "8",
        exit_key          : str  = "#",
        keypad            = None,
        get_key_func      = None,
        show_scroll_indicator : bool = True,
    ) -> Optional[int]:
        """
        Display a scrollable list that is longer than the LCD row count.

        The caller provides a *key-reading function* so this method stays
        hardware-agnostic.  Pass either:
          • keypad     – an object with a ``get_key()`` method (e.g. keypad_4x4)
          • get_key_func – any callable() that blocks until a key is pressed
                           and returns a single-character string, or None on
                           timeout.

        If neither is supplied the function falls back to ``input()`` so you
        can test it on a regular terminal.

        Args:
            lines        : List of text lines to display (any length).
            title        : Optional fixed header shown on row 0.
            scroll_up_key   : Key that scrolls the view up   (default '2').
            scroll_down_key : Key that scrolls the view down (default '8').
            exit_key     : Key that exits the scroll loop    (default '#').
            keypad       : Object with .get_key() method.
            get_key_func : Callable() → str | None.
            show_scroll_indicator : Show '^'/'v' scroll hint characters.

        Returns:
            The current scroll offset when the user pressed exit_key, or None.

        Example (with a keypad library)::

            from keypad_4x4 import Keypad
            kp = Keypad(...)

            lcd.show_scrollable(
                lines=[
                    "Alice  – 48/50",
                    "Bob    – 45/50",
                    "Carol  – 50/50",
                    "Dave   – 40/50",
                    "Eve    – 47/50",
                    "Frank  – 43/50",
                    "Grace  – 49/50",
                ],
                title="STUDENT SCORES",
                scroll_up_key="2",
                scroll_down_key="8",
                exit_key="#",
                keypad=kp,
            )

        Example (terminal / testing without real keypad)::

            lcd.show_scrollable(
                lines=["Line " + str(i) for i in range(20)],
                title="BIG LIST",
            )
            # Uses input() automatically – press 2/8/# in the terminal.
        """
        if not lines:
            self.show("(empty list)")
            return None

        # Resolve the key-reading callable
        if get_key_func is not None:
            _get_key = get_key_func
        elif keypad is not None:
            _get_key = keypad.get_key
        else:
            # Fallback: terminal input (useful for testing)
            def _get_key():
                return input("Key [2=up 8=down #=exit]: ").strip() or None

        content_start_row = 1 if title is not None else 0
        visible_rows      = self.rows - content_start_row
        total             = len(lines)
        offset            = 0  # Index of the topmost visible line

        # Initial render
        self._render_scroll_view(lines, offset, title, show_scroll_indicator)

        while True:
            key = _get_key()

            if key is None:
                continue

            if key == scroll_down_key:
                # Scroll down: shift the window down by one line
                if offset + visible_rows < total:
                    offset += 1
                    self._render_scroll_view(lines, offset, title, show_scroll_indicator)

            elif key == scroll_up_key:
                # Scroll up: shift the window up by one line
                if offset > 0:
                    offset -= 1
                    self._render_scroll_view(lines, offset, title, show_scroll_indicator)

            elif key == exit_key:
                break

        return offset

    def show_scrollable_menu(
        self,
        title             : str,
        options           : List[str],
        scroll_up_key     : str  = "2",
        scroll_down_key   : str  = "8",
        select_key        : str  = "*",
        exit_key          : str  = "#",
        keypad            = None,
        get_key_func      = None,
        cursor_char       : str  = ">",
    ) -> Optional[int]:
        """
        Interactive scrollable menu with a cursor – returns the selected index.

        The cursor highlights which option is currently focused.  Use the
        scroll keys to move it; press select_key to confirm the choice.

        Args:
            title           : Fixed header row.
            options         : List of option strings (any length).
            scroll_up_key   : Move cursor up   (default '2').
            scroll_down_key : Move cursor down (default '8').
            select_key      : Confirm selection (default '*').
            exit_key        : Abort without selecting (default '#').
            keypad          : Object with .get_key() method.
            get_key_func    : Callable() → str | None.
            cursor_char     : Character shown to the left of the focused option.

        Returns:
            Index of the selected option (0-based), or None if aborted.

        Example::

            choice = lcd.show_scrollable_menu(
                title="SELECT MODE",
                options=[
                    "[1] Scan Answer Key",
                    "[2] Check Sheets",
                    "[3] View Scores",
                    "[4] Export CSV",
                    "[5] Settings",
                    "[6] About",
                ],
                scroll_up_key="2",
                scroll_down_key="8",
                select_key="*",
                exit_key="#",
                keypad=kp,
            )
            if choice is not None:
                print(f"User chose option {choice}: {options[choice]}")
        """
        if not options:
            self.show("(no options)")
            return None

        # Resolve the key-reading callable
        if get_key_func is not None:
            _get_key = get_key_func
        elif keypad is not None:
            _get_key = keypad.get_key
        else:
            def _get_key():
                return input(
                    f"Key [{scroll_up_key}=up {scroll_down_key}=down "
                    f"{select_key}=select {exit_key}=exit]: "
                ).strip() or None

        content_start_row = 1  # Row 0 is always the title
        visible_rows      = self.rows - content_start_row
        total             = len(options)
        cursor            = 0   # Currently focused option index
        offset            = 0   # Top of the visible window

        def _render():
            self.clear()
            self.write_at(0, 0, title[:self.cols].center(self.cols))

            for i in range(visible_rows):
                line_index = offset + i
                if line_index >= total:
                    break

                is_selected = (line_index == cursor)
                prefix      = cursor_char if is_selected else " "

                # Reserve 1 char for prefix + 1 for scroll hint
                text = options[line_index]
                max_text_len = self.cols - 2

                # Scroll hint
                hint = " "
                if i == 0 and offset > 0:
                    hint = "^"
                elif i == visible_rows - 1 and (offset + visible_rows) < total:
                    hint = "v"

                display_line = f"{prefix}{text[:max_text_len]:<{max_text_len}}{hint}"
                self.write_at(0, content_start_row + i, display_line)

        _render()

        while True:
            key = _get_key()
            if key is None:
                continue

            if key == scroll_down_key:
                if cursor < total - 1:
                    cursor += 1
                    # Scroll window down if cursor moves past visible area
                    if cursor >= offset + visible_rows:
                        offset += 1
                    _render()

            elif key == scroll_up_key:
                if cursor > 0:
                    cursor -= 1
                    # Scroll window up if cursor moves above visible area
                    if cursor < offset:
                        offset -= 1
                    _render()

            elif key == select_key:
                return cursor

            elif key == exit_key:
                return None

    # -------------------------------------------------------------------------
    # END SCROLLABLE DISPLAY
    # -------------------------------------------------------------------------

    def show_menu(
        self,
        title: str,
        options: List[str],
        clear_first: bool = True
    ) -> None:
        """
        Display a static menu (no scrolling).

        For menus longer than the available rows, use show_scrollable_menu().

        Args:
            title: Menu title (row 0)
            options: List of menu options (remaining rows)
            clear_first: Clear display first
        
        Example:
            lcd.show_menu("HOME MENU", [
                "[1] Scan Answer Key",
                "[2] Check Sheets",
                "[3] Settings"
            ])
        """
        if clear_first:
            self.clear()
        
        # Write title
        self.write_at(0, 0, title.center(self.cols))
        
        # Write separator (if 20x4)
        if self.rows >= 2:
            self.write_at(0, 1, "=" * self.cols)
        
        # Write options
        start_row = 2 if self.rows >= 4 else 1
        for i, option in enumerate(options):
            if start_row + i < self.rows:
                self.write_at(0, start_row + i, option[:self.cols])
    
    def backlight_on(self) -> None:
        """Turn backlight on"""
        self.backlight_state = self.LCD_BACKLIGHT
        self._write_command(0)
    
    def backlight_off(self) -> None:
        """Turn backlight off"""
        self.backlight_state = self.LCD_NOBACKLIGHT
        self._write_command(0)
    
    def display_on(self) -> None:
        """Turn display on"""
        self._write_command(
            self.LCD_DISPLAYCONTROL |
            self.LCD_DISPLAYON
        )
    
    def display_off(self) -> None:
        """Turn display off"""
        self._write_command(
            self.LCD_DISPLAYCONTROL |
            self.LCD_DISPLAYOFF
        )
    
    def cursor_on(self) -> None:
        """Show cursor"""
        self._write_command(
            self.LCD_DISPLAYCONTROL |
            self.LCD_DISPLAYON |
            self.LCD_CURSORON
        )
    
    def cursor_off(self) -> None:
        """Hide cursor"""
        self._write_command(
            self.LCD_DISPLAYCONTROL |
            self.LCD_DISPLAYON |
            self.LCD_CURSOROFF
        )
    
    def blink_on(self) -> None:
        """Enable cursor blink"""
        self._write_command(
            self.LCD_DISPLAYCONTROL |
            self.LCD_DISPLAYON |
            self.LCD_CURSORON |
            self.LCD_BLINKON
        )
    
    def blink_off(self) -> None:
        """Disable cursor blink"""
        self._write_command(
            self.LCD_DISPLAYCONTROL |
            self.LCD_DISPLAYON |
            self.LCD_CURSORON |
            self.LCD_BLINKOFF
        )
    
    def scroll_left(self) -> None:
        """Scroll display left"""
        self._write_command(
            self.LCD_CURSORSHIFT |
            self.LCD_DISPLAYMOVE |
            self.LCD_MOVELEFT
        )
    
    def scroll_right(self) -> None:
        """Scroll display right"""
        self._write_command(
            self.LCD_CURSORSHIFT |
            self.LCD_DISPLAYMOVE |
            self.LCD_MOVERIGHT
        )
    
    def create_char(self, location: int, charmap: List[int]) -> None:
        """
        Create custom character.
        
        Args:
            location: Character location (0-7)
            charmap: List of 8 bytes defining 5x8 character
        
        Example:
            # Create heart symbol
            heart = [
                0b00000,
                0b01010,
                0b11111,
                0b11111,
                0b01110,
                0b00100,
                0b00000,
                0b00000
            ]
            lcd.create_char(0, heart)
            lcd.write(chr(0))  # Display heart
        """
        location &= 0x7  # Only 0-7 locations
        self._write_command(self.LCD_SETCGRAMADDR | (location << 3))
        for byte in charmap:
            self._write_data(byte)
    
    def get_size(self) -> Tuple[int, int]:
        """Get LCD size (cols, rows)"""
        return (self.cols, self.rows)
    
    def close(self) -> None:
        """Close I2C connection"""
        self.clear()
        self.backlight_off()
        self.bus.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def __repr__(self) -> str:
        return f"LCD_I2C(address=0x{self.address:02X}, size={self.cols}x{self.rows})"


# ===== UTILITY FUNCTIONS =====

def detect_i2c_address(bus: int = 1) -> List[int]:
    """
    Scan I2C bus for devices.
    
    Args:
        bus: I2C bus number
    
    Returns:
        List of detected I2C addresses
    """
    devices = []
    try:
        i2c_bus = smbus2.SMBus(bus)
        for address in range(0x03, 0x78):
            try:
                i2c_bus.read_byte(address)
                devices.append(address)
            except:
                pass
        i2c_bus.close()
    except Exception as e:
        print(f"Error scanning I2C bus: {e}")
    
    return devices


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    print("="*70)
    print("Example 1: Detect I2C LCD address")
    print("="*70)
    
    print("Scanning I2C bus...")
    devices = detect_i2c_address()
    
    if devices:
        print(f"Found {len(devices)} device(s):")
        for addr in devices:
            print(f"  - 0x{addr:02X}")
    else:
        print("No I2C devices found")
    
    # Use detected address or default
    lcd_address = devices[0] if devices else 0x27
    
    
    print("\n" + "="*70)
    print("Example 2: Basic text display")
    print("="*70)
    
    lcd = LCD_I2C(address=lcd_address, size=LCDSize.LCD_20x4)
    
    # Simple text
    lcd.show("Hello, World!")
    time.sleep(2)
    
    # Clear and show new text
    lcd.show("RaspberryPi Grading")
    time.sleep(2)
    
    
    print("\n" + "="*70)
    print("Example 3: Multi-line display")
    print("="*70)
    
    lcd.show([
        "CheckMe System",
        "Version 1.0",
        "Ready to scan",
        "Press key to start"
    ])
    time.sleep(3)
    
    
    print("\n" + "="*70)
    print("Example 4: Temporary messages")
    print("="*70)
    
    lcd.show("Loading...", duration=2)
    # Auto-clears after 2 seconds
    
    lcd.show("Scan complete!", duration=2)
    
    
    print("\n" + "="*70)
    print("Example 5: Centered text")
    print("="*70)
    
    lcd.show("MAIN MENU", center=True)
    time.sleep(2)
    
    
    print("\n" + "="*70)
    print("Example 6: Menu display")
    print("="*70)
    
    lcd.show_menu("HOME MENU", [
        "[1] Scan Ans Key",
        "[2] Check Sheets",
        "[3] Settings"
    ])
    time.sleep(3)
    
    
    print("\n" + "="*70)
    print("Example 7: Positioned text")
    print("="*70)
    
    lcd.clear()
    lcd.write_at(0, 0, "Top Left")
    lcd.write_at(10, 1, "Mid Right")
    lcd.write_at(0, 3, "Bottom Left")
    time.sleep(3)
    
    
    print("\n" + "="*70)
    print("Example 8: Login screen")
    print("="*70)
    
    lcd.show([
        "    LOGIN REQUIRED",
        "====================",
        "Open mobile app",
        "Enter code: ________"
    ])
    time.sleep(3)
    
    
    print("\n" + "="*70)
    print("Example 9: Progress indicator")
    print("="*70)
    
    lcd.clear()
    lcd.write_at(0, 0, "Uploading images...")
    
    # Simulate progress
    for i in range(21):
        progress = "█" * i
        lcd.write_at(0, 2, f"[{progress:<20}]")
        lcd.write_at(0, 3, f"{i*5}%")
        time.sleep(0.2)
    
    lcd.show("Upload complete!", duration=2)
    
    
    print("\n" + "="*70)
    print("Example 10: Custom characters")
    print("="*70)
    
    # Create check mark symbol
    checkmark = [
        0b00000,
        0b00001,
        0b00011,
        0b10110,
        0b11100,
        0b01000,
        0b00000,
        0b00000
    ]
    
    # Create X symbol
    x_mark = [
        0b00000,
        0b10001,
        0b01010,
        0b00100,
        0b01010,
        0b10001,
        0b00000,
        0b00000
    ]
    
    lcd.create_char(0, checkmark)
    lcd.create_char(1, x_mark)
    
    lcd.clear()
    lcd.write_at(0, 0, "Q1: ")
    lcd.write(chr(0))  # Display checkmark
    lcd.write_at(10, 0, "Q2: ")
    lcd.write(chr(1))  # Display X
    
    lcd.write_at(0, 1, "Correct")
    lcd.write_at(10, 1, "Wrong")
    time.sleep(3)
    
    
    print("\n" + "="*70)
    print("Example 11: Backlight control")
    print("="*70)
    
    lcd.show("Backlight test")
    
    for i in range(3):
        time.sleep(1)
        lcd.backlight_off()
        time.sleep(0.5)
        lcd.backlight_on()
    
    
    print("\n" + "="*70)
    print("Example 12: Integration with keypad")
    print("="*70)
    
    def show_pin_entry():
        """Simulate PIN entry with LCD"""
        lcd.clear()
        lcd.write_at(0, 0, "Enter 4-digit PIN:")
        lcd.write_at(0, 2, "PIN: ")
        
        # Simulate entering PIN
        pin = ""
        for digit in "1234":
            pin += digit
            masked = "*" * len(pin)
            lcd.write_at(5, 2, masked + "    ")
            time.sleep(0.5)
        
        lcd.write_at(0, 3, "Verifying...")
        time.sleep(1)
        
        lcd.show([
            "PIN Accepted!",
            "",
            "Welcome back",
            "Prof. Smith"
        ], duration=2)
    
    show_pin_entry()
    
    
    print("\n" + "="*70)
    print("Example 13: Context manager usage")
    print("="*70)
    
    with LCD_I2C(address=lcd_address, size=LCDSize.LCD_20x4) as display:
        display.show("Using context manager")
        time.sleep(2)
    # Automatically closed and backlight off
    
    
    print("\n" + "="*70)
    print("Example 14: Student score display")
    print("="*70)
    
    lcd.show([
        "Student: STUD-001",
        "Score: 45/50",
        "",
        "Press # to continue"
    ])
    time.sleep(3)


    # =========================================================================
    # NEW — Example 15: Scrollable list (more lines than LCD rows)
    # =========================================================================
    print("\n" + "="*70)
    print("Example 15: Scrollable list  (2=up  8=down  #=exit)")
    print("="*70)
    print("This uses terminal input as a stand-in for a real keypad.")
    print("On your Pi, pass  keypad=<your_keypad_object>  instead.")

    long_list = [
        "Alice  – 48/50",
        "Bob    – 45/50",
        "Carol  – 50/50",
        "Dave   – 40/50",
        "Eve    – 47/50",
        "Frank  – 43/50",
        "Grace  – 49/50",
        "Henry  – 38/50",
        "Iris   – 46/50",
        "Jack   – 42/50",
    ]

    lcd.show_scrollable(
        lines=long_list,
        title="STUDENT SCORES",
        scroll_up_key="2",
        scroll_down_key="8",
        exit_key="#",
        # keypad=kp   ← uncomment and pass your keypad object on real hardware
    )


    # =========================================================================
    # NEW — Example 16: Scrollable interactive menu with cursor
    # =========================================================================
    print("\n" + "="*70)
    print("Example 16: Scrollable menu  (2=up  8=down  *=select  #=exit)")
    print("="*70)

    menu_options = [
        "Scan Answer Key",
        "Check Sheets",
        "View Scores",
        "Export CSV",
        "Settings",
        "About",
        "Logout",
    ]

    selected = lcd.show_scrollable_menu(
        title="MAIN MENU",
        options=menu_options,
        scroll_up_key="2",
        scroll_down_key="8",
        select_key="*",
        exit_key="#",
        # keypad=kp   ← uncomment and pass your keypad object on real hardware
    )

    if selected is not None:
        lcd.show([
            "Selected:",
            menu_options[selected][:20],
            "",
            "Press # to continue"
        ], duration=3)
        print(f"User selected [{selected}]: {menu_options[selected]}")
    else:
        lcd.show("Cancelled.", duration=2)
        print("User cancelled menu.")


    print("\n" + "="*70)
    print("Cleanup")
    print("="*70)
    
    lcd.close()
    print("✅ LCD closed")
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)