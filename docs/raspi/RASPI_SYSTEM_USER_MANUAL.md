# CheckMe: Grading System
*Teacher User Guide*

---

## What is CheckMe?

CheckMe is an automated grading machine that reads and scores student answer sheets using a scanner. You place the answer sheet on the scanner, press a button, and the system grades it automatically. Results are saved to your school's database and can be viewed in the CheckMe mobile app.

---

## Before You Start

Make sure the following are ready before using the device:

- The CheckMe device is powered on
- The scanner is connected and warmed up
- You have the CheckMe mobile app installed on your phone
- Your answer sheets follow the CheckMe paper format rules

---

## Paper Format Rules

The CheckMe system uses AI (Gemini OCR) to read your test papers. For the best results and accurate scoring, your answer key and student answer sheets must follow these rules.

### Answer Key Paper Rules

#### 1. Assessment UID at the top

Write or print the Assessment UID clearly at the very top of the answer key paper. This is the 8-character code from the mobile app (e.g., `QWER1234`). The system cannot save the answer key without it.

#### 2. Mark answers clearly

The correct answer per question must be circled, underlined, or written in the blank. If multiple marks exist for one item, the circled or underlined one takes priority. Never leave two marks without crossing one out.

#### 3. True/False answers

Always write True or False in full. Never use T or F.

| Correct | Wrong |
|---------|-------|
| True    | T     |
| False   | F     |

#### 4. Multiple Choice

Use only A, B, C, or D. Circle or underline the correct letter.

#### 5. Essay questions

Essay questions are automatically detected and marked as **Pending**. You will manually score them in the mobile app.

#### 6. Numbering must be continuous

Questions must be numbered continuously from 1 to the total number of questions with no gaps. If a question spans multiple pages, numbering must continue without skipping.

#### 7. Write clearly

Faint marks, accidental marks, or ambiguous marks will be returned as unreadable and will not count toward the score.

---

### Student Answer Sheet Rules

Share these rules with your students before the exam.

#### 1. Student ID at the top

Each student must write their Student ID clearly at the top of their answer sheet. If it is missing or unreadable, the result cannot be saved properly.

#### 2. Mark answers clearly

The system recognizes: circled letter, filled or shaded bubble, checkmark next to a letter, written letter in a blank, or underlined answer.

#### 3. Cancelling an answer

If a student wants to change an answer, they must cross out the old answer with a strikethrough, then mark the new one. Do not erase.

| Situation                        | What the system reads             |
|----------------------------------|-----------------------------------|
| Two marks, one crossed out       | The non-crossed answer is read    |
| Two marks, none crossed out      | Marked as unreadable              |
| Blank / no mark                  | Marked as `missing_answer`        |
| Faint or unclear mark            | Marked as unreadable              |

#### 4. Keep sheets clean and flat

Crumpled, torn, or heavily smudged sheets may cause scanning errors.

---

## Logging In

When the device starts, it will ask you to log in.

1. Open the CheckMe mobile app on your phone
2. Tap **Generate Login Code**
3. You will see an 8-digit code (e.g., `12345678`)
4. Enter the code using the keypad on the device
5. Press `#` to confirm

> **⚠ WARNING** — The code expires in 30 seconds. If it expires, generate a new one in the app.

Once logged in, your session is saved. You will not need to log in again unless you log out or the device restarts.

---

## Main Menu

After logging in, you will see the **MAIN MENU**. Navigate using these keys:

| Key | Action                    |
|-----|---------------------------|
| `2` | Move cursor up            |
| `8` | Move cursor down          |
| `*` | Select highlighted option |
| `#` | Go back / Cancel          |

---

## Mobile App — Managing Assessments

### Creating an Assessment

1. Open the CheckMe mobile app
2. Navigate to your subject dashboard
3. Tap **Create Assessment**
4. Enter an assessment name
5. Select the assessment type: **Quiz** or **Exam**
6. Choose UID mode: **Auto-generate** or **Enter existing UID**
7. Tap **Create**

> **💡 TIP** — Write the Assessment UID at the top of your answer key paper immediately after creating it.

---

### 🆕 Entering an Existing Assessment UID

If another teacher has already printed a test paper with an Assessment UID, you can reuse that same UID for your own account. This is useful when multiple teachers use the same exam paper.

1. Tap **Create Assessment**
2. Enter the assessment name and type
3. Tap **Enter existing UID** in the Assessment UID toggle
4. Type the 8-character UID from the printed test paper
5. Tap **Create**

> **💡 TIP** — If the teacher who owns that UID has shared their answer key publicly, it will be automatically copied to your account. You will see a confirmation in the success message.

---

### 🆕 Renaming an Assessment

You can rename an assessment or change its type after creation.

1. Go to your subject dashboard
2. Find the assessment card you want to edit
3. Tap the **pencil icon** on the card
4. Edit the name or change the type
5. Tap **Save**

> **Note:** The Assessment UID cannot be changed after creation.

---

## Answer Keys

### Viewing Answer Keys

From your subject dashboard, tap **Answer Keys** to see all assessments and their scanned answer keys. Each card shows:

