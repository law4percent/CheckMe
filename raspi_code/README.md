# CheckMe: Grading System
> Raspberry Pi Hardware Interface — Developer Documentation

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
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

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TEACHER (Mobile App)                         │
│                     React Native (Expo SDK 52)                      │
│                                                                     │
│   ┌─────────────┐   ┌──────────────┐   ┌───────────────────────┐  │
│   │  Auth Flow  │   │  Answer Keys │   │   Student Scores      │  │
│   │  Temp Code  │   │  View / Edit │   │   View / Re-score     │  │
│   └──────┬──────┘   └──────┬───────┘   └───────────┬───────────┘  │
└──────────┼────────────────┼───────────────────────┼───────────────┘
           │                │                        │
           ▼                ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Firebase RTDB                                  │
│               (asia-southeast1 — Real-time Sync)                    │
│                                                                     │
│  /users_temp_code/{code}         /answer_keys/{teacher}/{uid}       │
│  /users/teachers/{uid}           /answer_sheets/{teacher}/{uid}     │
│  /enrollments/{teacher}/{subj}   /assessments/{teacher}/{uid}       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Read / Write (Admin SDK)
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                    Raspberry Pi 4B                                  │
│                  Raspberry Pi OS Bookworm 32-bit                    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      main.py                                 │  │
│  │              (Entry point — orchestrates all)                │  │
│  └──────┬───────────────────┬──────────────────┬───────────────┘  │
│         │                   │                  │                   │
│         ▼                   ▼                  ▼                   │
│  ┌─────────────┐   ┌───────────────┐   ┌─────────────────┐       │
│  │  auth.py    │   │menu_scan_     │   │menu_check_      │       │
│  │  Temp code  │   │answer_key.py  │   │answer_sheets.py │       │
│  │  login      │   │               │   │                 │       │
│  └─────────────┘   └──────┬────────┘   └────────┬────────┘       │
│                            │                     │                  │
│         ┌──────────────────┴─────────────────────┘                 │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                        Services                              │  │
│  │                                                              │  │
│  │  lcd_hardware.py      keypad_hardware.py                     │  │
│  │  l3210_scanner.py     smart_collage.py                       │  │
│  │  gemini_client.py     firebase_rtdb_client.py                │  │
│  │  cloudinary_client.py scorer.py  sanitizer.py                │  │
│  └──────┬──────────┬──────────────────┬──────────────┬─────────┘  │
│         │          │                  │              │              │
└─────────┼──────────┼──────────────────┼──────────────┼─────────────┘
          │          │                  │              │
          ▼          ▼                  ▼              ▼
   ┌──────────┐ ┌─────────┐    ┌──────────────┐ ┌──────────────┐
   │I2C LCD   │ │ Keypad  │    │ Epson L3210  │ │  Cloudinary  │
   │16x2/20x4 │ │ 4x3     │    │ Scanner      │ │  Image Store │
   │ 0x27     │ │ Matrix  │    │ (SANE/epson2)│ │              │
   └──────────┘ └─────────┘    └──────────────┘ └──────────────┘
                                       │
                                       ▼
                               ┌──────────────┐
                               │ Google Gemini│
                               │  OCR / AI    │
                               │  Extraction  │
                               └──────────────┘
```

### Data Flow — Scan Answer Key

```
Teacher presses [Scan]
        │
        ▼
Epson L3210 → scanimage → PNG saved locally
        │
        ▼ (if multi-page)
smart_collage.py → stitch pages into one image
        │
        ▼
gemini_client.py → OCR → extract assessment_uid + answer_key JSON
        │
        ▼
sanitizer.py → validate + clean JSON response
        │
        ├──▶ cloudinary_client.py → upload PNG → get public URL
        │
        └──▶ firebase_rtdb_client.py → save to /answer_keys/{teacher}/{uid}
```

### Data Flow — Check Answer Sheets

```
Teacher selects assessment → scans student sheet
        │
        ▼
Epson L3210 → scanimage → PNG saved locally
        │
        ▼ (if multi-page)
smart_collage.py → stitch pages
        │
        ▼
gemini_client.py → OCR → extract student_id + student answers JSON
        │
        ▼
scorer.py → compare vs answer_key → calculate score + breakdown
        │
        ├──▶ cloudinary_client.py → upload PNG → get public URL
        │
        └──▶ firebase_rtdb_client.py → save to /answer_sheets/{teacher}/{uid}/{student_id}
```

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

**All pins used (BCM):** `4, 5, 6, 7, 11, 12, 17`

**Key-to-pin mapping** (discovered via hardware scan):

| Key | OUT pin | IN pin |
|-----|---------|--------|
| `1` | 6       | 5      |
| `2` | 4       | 5      |
| `3` | 5       | 11     |
| `4` | 6       | 17     |
| `5` | 4       | 17     |
| `6` | 11      | 17     |
| `7` | 6       | 12     |
| `8` | 4       | 12     |
| `9` | 11      | 12     |
| `*` | 6       | 7      |
| `0` | 4       | 7      |
| `#` | 7       | 11     |

