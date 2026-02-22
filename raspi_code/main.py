import time

from services.keypad_hardware import Keypad3x4
from services.auth import TeacherAuth
from services.lcd_hardware import detect_i2c_address, LCD_I2C, LCDSize
from services.logger import get_logger
from services.utils import normalize_path

import menus.menu_scan_answer_key   as menu_scan_answer_key
import menus.menu_check_answer_sheets as menu_check_answer_sheets

log = get_logger("main.py")

import os
from dotenv import load_dotenv
load_dotenv(normalize_path("config/.env"))

USER_CREDENTIALS_FILE           = os.getenv("USER_CREDENTIALS_FILE")
FIREBASE_CREDENTIALS_PATH       = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_RTDB_BASE_REFERENCE    = os.getenv("FIREBASE_RTDB_BASE_REFERENCE")


def main():
    try:
        # LCD setup
        lcd_address = find_i2c_address()
        lcd         = LCD_I2C(address=lcd_address, size=LCDSize.LCD_16x2)

        # Keypad setup
        keypad = Keypad3x4()

        # Authentication setup
        auth = TeacherAuth(
            credentials_file            = normalize_path(USER_CREDENTIALS_FILE),
            firebase_credentials_path   = normalize_path(FIREBASE_CREDENTIALS_PATH), 
            firebase_url                = FIREBASE_RTDB_BASE_REFERENCE
        )
    except Exception as e:
        log(f"Error occurred during setup: {e}", "error")
        return

    lcd.show("Initializing...", duration=3)

    # =========================================================================
    # STEP 1: Authentication
    # =========================================================================
    if not auth.is_authenticated():
        lcd.show(["Unauthorized", "system..."], duration=2)

        while True:
            lcd.show("LOGIN REQUIRED", duration=3)
            lcd.show("Enter 8-digit PIN:")

            temp_code = keypad.read_input(
                length      = 8,
                valid_keys  = ['0','1','2','3','4','5','6','7','8','9'],
                echo_callback = lambda text: lcd.write_at(0, 1, f"{'*' * len(text)}"),
                timeout     = 60 * 5
            )

            if temp_code is None:
                continue

            success, message = auth.login_with_temp_code(temp_code)
            if not success:
                log(message, log_type="warning")
                lcd.show(["Login failed!", "Try again."], duration=2)
                continue

            break

    user = auth.get_current_user()

    # =========================================================================
    # STEP 2: Main Menu loop
    # =========================================================================
    main_menu_options = [
        "Scan Answer Key",
        "Check Sheets",
        "Settings",
    ]

    while True:
        selected = lcd.show_scrollable_menu(
            title           = "MAIN MENU",
            options         = main_menu_options,
            scroll_up_key   = "2",
            scroll_down_key = "8",
            select_key      = "*",
            exit_key        = "#",
            get_key_func    = keypad.read_key
        )

        # =====================================================================
        # [0] Scan Answer Key
        # =====================================================================
        if selected == 0:
            menu_scan_answer_key.run(lcd, keypad, user)

        # =====================================================================
        # [1] Check Answer Sheets
        # =====================================================================
        elif selected == 1:
            menu_check_answer_sheets.run(lcd, keypad, user)

        # =====================================================================
        # [2] Settings
        # =====================================================================
        elif selected == 2:
            _run_settings(lcd, keypad, auth)


def _run_settings(lcd, keypad, auth) -> None:
    """Settings menu: Logout / Shutdown / Back"""
    settings_options = [
        "Logout",
        "Shutdown",
        "Back",
    ]

    while True:
        selected = lcd.show_scrollable_menu(
            title           = "SETTINGS",
            options         = settings_options,
            scroll_up_key   = "2",
            scroll_down_key = "8",
            select_key      = "*",
            exit_key        = "#",
            get_key_func    = keypad.read_key
        )

        if selected == 0:   # Logout
            auth.logout()
            lcd.show("Logged out.", duration=2)
            # Re-enter main() effectively by restarting — or handle in caller
            import os
            os.execv(__import__('sys').executable, [__import__('sys').executable] + __import__('sys').argv)

        elif selected == 1:  # Shutdown
            lcd.show(["Confirm shutdown?", "# Yes  * No"])
            confirmed = keypad.confirm_action(confirm_key='#', cancel_key='*', timeout=10)
            if confirmed:
                lcd.show("Shutting down...", duration=2)
                lcd.close()
                os.system("sudo shutdown -h now")
            # else stay in settings

        elif selected == 2 or selected is None:  # Back
            return


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