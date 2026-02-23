"""
Menu Flow: Check Answer Sheets
Handles scan → Gemini OCR → compare with answer key → score → upload → save to RTDB.
"""

from services.logger import get_logger
from services.utils import delete_files, normalize_path, join_and_ensure_path, delete_file
from services.sanitizer import sanitize_gemini_json
from services.l3210_scanner_hardware import L3210Scanner
from services.prompts import answer_sheet_prompt
from services.scorer import compare_answers

import time
import os
from dotenv import load_dotenv
load_dotenv(normalize_path("config/.env"))

GEMINI_API_KEY                  = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL                    = os.getenv("GEMINI_MODEL")
GEMINI_PREFERRED_METHOD         = os.getenv("GEMINI_PREFERRED_METHOD")

CLOUDINARY_NAME                 = os.getenv("CLOUDINARY_NAME")
CLOUDINARY_API_KEY              = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET           = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_ANSWER_SHEETS_PATH   = os.getenv("CLOUDINARY_ANSWER_SHEETS_PATH")

FIREBASE_RTDB_BASE_REFERENCE    = os.getenv("FIREBASE_RTDB_BASE_REFERENCE")
FIREBASE_CREDENTIALS_PATH       = os.getenv("FIREBASE_CREDENTIALS_PATH")

ANSWER_SHEETS_PATH              = os.getenv("ANSWER_SHEETS_PATH")

SCAN_DEBOUNCE_SECONDS   = 3

log = get_logger("menu_check_answer_sheets.py")


def run(lcd, keypad, user) -> None:
    """
    Entry point for the Check Answer Sheets flow.

    Args:
        lcd     : LCD_I2C instance
        keypad  : Keypad3x4 instance
        user    : Authenticated user object (user.teacher_uid)
    """
    from services.firebase_rtdb_client import FirebaseRTDB

    check_sheets_menu_options = [
        "Scan",
        "Done & Save",
        "Cancel",
    ]

    # =========================================================================
    # Step 1: Check if answer keys exist in RTDB
    # =========================================================================
    lcd.show(["Loading answer", "keys..."])

    try:
        firebase    = FirebaseRTDB(
            database_url     = FIREBASE_RTDB_BASE_REFERENCE,
            credentials_path = normalize_path(FIREBASE_CREDENTIALS_PATH)
        )
        answer_keys = firebase.get_answer_keys(teacher_uid=user.teacher_uid)
    except Exception as e:
        log(f"Failed to load answer keys: {e}", log_type="error")
        lcd.show(["Failed to load", "answer keys."], duration=3)
        return

    if not answer_keys:
        lcd.show(["No answer keys!", "Scan key first."], duration=3)
        return

    # =========================================================================
    # Step 2: Let user pick which assessment to check against
    # =========================================================================
    assessment_options = [key["assessment_uid"] for key in answer_keys]
    
    selected_index = lcd.show_scrollable_menu(
        title           = "SELECT ASSESSMENT",
        options         = assessment_options,
        scroll_up_key   = "2",
        scroll_down_key = "8",
        select_key      = "*",
        exit_key        = "#",
        get_key_func    = keypad.read_key
    )

    if selected_index is None:
        return  # User cancelled

    assessment_uid  = assessment_options[selected_index]
    answer_key_data = answer_keys[selected_index]

    lcd.show([f"Assessment:", f"{assessment_uid}"], duration=2)

    scanned_files   = []
    page_number     = 1
    all_scanned_files = []

    assessment_data = firebase.validate_assessment_exists_get_data(assessment_uid, user.teacher_uid)
    if not assessment_data:
        lcd.show([
            "INVALID assesUid",
            "# to continue"
        ])
        keypad.wait_for_key(valid_keys=['#'])
        return # Back to main menu

    # =========================================================================
    # Step 3: Check Answer Sheets loop
    # =========================================================================
    while True:
        selected = lcd.show_scrollable_menu(
            title           = "CHECK SHEETS",
            options         = check_sheets_menu_options,
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
                assessment_uid,
                answer_key_data,
                assessment_data
            )

            if done:
                # Reset state for next student sheet
                all_scanned_files = all_scanned_files + scanned_files
                scanned_files.clear()
                page_number = 1
                # Continue loop for next student
                continue

        # =====================================================================
        # [2] Cancel
        # =====================================================================
        elif selected == 2:
            if all_scanned_files:
                delete_files(all_scanned_files) # might be better to use mulprocessing in future to avoid loading interuption
            lcd.show("Cancelled.", duration=2)
            break  # back to Main Menu


# =============================================================================
# Private helpers
# =============================================================================

def _do_scan(
    lcd,
    keypad,
    scanned_files: list,
    page_number: int,
    debounce: int = SCAN_DEBOUNCE_SECONDS
) -> None:
    """Trigger the scanner and append the result to scanned_files."""
    scanner = L3210Scanner()

    lcd.show(["Place document,", "then press #"])
    keypad.wait_for_key(valid_keys=['#'])

    lcd.show(["Scanning page", f"{page_number}..."])

    try:
        filename = scanner.scan(target_directory=normalize_path(ANSWER_SHEETS_PATH))
        time.sleep(debounce)

        scanned_files.append(filename)

        lcd.show(
            [f"Page {page_number} scanned!", f"Total: {len(scanned_files)}"],
            duration=2
        )

    except Exception as e:
        log(f"Scan error: {e}", log_type="error")
        lcd.show(["Scan failed!", "Try again."], duration=2)


