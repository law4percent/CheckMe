# CheckMe: Grading System
> Raspberry Pi Hardware Interface — Developer Documentation

---

## Table of Contents

- [Overview](#overview)
- [Hardware Requirements](#hardware-requirements)
- [GPIO Pin Configuration](#gpio-pin-configuration)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [System Flow](#system-flow)
- [Menu Modules](#menu-modules)
- [Services](#services)
- [Scanner Setup](#scanner-setup)
- [Troubleshooting](#troubleshooting)

---

## Overview

CheckMe is an automated grading system that runs on a Raspberry Pi. It uses a flatbed scanner to capture answer sheets and answer keys, sends images to **Gemini OCR** for extraction, scores student answers automatically, uploads images to **Cloudinary**, and saves results to **Firebase RTDB**.

**Core capabilities:**
- Teacher authentication via 8-digit temporary code from the mobile app
- Scan and process answer keys (multi-page supported)
- Scan and grade student answer sheets (multi-page supported)
- Automatic answer comparison and scoring
- Essay answer detection (flagged as pending, not auto-scored)
- Firebase RTDB persistence
- Cloudinary image storage

---

## Hardware Requirements

| Component | Model / Spec |
|---|---|
| Raspberry Pi | Raspberry Pi 4B |
| LCD Display | I2C LCD — 16x2 or 20x4 |
| Keypad | 4x3 Matrix Keypad |
| Scanner | Epson L3210 |

---

## GPIO Pin Configuration

### Keypad (4x3 Matrix)

> Replace the images below with your actual wiring diagrams.

**Row Pins (BCM):** `19, 21, 20, 16`  
**Column Pins (BCM):** `12, 13, 6`

```
Default Key Layout:
[1] [2] [3]
[4] [5] [6]
[7] [8] [9]
[*] [0] [#]
```

📷 **Keypad Wiring Diagram:**
```
[ Insert keypad_wiring.png here ]
```

---

### LCD I2C

**I2C Address:** `0x27` or `0x3F` (detected automatically at startup)  
**Bus:** I2C Bus 1 (default on Raspberry Pi 4B)

📷 **LCD Wiring Diagram:**
```
[ Insert lcd_wiring.png here ]
```

---

## Project Structure

```
raspi_code/
├── main.py                         # Entry point
├── requirements.txt                # Python dependencies
├── config/
│   ├── .env                        # Environment variables (not committed)
│   ├── .env.example                # Environment variable template
│   └── firebase-credentials.json  # Firebase service account (not committed)
├── menus/
│   ├── menu_scan_answer_key.py     # Option 1: Scan Answer Key flow
│   └── menu_check_answer_sheets.py # Option 2: Check Answer Sheets flow
├── services/
│   ├── auth.py                     # Teacher authentication
│   ├── lcd_hardware.py             # LCD I2C driver
│   ├── keypad_hardware.py          # 4x3 Keypad driver
│   ├── l3210_scanner_hardware.py   # Epson L3210 scanner interface
│   ├── firebase_rtdb_client.py     # Firebase RTDB (Admin SDK)
│   ├── cloudinary_client.py        # Cloudinary image uploader
│   ├── gemini_client.py            # Gemini OCR client
│   ├── smart_collage.py            # Multi-page image collage builder
│   ├── scorer.py                   # Answer comparison and scoring logic
│   ├── sanitizer.py                # Gemini JSON response sanitizer
│   ├── prompts.py                  # Gemini prompt templates
│   ├── logger.py                   # Logging utility
│   └── utils.py                    # File and path utilities
├── credentials/
│   └── cred.txt                    # Local session cache (auto-generated)
├── scans/
│   ├── answer_keys/                # Scanned answer key images
│   └── answer_sheets/              # Scanned student sheet images
└── docs/
    └── raspi/
        └── RASPI_L3210_SETUP.md    # Scanner setup guide
```

---

## Prerequisites

- **Python:** 3.12 or above
- **OS:** Raspberry Pi OS Desktop (Bookworm recommended)
- **System packages:** See `requirements.txt` and `docs/raspi/RASPI_L3210_SETUP.md`

Enable I2C on your Raspberry Pi:
```bash
sudo raspi-config
# Interface Options → I2C → Enable
```

---

## Installation

**1. Clone the repository**
```bash
git clone <your-repo-url>
cd raspi_code
```

**2. Create and activate a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up scanner**

Follow the full scanner setup guide:
```
docs/raspi/RASPI_L3210_SETUP.md
```

**5. Set up Firebase credentials**

Place your Firebase service account JSON file at:
```
config/firebase-credentials.json
```

**6. Configure environment variables**
```bash
cp config/.env.example config/.env
# Edit config/.env with your values
```

---

## Configuration

All configuration lives in `config/.env`. See `config/.env.example` for the full list of required variables:

```
raspi_code/config/.env.example
```

Key variables include:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Gemini API key |
| `GEMINI_MODEL` | Gemini model name |
| `GEMINI_PREFERRED_METHOD` | `sdk` or `rest` |
| `CLOUDINARY_NAME` | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `CLOUDINARY_ANSWER_SHEETS_PATH` | Cloudinary folder for answer sheets |
| `FIREBASE_RTDB_BASE_REFERENCE` | Firebase RTDB URL |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase service account JSON |
| `USER_CREDENTIALS_FILE` | Path to local session cache file |
| `ANSWER_KEYS_PATH` | Local directory for scanned answer key images |
| `ANSWER_SHEETS_PATH` | Local directory for scanned student sheet images |
| `SCAN_DEBOUNCE_SECONDS` | Scanner debounce delay in seconds |

---

## Running the System

```bash
cd raspi_code
source venv/bin/activate
python main.py
```

To run on boot (systemd):

```bash
# Create a service file at /etc/systemd/system/checkme.service
# Then:
sudo systemctl enable checkme
sudo systemctl start checkme
```

---

## System Flow

```
System Start
    │
    ├─ Setup (LCD, Keypad, Auth)
    │
    ├─ Authentication
    │   ├─ Check cred.txt → AUTHENTICATED → Main Menu
    │   └─ NOT AUTHENTICATED → Enter 8-digit code from mobile app
    │           └─ Validate via Firebase RTDB → Save credentials → Main Menu
    │
    └─ Main Menu
        ├─ [0] Scan Answer Key  → menu_scan_answer_key.run()
        ├─ [1] Check Sheets     → menu_check_answer_sheets.run()
        └─ [2] Settings
                ├─ Logout   → Clear cred.txt → Restart process
                ├─ Shutdown → Confirm → sudo shutdown -h now
                └─ Back     → Main Menu
```

---

## Menu Modules

### `menus/menu_scan_answer_key.py`

Handles the full answer key ingestion flow:

1. Ask teacher for total number of questions (1–99)
2. Show **SCAN ANSWER KEY** menu loop:
   - **[0] Scan** — Trigger scanner, append file to list, loop back
   - **[1] Done & Save** — Collage (if multi-page) → Gemini OCR → Extract `assessment_uid` + `answer_key` → Validate in RTDB → Save → Prompt to scan another or exit
   - **[2] Cancel** — Delete local scans, return to Main Menu

Error handling at each step: Cloudinary upload failure, collage failure, Gemini extraction failure, Firebase save failure — each shows a **Retry / Exit** menu.

---

### `menus/menu_check_answer_sheets.py`

Handles the full student sheet grading flow:

1. Load answer keys from Firebase RTDB
2. Teacher selects which assessment to grade against
3. Validate assessment exists in RTDB
4. Show **CHECK SHEETS** menu loop:
   - **[0] Scan** — Trigger scanner, append file to list, loop back
   - **[1] Done & Save** — Collage (if multi-page) → Gemini OCR → Extract `student_id` + `answers` → Score vs answer key → Upload to Cloudinary → Save to RTDB → Reset for next student
   - **[2] Cancel** — Delete local scans, return to Main Menu

Scoring features:
- Automatic answer comparison per question
- Essay answers detected and flagged as `pending` (not auto-scored, `is_final_score = False`)
- Warning shown if scanned answer count doesn't match answer key count

---

## Services

| Service | Description |
|---|---|
| `auth.py` | Manages `cred.txt` session, validates 8-digit temp codes via Firebase |
| `lcd_hardware.py` | I2C LCD driver with scrollable menus, multi-line display |
| `keypad_hardware.py` | 4x3 matrix keypad GPIO driver with debounce |
| `l3210_scanner_hardware.py` | Epson L3210 scanner interface via SANE |
| `firebase_rtdb_client.py` | Firebase Admin SDK RTDB client (answer keys, student results, temp codes) |
| `cloudinary_client.py` | Single and batch image upload, delete |
| `gemini_client.py` | Gemini OCR with retry logic |
| `smart_collage.py` | Stitches multiple scanned pages into one image for Gemini |
| `scorer.py` | Compares student answers to answer key, calculates score and breakdown |
| `sanitizer.py` | Cleans and parses raw Gemini JSON responses |
| `prompts.py` | Gemini prompt templates for answer key and answer sheet extraction |
| `logger.py` | Timestamped logger with log levels |
| `utils.py` | `normalize_path`, `delete_files`, `delete_file`, `join_and_ensure_path` |

---

## Scanner Setup

Full Epson L3210 setup instructions (SANE driver, permissions, testing):

```
docs/raspi/RASPI_L3210_SETUP.md
```

---

## Troubleshooting

**LCD not detected**
```bash
i2cdetect -y 1
# Should show 0x27 or 0x3F
```

**Scanner not found**
```bash
scanimage -L
# Should list the Epson L3210
```

**Firebase initialization error**
- Confirm `config/firebase-credentials.json` exists and is valid
- Confirm `FIREBASE_RTDB_BASE_REFERENCE` in `.env` matches your project URL

**`SCAN_DEBOUNCE_SECONDS` crash on startup**
- Ensure this variable is set in `config/.env` as an integer string e.g. `SCAN_DEBOUNCE_SECONDS=3`

**Keypad not responding**
- Check BCM pin assignments in `services/keypad_hardware.py`
- Confirm I2C and GPIO are enabled via `raspi-config`

**Gemini returns None or bad JSON**
- Check `GEMINI_API_KEY` is valid
- Check quota limits on your Gemini project
- Review raw responses in logs (debug level)