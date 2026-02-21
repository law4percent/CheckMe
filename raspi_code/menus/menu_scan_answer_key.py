"""
Menu Flow: Scan Answer Key
Handles the full scan → upload → Gemini OCR → save to RTDB flow for answer keys.
"""

import time
import os

from services.logger import get_logger
from services.utils import delete_local_files
from services.l3210_scanner_hardware import L3210Scanner

log = get_logger("menu_scan_answer_key.py")


def run(lcd, keypad, user) -> None:
    """
    Entry point for the Scan Answer Key flow.

    Args:
        lcd     : LCD_I2C instance
        keypad  : Keypad3x4 instance
        user    : Authenticated user object (user.teacher_uid)
    """
    answer_key_menu_options = [
        "Scan",
        "Done & Save",
        "Cancel",
    ]

    # =========================================================================
    # Step 1: Ask for total number of questions
    # =========================================================================
    lcd.show(["Enter total no.", "of questions:"])

    exact_total_number_of_questions = keypad.read_input(
        length      = 2,        # up to 99 questions
        valid_keys  = ['0','1','2','3','4','5','6','7','8','9'],
        end_key     = '#',
        timeout     = 60 * 5
    )

    if exact_total_number_of_questions is None:
        return  # Back to Main Menu

    scanned_files = []
    page_number   = 1

    # =========================================================================
    # Step 2: Scan Answer Key loop
    # =========================================================================
    while True:
        selected = lcd.show_scrollable_menu(
            title           = "SCAN ANSWER KEY",
            options         = answer_key_menu_options,
            scroll_up_key   = "2",
            scroll_down_key = "8",
            select_key      = "*",
            exit_key        = "#",
            get_key_func    = keypad.read_key
        )

        # =====================================================================
        # [0] Scan
        # =====================================================================
        if selected == 0:
            _do_scan(lcd, keypad, scanned_files, page_number)
            page_number = len(scanned_files) + 1

        # =====================================================================
        # [1] Done & Save
        # =====================================================================
        elif selected == 1:
            if not scanned_files:
                lcd.show(["No scans yet!", "Scan first."], duration=2)
                continue

            done = _do_upload_and_save(
                lcd, keypad, user,
                scanned_files,
                int(exact_total_number_of_questions)
            )

            if done:
                break  # back to Main Menu

        # =====================================================================
        # [2] Cancel
        # =====================================================================
        elif selected == 2:
            if scanned_files:
                delete_local_files(scanned_files)
            lcd.show("Cancelled.", duration=2)
            break  # back to Main Menu


# =============================================================================
# Private helpers
# =============================================================================

def _do_scan(lcd, keypad, scanned_files: list, page_number: int) -> None:
    """Trigger the scanner and append the result to scanned_files."""
    scanner = L3210Scanner()

    lcd.show(["Place document,", "then press #"])
    keypad.wait_for_key(valid_keys=['#'])

    lcd.show(["Scanning page", f"{page_number}..."])

    try:
        filename = scanner.scan()   # expected to return the saved filename

        time.sleep(10)              # 10s debounce / scanner settle time

        scanned_files.append(filename)

        lcd.show(
            [f"Page {page_number} scanned!", f"Total: {len(scanned_files)}"],
            duration=2
        )

    except Exception as e:
        log(f"Scan error: {e}", "error")
        lcd.show(["Scan failed!", "Try again."], duration=2)


def _do_upload_and_save(lcd, keypad, user, scanned_files: list, total_questions: int) -> bool:
    """
    Upload images → Gemini OCR → save to RTDB.

    Returns:
        True  if the full flow completed (success or user chose to exit).
        False if the user chose to re-upload (caller should stay in loop).
    """
    from services.cloudinary_service import CloudinaryService
    from services.gemini_service import GeminiService
    from services.firebase_service import FirebaseService

    while True:
        # -----------------------------------------------------------------
        # Upload to Cloudinary
        # -----------------------------------------------------------------
        lcd.show(["Uploading...", "Please wait."])

        try:
            cloudinary = CloudinaryService()

            if len(scanned_files) > 1:
                from services.image_utils import create_collage
                image_to_send = create_collage(scanned_files)
            else:
                image_to_send = scanned_files[0]

            upload_url      = cloudinary.upload(image_to_send)
            upload_success  = upload_url is not None

        except Exception as e:
            log(f"Upload error: {e}", "error")
            upload_success = False

        # -----------------------------------------------------------------
        # Upload failed → ask user
        # -----------------------------------------------------------------
        if not upload_success:
            choice = lcd.show_scrollable_menu(
                title           = "UPLOAD FAILED",
                options         = ["Re-upload", "Exit"],
                scroll_up_key   = "2",
                scroll_down_key = "8",
                select_key      = "*",
                exit_key        = "#",
                get_key_func    = keypad.read_key
            )

            if choice == 0:
                continue                        # retry upload
            else:
                delete_local_files(scanned_files)
                return True                     # exit to Main Menu

        # -----------------------------------------------------------------
        # Gemini OCR
        # -----------------------------------------------------------------
        lcd.show(["Processing with", "Gemini OCR..."])

        try:
            gemini = GeminiService()
            result = gemini.extract_answer_key(
                image_url       = upload_url,
                total_questions = total_questions
            )

            assessment_uid  = result.get("assessment_uid")
            answer_key      = result.get("answer_key")

        except Exception as e:
            log(f"Gemini error: {e}", "error")
            lcd.show(["Gemini failed!", "Retrying..."], duration=2)
            continue  # retry from upload

        # -----------------------------------------------------------------
        # Save to RTDB
        # -----------------------------------------------------------------
        try:
            firebase = FirebaseService()
            firebase.save_answer_key(
                teacher_uid     = user.teacher_uid,
                assessment_uid  = assessment_uid,
                answer_key      = answer_key
            )

            lcd.show(["Saved!", f"ID:{assessment_uid}"], duration=3)

        except Exception as e:
            log(f"Firebase error: {e}", "error")
            lcd.show(["Save failed!", "Try again."], duration=2)
            continue  # retry from upload

        # -----------------------------------------------------------------
        # Cleanup
        # -----------------------------------------------------------------
        delete_local_files(scanned_files)
        return True  # done → back to Main Menu