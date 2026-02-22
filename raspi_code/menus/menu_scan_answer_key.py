"""
Menu Flow: Scan Answer Key
Handles the full scan → upload → Gemini OCR → save to RTDB flow for answer keys.
"""

import time

from services.logger import get_logger
from services.utils import delete_files, normalize_path, join_and_ensure_path, delete_file
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
FIREBASE_RTDB_REFERENCE = os.getenv("FIREBASE_RTDB_REFERENCE")

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
    Returns True if done (success or exit), False means failed.
    """
    from services.cloudinary_client import ImageUploader
    from services.gemini_client import gemini_with_retry
    from services.firebase_rtdb_client import FirebaseRTDB
    from services.smart_collage import SmartCollage

    upload_and_save_status  = False
    image_urls              = None
    image_public_ids        = None
    image_to_send_gemini    = None
    assessment_uid          = None
    answer_key              = None
    collage_path            = None
    
    while True:
        # =================================================================
        # STEP 1: Upload to Cloudinary
        # =================================================================
        if image_urls is None:  # Only upload if not done yet
            lcd.show(["Uploading...", "Please wait."])
            
            try:
                uploader = ImageUploader(
                    cloud_name  = CLOUDINARY_NAME,
                    api_key     = CLOUDINARY_API_KEY,
                    api_secret  = CLOUDINARY_API_SECRET,
                    folder      = normalize_path(target_path)
                )
                
                if len(scanned_files) > 1:
                    results = uploader.upload_batch(scanned_files)
                else:
                    results = [uploader.upload_single(scanned_files[0])]
                
                image_urls = [r["url"] for r in results]
                image_public_ids = [r["public_id"] for r in results]
                
                log(f"Uploaded {len(image_urls)} images", "info")
                
            except Exception as e:
                log(f"Upload error: {e}", "error")
                
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
                    continue  # Retry upload
                else:
                    delete_files(scanned_files)
                    break
        
        # =================================================================
        # STEP 2: Create Collage (if needed)
        # =================================================================
        if image_to_send_gemini is None:  # Only collage if not done yet
            lcd.show(["Processing images..."])
            
            try:
                if len(scanned_files) > 1:
                    collage_builder         = SmartCollage(scanned_files)
                    image_to_send_gemini    = collage_builder.create_collage()
                    
                    # Optionally save collage
                    if collage_save_to_local:
                        collage_path = join_and_ensure_path(
                            target_path,
                            f"collage_{int(time.time())}.png"
                        )
                        collage_builder.save(image_to_send_gemini, collage_path)
                else:
                    image_to_send_gemini = scanned_files[0]
                
            except Exception as e:
                log(f"Collage error: {e}", "error")
                
                choice = lcd.show_scrollable_menu(
                    title           = "COLLAGE FAILED",
                    options         = ["Retry", "Exit"],
                    scroll_up_key   = "2",
                    scroll_down_key = "8",
                    select_key      = "*",
                    exit_key        = "#",
                    get_key_func    = keypad.read_key
                )
                
                if choice == 0:
                    continue  # Retry collage
                else:
                    delete_files(scanned_files)
                    break
        
        # =================================================================
        # STEP 3: Gemini OCR Extraction
        # =================================================================
        if assessment_uid is None:  # Only extract if not done yet
            lcd.show(["Processing with", "Gemini OCR..."])
            
            try:
                raw_result = gemini_with_retry(
                    api_key         = GEMINI_API_KEY,
                    image_path      = image_to_send_gemini,
                    prompt          = answer_key_prompt(total_number_of_questions=total_questions),
                    model           = GEMINI_MODEL,
                    prefer_method   = "sdk"
                )
                
                if raw_result is None:
                    raise Exception("Gemini returned None")
                
                data            = sanitize_gemini_json(raw_result)
                assessment_uid  = data.get("assessment_uid")
                answer_key      = data.get("answers")
                
                if assessment_uid is None and answer_key is None:
                    log(
                        f"\nAssessment UID or Answers not found.\n"
                        f"assessment_uid    : {assessment_uid}\n"
                        f"answer_key        : {answer_key}\n"
                        f"Bad gemini response.", 
                        "error"
                    )
                    raise Exception(
                        f"\nAssessment UID or Answers not found.\n"
                        f"assessment_uid    : {assessment_uid}\n"
                        f"answer_key        : {answer_key}\n"
                        f"Bad gemini response."
                    )
                
                
            except Exception as e:
                log(f"Gemini error: {e}", "error")
                
                choice = lcd.show_scrollable_menu(
                    title           = "EXTRACTION FAILED",
                    options         = ["Retry", "Exit"],
                    scroll_up_key   = "2",
                    scroll_down_key = "8",
                    select_key      = "*",
                    exit_key        = "#",
                    get_key_func    = keypad.read_key
                )
                
                if choice == 0:
                    continue  # Retry extraction
                else:
                    # Cleanup Cloudinary uploads
                    if image_public_ids:
                        try:
                            uploader.delete_batch(image_public_ids)
                        except:
                            pass
                    delete_files(scanned_files)
                    break
        
        # =================================================================
        # STEP 4: Save to Firebase RTDB
        # =================================================================
        lcd.show(["Saving to database..."])
        
        try:
            firebase = FirebaseRTDB(database_url=FIREBASE_RTDB_REFERENCE)
            
            firebase.save_answer_key(
                assessment_uid  = assessment_uid,
                answer_key      = answer_key,
                total_questions = total_questions,
                image_urls      = image_urls,
                teacher_uid     = user.teacher_uid
            )
            
            log(f"Saved to RTDB: {assessment_uid}", "info")
            lcd.show(["Saved!", f"ID: {assessment_uid}"], duration=3)
            
            # Cleanup local files
            delete_files(scanned_files)
            
            return True  # Success - exit to menu
            
        except Exception as e:
            log(f"Firebase error: {e}", "error")
            
            choice = lcd.show_scrollable_menu(
                title           = "DATABASE FAILED",
                options         = ["Retry", "Exit"],
                scroll_up_key   = "2",
                scroll_down_key = "8",
                select_key      = "*",
                exit_key        = "#",
                get_key_func    = keypad.read_key
            )
            
            if choice == 0:
                continue  # Retry save
            else:
                delete_files(scanned_files)
                upload_and_save_status = False
                break
        
        upload_and_save_status = True
        break
            
    if collage_path and delete_local_collage:
        delete_file(collage_path)
    
    return upload_and_save_status