```
Keypad Layout:
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

**I2C Address:** `0x27` (detected via `i2cdetect -y 1`)
**Bus:** I2C Bus 1 (default on Raspberry Pi 4B)

| LCD Pin | Raspberry Pi Pin |
|---------|-----------------|
| GND     | Pin 6 (GND)     |
| VCC     | Pin 2 (5V)      |
| SDA     | Pin 3 (GPIO 2)  |
| SCL     | Pin 5 (GPIO 3)  |

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

- **Python:** 3.11 or above
- **OS:** Raspberry Pi OS Bookworm 32-bit (armhf) — headless
- **Kernel:** 32-bit userland required (`dpkg --print-architecture` = `armhf`)
- **System packages:** See `setup.sh` in project root

Enable I2C on your Raspberry Pi:
```bash
# Add to /boot/firmware/config.txt (Bookworm)
dtparam=i2c_arm=on

# Load module without reboot
sudo modprobe i2c-dev

# Add to /etc/modules for persistence on boot
echo "i2c-dev" | sudo tee -a /etc/modules
```

---

## Installation

**1. Clone the repository**
```bash
git clone <your-repo-url>
cd CheckMe
```

**2. Run the setup script**
```bash
chmod +x setup.sh
./setup.sh
```

The setup script handles:
- System packages (SANE, OpenCV deps, I2C tools, libopenblas)
- Python virtual environment (`~/checkme-env`) with piwheels
- All Python dependencies
- SANE backend configuration for Epson L3210
- I2C enable in `/boot/firmware/config.txt`
- User group assignments (scanner, i2c, gpio, lp)

**3. Reboot after setup**
```bash
sudo reboot
```

**4. Set up Firebase credentials**
```
raspi_code/config/firebase-credentials.json
```

**5. Configure environment variables**
```bash
cp raspi_code/config/.env.example raspi_code/config/.env
nano raspi_code/config/.env
```

---

## Configuration

All configuration lives in `config/.env`:

| Variable | Description | Example |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API key | `AIzaSy...` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash-preview-04-17` |
| `GEMINI_PREFERRED_METHOD` | `sdk` or `rest` | `sdk` |
| `CLOUDINARY_NAME` | Cloudinary cloud name | `dyls...` |
| `CLOUDINARY_API_KEY` | Cloudinary API key | `628...` |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | `6F7...` |
| `CLOUDINARY_ANSWER_KEYS_PATH` | Cloudinary folder for answer keys | `answer-keys` |
| `CLOUDINARY_ANSWER_SHEETS_PATH` | Cloudinary folder for answer sheets | `answer-sheets` |
| `FIREBASE_RTDB_BASE_REFERENCE` | Firebase RTDB URL | `https://project.asia-southeast1.firebasedatabase.app` |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase service account JSON | `config/firebase-credentials.json` |
| `USER_CREDENTIALS_FILE` | Path to local session cache | `credentials/cred.txt` |
| `ANSWER_KEYS_PATH` | Local dir for scanned answer key images | `scans/answer_keys` |
| `ANSWER_SHEETS_PATH` | Local dir for scanned student sheet images | `scans/answer_sheets` |
| `MAX_QUESTION_DIGITS` | Max digits for question count input | `2` |
| `SCAN_DEBOUNCE_SECONDS` | Scanner debounce delay (seconds) | `3` |
| `INPUT_TIMEOUT_SECONDS` | Keypad input timeout (seconds) | `300` |

---

## Running the System

```bash
source ~/checkme-env/bin/activate
cd ~/CheckMe/raspi_code
python main.py
```

To run on boot (systemd):

```bash
sudo nano /etc/systemd/system/checkme.service
```

```ini
[Unit]
Description=CheckMe Grading System
After=network.target

[Service]
User=checkme
WorkingDirectory=/home/checkme/CheckMe/raspi_code
ExecStart=/home/checkme/checkme-env/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable checkme
sudo systemctl start checkme
sudo systemctl status checkme
```

---

## System Flow

```
System Start
    │
    ├─ Setup (LCD, Keypad, Scanner, Auth)
    │
    ├─ Authentication
    │   ├─ Check cred.txt → AUTHENTICATED → Main Menu
    │   └─ NOT AUTHENTICATED
    │           └─ Enter 8-digit code from mobile app
    │                   └─ Validate via Firebase RTDB
    │                           └─ Save to cred.txt → Main Menu
    │
    └─ Main Menu
        ├─ [0] Scan Answer Key  → menu_scan_answer_key.run()
        ├─ [1] Check Sheets     → menu_check_answer_sheets.run()
        └─ [2] Settings
                ├─ Logout   → Clear cred.txt → os.execv() restart
                ├─ Shutdown → Confirm → sudo shutdown -h now
                └─ Back     → Main Menu
```

