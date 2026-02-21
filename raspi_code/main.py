import time

from services.keypad_hardware import Keypad3x4
from services.auth import TeacherAuth
from services.lcd_hardware import detect_i2c_address, LCD_I2C, LCDSize
from services.logger import get_logger
from services.l3210_scanner_hardware import L3210Scanner


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
        log(f"Error occured during setup: {e}", "error")
    
    
    
    lcd.show("Initilaizing...", duration=3)
    
    # =============================
    # STEP 1: Authenticating
    # =============================
    if not auth.is_authenticated():
        lcd.show(
            content   = [
              "Unauthorized", 
              "system..."
            ],
            duration  = 2
        )
        
        while True:
            lcd.show("LOGIN REQUIRED", duration=3)
            lcd.show("Enter 8-digit PIN:")
            
            temp_code = keypad.read_input(
                length          = 8,
                valid_keys      = ['0','1','2','3','4','5','6','7','8','9'],
                echo_callback   = lambda text: lcd.write_at(0, 1, f"{'*' * len(text)}"),
                timeout         = 60 * 5
            )
            if temp_code == None:
                continue
            
            success, message = auth.login_with_temp_code(temp_code)
            if not success:
                log(message, log_type="warning")
                continue
            
            break
        
    user = auth.get_current_user()
    # Sample usage for later
    # user.username
    # user.teacher_uid


    # =============================
    # STEP 2: Home Menu
    # [1] Scan Answer Key
    # [2] Check Answer Sheets
    # [3] Settings
    # =============================
    main_menu_options = [
        "Scan Answer Key",
        "Check Sheets",
        "Settings",
    ]
    answer_key_menu_options = [
        "Scan",
        "Done & Save",
        "Cancel",
    ]
    while True:
        # =============================
        # 2.1 Scan Answer Key Procedure
        # =============================
        selected_option_from_main_menu = lcd.show_scrollable_menu(
            title           = "MAIN MENU",
            options         = main_menu_options,
            scroll_up_key   = "2",
            scroll_down_key = "8",
            select_key      = "*",
            exit_key        = "#",
            keypad          = keypad.read_key
        )
        if selected_option_from_main_menu == 0:
            # =============================
            # 2.1.1 Ask for the total number of questions
            # =============================
            
            exact_total_number_of_questions = keypad.read_input(
                length      = 1,
                valid_keys  = ['0','1','2','3','4','5','6','7','8','9'],
                timeout     = 60 * 5
            )
            if exact_total_number_of_questions == None:
                continue # Back to Main Menu
            
            selected_option_from_answer_key_menu = lcd.show_scrollable_menu(
                title           = "SCAN ANSWER KEY",
                options         = answer_key_menu_options,
                scroll_up_key   = "2",
                scroll_down_key = "8",
                select_key      = "*",
                exit_key        = "#",
                keypad          = keypad.read_key
            )
            
            # =============================
            # 2.1.1.1 Scan
            # =============================
            if selected_option_from_answer_key_menu == 0:
                pass
            
            # =============================
            # 2.1.1.2 Done & Save
            # =============================
            if selected_option_from_answer_key_menu == 1:
                pass
            
            # =============================
            # 2.1.1.3 Cancel
            # =============================
            if selected_option_from_answer_key_menu == 2:
                pass
            
         

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