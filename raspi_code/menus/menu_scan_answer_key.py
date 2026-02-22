"""
Menu Flow: Scan Answer Key
Handles the full scan → upload → Gemini OCR → save to RTDB flow for answer keys.
"""

import time

from services.logger import get_logger
from services.utils import delete_files, normalize_path, join_and_ensure_path
from services.sanitizer import sanitize_gemini_json
from services.l3210_scanner_hardware import L3210Scanner
from services.prompts import answer_key_prompt

import time
import os
from dotenv import load_dotenv
load_dotenv(normalize_path("config/.env"))

GEMINI_API_KEY          = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL            = os.getenv("GEMINI_MODEL")
CLOUDINARY_NAME         = os.getenv("CLOUDINARY_NAME")
CLOUDINARY_API_KEY      = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET   = os.getenv("CLOUDINARY_API_SECRET")

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

def _do_scan(
        lcd, 
        keypad, 
        scanned_files   : list, 
        page_number     : int, 
        debounce        : int = 3
    ) -> None:
    """Trigger the scanner and append the result to scanned_files."""
    scanner = L3210Scanner()

    lcd.show(["Place document,", "then press #"])
    keypad.wait_for_key(valid_keys=['#'])

    lcd.show(["Scanning page", f"{page_number}..."])

    try:
        filename = scanner.scan(target_directory="scans/answer_keys")
        time.sleep(debounce)

        scanned_files.append(filename)

        lcd.show(
            [f"Page {page_number} scanned!", f"Total: {len(scanned_files)}"],
            duration=2
        )

    except Exception as e:
        log(f"Scan error: {e}", "error")
        lcd.show(["Scan failed!", "Try again."], duration=2)


