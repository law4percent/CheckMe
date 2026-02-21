import time

from services.keypad_hardware import Keypad3x4
from services.auth import TeacherAuth
from services.lcd_hardware import detect_i2c_address, LCD_I2C, LCDSize
from services.logger import get_logger


log = get_logger("main.py")

def main():
    try:
        # LCD setup
        lcd_address = find_i2c_address()
        lcd = LCD_I2C(address=lcd_address, size=LCDSize.LCD_16x2)
        
        # Keypad setup
        keypad = Keypad3x4()
        
        # Authentication Setup
        auth = TeacherAuth()
    except Exception as e:
        log(f"Error occur during setup: {e}", "error")
    
    
    
    lcd.show("Initilaizing...", duration=3)
    
    # STEP 1: Authenticating
    if not auth.is_authenticated():
        lcd.show(
            content   = [
              "Unauthorized", 
              "system..."
            ],
            duration  = 2
        )
        lcd.show("LOGIN REQUIRED", duration=3)
        
        while True:
            lcd.show("Enter 8-digit PIN:")
            
            temp_code = keypad.read_input(
                length          = 8,
                valid_keys      = ['0','1','2','3','4','5','6','7','8','9'],
                echo_callback   = lambda text: lcd.write_at(0, 1, f"{'*' * len(text)}"),
                timeout         = 60 * 5
            )
            if temp_code == None:
                lcd.show("LOGIN REQUIRED", duration=3)
                continue
            
            success, message = auth.login_with_temp_code(temp_code)
            if not success:
                lcd.show("LOGIN REQUIRED", duration=3)
                log(message, log_type="warning")
                continue
            
            break
        
    user = auth.get_current_user()
    
    # 
    user.username
    user.teacher_uid




def find_i2c_address():
    log("Scanning I2C bus...", log_type="info")
    devices = detect_i2c_address()
    
    if devices:
        log(f"Found {len(devices)} device(s):", log_type="info")
        for addr in devices:
            log(f"  - 0x{addr:02X}")
    else:
        log("No I2C devices found", log_type="info")
    
    return devices[0] if devices else 0x27


if __name__ == "__main__":
    main()