---

## Menu Modules

### `menus/menu_scan_answer_key.py`

Handles the full answer key ingestion flow:

1. Ask teacher for total number of questions (1–99, shown on LCD as typed)
2. Show **SCAN ANSWER KEY** menu loop:
   - **[0] Scan** — Trigger scanner, append PNG to list, loop back
   - **[1] Done & Save** — Collage if multi-page → Gemini OCR → Extract `assessment_uid` + `answer_key` → Validate in RTDB → Upload to Cloudinary → Save to Firebase → Prompt to scan another or exit
   - **[2] Cancel** — Delete local scans, return to Main Menu

Error handling at each step shows a **Retry / Exit** menu on the LCD.

---

### `menus/menu_check_answer_sheets.py`

Handles the full student sheet grading flow:

1. Load answer keys from Firebase RTDB
2. Teacher selects which assessment to grade against
3. Validate assessment exists in RTDB
4. Show **CHECK SHEETS** menu loop:
   - **[0] Scan** — Trigger scanner, append PNG to list, loop back
   - **[1] Done & Save** — Collage if multi-page → Gemini OCR → Extract `student_id` + answers → Score vs answer key → Upload to Cloudinary → Save to RTDB → Reset for next student
   - **[2] Cancel** — Delete local scans, return to Main Menu

Scoring features:
- Automatic answer comparison per question
- Essay answers flagged as `pending` (`is_final_score = False`)
- Warning shown if scanned answer count doesn't match answer key count

---

## Services

| Service | Description |
|---|---|
| `auth.py` | Manages `cred.txt` session, validates 8-digit temp codes via Firebase |
| `lcd_hardware.py` | I2C LCD driver with scrollable menus, 16x2/20x4 support |
| `keypad_hardware.py` | 4x3 matrix keypad GPIO driver with debounce and echo callback |
| `l3210_scanner_hardware.py` | Epson L3210 scanner interface via SANE (`scanimage -L`) |
| `firebase_rtdb_client.py` | Firebase Admin SDK RTDB client — answer keys, student results, temp codes |
| `cloudinary_client.py` | Single and batch image upload, delete |
| `gemini_client.py` | Gemini OCR with retry logic (SDK and REST modes) |
| `smart_collage.py` | Stitches multiple scanned pages into one image for Gemini |
| `scorer.py` | Compares student answers to answer key, calculates score and breakdown |
| `sanitizer.py` | Cleans and parses raw Gemini JSON responses |
| `prompts.py` | Gemini prompt templates for answer key and answer sheet extraction |
| `logger.py` | Timestamped logger with log levels |
| `utils.py` | `normalize_path`, `delete_files`, `delete_file`, `join_and_ensure_path` |

---

## Scanner Setup

Full Epson L3210 setup instructions:
```
docs/raspi/RASPI_L3210_SETUP.md
```

**Known issue:** The L3210 is a multifunction printer+scanner. If the printer enters an error state (waste ink pad full, ink not detected), the scanner USB is reset by firmware and all scan commands return `Error during device I/O`. Fix the printer error first (reset waste ink counter via WIC Reset Utility on Windows), then scanning resumes normally.

---

## Troubleshooting

**LCD not detected**
```bash
sudo modprobe i2c-dev
i2cdetect -y 1
# Should show 0x27
```

**I2C not loading on boot**
```bash
echo "i2c-dev" | sudo tee -a /etc/modules
sudo reboot
```

**Scanner not found**
```bash
scanimage -L
# Should show: device 'epson2:libusb:001:xxx' is a Epson PID 1188 flatbed scanner
```

**Scanner `Error during device I/O`**
- Check printer LED status — 3 LEDs blinking = hardware error
- Most common cause: waste ink pad full — reset via WIC Reset Utility on Windows
- If LEDs stable and error persists: `groups $USER` must include `lp` and `scanner`

**numpy `libopenblas.so.0 not found`**
```bash
sudo apt install -y libopenblas-dev
```

**Firebase `db.SERVER_TIMESTAMP` AttributeError**
- Not supported in Python Admin SDK — use `datetime.now(timezone.utc).isoformat()` instead

**Keypad not responding**
- Verify BCM pins match the hardware scan table above
- `groups $USER` must include `gpio`
- Re-run hardware pin scan: `python services/keypad_remap.py`

**Gemini returns None or bad JSON**
- Verify `GEMINI_API_KEY` is valid
- Confirm model: `GEMINI_MODEL=gemini-2.5-flash-preview-04-17`
- Check quota limits and review raw responses in `logs/`

**Ethernet connection drops after ~1 minute**
- Windows ICS DHCP lease timeout — restart ICS: `net stop SharedAccess && net start SharedAccess`
- Or assign a static IP to the Pi's eth0 interface