- **Scanned** badge if the answer key has been processed by the Raspi
- **Missing** badge if no answer key has been scanned yet
- Number of questions and last updated date
- Scanned answer key images (tap to view full screen)

### Editing an Answer Key

If the Raspi OCR misread an answer, you can correct it manually:

1. Open the **Answer Keys** screen
2. Tap on the assessment card to expand it
3. Find the question with the wrong answer
4. Tap the **pencil icon** on that question row
5. Enter the correct answer and tap **Save**

> **💡 TIP** — If students have already been scored, you will be asked whether to re-score all existing answer sheets automatically.

---

### 🆕 Sharing an Answer Key Publicly

If you want another teacher to be able to use your scanned answer key, you can share it publicly. Only teachers who import the same Assessment UID will receive a copy.

1. Open the **Answer Keys** screen
2. Tap on the assessment card with a scanned key
3. Scroll to the bottom of the expanded card
4. Tap **Share Publicly**
5. Confirm the share

A **Shared** badge will appear on the card. You can unshare at any time by tapping **Unshare Answer Key** — only you can unshare your own shared keys.

> **⚠ WARNING** — Teachers who have already copied your shared answer key will keep their copy even after you unshare.

---

## Scanning an Answer Key (Raspi)

Do this once per assessment before checking student sheets.

> **⚠ WARNING** — The answer key sheet must have the Assessment UID written or printed at the top. Without it, the system cannot save the answer key.

1. From the Raspi Main Menu, select **Scan Answer Key**
2. Enter the total number of questions using the keypad, then press `#`
3. The **SCAN ANSWER KEY** menu will appear
4. Select **Scan**
5. Place your answer key sheet **face-down** on the scanner
6. Press `#` to start scanning
7. Wait for the device to finish scanning
8. Repeat if your answer key has multiple pages
9. When all pages are scanned, select **Done & Save**
10. When done, choose to **Scan Another** or **Exit to Main Menu**

---

## Checking Student Answer Sheets (Raspi)

1. From the Raspi Main Menu, select **Check Sheets**
2. The device will load your saved answer keys
3. Select which assessment you want to grade
4. The **CHECK SHEETS** menu will appear
5. Select **Scan**
6. Place the student answer sheet **face-down** on the scanner
7. Press `#` to start scanning
8. Repeat if the student sheet has multiple pages
9. Select **Done & Save**
10. The device will read answers, compare with the key, calculate score, and save
11. Select **Next sheet** to grade another student, or **Cancel** to go back

### About Essay Questions

Essay questions are marked as **Pending** and must be manually scored in the mobile app.

---

## Viewing and Exporting Scores

### Viewing Scores

From the subject dashboard, tap **View Scores** on an assessment card to see all student results. The screen shows:

- Total scanned, pending, and not-yet-scanned students
- Class average percentage
- Individual student scores with percentage and grade
- Students who have not yet been scanned

---

### 🆕 Exporting Scores to Excel

You can download a complete grade sheet as an Excel file (`.xlsx`) directly from the app.

1. Open the **View Scores** screen for an assessment
2. Tap **Export Excel** in the header area
3. Choose your preferred sort order:
   - Alphabetical by First Name
   - Alphabetical by Last Name
   - By Student ID (Numeric)
4. Tap **Download**
5. The file will open in your device's share sheet — save or send as needed

The exported file includes:

- Assessment name, UID, and type in the header rows
- All scanned students with score, percentage, grade, and scan date
- All enrolled students who have not yet been scanned, marked as *No Answer Sheet Scanned*

---

## Raspi Settings

From the Raspi Main Menu, select **Settings**:

### Logout

Clears your session from the device. The next person to use the device will need to log in with their own code.

### Shutdown

Safely turns off the Raspberry Pi. Always use this instead of unplugging the power.

1. Select **Shutdown**
2. Press `#` to confirm, or `*` to cancel
3. Wait for the screen to go blank before unplugging

---

## Keypad Reference

| Key   | Common Use                |
|-------|---------------------------|
| `0–9` | Enter numbers             |
| `#`   | Confirm / Select / Submit |
| `*`   | Cancel / No               |
| `2`   | Scroll up in menus        |
| `8`   | Scroll down in menus      |

---

## Common Issues

| Issue                     | What to do |
|---------------------------|------------|
| **Login failed!**         | Make sure you entered the code correctly. Generate a new code — the old one may have expired. Check that your phone has internet connection. |
| **Scan failed!**          | Make sure the scanner is on and connected. Place the sheet correctly (face-down) and try again. |
| **No answer keys!**       | You need to scan the answer key for this assessment before checking student sheets. Go to **Scan Answer Key** first. |
| **INVALID assessmentUid** | The assessment ID on the answer key was not found in the database. Make sure the assessment was created in the mobile app first. |
| **Extraction failed!**    | The system had trouble reading the sheet. Make sure the sheet is clean, flat, and properly aligned. Try scanning again. |
| **Score seems wrong**     | Check that the answer sheet format matches the CheckMe format. If essay questions are present, the score is partial — check the app for the full result. |
| **Export Excel fails**    | Ensure you have internet connection. If the error persists, try refreshing the scores screen and exporting again. |