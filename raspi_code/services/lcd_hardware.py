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
    
    def show_menu(
        self,
        title: str,
        options: List[str],
        clear_first: bool = True
    ) -> None:
        """
        Display a menu.
        
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
    
    
    print("\n" + "="*70)
    print("Cleanup")
    print("="*70)
    
    lcd.close()
    print("✅ LCD closed")
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)