def _do_upload_and_save(
    lcd,
    keypad,
    user,
    scanned_files           : list,
    assessment_uid          : str,
    answer_key_data         : dict,
    assessment_data         : dict,
    collage_save_to_local   : bool  = True,
    keep_local_collage      : bool  = False,
    target_path             : str   = "scans"
) -> bool:
    """
    Gemini OCR → Score → Upload → Save to RTDB.
    Returns True if done (next sheet or exit), False means stay in loop.
    """
    from services.cloudinary_client import ImageUploader
    from services.gemini_client import gemini_with_retry
    from services.firebase_rtdb_client import FirebaseRTDB
    from services.smart_collage import SmartCollage

    upload_and_save_status  = False
    image_urls              = None
    image_public_ids        = None
    image_to_send_gemini    = None
    student_id              = None
    student_answers         = None
    score                   = None
    total                   = None
    breakdown               = None
    collage_path            = None

    while True:
        # =================================================================
        # STEP 1: Create Collage (if needed)
        # =================================================================
        if image_to_send_gemini is None:
            lcd.show("Processing images...")

            try:
                if len(scanned_files) > 1:
                    collage_builder = SmartCollage(scanned_files)
                    image_to_send_gemini = collage_builder.create_collage()

                    if collage_save_to_local:
                        collage_path = join_and_ensure_path(
                            target_path,
                            f"collage_{int(time.time())}.png"
                        )
                        collage_builder.save(image_to_send_gemini, collage_path)
                else:
                    image_to_send_gemini = scanned_files[0]

            except Exception as e:
                log(f"Collage error: {e}", log_type="error")

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
                    continue
                else:
                    delete_files(scanned_files)
                    break

        # =================================================================
        # STEP 2: Gemini OCR Extraction
        # =================================================================
        if student_id is None:
            lcd.show(["Processing with", "Gemini OCR..."])

            try:
                total_questions = int(answer_key_data.get("total_questions", 0))
                raw_result = gemini_with_retry(
                    api_key         = GEMINI_API_KEY,
                    image_path      = image_to_send_gemini,
                    prompt          = answer_sheet_prompt(total_number_of_questions=total_questions),
                    model           = GEMINI_MODEL,
                    prefer_method   = GEMINI_PREFERRED_METHOD
                )

                data            = sanitize_gemini_json(raw_result)
                student_id      = data.get("student_id")
                student_answers = data.get("answers")

                if student_id is None or student_answers is None:
                    log(
                        f"\nStudent ID or Answers not found.\n"
                        f"student_id: {student_id}\n"
                        f"answers   : {student_answers}",
                        log_type="error"
                    )
                    raise Exception("Missing student_id or answers")

                log(f"Raw Gemini response: {raw_result}", log_type="debug")

            except Exception as e:
                log(f"Gemini error: {e}", log_type="error")

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
                    continue
                else:
                    delete_files(scanned_files)
                    break

        # =================================================================
        # STEP 3: Compare Answers and Calculate Score
        # =================================================================
        if score is None:
            try:
                score, total, breakdown, is_final_score, found_warning = compare_answers(
                    student_answers,
                    answer_key_data
                )
                if found_warning:
                    answer_sheets_len = len(answer_key_data.get("answer_key", {}))
                    lcd.show("WARNING", duration=2)
                    lcd.show([
                        f"{total} != {answer_sheets_len}",
                        "Not same quantity"
                        ], 
                        duration=2
                    )
                lcd.show(f"Score: {score}/{total}", duration=2)

            except Exception as e:
                log(f"Scoring error: {e}", log_type="error")
                lcd.show("Scoring failed!", duration=2)
                delete_files(scanned_files)
                break

        # =================================================================
        # STEP 4: Upload to Cloudinary
        # =================================================================
        if image_urls is None:
            lcd.show(["Uploading...", "Please wait."])

            try:
                uploader = ImageUploader(
                    cloud_name  = CLOUDINARY_NAME,
                    api_key     = CLOUDINARY_API_KEY,
                    api_secret  = CLOUDINARY_API_SECRET,
                    folder      = CLOUDINARY_ANSWER_SHEETS_PATH
                )

                if len(scanned_files) > 1:
                    results = uploader.upload_batch(scanned_files)
                else:
                    results = [uploader.upload_single(scanned_files[0])]

                image_urls          = [r["url"] for r in results]
                image_public_ids    = [r["public_id"] for r in results]

            except Exception as e:
                log(f"Upload error: {e}", log_type="error")

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
                    continue
                else:
                    delete_files(scanned_files)
                    break

        # =================================================================
        # STEP 5: Save to Firebase RTDB
        # =================================================================
        lcd.show("Saving to database...")

        try:
            firebase = FirebaseRTDB(
                database_url        = FIREBASE_RTDB_BASE_REFERENCE,
                credentials_path    = normalize_path(FIREBASE_CREDENTIALS_PATH)
            )

            firebase.save_student_result(
                student_id          = student_id,
                assessment_uid      = assessment_uid,
                answer_sheet        = student_answers,
                total_score         = score,
                total_questions     = total,
                image_urls          = image_urls,
                image_public_ids    = image_public_ids,
                teacher_uid         = user.teacher_uid,
                is_final_score      = is_final_score,
                section_uid         = assessment_data["section_uid"],
                subject_uid         = assessment_data["subject_uid"],
                breakdown           = breakdown
            )

            lcd.show([f"Saved! {score}/{total}", f"ID: {student_id}"], duration=3)

            # Cleanup local files
            delete_files(scanned_files)

        except Exception as e:
            log(f"Firebase error: {e}", log_type="error")

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
                continue
            else:
                delete_files(scanned_files)
                break

        upload_and_save_status = True
        break

    # Cleanup collage
    try:
        if collage_path and not keep_local_collage:
            delete_file(collage_path)
    except Exception as e:
        log(f"Delete collage failed: {e}", log_type="error")

    return upload_and_save_status