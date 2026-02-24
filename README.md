# CheckMe
# CheckMe: Grading System

An automated grading system that combines a **Raspberry Pi hardware device** with a **cross-platform mobile app** to digitize and accelerate the process of checking student answer sheets.

---

## Overview

CheckMe eliminates manual paper checking by using a flatbed scanner, AI-powered OCR (Google Gemini), and a mobile app to automate the entire grading workflow — from scanning answer keys to scoring student sheets and storing results in the cloud.

Teachers interact with the hardware device on-site to scan and grade answer sheets. Results are instantly available in the mobile app for review, manual scoring of essay questions, and record keeping.

---

## How It Works

```
Teacher creates assessment in mobile app
        ↓
Assessment UID is generated (e.g. QWER1234)
        ↓
Teacher writes UID on answer key paper
        ↓
Answer key is scanned on the Raspberry Pi device
        ↓
Gemini OCR extracts answers → saved to Firebase RTDB
        ↓
Student answer sheets are scanned one by one
        ↓
System scores each sheet automatically
        ↓
Results are saved to Firebase RTDB
        ↓
Teacher reviews results in the mobile app
```

---

## System Design

> Place your actual Raspberry Pi system product photo(s) here.

```
[ Insert system_design.png here ]
```

---

## Circuit Diagram

> Place your circuit diagram image here.

```
[ Insert circuit_diagram.png here ]
```

---

## Mobile Interface

> Place your mobile app UI screenshots here.

```
[ Insert mobile_interface.png here ]
```

---

## Repository Structure

```
CheckMe/
├── app/
│   └── CheckMe/                        # React Native mobile app source
│
├── docs/
│   ├── app/
│   │   ├── cross-platform-setup/
│   │   │   ├── COMMON_TROUBLESHOOTING.md
│   │   │   └── DURING_DEVELOPMENT.md
│   │   └── troubleshooting/
│   │       └── WORKLETS_TROUBLESHOOTING.md
│   │
│   ├── firebase/
│   │   └── FIREBASE_STRUCTURE.md       # Firebase RTDB schema reference
│   │
│   ├── github/
│   │   ├── ssh/
│   │   │   ├── QUICK_SETUP.md
│   │   │   └── SSH_DETAILED_SETUP.md
│   │   └── work-in-progress/
│   │       ├── BRANCHING_GUIDE.md
│   │       └── WIP_GUIDE.md
│   │
│   └── raspi/
│       ├── AUTOSTART_CONVERTION.md     # Run CheckMe on boot (systemd)
│       ├── L3210_INITIAL_SETUP.md      # Epson L3210 scanner setup
│       ├── RASPI_SYSTEM_FLOW.md        # Full system flowchart
│       ├── SCAN_ANSWER_KEY_FLOW.md     # Answer key scanning flowchart
│       ├── SCAN_ANSWER_SHEET_FLOW.md   # Answer sheet checking flowchart
│       ├── SPEC.md                     # Hardware specs and pin config
│       └── SYSTEM_USER_MANUAL.md       # Teacher user guide
│
├── raspi_code/                         # Raspberry Pi Python source code
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## Components

### Raspberry Pi Device
The physical grading machine. Runs Python on a Raspberry Pi 4B with an I2C LCD display, a 4x3 matrix keypad, and an Epson L3210 flatbed scanner.

See [`raspi_code/`](./raspi_code/) and [`docs/raspi/`](./docs/raspi/) for setup and documentation.

### Mobile App
Cross-platform mobile app (React Native) for teachers to create assessments, review graded results, and manually score essay questions.

See [`app/CheckMe/`](./app/CheckMe/) and [`app/README.md`](./app/README.md) for setup and documentation.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Hardware | Raspberry Pi 4B, Epson L3210, I2C LCD, 4x3 Keypad |
| Raspi Software | Python 3.12, Firebase Admin SDK, Gemini API, Cloudinary |
| Mobile App | React Native (cross-platform) |
| OCR | Google Gemini |
| Image Storage | Cloudinary |
| Database | Firebase Realtime Database |
| Authentication | Firebase (temp code via mobile app) |

---

## License

This project is licensed under the [MIT License](https://github.com/law4percent/CheckMe?tab=MIT-1-ov-file).