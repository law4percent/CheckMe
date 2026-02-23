"""
Menu Flow: Check Answer Sheets
Handles scan → Gemini OCR → compare with answer key → score → upload → save to RTDB.
"""

from services.logger import get_logger
from services.utils import delete_files, normalize_path, join_and_ensure_path, delete_file
from services.sanitizer import sanitize_gemini_json
from services.l3210_scanner_hardware import L3210Scanner
from services.prompts import answer_sheet_prompt

import time
import os
from dotenv import load_dotenv
load_dotenv(normalize_path("config/.env"))

GEMINI_API_KEY                  = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL                    = os.getenv("GEMINI_MODEL")

CLOUDINARY_NAME                 = os.getenv("CLOUDINARY_NAME")
CLOUDINARY_API_KEY              = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET           = os.getenv("CLOUDINARY_API_SECRET")

FIREBASE_RTDB_BASE_REFERENCE    = os.getenv("FIREBASE_RTDB_BASE_REFERENCE")
FIREBASE_CREDENTIALS_PATH       = os.getenv("FIREBASE_CREDENTIALS_PATH")

ANSWER_SHEETS_PATH =  os.getenv("ANSWER_SHEETS_PATH")

SCAN_DEBOUNCE_SECONDS = 3

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

    scanned_files       = []
    page_number         = 1
    is_gemini_task_done = False
    gemini_result       = None

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
            is_gemini_task_done = False

        # =====================================================================
        # [1] Done & Save
        # =====================================================================
        elif selected == 1:
            if not scanned_files:
                lcd.show(["No scans yet!", "Scan first."], duration=2)
                continue

            # Gemini OCR (only if not already done)
            if not is_gemini_task_done:
                success, gemini_result = _do_gemini_ocr(
                    lcd, keypad, scanned_files, answer_key_data
                )

                if not success:
                    # User chose to exit or retry from Gemini error screen
                    continue

                is_gemini_task_done = True

            # Upload and save
            done = _do_upload_and_save(
                lcd, keypad, user,
                scanned_files,
                assessment_uid,
                gemini_result
            )

            if done == "next":
                scanned_files.clear()
                page_number = 1
                is_gemini_task_done = False
                gemini_result = None
                continue

            elif done == "exit":
                break

        # =====================================================================
        # [2] Cancel
        # =====================================================================
        elif selected == 2:
            if scanned_files:
                delete_files(scanned_files)
            lcd.show(["Cancelled."], duration=2)
            break


# =============================================================================
# Private helpers
# =============================================================================

