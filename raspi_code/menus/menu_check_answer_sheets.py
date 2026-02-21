"""
Menu Flow: Check Answer Sheets
Handles scan → Gemini OCR → compare with answer key → score → upload → save to RTDB.
"""

import time

from services.logger import get_logger
from services.utils import delete_local_files
from services.l3210_scanner_hardware import L3210Scanner

log = get_logger("menu_check_answer_sheets.py")


def run(lcd, keypad, user) -> None:
    """
    Entry point for the Check Answer Sheets flow.

    Args:
        lcd     : LCD_I2C instance
        keypad  : Keypad3x4 instance
        user    : Authenticated user object (user.teacher_uid)
    """
    from services.firebase_service import FirebaseService

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
        firebase    = FirebaseService()
        answer_keys = firebase.get_answer_keys(teacher_uid=user.teacher_uid)
    except Exception as e:
        log(f"Failed to load answer keys: {e}", "error")
        lcd.show(["Failed to load", "answer keys."], duration=3)
        return

    if not answer_keys:
        lcd.show(["No answer keys!", "Scan key first."], duration=3)
        return

    # =========================================================================
    # Step 2: Let user pick which assessment to check against
    # =========================================================================
    assessment_options  = list(answer_keys.keys())   # list of assessment_uid strings
    selected_assessment = lcd.show_scrollable_menu(
        title           = "SELECT ASSESSMENT",
        options         = assessment_options,
        scroll_up_key   = "2",
        scroll_down_key = "8",
        select_key      = "*",
        exit_key        = "#",
        get_key_func    = keypad.read_key
    )

    if selected_assessment is None:
        return  # user cancelled → back to Main Menu

    assessment_uid  = assessment_options[selected_assessment]
    answer_key_data = answer_keys[assessment_uid]

    lcd.show([f"Assessment:", f"{assessment_uid}"], duration=2)

    scanned_files       = []
    page_number         = 1
    is_gemini_task_done = False
    gemini_result       = None   # holds extracted student data after Gemini succeeds

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
            page_number         = len(scanned_files) + 1
            is_gemini_task_done = False  # new scan invalidates previous Gemini result

        # =====================================================================
        # [1] Done & Save
        # =====================================================================
        elif selected == 1:
            if not scanned_files:
                lcd.show(["No scans yet!", "Scan first."], duration=2)
                continue

            # -----------------------------------------------------------------
            # Gemini OCR (only if not already done)
            # -----------------------------------------------------------------
            if not is_gemini_task_done:
                success, gemini_result = _do_gemini_ocr(
                    lcd, scanned_files, answer_key_data
                )

                if not success:
                    # Gemini failed → show retry prompt and stay in loop
                    lcd.show(["Gemini failed!", "Press # retry"], duration=1)
                    keypad.wait_for_key(valid_keys=['#'])
                    continue

                is_gemini_task_done = True

            # -----------------------------------------------------------------
            # Upload to Cloudinary
            # -----------------------------------------------------------------
            done = _do_upload_and_save(
                lcd, keypad, user,
                scanned_files,
                assessment_uid,
                gemini_result
            )

            if done == "next":
                # Reset for the next student sheet
                scanned_files.clear()
                page_number         = 1
                is_gemini_task_done = False
                gemini_result       = None
                continue

            elif done == "exit":
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
        filename = scanner.scan()  # expected to return the saved filename

        time.sleep(10)             # 10s debounce / scanner settle time

        scanned_files.append(filename)

        lcd.show(
            [f"Page {page_number} scanned!", f"Total: {len(scanned_files)}"],
            duration=2
        )

    except Exception as e:
        log(f"Scan error: {e}", "error")
        lcd.show(["Scan failed!", "Try again."], duration=2)