def _do_upload_and_save(
        lcd, 
        keypad, 
        user, 
        scanned_files           : list, 
        total_questions         : int, 
        collage_save_to_local   : bool  = True, 
        delete_local_collage    : bool  = False,
        target_path             : str   = "scans/answer_keys"
    ) -> bool:
    """
    Upload images → Gemini OCR → save to RTDB.

    Returns:
        True  if the full flow completed (success or user chose to exit).
        False if the user chose to re-upload (caller should stay in loop).
    """
    from services.cloudinary_client import ImageUploader
    from services.gemini_client import gemini_with_retry
    from services.firebase_rtdb_client import FirebaseRTDB
    from services.smart_collage import SmartCollage

    skip_image_reupload     = False
    skip_image_recollaged   = False
    skip_image_extraction   = False
    cloudinary_image_upload_result = None
    
    while True:
        # -----------------------------------------------------------------
        # A.1 Upload to Cloudinary
        # -----------------------------------------------------------------
        lcd.show(["Uploading...", "Please wait."])
        if not skip_image_reupload:
            try:
                image_uploader = ImageUploader(
                    cloud_name  = CLOUDINARY_NAME, 
                    api_key     = CLOUDINARY_API_KEY,
                    api_secret  = CLOUDINARY_API_SECRET
                )

                if len(scanned_files) > 1:
                    # Batch upload
                    cloudinary_image_upload_result = image_uploader.upload_batch(scanned_files)
                    
                    urls = [r["url"] for r in cloudinary_image_upload_result]
                else:
                    # Single upload
                    cloudinary_image_upload_result = image_uploader.upload_single("image.jpg")
                    url = cloudinary_image_upload_result["url"]
                
                upload_success  = url is not None or urls is not None

            except Exception as e:
                log(f"Upload error: {e}", "error")
                upload_success = False

        # -----------------------------------------------------------------
        # A.2 Upload failed → ask user
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
                delete_files(scanned_files)
                return True                     # exit to Main Menu
        
        skip_image_reupload = True
        
        # -----------------------------------------------------------------
        # B.1 Collage images
        # -----------------------------------------------------------------
        if not skip_image_recollaged:
            try:
                if len(scanned_files) > 1:
                    collage_builder         = SmartCollage(scanned_files)
                    image_to_send_gemini    = collage_builder.create_collage()
                else:
                    image_to_send_gemini = scanned_files[0]
                
            except Exception as e:
                log(f"Collage error: {e}", "error")
                collage_success = False

            finally:
                if collage_save_to_local:
                    collage_builder.save(
                        raw_collage = image_to_send_gemini,
                        output_path = normalize_path(f"{target_path}/collage_at_{time.localtime}.png")
                    )
                collage_success = True
        
        # -----------------------------------------------------------------
        # B.2 Collaged failed → ask user
        # -----------------------------------------------------------------
        if not collage_success:
            choice = lcd.show_scrollable_menu(
                title           = "Collage FAILED",
                options         = ["Re-collage", "Exit"],
                scroll_up_key   = "2",
                scroll_down_key = "8",
                select_key      = "*",
                exit_key        = "#",
                get_key_func    = keypad.read_key
            )

            if choice == 0:
                continue                        # retry upload
            else:
                delete_files(scanned_files)
                return True                     # exit to Main Menu

        skip_image_recollaged = True
        
        # -----------------------------------------------------------------
        # C.1 Gemini OCR
        # -----------------------------------------------------------------
        lcd.show(["Processing with", "Gemini OCR..."])
        if not skip_image_extraction:
            try:
                extraction_result = gemini_with_retry(
                    api_key         = GEMINI_API_KEY,
                    image_path      = image_to_send_gemini, # it is a raw image
                    prompt          = answer_key_prompt(total_number_of_questions=total_questions),
                    model           = GEMINI_MODEL,
                    prefer_method   = "sdk"
                )
                answer_key_data = sanitize_gemini_json(extraction_result)
                assessment_uid  = answer_key_data.get("assessment_uid")
                answer_key      = answer_key_data.get("answer_key")

            except Exception as e:
                log(f"Gemini error: {e}", "error")
                lcd.show("Gemini failed!", duration=2)
                # Delete the uploaded images in Cloudinary
                extraction_success = False
            
            finally:
                extraction_success = True

        # -----------------------------------------------------------------
        # C.2 Gemini OCR failed → ask user
        # -----------------------------------------------------------------
        if not extraction_success:
            choice = lcd.show_scrollable_menu(
                title           = "Extraction FAILED",
                options         = ["Re-extract", "Exit"],
                scroll_up_key   = "2",
                scroll_down_key = "8",
                select_key      = "*",
                exit_key        = "#",
                get_key_func    = keypad.read_key
            )

            if choice == 0:
                continue                        # retry upload
            else:
                delete_files(scanned_files)
                return True                     # exit to Main Menu

        skip_image_extraction = True
        
        # -----------------------------------------------------------------
        # D.1 Save to RTDB
        # -----------------------------------------------------------------
        try:
            firebase = FirebaseRTDB()
            firebase.save_answer_key(
                teacher_uid     = user.teacher_uid,
                assessment_uid  = assessment_uid,
                answer_key      = answer_key
            )

            lcd.show(["Saved!", f"ID:{assessment_uid}"], duration=3)

        except Exception as e:
            log(f"Firebase error: {e}", "error")
            lcd.show(["RTDB failed!", "Try again."], duration=2)
            rtdb_success = False
        
        finally:
            rtdb_success = True
        
        # -----------------------------------------------------------------
        # D.2 Save to RTDB failed → ask user
        # -----------------------------------------------------------------
        if not rtdb_success:
            choice = lcd.show_scrollable_menu(
                title           = "Posting DB FAILED",
                options         = ["Re-posting DB", "Exit"],
                scroll_up_key   = "2",
                scroll_down_key = "8",
                select_key      = "*",
                exit_key        = "#",
                get_key_func    = keypad.read_key
            )

            if choice == 0:
                continue                        # retry upload
            else:
                delete_files(scanned_files)
                return True                     # exit to Main Menu

        # -----------------------------------------------------------------
        # Cleanup
        # -----------------------------------------------------------------
        delete_files(scanned_files)
        return True  # done → back to Main Menu