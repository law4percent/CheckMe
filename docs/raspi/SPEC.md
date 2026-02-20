# System Specification: Automated Answer Sheet Checking System

**Version:** 1.0.0  
**Last Updated:** February 20, 2025  
**Status:** Draft  
**Project:** RaspberryPi Answer Sheet Grading System

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Prerequisites](#2-system-prerequisites)
3. [Architecture](#3-architecture)
4. [Service Modules](#4-service-modules)
5. [Data Models](#5-data-models)
6. [Authentication Flow](#6-authentication-flow)
7. [User Workflows](#7-user-workflows)
8. [Error Handling](#8-error-handling)
9. [Implementation Notes](#9-implementation-notes)

---

## 1. Overview

### 1.1 Purpose

An automated grading system that uses OCR (Gemini AI) to extract and score student answer sheets against teacher-provided answer keys. The system runs on Raspberry Pi and integrates with L3210 scanner, Cloudinary cloud storage, and Firebase Realtime Database.

### 1.2 Scope

**In Scope:**
- Teacher authentication and session management
- Answer key scanning and OCR extraction
- Student answer sheet scanning and automated grading
- Multi-page document support with smart collage
- Cloud image storage and backup
- Real-time score calculation
- Offline-capable scanning with delayed upload retry

**Out of Scope:**
- Web-based dashboard (future phase)
- Student-facing mobile app
- Batch processing from pre-scanned files
- Report generation and analytics

### 1.3 Key Users

| User Role | Responsibilities |
|---|---|
| **Teacher** | Scan answer keys, check student sheets, view scores |
| **System Administrator** | Configure API keys, manage hardware |

### 1.4 Success Metrics

- Scan-to-score cycle time: < 60 seconds per student sheet
- OCR accuracy: > 95% for machine-printed text, > 85% for handwriting
- System uptime: > 99% during school hours
- Failed upload recovery rate: > 90% within 5 minutes

---

## 2. System Prerequisites

### 2.1 Hardware Requirements

| Component | Specification | Notes |
|---|---|---|
| **Compute** | Raspberry Pi 4 Model B (4GB RAM minimum) | Must support USB 3.0 |
| **Scanner** | L3210 Document Scanner | USB-connected, 300+ DPI |
| **Input Device** | 3x4 Matrix Keypad | GPIO-connected |
| **Display** | 16x2 or 20x4 LCD Screen | I2C interface preferred |
| **Network** | WiFi or Ethernet | Stable internet required |

### 2.2 Software Dependencies

| Service | Purpose | Endpoint |
|---|---|---|
| **Cloudinary** | Image storage | `api.cloudinary.com` |
| **Google Gemini AI** | OCR extraction | `generativelanguage.googleapis.com` |
| **Firebase RTDB** | Data persistence | `<project-id>.firebaseio.com` |

### 2.3 Required Credentials

```bash
# Environment variables or config file
CLOUDINARY_CLOUD_NAME=<your_cloud_name>
CLOUDINARY_API_KEY=<your_api_key>
CLOUDINARY_API_SECRET=<your_api_secret>
GEMINI_API_KEY=<your_gemini_key>
FIREBASE_DATABASE_URL=<your_rtdb_url>
FIREBASE_API_KEY=<your_firebase_key>
```

### 2.4 Python Environment

```bash
Python 3.9+
Libraries:
- google-generativeai
- cloudinary
- firebase-admin (or pyrebase4)
- RPi.GPIO
- pillow
- requests
```

---

## 3. Architecture

### 3.1 System Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    Raspberry Pi 4                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Main Application (main.py)            │ │
│  │                                                    │ │
│  │  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ Auth Module  │  │  Menu System │              │ │
│  │  └──────┬───────┘  └──────┬───────┘              │ │
│  │         │                  │                       │ │
│  │  ┌──────▼──────────────────▼───────────────────┐ │ │
│  │  │         Service Layer                       │ │ │
│  │  │  - firebase_rtdb_client                     │ │ │
│  │  │  - gemini_client                            │ │ │
│  │  │  - image_uploader                           │ │ │
│  │  │  - scorer, sanitizer, prompts               │ │ │
│  │  └──────┬────────────────┬─────────────────────┘ │ │
│  │         │                │                        │ │
│  │  ┌──────▼────────┐  ┌────▼──────────┐           │ │
│  │  │  Hardware     │  │   Utilities   │           │ │
│  │  │  - scanner    │  │  - collage    │           │ │
│  │  │  - keypad     │  │  - logger     │           │ │
│  │  │  - lcd        │  │  - utils      │           │ │
│  │  └───────────────┘  └───────────────┘           │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼─────┐     ┌─────▼──────┐    ┌────▼──────┐
   │Cloudinary│     │ Gemini API │    │ Firebase  │
   │  Storage │     │    (OCR)   │    │   RTDB    │
   └──────────┘     └────────────┘    └───────────┘
```

### 3.2 Data Flow

```
┌─────────────────────────────────────────────────────────┐
│  1. Teacher Input (Keypad) → LCD Display Feedback      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  2. L3210 Scanner → Local Image Storage (.jpg files)   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  3. Smart Collage (if multi-page) → Single Image       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  4. Cloudinary Upload → Secure Image URLs              │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  5. Gemini OCR Extraction → Raw JSON Response          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  6. Sanitizer → Cleaned Structured Data                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  7. Scorer (for student sheets) → Final Grade          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  8. Firebase RTDB → Persistent Storage                 │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Service Modules

### 4.1 Core Services Overview

| Module | File | Primary Responsibility |
|---|---|---|
| **Authentication** | `cred.txt` | Store teacher credentials |
| **Database Client** | `firebase_rtdb_client.py` | CRUD operations on Firebase |
| **OCR Client** | `gemini_client.py` | Gemini API integration with retry logic |
| **Image Uploader** | `image_uploader.py` | Cloudinary batch upload |
| **Hardware - Keypad** | `keypad_hardware.py` | Read user input from 3x4 keypad |
| **Hardware - Scanner** | `l3210_scanner.py` | Control L3210 scanner |
| **Hardware - LCD** | `lcd_hardware.py` | Display menus and messages |
| **Logging** | `logger.py` | Centralized logging system |
| **Prompts** | `prompts.py` | OCR prompt templates |
| **Sanitizer** | `sanitizer.py` | Clean and normalize Gemini responses |
| **Scorer** | `scorer.py` | Compare answers and calculate grades |
| **Image Processing** | `smart_collage.py` | Stitch multi-page scans |
| **Utilities** | `utils.py` | File I/O, validation helpers |

### 4.2 Module API Specifications

#### 4.2.1 firebase_rtdb_client.py

```python
class FirebaseRTDBClient:
    def save_answer_key(
        assessment_uid: str,
        answer_key: dict,
        exact_number_of_questions: int,
        image_urls: list,
        teacher_uid: str
    ) -> bool:
        """Save answer key to RTDB under /answer_keys/{assessment_uid}"""
        pass
    
    def get_answer_keys(teacher_uid: str) -> list:
        """Retrieve all answer keys for a teacher"""
        pass
    
    def save_student_result(
        student_id: str,
        assessment_uid: str,
        answer_sheet: dict,
        total_score: int,
        exact_number_of_questions: int,
        image_urls: list,
        teacher_uid: str,
        is_final_score: bool = True
    ) -> bool:
        """Save student grading result"""
        pass
```

#### 4.2.2 gemini_client.py

```python
def gemini_with_retry(
    api_key: str,
    image_path: str,
    prompt: str,
    model: str,
    max_attempts: int = 3,
    use_exponential_backoff: bool = True,
    prefer_method: str = "sdk"
) -> Optional[str]:
    """
    Send image to Gemini with circuit breaker and retry logic.
    Returns raw JSON string or None if all attempts fail.
    """
    pass

class GeminiSDKClient:
    def send_request(prompt: str, image_path: str, upload_to_cloud: bool = True) -> str:
        pass

class GeminiHTTPClient:
    def send_request(prompt: str, image_path: str, upload_to_cloud: bool = True) -> str:
        pass
```

#### 4.2.3 image_uploader.py

```python
def batch_upload(image_paths: list, folder: str = "answer-sheets") -> list:
    """
    Upload multiple images to Cloudinary.
    Returns list of secure URLs.
    """
    pass

def upload_with_retry(image_path: str, max_attempts: int = 3) -> Optional[str]:
    """Single image upload with retry logic"""
    pass
```

#### 4.2.4 prompts.py

```python
def answer_key_prompt(total_number_of_questions: int) -> str:
    """Generate Gemini prompt for answer key extraction"""
    pass

def answer_sheet_prompt(total_number_of_questions: int) -> str:
    """Generate Gemini prompt for student answer extraction"""
    pass
```

#### 4.2.5 sanitizer.py

```python
def sanitize_gemini_json(raw: str) -> dict:
    """
    Clean Gemini response:
    - Strip markdown code fences
    - Parse JSON
    - Normalize sentinel values
    - Uppercase MC answers
    """
    pass
```

#### 4.2.6 scorer.py

```python
def calculate_score(
    answer_key: dict,
    answer_sheet: dict,
    exact_number_of_questions: int
) -> dict:
    """
    Compare student answers against answer key.
    Returns:
    {
        "total_score": int,
        "correct": list,
        "incorrect": list,
        "missing": list,
        "unreadable": list
    }
    """
    pass
```

#### 4.2.7 smart_collage.py

```python
def collage_images(image_paths: list, output_path: str = None) -> str:
    """
    Vertically stitch multiple images into a single image.
    Returns path to collaged image.
    """
    pass
```

#### 4.2.8 Hardware Modules

```python
# keypad_hardware.py
def read_key() -> Optional[str]:
    """Non-blocking read from keypad. Returns '0'-'9', '*', '#', or None"""
    pass

def wait_for_key(valid_keys: list = None, timeout: int = None) -> str:
    """Blocking read until valid key is pressed"""
    pass

# l3210_scanner.py
def scan() -> bool:
    """Trigger scanner. Returns True if scan initiated successfully"""
    pass

def is_scanning() -> bool:
    """Check if scanner is currently scanning"""
    pass

def get_last_scan() -> Optional[str]:
    """Get filepath of most recent scan"""
    pass

# lcd_hardware.py
def show(text: str | list, duration: int = None) -> None:
    """Display text on LCD. Auto-clear after duration (seconds) if provided"""
    pass

def clear() -> None:
    """Clear LCD display"""
    pass
```

---

## 5. Data Models

### 5.1 Authentication Data (`cred.txt`)

**Format:** JSON  
**Location:** `/home/pi/grading-system/cred.txt`

```json
{
  "teacher_uid": "TCHR-12345",
  "username": "prof_smith"
}
```

**States:**
- Both `null` → `NOT_AUTHENTICATED`
- Either `null` → `NOT_AUTHENTICATED`
- Both present → `AUTHENTICATED`

### 5.2 Answer Key Record

**Storage:** Firebase RTDB at `/answer_keys/{assessment_uid}`

```json
{
  "assessment_uid": "EXAM-2025-MATH-001",
  "answer_key": {
    "Q1": "A",
    "Q2": "TRUE",
    "Q3": "Mitochondria",
    "Q4": "missing_answer",
    "Q5": "unreadable",
    "Q50": "D"
  },
  "exact_number_of_questions": 50,
  "image_urls": [
    "https://res.cloudinary.com/.../page1.jpg",
    "https://res.cloudinary.com/.../page2.jpg"
  ],
  "created_at": "2025-02-20T10:30:00Z",
  "created_by": "TCHR-12345"
}
```

### 5.3 Student Result Record

**Storage:** Firebase RTDB at `/results/{assessment_uid}/{student_id}`

```json
{
  "student_id": "STUD-67890",
  "assessment_uid": "EXAM-2025-MATH-001",
  "answer_sheet": {
    "Q1": "A",
    "Q2": "FALSE",
    "Q3": "Mitochondria",
    "Q4": "missing_answer",
    "Q5": "B",
    "Q50": "D"
  },
  "exact_number_of_questions": 50,
  "total_score": 45,
  "is_final_score": true,
  "image_urls": [
    "https://res.cloudinary.com/.../student_001_page1.jpg"
  ],
  "checked_at": "2025-02-20T11:15:00Z",
  "checked_by": "TCHR-12345"
}
```

### 5.4 Sentinel Values

| Value | Meaning | Use Case |
|---|---|---|
| `"missing_uid"` | UID field is completely blank | No assessment/student ID written |
| `"unreadable"` | Text exists but illegible | Blurry, faint, or ambiguous marks |
| `"missing_answer"` | No mark/answer provided | Student left question blank |
| `"missing_question"` | Question not visible in image | Page not scanned / missing |
| `"essay_answer"` | Essay question detected | Full text not extracted (placeholder) |

**Normalization Rules:**
- Multiple choice: Uppercase letters (`"a"` → `"A"`)
- True/False: Uppercase (`"true"` → `"TRUE"`, `"false"` → `"FALSE"`)
- Sentinels: Lowercase as specified above

---

## 6. Authentication Flow

### 6.1 Credential Check Process

```
START
  │
  ▼
Does cred.txt exist?
  │
  ├─NO──► Create cred.txt with {"teacher_uid": null, "username": null}
  │       │
  │       ▼
  │     Return NOT_AUTHENTICATED
  │
  ├─YES─► Load cred.txt
          │
          ▼
        Do teacher_uid AND username keys exist?
          │
          ├─NO──► Return NOT_AUTHENTICATED
          │
          ├─YES─► Are BOTH values non-null?
                  │
                  ├─NO──► Return NOT_AUTHENTICATED
                  │
                  └─YES─► Return AUTHENTICATED
                          + teacher_uid value
                          + username value
```

### 6.2 Login Flow (NOT_AUTHENTICATED State)

```
╔════════════════════════════╗
║      LOGIN REQUIRED        ║
╠════════════════════════════╣
║  Enter Teacher ID:         ║
║  > TCHR-_____              ║
║                            ║
║  Press # to confirm        ║
║  Press * to clear          ║
╚════════════════════════════╝
        │
        ▼ (User enters ID and presses #)
╔════════════════════════════╗
║  Enter Username:           ║
║  > prof______              ║
║                            ║
║  Press # to confirm        ║
║  Press * to clear          ║
╚════════════════════════════╝
        │
        ▼ (User enters username and presses #)
        
Save to cred.txt:
{
  "teacher_uid": "TCHR-12345",
  "username": "prof_smith"
}
        │
        ▼
    Proceed to Home Menu (STEP 2)
```

---

## 7. User Workflows

### 7.1 STEP 2: Home Menu

```
╔════════════════════════════╗
║        HOME MENU           ║
╠════════════════════════════╣
║  Logged in: prof_smith     ║
║                            ║
║  [1] Scan new Answer Key   ║
║  [2] Check Answer Sheets   ║
║  [3] Settings              ║
║                            ║
║  Press 1, 2, or 3          ║
╚════════════════════════════╝
```

**Navigation:**
- `1` → STEP 2.A (Scan Answer Key)
- `2` → STEP 2.B (Check Student Sheets)
- `3` → Settings menu (future implementation)
- `*` → Logout (clear cred.txt)

---

### 7.2 STEP 2.A: Scan New Answer Key

#### 7.2.1 Initial Setup

```
╔════════════════════════════╗
║   SCAN ANSWER KEY          ║
╠════════════════════════════╣
║  Enter total questions:    ║
║  > 50                      ║
║                            ║
║  Press # to confirm        ║
║  Press * to go back        ║
╚════════════════════════════╝
```

**Input Validation:**
- Accept only digits `0-9`
- Range: 1-999
- Press `#` to confirm
- Press `*` to cancel and return to Home

**State Variables:**
```python
exact_number_of_questions: int = None
local_scanned_images: list = []
page_counter: int = 0
```

#### 7.2.2 Scan Loop Menu

```
╔════════════════════════════╗
║   ANSWER KEY SCAN          ║
╠════════════════════════════╣
║  Total Questions: 50       ║
║  Pages scanned: 0          ║
║                            ║
║  [1] Scan Page             ║
║  [2] Done & Save           ║
║  [3] Cancel                ║
╚════════════════════════════╝
```

#### 7.2.3 Option [1] Scan Page

**Flow:**

```python
def scan_answer_key_page():
    """Scan a single page of the answer key"""
    
    # Step 1: Trigger scanner
    lcd.show("Place paper and wait...")
    scanner.scan()
    
    # Step 2: Debounce delay (prevent double-scan)
    time.sleep(10)
    
    # Step 3: Show scanning progress
    page_counter += 1
    lcd.show(f"Scanning Page {page_counter}...")
    
    # Step 4: Wait for scan completion
    while scanner.is_scanning():
        time.sleep(1)
    
    # Step 5: Retrieve scanned file
    filename = scanner.get_last_scan()
    
    if filename:
        local_scanned_images.append(filename)
        lcd.show(f"Page {page_counter} saved!", duration=2)
    else:
        lcd.show("Scan failed! Try again", duration=3)
        page_counter -= 1
    
    # Step 6: Return to scan menu
    show_scan_menu()
```

**Error Handling:**
- Scanner not ready → Display "Scanner offline. Check connection."
- Scan timeout (>60s) → Display "Scan timeout. Try again."
- File not found → Display "Scan failed. Retry."

#### 7.2.4 Option [2] Done and Save

**High-Level Flow:**

```
[2] Done & Save pressed
        │
        ▼
Upload images to Cloudinary
        │
        ├─SUCCESS──► len(local_scanned_images) > 1?
        │            │
        │            ├─YES──► Create collage
        │            │        │
        │            │        ▼
        │            └─NO───► Use single image
        │                     │
        │                     ▼
        │            Send image to Gemini OCR
        │                     │
        │                     ├─SUCCESS──► Extract data
        │                     │            │
        │                     │            ▼
        │                     │      Save to Firebase RTDB
        │                     │            │
        │                     │            ▼
        │                     │      Delete local images
        │                     │            │
        │                     │            ▼
        │                     │      Return to Home Menu
        │                     │
        │                     └─FAIL─────► Display Gemini error
        │                                  │
        │                                  ▼
        │                            Return to scan menu
        │
        └─FAIL─────► Show upload error menu
                     │
                     ├─[1] Re-upload──► Retry from start
                     │
                     └─[2] Exit───────► Delete local images
                                        │
                                        ▼
                                  Return to Home Menu
```

**Detailed Implementation:**

```python
def done_and_save_answer_key():
    """Process and save scanned answer key"""
    
    # Phase 1: Upload to Cloudinary
    lcd.show("Uploading images...")
    logger.log(f"Uploading {len(local_scanned_images)} images")
    
    try:
        image_urls = image_uploader.batch_upload(
            local_scanned_images,
            folder="answer-keys"
        )
        
        if not image_urls:
            raise Exception("Upload failed - no URLs returned")
        
        logger.log(f"Upload success: {len(image_urls)} URLs")
        
    except Exception as e:
        logger.log(f"Upload error: {e}", type="error")
        return show_upload_error_menu()
    
    # Phase 2: Image Processing
    lcd.show("Processing images...")
    
    if len(local_scanned_images) > 1:
        logger.log("Creating collage...")
        lcd.show("Creating collage...")
        collage_path = smart_collage.collage_images(local_scanned_images)
    else:
        collage_path = local_scanned_images[0]
    
    # Phase 3: OCR Extraction
    lcd.show("Extracting answers...")
    logger.log("Starting Gemini OCR")
    
    prompt = prompts.answer_key_prompt(exact_number_of_questions)
    
    raw_response = gemini_client.gemini_with_retry(
        api_key=os.getenv("GEMINI_API_KEY"),
        image_path=collage_path,
        prompt=prompt,
        model="gemini-2.0-flash-exp",
        max_attempts=3
    )
    
    if not raw_response:
        logger.log("Gemini extraction failed", type="error")
        lcd.show([
            "OCR failed!",
            "Check image quality",
            "and try again",
            "",
            "Press # to continue"
        ])
        keypad.wait_for_key("#")
        return show_scan_menu()
    
    # Phase 4: Sanitize and Validate
    lcd.show("Validating data...")
    
    try:
        data = sanitizer.sanitize_gemini_json(raw_response)
        assessment_uid = data.get("assessment_uid")
        answer_key = data.get("answers")
        
        if assessment_uid == "missing_uid":
            raise ValueError("Assessment UID not found in image")
        
        if len(answer_key) != exact_number_of_questions:
            logger.log(
                f"Warning: Expected {exact_number_of_questions} answers, "
                f"got {len(answer_key)}",
                type="warning"
            )
        
    except Exception as e:
        logger.log(f"Validation error: {e}", type="error")
        lcd.show([
            "Data validation failed!",
            str(e)[:20],
            "",
            "Press # to continue"
        ])
        keypad.wait_for_key("#")
        return show_scan_menu()
    
    # Phase 5: Save to Firebase
    lcd.show("Saving to database...")
    logger.log("Saving to Firebase RTDB")
    
    success = firebase_rtdb_client.save_answer_key(
        assessment_uid=assessment_uid,
        answer_key=answer_key,
        exact_number_of_questions=exact_number_of_questions,
        image_urls=image_urls,
        teacher_uid=current_teacher_uid
    )
    
    if not success:
        logger.log("Firebase save failed", type="error")
        lcd.show([
            "Database save failed!",
            "Check connection",
            "",
            "Press # to continue"
        ])
        keypad.wait_for_key("#")
        return show_scan_menu()
    
    # Phase 6: Cleanup
    logger.log("Cleaning up local files")
    utils.delete_local_images(local_scanned_images)
    local_scanned_images.clear()
    page_counter = 0
    
    lcd.show([
        "Answer key saved!",
        f"Assessment: {assessment_uid[:12]}",
        f"Questions: {exact_number_of_questions}",
        "",
        "Press # to continue"
    ])
    keypad.wait_for_key("#")
    
    return HOME_MENU


def show_upload_error_menu():
    """Display options when Cloudinary upload fails"""
    
    lcd.show([
        "Upload failed!",
        "",
        "[1] Retry upload",
        "[2] Cancel & exit"
    ])
    
    while True:
        key = keypad.wait_for_key(valid_keys=["1", "2"])
        
        if key == "1":
            # Retry from upload phase
            return done_and_save_answer_key()
        
        elif key == "2":
            # Cleanup and exit
            utils.delete_local_images(local_scanned_images)
            local_scanned_images.clear()
            page_counter = 0
            lcd.show("Cancelled", duration=2)
            return HOME_MENU
```

#### 7.2.5 Option [3] Cancel

**Flow:**

```python
def cancel_answer_key_scan():
    """Cancel answer key scanning and cleanup"""
    
    lcd.show("Cancelling...")
    logger.log("User cancelled answer key scan")
    
    # Delete all local scanned images
    utils.delete_local_images(local_scanned_images)
    
    # Reset state
    local_scanned_images.clear()
    page_counter = 0
    exact_number_of_questions = None
    
    lcd.show("Cancelled", duration=2)
    return HOME_MENU
```

---

### 7.3 STEP 2.B: Check Student Answer Sheets

#### 7.3.1 Prerequisites Check

**Flow:**

```python
def start_checking_sheets():
    """Initialize student sheet checking workflow"""
    
    lcd.show("Loading answer keys...")
    logger.log("Fetching answer keys from RTDB")
    
    # Fetch all answer keys for this teacher
    answer_keys = firebase_rtdb_client.get_answer_keys(current_teacher_uid)
    
    if not answer_keys or len(answer_keys) == 0:
        lcd.show([
            "No answer keys found!",
            "",
            "Please scan an",
            "answer key first",
            "",
            "Press # to go back"
        ])
        keypad.wait_for_key("#")
        return HOME_MENU
    
    # If multiple answer keys exist, let teacher select
    if len(answer_keys) > 1:
        selected_key = show_answer_key_selection_menu(answer_keys)
    else:
        selected_key = answer_keys[0]
    
    # Load selected answer key into global state
    global current_assessment_uid, current_answer_key, current_total_questions
    current_assessment_uid = selected_key["assessment_uid"]
    current_answer_key = selected_key["answer_key"]
    current_total_questions = selected_key["exact_number_of_questions"]
    
    logger.log(f"Loaded answer key: {current_assessment_uid}")
    
    return show_check_sheet_menu()


def show_answer_key_selection_menu(answer_keys: list) -> dict:
    """Display menu to select from multiple answer keys"""
    
    # Display first 3 answer keys
    options = []
    for i, key in enumerate(answer_keys[:3]):
        uid = key["assessment_uid"][:15]  # Truncate for display
        options.append(f"[{i+1}] {uid}")
    
    lcd.show([
        "Select Answer Key:",
        "",
        *options,
        "",
        "Press 1, 2, or 3"
    ])
    
    while True:
        choice = keypad.wait_for_key(valid_keys=["1", "2", "3"])
        index = int(choice) - 1
        
        if index < len(answer_keys):
            return answer_keys[index]
```

#### 7.3.2 Check Sheet Scan Loop Menu

```
╔════════════════════════════╗
║  CHECK ANSWER SHEETS       ║
╠════════════════════════════╣
║  Assessment: MATH-001      ║
║  Questions: 50             ║
║  Pages scanned: 0          ║
║                            ║
║  [1] Scan Page             ║
║  [2] Done & Save           ║
║  [3] Cancel                ║
╚════════════════════════════╝
```

**State Variables:**
```python
is_gemini_task_done: bool = False
local_scanned_images: list = []
page_counter: int = 0
current_student_score: int = None
current_student_id: str = None
```

#### 7.3.3 Option [1] Scan Page

**Flow:** (Identical to answer key scanning)

```python
def scan_student_sheet_page():
    """Scan a single page of student answer sheet"""
    
    lcd.show("Place paper and wait...")
    scanner.scan()
    time.sleep(10)  # Debounce
    
    page_counter += 1
    lcd.show(f"Scanning Page {page_counter}...")
    
    while scanner.is_scanning():
        time.sleep(1)
    
    filename = scanner.get_last_scan()
    
    if filename:
        local_scanned_images.append(filename)
        lcd.show(f"Page {page_counter} saved!", duration=2)
    else:
        lcd.show("Scan failed! Try again", duration=3)
        page_counter -= 1
    
    show_check_sheet_menu()
```

#### 7.3.4 Option [2] Done and Save

**High-Level Flow:**

```
[2] Done & Save pressed
        │
        ▼
is_gemini_task_done == False?
        │
        ├─YES──► Process image with Gemini
        │        │
        │        ├─len(images) > 1?──YES──► Create collage
        │        │                    NO───► Use single image
        │        │
        │        ▼
        │   Send to Gemini OCR
        │        │
        │        ├─SUCCESS──► Extract student_id & answers
        │        │            │
        │        │            ▼
        │        │       Compare with answer_key
        │        │            │
        │        │            ▼
        │        │       Calculate score
        │        │            │
        │        │            ▼
        │        │       is_gemini_task_done = True
        │        │            │
        │        │            ▼
        │        │       Proceed to upload phase
        │        │
        │        └─FAIL─────► Show Gemini error
        │                     │
        │                     ▼
        │               Return to check menu
        │
        └─NO───► Skip Gemini (already processed)
                 │
                 ▼
Upload images to Cloudinary
        │
        ├─SUCCESS──► Save to Firebase RTDB
        │            │
        │            ▼
        │       Display score to teacher
        │            │
        │            ▼
        │       Show next options:
        │       [1] Next sheet
        │       [2] Exit
        │
        └─FAIL─────► Show upload error menu
                     │
                     ├─[1] Re-upload──► Retry upload
                     │
                     ├─[2] Proceed anyway──► Background retry + Next sheet
                     │
                     └─[3] Exit─────► Return to Home Menu
```

**Detailed Implementation:**

```python
def done_and_save_student_sheet():
    """Process and save student answer sheet"""
    
    global is_gemini_task_done, current_student_id, current_student_score
    
    # ===== PHASE 1: Gemini OCR (if not already done) =====
    if not is_gemini_task_done:
        lcd.show("Processing sheet...")
        logger.log("Starting Gemini OCR for student sheet")
        
        # Create collage if multiple pages
        if len(local_scanned_images) > 1:
            lcd.show("Creating collage...")
            collage_path = smart_collage.collage_images(local_scanned_images)
        else:
            collage_path = local_scanned_images[0]
        
        # Send to Gemini
        lcd.show("Extracting answers...")
        prompt = prompts.answer_sheet_prompt(current_total_questions)
        
        raw_response = gemini_client.gemini_with_retry(
            api_key=os.getenv("GEMINI_API_KEY"),
            image_path=collage_path,
            prompt=prompt,
            model="gemini-2.0-flash-exp",
            max_attempts=3
        )
        
        if not raw_response:
            logger.log("Gemini extraction failed", type="error")
            show_gemini_error_menu()
            return show_check_sheet_menu()
        
        # Sanitize response
        try:
            data = sanitizer.sanitize_gemini_json(raw_response)
            current_student_id = data.get("student_id")
            student_answers = data.get("answers")
            
            if current_student_id == "missing_uid":
                raise ValueError("Student ID not found")
            
        except Exception as e:
            logger.log(f"Sanitization error: {e}", type="error")
            lcd.show([
                "Invalid response!",
                str(e)[:20],
                "",
                "Press # to retry"
            ])
            keypad.wait_for_key("#")
            return show_check_sheet_menu()
        
        # Calculate score
        lcd.show("Calculating score...")
        result = scorer.calculate_score(
            answer_key=current_answer_key,
            answer_sheet=student_answers,
            exact_number_of_questions=current_total_questions
        )
        
        current_student_score = result["total_score"]
        
        logger.log(
            f"Student {current_student_id} scored "
            f"{current_student_score}/{current_total_questions}"
        )
        
        # Mark Gemini task as complete
        is_gemini_task_done = True
    
    # ===== PHASE 2: Upload to Cloudinary =====
    lcd.show("Uploading images...")
    logger.log(f"Uploading {len(local_scanned_images)} images")
    
    try:
        image_urls = image_uploader.batch_upload(
            local_scanned_images,
            folder=f"student-sheets/{current_assessment_uid}"
        )
        
        if not image_urls:
            raise Exception("Upload failed")
        
        logger.log(f"Upload success: {len(image_urls)} URLs")
        
    except Exception as e:
        logger.log(f"Upload error: {e}", type="error")
        return show_upload_error_menu_with_proceed()
    
    # ===== PHASE 3: Save to Firebase =====
    lcd.show("Saving to database...")
    
    success = firebase_rtdb_client.save_student_result(
        student_id=current_student_id,
        assessment_uid=current_assessment_uid,
        answer_sheet=student_answers,
        total_score=current_student_score,
        exact_number_of_questions=current_total_questions,
        image_urls=image_urls,
        teacher_uid=current_teacher_uid,
        is_final_score=True
    )
    
    if not success:
        logger.log("Firebase save failed", type="error")
        lcd.show([
            "Database save failed!",
            "",
            "Press # to continue"
        ])
        keypad.wait_for_key("#")
        return show_check_sheet_menu()
    
    # ===== PHASE 4: Display Result and Next Options =====
    lcd.show([
        f"Student: {current_student_id[:12]}",
        f"Score: {current_student_score}/{current_total_questions}",
        "",
        "[1] Next sheet",
        "[2] Exit to menu"
    ])
    
    while True:
        key = keypad.wait_for_key(valid_keys=["1", "2"])
        
        if key == "1":
            # Prepare for next sheet
            reset_student_sheet_state()
            return show_check_sheet_menu()
        
        elif key == "2":
            # Return to home
            reset_student_sheet_state()
            return HOME_MENU


def show_gemini_error_menu():
    """Display error when Gemini OCR fails"""
    
    lcd.show([
        "OCR extraction failed!",
        "",
        "Possible causes:",
        "- Poor image quality",
        "- API quota exceeded",
        "- Network issue",
        "",
        "Press # to retry"
    ])
    
    keypad.wait_for_key("#")


def show_upload_error_menu_with_proceed():
    """Enhanced upload error menu with proceed option"""
    
    lcd.show([
        "Image upload failed!",
        "",
        "[1] Retry upload",
        "[2] Proceed anyway",
        "[3] Exit to menu"
    ])
    
    while True:
        key = keypad.wait_for_key(valid_keys=["1", "2", "3"])
        
        if key == "1":
            # Retry upload
            return done_and_save_student_sheet()
        
        elif key == "2":
            # Proceed to next sheet with background retry
            lcd.show("Starting background retry...")
            
            # Launch background upload process
            from multiprocessing import Process
            
            def background_upload_retry():
                """Retry upload in background (max 3 attempts)"""
                for attempt in range(1, 4):
                    logger.log(f"Background upload attempt {attempt}/3")
                    try:
                        urls = image_uploader.batch_upload(
                            local_scanned_images,
                            folder=f"student-sheets/{current_assessment_uid}"
                        )
                        if urls:
                            # Update RTDB with URLs
                            firebase_rtdb_client.update_image_urls(
                                student_id=current_student_id,
                                assessment_uid=current_assessment_uid,
                                image_urls=urls
                            )
                            logger.log("Background upload succeeded")
                            break
                    except Exception as e:
                        logger.log(f"Background attempt {attempt} failed: {e}")
                        time.sleep(5)
                else:
                    # All attempts failed - save empty list
                    logger.log("All background upload attempts failed")
                    firebase_rtdb_client.update_image_urls(
                        student_id=current_student_id,
                        assessment_uid=current_assessment_uid,
                        image_urls=[]
                    )
                
                # Cleanup local files
                utils.delete_local_images(local_scanned_images)
            
            # Start background process
            p = Process(target=background_upload_retry)
            p.start()
            
            lcd.show([
                "Upload queued",
                "for background retry",
                "",
                "Press # for next sheet"
            ])
            keypad.wait_for_key("#")
            
            reset_student_sheet_state()
            return show_check_sheet_menu()
        
        elif key == "3":
            # Exit to home
            utils.delete_local_images(local_scanned_images)
            reset_student_sheet_state()
            return HOME_MENU


def reset_student_sheet_state():
    """Reset state variables for next student sheet"""
    global is_gemini_task_done, local_scanned_images, page_counter
    global current_student_id, current_student_score
    
    is_gemini_task_done = False
    local_scanned_images.clear()
    page_counter = 0
    current_student_id = None
    current_student_score = None
    
    utils.delete_local_images(local_scanned_images)
```

#### 7.3.5 Option [3] Cancel

**Flow:**

```python
def cancel_student_sheet_check():
    """Cancel student sheet checking and cleanup"""
    
    lcd.show("Cancelling...")
    logger.log("User cancelled student sheet check")
    
    utils.delete_local_images(local_scanned_images)
    reset_student_sheet_state()
    
    lcd.show("Cancelled", duration=2)
    return HOME_MENU
```

---

## 8. Error Handling

### 8.1 Error Categories

| Category | Examples | Recovery Strategy |
|---|---|---|
| **Hardware** | Scanner offline, keypad not responding | Display error, prompt reconnection, retry |
| **Network** | No internet, API timeout | Retry with exponential backoff, offline queue |
| **API** | Gemini quota exceeded, Cloudinary limit | Inform user, suggest retry later, fallback method |
| **Data** | Invalid JSON, missing fields | Show validation error, prompt rescan |
| **User** | Invalid input, timeout | Clear input, re-prompt with guidance |

### 8.2 Hardware Error Handling

#### Scanner Errors

```python
def handle_scanner_error(error_type: str):
    """Handle L3210 scanner errors"""
    
    if error_type == "not_connected":
        lcd.show([
            "Scanner not found!",
            "",
            "Check USB connection",
            "and power",
            "",
            "[1] Retry",
            "[2] Exit"
        ])
        
        choice = keypad.wait_for_key(valid_keys=["1", "2"])
        
        if choice == "1":
            if scanner.reconnect():
                lcd.show("Scanner connected!", duration=2)
                return True
            else:
                return handle_scanner_error("not_connected")
        else:
            return HOME_MENU
    
    elif error_type == "paper_jam":
        lcd.show([
            "Paper jam detected!",
            "",
            "Clear jam and",
            "press # to continue"
        ])
        keypad.wait_for_key("#")
        return True
    
    elif error_type == "timeout":
        lcd.show([
            "Scan timeout!",
            "",
            "[1] Retry scan",
            "[2] Cancel"
        ])
        
        choice = keypad.wait_for_key(valid_keys=["1", "2"])
        return choice == "1"
```

### 8.3 Network Error Handling

#### Cloudinary Upload Errors

```python
def handle_upload_error(error: Exception, context: str) -> str:
    """Handle Cloudinary upload failures"""
    
    error_msg = str(error).lower()
    
    if "timeout" in error_msg or "connection" in error_msg:
        lcd.show([
            "Network timeout!",
            "",
            "Check internet",
            "connection",
            "",
            "[1] Retry",
            "[2] Cancel"
        ])
        
        choice = keypad.wait_for_key(valid_keys=["1", "2"])
        return "retry" if choice == "1" else "cancel"
    
    elif "quota" in error_msg or "limit" in error_msg:
        lcd.show([
            "Upload limit reached!",
            "",
            "Contact admin to",
            "increase quota",
            "",
            "Press # to go back"
        ])
        keypad.wait_for_key("#")
        return "cancel"
    
    else:
        lcd.show([
            "Upload failed!",
            error_msg[:40],
            "",
            "[1] Retry",
            "[2] Cancel"
        ])
        
        choice = keypad.wait_for_key(valid_keys=["1", "2"])
        return "retry" if choice == "1" else "cancel"
```

#### Gemini API Errors

```python
def handle_gemini_error(error_type: str) -> bool:
    """Handle Gemini OCR errors"""
    
    if error_type == "quota_exceeded":
        lcd.show([
            "Gemini API quota",
            "exceeded!",
            "",
            "Try again in 1 hour",
            "or contact admin",
            "",
            "Press # to go back"
        ])
        keypad.wait_for_key("#")
        return False
    
    elif error_type == "invalid_image":
        lcd.show([
            "Invalid image format!",
            "",
            "Check scan quality",
            "and try again",
            "",
            "Press # to retry"
        ])
        keypad.wait_for_key("#")
        return True
    
    elif error_type == "extraction_failed":
        lcd.show([
            "OCR extraction failed!",
            "",
            "Possible causes:",
            "- Blurry image",
            "- Wrong document",
            "- Missing required fields",
            "",
            "Press # to retry"
        ])
        keypad.wait_for_key("#")
        return True
    
    else:
        lcd.show([
            "Gemini API error!",
            "",
            "Contact admin if",
            "problem persists",
            "",
            "Press # to retry"
        ])
        keypad.wait_for_key("#")
        return True
```

### 8.4 Firebase RTDB Error Handling

```python
def handle_firebase_error(operation: str, error: Exception):
    """Handle Firebase RTDB errors"""
    
    error_msg = str(error).lower()
    
    if "permission" in error_msg or "unauthorized" in error_msg:
        lcd.show([
            "Database access denied!",
            "",
            "Check authentication",
            "and database rules",
            "",
            "Press # to go back"
        ])
        keypad.wait_for_key("#")
        return HOME_MENU
    
    elif "network" in error_msg or "timeout" in error_msg:
        lcd.show([
            "Database timeout!",
            "",
            "[1] Retry",
            "[2] Cancel"
        ])
        
        choice = keypad.wait_for_key(valid_keys=["1", "2"])
        return "retry" if choice == "1" else "cancel"
    
    else:
        lcd.show([
            f"Database {operation} failed!",
            error_msg[:40],
            "",
            "Press # to go back"
        ])
        keypad.wait_for_key("#")
        return "cancel"
```

---

## 9. Implementation Notes

### 9.1 Development Roadmap

**Phase 1: Core Foundation (Week 1-2)**
- [ ] Set up Raspberry Pi environment
- [ ] Implement hardware modules (scanner, keypad, LCD)
- [ ] Create authentication system
- [ ] Build basic menu navigation

**Phase 2: Service Layer (Week 3-4)**
- [ ] Integrate Cloudinary upload
- [ ] Implement Gemini OCR client
- [ ] Build Firebase RTDB client
- [ ] Create sanitizer and scorer modules

**Phase 3: Workflows (Week 5-6)**
- [ ] Implement answer key scanning flow
- [ ] Implement student sheet checking flow
- [ ] Add image collage functionality
- [ ] Implement error handling

**Phase 4: Testing & Polish (Week 7-8)**
- [ ] End-to-end testing
- [ ] Error recovery testing
- [ ] Performance optimization
- [ ] User experience refinement

### 9.2 Testing Strategy

**Unit Tests:**
- Sanitizer normalization rules
- Scorer calculation logic
- Collage image stitching
- Input validation functions

**Integration Tests:**
- Scanner → Local storage
- Local storage → Cloudinary
- Cloudinary URL → Gemini
- Gemini response → Firebase

**Hardware Tests:**
- Scanner reliability (1000+ scans)
- Keypad input accuracy
- LCD display clarity
- Multi-page scanning

**End-to-End Tests:**
- Complete answer key workflow
- Complete student sheet workflow
- Error recovery scenarios
- Network interruption handling

### 9.3 Performance Considerations

**Target Metrics:**
- Single page scan: < 10 seconds
- Multi-page collage: < 5 seconds for 5 pages
- Cloudinary upload: < 15 seconds per image
- Gemini OCR: < 30 seconds per request
- Total cycle time: < 60 seconds per student

**Optimization Strategies:**
- Compress images before upload (JPEG quality 85%)
- Use Gemini SDK with upload_to_cloud=True for large images
- Implement circuit breaker to fail fast during outages
- Cache answer keys in memory to avoid repeated RTDB calls

### 9.4 Security Considerations

**Credentials:**
- Store API keys in environment variables or encrypted config
- Never log API keys or sensitive data
- Implement API key rotation schedule

**Data Protection:**
- Use HTTPS for all API calls
- Encrypt student data in transit
- Implement Firebase security rules to restrict access

**Privacy:**
- Auto-delete local scanned images after upload
- Implement data retention policy (e.g., delete after 1 year)
- Provide opt-out for cloud storage (local-only mode)

### 9.5 Future Enhancements

**Phase 2 Features:**
- Web dashboard for teachers to view results
- Export results to CSV/Excel
- Generate score distribution graphs
- Support for essay question grading
- Multi-language OCR support

**Phase 3 Features:**
- Mobile app for teachers
- Real-time student result notifications
- Class performance analytics
- Integration with Learning Management Systems (LMS)

---

## Appendix A: Configuration Files

### A.1 Environment Variables (.env)

```bash
# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Gemini
GEMINI_API_KEY=your_gemini_api_key

# Firebase
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_PROJECT_ID=your-project-id

# Hardware (optional)
SCANNER_DEVICE=/dev/usb/lp0
LCD_I2C_ADDRESS=0x27
KEYPAD_ROWS=4,17,27,22
KEYPAD_COLS=10,9,11
```

### A.2 Firebase Security Rules

```json
{
  "rules": {
    "answer_keys": {
      "$assessment_uid": {
        ".read": "auth != null && data.child('created_by').val() == auth.uid",
        ".write": "auth != null",
        ".validate": "newData.hasChildren(['assessment_uid', 'answer_key', 'exact_number_of_questions'])"
      }
    },
    "results": {
      "$assessment_uid": {
        "$student_id": {
          ".read": "auth != null",
          ".write": "auth != null",
          ".validate": "newData.hasChildren(['student_id', 'assessment_uid', 'total_score'])"
        }
      }
    }
  }
}
```

---

## Appendix B: Troubleshooting Guide

### B.1 Common Issues

| Issue | Cause | Solution |
|---|---|---|
| Scanner not detected | USB not connected / Driver issue | Check connection, reinstall driver |
| Gemini quota exceeded | Daily API limit reached | Wait 24 hours or upgrade plan |
| Cloudinary upload fails | Network issue / Quota exceeded | Check internet, verify quota |
| Firebase permission denied | Invalid authentication | Re-authenticate, check RTDB rules |
| OCR extraction inaccurate | Poor scan quality / Wrong prompt | Rescan with better lighting, adjust prompt |
| LCD not displaying | I2C address mismatch | Run `i2cdetect -y 1`, update address |

### B.2 Diagnostic Commands

```bash
# Check scanner status
lsusb | grep -i scanner

# Test LCD connection
i2cdetect -y 1

# View system logs
tail -f /var/log/grading-system.log

# Check network connectivity
ping -c 3 api.cloudinary.com
ping -c 3 generativelanguage.googleapis.com

# Monitor CPU/memory
htop
```

---

## Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0 | 2025-02-20 | System Architect | Initial specification |

---

**END OF SPECIFICATION**