def _do_scan(
    lcd,
    keypad,
    scanned_files   : list,
    page_number     : int,
    debounce        : int = SCAN_DEBOUNCE_SECONDS
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


def _do_gemini_ocr(
    lcd,
    keypad,
    scanned_files: list,
    answer_key_data: dict
) -> tuple:
    """
    Send scanned images to Gemini, extract student answers, compare, calculate score.

    Returns:
        (True, result_dict) on success
        (False, None) on failure
    """
    from services.gemini_client import gemini_with_retry
    from services.smart_collage import SmartCollage

    image_to_send_gemini = None
    student_id = None
    student_answers = None
    collage_path = None
    target_path = "scans/answer_sheets"

    while True:
        # =================================================================
        # STEP 1: Create Collage (if needed)
        # =================================================================
        if image_to_send_gemini is None:
            lcd.show(["Processing images..."])

            try:
                if len(scanned_files) > 1:
                    collage_builder = SmartCollage(scanned_files)
                    image_to_send_gemini = collage_builder.create_collage()

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
                    title="COLLAGE FAILED",
                    options=["Retry", "Exit"],
                    scroll_up_key="2",
                    scroll_down_key="8",
                    select_key="*",
                    exit_key="#",
                    get_key_func=keypad.read_key
                )

                if choice == 0:
                    continue
                else:
                    return (False, None)

        # =================================================================
        # STEP 2: Gemini OCR Extraction
        # =================================================================
        if student_id is None:
            lcd.show(["Processing with", "Gemini OCR..."])

            try:
                total_questions = answer_key_data.get("total_questions", 0)

                raw_result = gemini_with_retry(
                    api_key=GEMINI_API_KEY,
                    image_path=image_to_send_gemini,
                    prompt=answer_sheet_prompt(total_number_of_questions=total_questions),
                    model=GEMINI_MODEL,
                    prefer_method="sdk"
                )

                if raw_result is None:
                    raise Exception("Gemini returned None")

                data = sanitize_gemini_json(raw_result)
                student_id = data.get("student_id")
                student_answers = data.get("answers")

                if not student_id or not student_answers:
                    log(
                        f"Student ID or Answers not found.\n"
                        f"student_id: {student_id}\n"
                        f"answers: {student_answers}",
                        log_type="error"
                    )
                    raise Exception("Missing student_id or answers")

                log(f"Raw Gemini response: {raw_result}", log_type="debug")

            except Exception as e:
                log(f"Gemini error: {e}", log_type="error")

                choice = lcd.show_scrollable_menu(
                    title="EXTRACTION FAILED",
                    options=["Retry", "Exit"],
                    scroll_up_key="2",
                    scroll_down_key="8",
                    select_key="*",
                    exit_key="#",
                    get_key_func=keypad.read_key
                )

                if choice == 0:
                    continue
                else:
                    if collage_path:
                        delete_file(collage_path)
                    return (False, None)

        # =================================================================
        # STEP 3: Compare Answers and Calculate Score
        # =================================================================
        try:
            score, total, breakdown = _compare_answers(
                student_answers,
                answer_key_data
            )

            lcd.show([f"Score: {score}/{total}"], duration=2)

            # Cleanup collage
            if collage_path:
                try:
                    delete_file(collage_path)
                except Exception as e:
                    log(f"Delete collage failed: {e}", log_type="error")

            return (True, {
                "student_id": student_id,
                "answers": student_answers,
                "score": score,
                "total": total,
                "breakdown": breakdown,
            })

        except Exception as e:
            log(f"Scoring error: {e}", log_type="error")
            lcd.show(["Scoring failed!", "Try again."], duration=2)
            return (False, None)


def _compare_answers(
    student_answers: dict,
    answer_key_data: dict
) -> tuple:
    """
    Compare student answers against the answer key.

    Returns:
        (score, total_questions, breakdown_dict)
    """
    answer_key = answer_key_data.get("answer_key", {})
    total = len(answer_key)
    score = 0
    breakdown = {}

    for q_num, correct_answer in answer_key.items():
        student_answer = student_answers.get(q_num, "missing_answer")
        is_correct = student_answer == correct_answer
        
        breakdown[q_num] = {
            "student": student_answer,
            "correct": correct_answer,
            "is_correct": is_correct,
        }
        
        if is_correct:
            score += 1

    return score, total, breakdown