def _do_gemini_ocr(lcd, scanned_files: list, answer_key_data: dict) -> tuple[bool, dict | None]:
    """
    Send scanned images to Gemini, extract student answers, compare, calculate score.

    Returns:
        (True, result_dict)  on success
        (False, None)        on failure
    """
    from services.gemini_service import GeminiService

    lcd.show(["Processing with", "Gemini OCR..."])

    try:
        if len(scanned_files) > 1:
            from services.image_utils import create_collage
            image_to_process = create_collage(scanned_files)
        else:
            image_to_process = scanned_files[0]

        gemini = GeminiService()
        result = gemini.extract_student_answers(image_path=image_to_process)

        student_id      = result.get("student_id")
        student_answers = result.get("answers")          # dict: {q_num: answer}

        # Compare with answer key
        score, total, breakdown = _compare_answers(student_answers, answer_key_data)

        lcd.show([f"Score: {score}/{total}", "Saving..."], duration=2)

        return True, {
            "student_id"  : student_id,
            "answers"     : student_answers,
            "score"       : score,
            "total"       : total,
            "breakdown"   : breakdown,
        }

    except Exception as e:
        log(f"Gemini error: {e}", "error")
        return False, None


def _compare_answers(student_answers: dict, answer_key_data: dict) -> tuple[int, int, dict]:
    """
    Compare student answers against the answer key.

    Returns:
        (score, total_questions, breakdown_dict)
    """
    answer_key = answer_key_data.get("answer_key", {})
    total       = len(answer_key)
    score       = 0
    breakdown   = {}

    for q_num, correct_answer in answer_key.items():
        student_answer          = student_answers.get(q_num, None)
        is_correct              = student_answer == correct_answer
        breakdown[q_num]        = {
            "student"   : student_answer,
            "correct"   : correct_answer,
            "is_correct": is_correct,
        }
        if is_correct:
            score += 1

    return score, total, breakdown


def _do_upload_and_save(
    lcd, keypad, user,
    scanned_files   : list,
    assessment_uid  : str,
    gemini_result   : dict
) -> str:
    """
    Upload images to Cloudinary → save student result to RTDB → show score.

    Returns:
        "next"  → user wants to scan next sheet (reset state)
        "exit"  → user wants to go back to Main Menu
    """
    from services.cloudinary_service import CloudinaryService
    from services.firebase_service import FirebaseService

    score   = gemini_result["score"]
    total   = gemini_result["total"]

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
                options         = ["Re-upload", "Proceed anyway", "Exit"],
                scroll_up_key   = "2",
                scroll_down_key = "8",
                select_key      = "*",
                exit_key        = "#",
                get_key_func    = keypad.read_key
            )

            if choice == 0:
                continue                        # retry upload

            elif choice == 1:
                # Proceed without image URL (save score only)
                upload_url = None
                upload_success = True           # fall through to save

            else:
                delete_local_files(scanned_files)
                return "exit"

        # -----------------------------------------------------------------
        # Save to RTDB
        # -----------------------------------------------------------------
        try:
            firebase = FirebaseService()
            firebase.save_student_result(
                teacher_uid     = user.teacher_uid,
                assessment_uid  = assessment_uid,
                student_id      = gemini_result["student_id"],
                score           = score,
                total           = gemini_result["total"],
                breakdown       = gemini_result["breakdown"],
                image_url       = upload_url,
            )

        except Exception as e:
            log(f"Firebase save error: {e}", "error")
            lcd.show(["Save failed!", "Try again."], duration=2)
            continue  # retry from upload

        # -----------------------------------------------------------------
        # Show score + ask next action
        # -----------------------------------------------------------------
        delete_local_files(scanned_files)

        next_choice = lcd.show_scrollable_menu(
            title           = f"Score:{score}/{total}",
            options         = ["Next sheet", "Exit"],
            scroll_up_key   = "2",
            scroll_down_key = "8",
            select_key      = "*",
            exit_key        = "#",
            get_key_func    = keypad.read_key
        )

        if next_choice == 0:
            return "next"   # scan another sheet
        else:
            return "exit"   # back to Main Menu.