# CheckMe: Grading System
> Teacher User Guide

---

## Table of Contents

- [What is CheckMe?](#what-is-checkme)
- [Before You Start](#before-you-start)
- [Paper Format Rules](#paper-format-rules)
- [Logging In](#logging-in)
- [Main Menu](#main-menu)
- [Scanning an Answer Key](#scanning-an-answer-key)
- [Checking Student Answer Sheets](#checking-student-answer-sheets)
- [Settings](#settings)
- [Keypad Reference](#keypad-reference)
- [Common Issues](#common-issues)

---

## What is CheckMe?

CheckMe is an automated grading machine that reads and scores student answer sheets using a scanner. You place the answer sheet on the scanner, press a button, and the system grades it automatically.

Results are saved to your school's database and can be viewed in the CheckMe mobile app.

---

## Before You Start

Make sure the following are ready:

- ✅ The CheckMe device is powered on
- ✅ The scanner is connected and warmed up
- ✅ You have the **CheckMe mobile app** installed on your phone
- ✅ Your answer sheets follow the CheckMe format

---

## Paper Format Rules

The CheckMe system uses AI (Gemini OCR) to read your test papers. For the best results and accurate scoring, your answer key and student answer sheets must follow these rules when you create them.

---

### Answer Key Paper Rules

**1. Assessment UID at the top**
Write or print the **Assessment UID** clearly at the very top of the answer key paper. This is the 8-character code from the mobile app (e.g., `QWER1234`). The system cannot save the answer key without it.

**2. Mark answers clearly**
The correct answer per question must be:
- Circled ⭕
- Underlined
- Written in the blank

If multiple marks exist for one item, the one that is **circled or underlined takes priority**. Never leave two marks without crossing one out — the system will mark it as unreadable.

**3. True/False answers — spell them out fully**
Always write `True` or `False` in full. Never use `T` or `F`.

| ✅ Correct | ❌ Wrong |
|---|---|
| `True` | `T` |
| `False` | `F` |

**4. Multiple Choice**
Use only `A`, `B`, `C`, or `D`. Circle or underline the correct letter.

**5. Enumeration answers**
Write the answer exactly as you expect it. The system will preserve the exact casing you write, so be consistent (e.g., always write `CPU` not `cpu`).

**6. Essay questions**
Essay questions are automatically detected and marked as **Pending** — they will not be auto-scored. You will need to manually score them in the mobile app.

**7. Numbering must be continuous**
Questions must be numbered continuously from `1` to the total number of questions with no gaps. If a question spans multiple pages, make sure the numbering continues without skipping.

**8. Missing or unscanned pages**
If a page is missing from the scan, the system will fill those question numbers with `missing_question`. Always make sure all pages are scanned in order.

**9. Write clearly — avoid faint or ambiguous marks**
Faint marks, accidental marks, or marks that are hard to read will be returned as `unreadable` and will not count toward the score.

---

### Student Answer Sheet Rules

Share these rules with your students before the exam so the system can read their sheets correctly.

**1. Student ID at the top**
Each student must write their **Student ID** clearly at the top of their answer sheet. If it is missing or unreadable, the result cannot be saved properly.

**2. Mark answers clearly**
The system recognizes the following as valid answer marks:
- Circled letter (e.g., circle around `A`)
- Filled or shaded bubble
- Checkmark next to a letter
- Written letter or text in a blank
- Underlined answer

**3. Cancelling an answer**
If a student wants to change an answer, they must **cross out the old answer** with a strikethrough, then mark the new one. Do not erase — erased marks may still be detected.

| Situation | What the system reads |
|---|---|
| Two marks, one crossed out | The non-crossed answer ✅ |
| Two marks, none crossed out | `unreadable` ❌ |
| Blank / no mark | `missing_answer` |
| Faint or unclear mark | `unreadable` |

**4. True/False answers — spell them out fully**
Students must write `True` or `False` in full. Never `T` or `F`.

**5. Multiple Choice**
Students should clearly circle or shade only one letter: `A`, `B`, `C`, or `D`.

**6. Essay questions**
Essay answers are detected automatically and will be marked as **Pending** for manual teacher review. Students should still write their essay answers normally.

**7. Numbering must match the answer key**
The student sheet must follow the same continuous question numbering as the answer key. The system expects exactly the same number of questions as declared when the answer key was scanned.

**8. Keep sheets clean and flat**
Crumpled, torn, or heavily smudged sheets may cause scanning errors. Instruct students to keep their answer sheets clean throughout the exam.

---

## Logging In

When the device starts, it will ask you to log in.

**Steps:**
1. Open the **CheckMe mobile app** on your phone
2. Tap **Generate Login Code**
3. You will see an **8-digit code** (e.g., `12345678`)
4. Enter the code using the keypad on the device
5. Press **`#`** to confirm

> ⚠️ The code expires in **30 seconds**. If it expires, generate a new one.

Once logged in, your session is saved. You won't need to log in again unless you log out or the device restarts.

---

## Main Menu

After logging in, you will see the **MAIN MENU**:

```
> Scan Answer Key
  Check Sheets
  Settings
```

**Navigation:**
| Key | Action |
|---|---|
| `2` | Move cursor up |
| `8` | Move cursor down |
| `*` | Select highlighted option |
| `#` | Go back / Cancel |

---

## Scanning an Answer Key

Do this **once per assessment** before checking student sheets.

> ⚠️ **Before you scan — prepare your answer key paper first.**
>
> The answer key sheet must have the **Assessment UID** written or printed at the **top of the paper**. The system reads this code to identify which assessment the answer key belongs to.
>
> **How to get your Assessment UID:**
> 1. Open the **CheckMe mobile app**
> 2. Tap **Create Assessment**
> 3. You will receive an **8-character alphanumeric code** (e.g., `QWER1234`)
> 4. Write or print this code clearly at the **top of your answer key paper**
>
> Without this code written on the paper, the system will not be able to save the answer key.

**Steps:**

1. From the Main Menu, select **Scan Answer Key**
2. Enter the **total number of questions** using the keypad, then press **`#`**
   - Example: for 50 questions, press `5` `0` `#`
3. The **SCAN ANSWER KEY** menu will appear:

```
> Scan
  Done & Save
  Cancel
```

4. Select **Scan**
5. Place your **answer key sheet** face-down on the scanner
6. Press **`#`** to start scanning
7. Wait for the device to finish scanning
8. Repeat steps 4–7 if your answer key has **multiple pages**
9. When all pages are scanned, select **Done & Save**
10. The device will process and save the answer key
11. When done, you can choose to **Scan Another** answer key or **Exit** to the Main Menu

---

## Checking Student Answer Sheets

**Steps:**

1. From the Main Menu, select **Check Sheets**
2. The device will load your saved answer keys
3. Select which **assessment** you want to grade
4. The **CHECK SHEETS** menu will appear:

```
> Scan
  Done & Save
  Cancel
```

5. Select **Scan**
6. Place the **student's answer sheet** face-down on the scanner
7. Press **`#`** to start scanning
8. Wait for the device to finish
9. Repeat steps 5–8 if the student's sheet has **multiple pages**
10. Select **Done & Save**
11. The device will:
    - Read the student's answers
    - Compare with the answer key
    - Calculate the score
    - Save the result to the database
12. The score will be displayed on screen
13. Select **Next sheet** to grade another student, or **Cancel** to go back

### About Essay Questions

If the answer key contains essay-type questions, the system will mark them as **Pending**. These need to be manually scored by the teacher in the mobile app.

### Score Mismatch Warning

If the number of answers found doesn't match the answer key, the device will show a warning. The score will still be recorded but may be incomplete.

---

## Settings

From the Main Menu, select **Settings**:

```
> Logout
  Shutdown
  Back
```

### Logout
Clears your session from the device. The next person to use the device will need to log in with their own code.

### Shutdown
Safely turns off the Raspberry Pi. Always use this instead of unplugging the power.

1. Select **Shutdown**
2. Press **`#`** to confirm, or **`*`** to cancel
3. Wait for the screen to go blank before unplugging

### Back
Returns to the Main Menu.

---

## Keypad Reference

```
[1] [2] [3]
[4] [5] [6]
[7] [8] [9]
[*] [0] [#]
```

| Key | Common Use |
|---|---|
| `0`–`9` | Enter numbers |
| `#` | Confirm / Select / Submit |
| `*` | Cancel / No |
| `2` | Scroll up in menus |
| `8` | Scroll down in menus |
| `*` | Select highlighted menu item |

---

## When the System is Deployed

Once the CheckMe device has been set up by your administrator, it runs **automatically**. You do not need to do anything technical — just power it on.

### Turning the Device On

1. Plug in the power cable to the Raspberry Pi
2. Wait for the LCD screen to light up
3. The screen will show **"Initializing..."** for a few seconds
4. If you are already logged in from a previous session, the **Main Menu** will appear directly
5. If not, the **Login screen** will appear — follow the [Logging In](#logging-in) steps

### Turning the Device Off

**Always use the proper shutdown procedure.** Do not unplug the power directly — this can corrupt the system.

1. From the Main Menu, go to **Settings**
2. Select **Shutdown**
3. Press **`#`** to confirm
4. Wait for the LCD screen to go **blank**
5. Only then unplug the power cable

### After a Power Outage or Accidental Unplug

If the device was shut down improperly (power cut), plug it back in and it will start normally. If the LCD does not turn on after 30 seconds, contact your administrator.

### Session Persistence

Your login session is saved on the device. After a normal shutdown and restart, you will be taken directly to the Main Menu without needing to log in again.

Your session will be cleared if:
- You manually **Logout** from Settings
- An administrator resets the device

---

## Common Issues

**The device shows "Login failed!"**
- Make sure you entered the code correctly
- Generate a new code in the app (the old one may have expired)
- Check that your phone has internet connection

**The device shows "Scan failed!"**
- Make sure the scanner is on and connected
- Make sure the sheet is placed correctly (face-down)
- Try placing the sheet again and scan once more

**The device shows "No answer keys! Scan key first."**
- You need to scan the answer key for this assessment before checking student sheets
- Go to **Scan Answer Key** first

**The device shows "INVALID assesUid"**
- The assessment ID on the answer key was not found in the database
- Make sure the assessment was created in the mobile app first
- Contact your system administrator

**The device shows "Extraction failed!"**
- The system had trouble reading the sheet
- Make sure the sheet is clean, flat, and properly aligned
- Try scanning again

**The score seems wrong**
- Check that the answer sheet format matches the expected CheckMe format
- If essay questions are present, the score shown is partial — check the app for the full result
- Contact your system administrator if the issue persists