def _do_upload_and_save(
    lcd,
    keypad,
    user,
    scanned_files: list,
    assessment_uid: str,
    gemini_result: dict
) -> str:
    """
    Upload images to Cloudinary → save student result to RTDB → show score.

    Returns:
        "next" → user wants to scan next sheet
        "exit" → user wants to go back to Main Menu
    """
    from services.cloudinary_client import ImageUploader
    from services.firebase_rtdb_client import FirebaseRTDB
    from services.smart_collage import SmartCollage
    import multiprocessing

    score = gemini_result["score"]
    total = gemini_result["total"]
    image_urls = None
    image_public_ids = None

    while True:
        # =================================================================
        # STEP 1: Upload to Cloudinary
        # =================================================================
        if image_urls is None:
            lcd.show(["Uploading...", "Please wait."])

            try:
                uploader = ImageUploader(
                    cloud_name=CLOUDINARY_NAME,
                    api_key=CLOUDINARY_API_KEY,
                    api_secret=CLOUDINARY_API_SECRET,
                    folder="answer-sheets"
                )

                if len(scanned_files) > 1:
                    results = uploader.upload_batch(scanned_files)
                else:
                    results = [uploader.upload_single(scanned_files[0])]

                image_urls = [r["url"] for r in results]
                image_public_ids = [r["public_id"] for r in results]

            except Exception as e:
                log(f"Upload error: {e}", log_type="error")

                choice = lcd.show_scrollable_menu(
                    title="UPLOAD FAILED",
                    options=["Re-upload", "Proceed anyway", "Exit"],
                    scroll_up_key="2",
                    scroll_down_key="8",
                    select_key="*",
                    exit_key="#",
                    get_key_func=keypad.read_key
                )

                if choice == 0:
                    continue
                elif choice == 1:
                    # Start background retry process
                    def background_retry():
                        for attempt in range(1, 4):
                            try:
                                uploader = ImageUploader(
                                    cloud_name=CLOUDINARY_NAME,
                                    api_key=CLOUDINARY_API_KEY,
                                    api_secret=CLOUDINARY_API_SECRET,
                                    folder="answer-sheets"
                                )
                                
                                if len(scanned_files) > 1:
                                    results = uploader.upload_batch(scanned_files)
                                else:
                                    results = [uploader.upload_single(scanned_files[0])]
                                
                                urls = [r["url"] for r in results]
                                
                                # Update RTDB with URLs
                                firebase = FirebaseRTDB(
                                    database_url=FIREBASE_RTDB_BASE_REFERENCE,
                                    credentials_path=normalize_path(FIREBASE_CREDENTIALS_PATH)
                                )
                                firebase.update_image_urls(
                                    assessment_uid,
                                    gemini_result["student_id"],
                                    urls
                                )
                                log(f"Background upload succeeded on attempt {attempt}", log_type="info")
                                return
                            except Exception as e:
                                log(f"Background upload attempt {attempt} failed: {e}", log_type="error")
                                if attempt < 3:
                                    time.sleep(5)
                        
                        # All attempts failed - save empty URLs
                        try:
                            firebase = FirebaseRTDB(
                                database_url=FIREBASE_RTDB_BASE_REFERENCE,
                                credentials_path=normalize_path(FIREBASE_CREDENTIALS_PATH)
                            )
                            firebase.update_image_urls(
                                assessment_uid,
                                gemini_result["student_id"],
                                []
                            )
                            log("Background upload failed all attempts, saved empty URLs", log_type="warning")
                        except:
                            pass

                    # Start background process
                    p = multiprocessing.Process(target=background_retry)
                    p.daemon = True
                    p.start()

                    # Set empty URLs to proceed
                    image_urls = []
                else:
                    delete_files(scanned_files)
                    return "exit"

        # =================================================================
        # STEP 2: Save to RTDB
        # =================================================================
        lcd.show(["Saving to database..."])

        try:
            firebase = FirebaseRTDB(
                database_url=FIREBASE_RTDB_BASE_REFERENCE,
                credentials_path=normalize_path(FIREBASE_CREDENTIALS_PATH)
            )

            firebase.save_student_result(
                student_id=gemini_result["student_id"],
                assessment_uid=assessment_uid,
                answer_sheet=gemini_result["answers"],
                total_score=score,
                total_questions=total,
                image_urls=image_urls,
                teacher_uid=user.teacher_uid,
                is_final_score=True
            )

            log(f"Saved result for {gemini_result['student_id']}", log_type="info")

            # Cleanup local files
            delete_files(scanned_files)

            # Show score and next action
            next_choice = lcd.show_scrollable_menu(
                title=f"Score: {score}/{total}",
                options=["Next sheet", "Exit"],
                scroll_up_key="2",
                scroll_down_key="8",
                select_key="*",
                exit_key="#",
                get_key_func=keypad.read_key
            )

            if next_choice == 0:
                return "next"
            else:
                return "exit"

        except Exception as e:
            log(f"Firebase save error: {e}", log_type="error")

            choice = lcd.show_scrollable_menu(
                title="DATABASE FAILED",
                options=["Retry", "Exit"],
                scroll_up_key="2",
                scroll_down_key="8",
                select_key="*",
                exit_key="#",
                get_key_func=keypad.read_key
            )

            if choice == 0:
                continue
            else:
                delete_files(scanned_files)
                return "exit"