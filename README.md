# CheckMe: AI-Assisted Automated Answer Sheet Checking System

CheckMe is an integrated automated answer sheet checking system that combines a
Raspberry Pi-powered optical scanner, a cross-platform mobile application, and a
Firebase cloud backend. The system is designed to help teachers check student answer
sheets quickly and accurately — eliminating manual checking, reducing errors, and
giving teachers more time to focus on teaching.

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Being Solved](#problem-being-solved)
3. [Project Goals](#project-goals)
4. [System Components](#system-components)
5. [System Architecture](#system-architecture)
6. [How It Works (End-to-End Flow)](#how-it-works-end-to-end-flow)
7. [Key Features](#key-features)
8. [Supported Scanners](#supported-scanners)
9. [RTDB Structure](#rtdb-structure)
10. [Development Environment](#development-environment)
11. [Repository Structure](#repository-structure)
12. [Future Works](#future-works)
13. [Circuit Diagram](#circuit-diagram)
14. [3D Model](#3d-model)
15. [App UI Screenshots](#app-ui-screenshots)
16. [Downloads](#downloads)
17. [Acknowledgments](#acknowledgments)

---

## Overview

CheckMe addresses one of the most time-consuming tasks in a teacher's daily workflow:
manually checking student answer sheets. Using a combination of flatbed scanner
hardware, optical character recognition (OCR), Firebase cloud infrastructure, and a
React Native mobile application, CheckMe automates the entire checking pipeline —
from scanning a printed answer sheet to displaying individual scores and question
breakdowns on the teacher's phone.

The system follows a clear separation of responsibilities:

| Component | Role |
|---|---|
| **Raspberry Pi + Scanner** | Scans answer sheets, runs OCR, writes results to Firebase |
| **Firebase RTDB** | Single source of truth — shared state between Raspi and app |
| **Cloudinary** | Stores scanned answer sheet images for teacher review |
| **React Native App** | Teacher and student portal — manages assessments, views scores |

---

## Problem Being Solved

Manual answer sheet checking is slow, prone to human error, and takes significant
time away from teachers — especially when handling large classes with multiple
assessments. In schools without access to expensive commercial scanners or OMR
(Optical Mark Recognition) machines, teachers have no practical alternative to
checking papers one by one by hand.

CheckMe proposes a low-cost, locally deployable solution using widely available
flatbed scanners, a Raspberry Pi, and a free-tier Firebase backend — making
automated checking accessible to any school.

---

## Project Goals

1. Build a Raspberry Pi-powered scanning pipeline that reads printed answer sheets,
   performs OCR, and automatically scores student responses against a stored answer key.
2. Develop a cross-platform mobile application for teachers to manage sections,
   subjects, assessments, answer keys, and student scores.
3. Provide a student portal where enrolled students can view their own scores and
   question breakdowns.
4. Implement an enrollment system where students request to join a subject and
   teachers approve or reject requests.
5. Enable teachers to share answer keys across accounts so that multiple teachers
   using the same printed test paper can reuse each other's scanned answer keys.
6. Store scanned answer sheet images on Cloudinary so teachers can visually review
   the original paper alongside the OCR results.

---

## System Components

### 1. Raspberry Pi Scanner Unit

The Raspberry Pi is the hardware backbone of the checking pipeline. It sits
connected to a standard USB flatbed scanner at the teacher's desk or scanning
station.

**What it does:**
- Accepts a teacher login via a one-time 8-digit code generated from the mobile app
- Scans a printed answer sheet using the connected flatbed scanner
- Runs OCR (Optical Character Recognition) on the scanned image to extract student
  answers
- Reads the stored answer key from Firebase for the given Assessment UID
- Compares student answers to the answer key question by question
- Writes the full result — score, question breakdown, and image URLs — back to Firebase
- Uploads scanned images to Cloudinary for teacher review in the app

**Why Raspberry Pi:**
The Raspberry Pi is affordable, widely available, and capable of running a full
Python environment with USB scanner access — making it an ideal low-cost scanning
station for schools that cannot afford commercial OMR machines.

**Scanner compatibility:**
CheckMe has been tested and confirmed working with:
- **Epson L3210 Series**
- **Canon PIXMA MG2570S**

Other flatbed scanners with standard SANE-compatible USB drivers are expected to
work but have not yet been formally tested.

---

### 2. Firebase Backend

Firebase Realtime Database (RTDB) serves as the cloud backbone, providing real-time
data synchronization between the Raspberry Pi scanner and the mobile application.

**What Firebase stores:**
- Teacher and student user profiles
- Sections, subjects, and assessment records
- Scanned answer keys (per teacher, per assessment)
- Student answer sheets and score breakdowns
- Enrollment records (pending, approved, rejected)
- Subject invite codes for student enrollment
- Publicly shared answer keys (for cross-teacher reuse)
- Temporary Raspi login codes

**Why Firebase RTDB:**
Firebase provides real-time sync out of the box — the moment the Raspberry Pi writes
a score, the teacher's phone updates without any manual refresh. It also eliminates
the need to run and maintain a separate backend server.

---

### 3. Cloudinary (Image Storage)

Every scanned answer sheet image is uploaded to Cloudinary and linked to the
student's result record in Firebase.

**Why Cloudinary:**
Firebase Storage adds cost at scale, while Cloudinary's free tier is generous and
provides fast CDN-delivered image URLs. Teachers can tap any student result in the
app to view the original scanned paper alongside the OCR breakdown — making it easy
to spot and correct OCR errors manually.

---

### 4. Mobile Application (React Native + Expo)

Built with **React Native (Expo)** for cross-platform compatibility (iOS and Android).

The app has two separate portals:

#### Teacher Portal
- **Dashboard** — manage sections and subjects
- **Subject Dashboard** — create assessments, manage enrollments, view answer keys
- **Answer Keys** — view scanned answer keys, edit individual answers, re-score sheets, share answer keys publicly
- **View Scores** — full student result list with scores, percentages, grades, and breakdown
- **Score Table** — per-question breakdown for individual students with manual edit support
- **Export to Excel** — download assessment results as a formatted `.xlsx` file sorted by name or student ID

#### Student Portal
- **Dashboard** — view enrolled subjects and assessment results
- **Enrollment** — search subjects by invite code and request enrollment

---

## System Architecture

```
Teacher prints test paper with Assessment UID written at the top
        │
        │  Student fills in answers on paper
        ▼
Raspberry Pi + Flatbed Scanner (at teacher's desk)
        │
        │  1. Teacher logs in via 8-digit one-time code (from mobile app)
        │  2. Raspi scans the paper
        │  3. OCR extracts student answers
        │  4. Raspi reads answer key from Firebase
        │  5. Raspi compares answers, calculates score
        │  6. Raspi uploads images to Cloudinary
        │  7. Raspi writes full result to Firebase
        ▼
Firebase Realtime Database
        │
        ▼
React Native Mobile App (Teacher's phone)
        ├── View Scores → individual student results appear instantly
        ├── Answer Keys → scanned paper images + per-question answers
        ├── Export Excel → download results as .xlsx
        └── Share Answer Key → other teachers can copy the answer key
```

---

## How It Works (End-to-End Flow)

### Step 1 — Teacher creates an assessment
The teacher opens the app, navigates to a subject, and creates an assessment (quiz
or exam). The app generates a unique 8-character Assessment UID (e.g., `QWER1234`).

### Step 2 — Teacher prints the test paper
The teacher writes or prints the Assessment UID at the top of the answer sheet
paper. Students fill in their school ID and answers on the paper.

### Step 3 — Teacher scans the answer key
The teacher places their own filled answer key paper on the scanner. The Raspberry
Pi reads the correct answers and stores them in Firebase under the teacher's account.

### Step 4 — Teacher scans student answer sheets
One by one, student answer sheets are placed on the scanner. The Raspberry Pi:
- Reads the student's school ID from the paper
- Looks up the answer key for the Assessment UID
- Compares each answer and calculates the score
- Writes the result to Firebase and uploads images to Cloudinary

### Step 5 — Teacher views results on the app
Scores appear instantly on the teacher's phone. The teacher can:
- View each student's score, percentage, and grade
- See a per-question breakdown (correct / wrong / unreadable)
- Manually correct OCR errors and re-score
- Export the full class results as an Excel file

---

## Key Features

### For Teachers
- **Assessment management** — create quizzes and exams with auto-generated UIDs
- **Import existing UID** — reuse another teacher's Assessment UID and automatically
  receive their shared answer key
- **Share answer key publicly** — share a scanned answer key so other teachers using
  the same test paper can import it without re-scanning
- **Enrollment management** — approve or reject student enrollment requests per subject
- **Answer key editing** — correct individual OCR errors and automatically re-score
  all affected student sheets
- **Manual score editing** — override individual student answers with teacher judgment
- **Export to Excel** — download class results sorted alphabetically or by student ID,
  including students who have not yet been scanned
- **Invite codes** — share a subject invite code with students for easy enrollment

### For Students
- View scores and question breakdowns for each assessment
- Enroll in subjects using teacher-provided invite codes
- Track pending enrollment approval status

---

## Supported Scanners

| Scanner Model | Status |
|---|---|
| Epson L3210 Series | ✅ Tested and confirmed |
| Canon PIXMA MG2570S | ✅ Tested and confirmed |
| Other SANE-compatible USB flatbed scanners | ⚠️ Expected to work, not yet tested |

> **Note:** The scanning pipeline uses standard SANE (Scanner Access Now Easy)
> drivers on the Raspberry Pi. Any flatbed scanner with a working SANE driver
> should be compatible, though only the two models above have been formally verified.

---

## RTDB Structure

```
/users/
  teachers/{uid}/          ← teacher profile
  students/{uid}/          ← student profile

/sections/{teacherId}/{sectionId}/
/subjects/{teacherId}/{sectionId}/{subjectId}/
/assessments/{teacherId}/{assessmentUid}/
/answer_keys/{teacherId}/{assessmentUid}/
/answer_sheets/{teacherId}/{assessmentUid}/{studentId}/
/enrollments/{teacherId}/{subjectId}/{studentUid}/
/invite_codes/{teacherId}/{subjectId}/
/open_share_answer_keys/{assessmentUid}/   ← publicly shared answer keys
/temp_codes/{uid}/                         ← Raspi one-time login codes
```

---

## Development Environment

| Tool | Version / Detail |
|---|---|
| React Native | Expo SDK 54 |
| TypeScript | ~5.9.2 |
| Firebase | ^12.3.0 (RTDB) |
| Cloudinary | CDN image hosting |
| Python | Raspberry Pi scanning pipeline |
| Node.js | ≥ v22.20.0 |
| npm | ≥ 11.4.2 |
| Target Platforms | Android, iOS |
| Scanner Interface | SANE (Linux USB) on Raspberry Pi |

---

## Repository Structure

```
CheckMe/
├── src/
│   ├── screens/
│   │   ├── teacher/
│   │   │   ├── DashboardScreen.tsx
│   │   │   ├── SectionDashboardScreen.tsx
│   │   │   ├── SubjectDashboardScreen.tsx
│   │   │   ├── AnswerKeysScreen.tsx
│   │   │   ├── ViewScoresScreen.tsx
│   │   │   └── TeacherAssessmentScoreTableScreen.tsx
│   │   └── student/
│   │       ├── StudentDashboardScreen.tsx
│   │       └── StudentEnrollmentScreen.tsx
│   ├── services/
│   │   ├── assessmentService.ts
│   │   ├── answerSheetService.ts
│   │   ├── enrollmentService.ts
│   │   ├── inviteCodeService.ts
│   │   ├── sectionService.ts
│   │   ├── subjectService.ts
│   │   └── authService.ts
│   ├── contexts/
│   │   └── AuthContext.tsx
│   ├── config/
│   │   └── firebase.ts
│   └── types/
│       └── index.ts
├── raspi/                        ← Raspberry Pi Python scanning pipeline
│   ├── main.py
│   ├── scanner.py
│   ├── ocr.py
│   ├── firebase_writer.py
│   └── cloudinary_uploader.py
├── assets/
├── App.tsx
├── app.json
├── package.json
└── tsconfig.json
```

---

## Circuit Diagram

<!-- Replace with your actual circuit diagram image -->
![Circuit Diagram](docs/images/circuit_diagram.png)

> Wiring diagram of the Raspberry Pi connected to the USB flatbed scanner,
> power supply, and any GPIO components used in the scanning station.

---

## 3D Model

<!-- Replace with your actual 3D render screenshots -->

| Front | Back | Assembled |
|:---:|:---:|:---:|
| ![Front](docs/images/3d_front.png) | ![Back](docs/images/3d_back.png) | ![Assembled](docs/images/3d_assembled.png) |

> **[⬇️ Download STL File (Google Drive)](https://your-google-drive-link-here)**
>
> Recommended print settings: PLA, 0.2mm layer height, 20% infill.

---

## App UI Screenshots

| Teacher Login | Teacher Dashboard | Section Dashboard |
|:---:|:---:|:---:|
| <img src="docs/images/ui_teacher_login.jpg" width="200"> | <img src="docs/images/ui_teacher_dashboard.jpg" width="200"> | <img src="docs/images/ui_section_dashboard.jpg" width="200"> |
| Teacher login with email and password | Overview of all sections and subjects | Subjects list with assessment counts |

| Subject Dashboard | Answer Keys | View Scores |
|:---:|:---:|:---:|
| <img src="docs/images/ui_subject_dashboard.jpg" width="200"> | <img src="docs/images/ui_answer_keys.jpg" width="200"> | <img src="docs/images/ui_view_scores.jpg" width="200"> |
| Assessments list with UID, create and manage | Scanned answer keys with per-question breakdown | Full class results with scores and grades |

| Score Breakdown | Export Excel | Student Dashboard |
|:---:|:---:|:---:|
| <img src="docs/images/ui_score_breakdown.jpg" width="200"> | <img src="docs/images/ui_export.jpg" width="200"> | <img src="docs/images/ui_student_dashboard.jpg" width="200"> |
| Per-question result with manual edit support | Sort and download results as .xlsx | Student view of enrolled subjects and scores |

---

## Downloads

### 📱 Android APK

> **[⬇️ Download CheckMe APK (Google Drive)](https://your-google-drive-link-here)**
>
> Minimum Android version: API 21 (Android 5.0)
>
> **Install instructions:**
> 1. Download the APK on your Android phone
> 2. Go to **Settings → Security → Enable Install from unknown sources**
> 3. Open the APK and tap **Install**
> 4. Open CheckMe and sign in as a Teacher or Student

### 🖥️ Raspberry Pi Setup

> **[⬇️ Download Raspi Scanning Pipeline (Google Drive)](https://your-google-drive-link-here)**
>
> **Requirements:**
> - Raspberry Pi 3B+ or newer
> - Python 3.10+
> - SANE-compatible USB flatbed scanner (see [Supported Scanners](#supported-scanners))
>
> **Setup instructions:**
> 1. Clone or download the `raspi/` folder onto your Raspberry Pi
> 2. Run `pip install -r requirements.txt`
> 3. Connect your USB scanner and verify with `scanimage -L`
> 4. Add your Firebase service account key as `serviceAccountKey.json`
> 5. Run `python main.py` to start the scanning pipeline
> 6. Log in using the 8-digit one-time code generated from the mobile app

---

## Future Works

CheckMe was designed with extensibility in mind. The following features and
directions are planned or proposed for future development:

### 🖥️ Web or Desktop Application
A web-based or desktop version of the teacher portal would allow teachers to manage
assessments, view scores, and export results directly from a browser or desktop
computer — without needing a phone. This would be particularly useful in school
computer labs or for teachers who prefer a larger screen for data review.

### 🖨️ PC-Based Scanning (No Raspberry Pi Required)
The current system requires a Raspberry Pi as the scanning station. A future version
could replace the Raspberry Pi entirely with a desktop or laptop application that
communicates directly with a USB-connected scanner. Since most school computers
already have scanner software installed, this would dramatically lower the hardware
cost and setup complexity. Any PC with a compatible scanner could become a checking
station.

### 👨‍💼 Admin Portal
An admin panel for school administrators to oversee all teacher accounts, subjects,
sections, and assessment activity across the institution — providing a school-wide
view of assessment data without requiring access to individual teacher accounts.

### 📊 Analytics Dashboard
Visual analytics for teachers showing class performance trends across assessments —
including score distributions, question-level difficulty analysis, and student
progress over time.

### 🔔 Push Notifications
Real-time push notifications to notify teachers when a student's answer sheet has
been successfully scanned and scored, or when a student requests enrollment in their
subject.

### 🌐 Broader Scanner Compatibility Testing
CheckMe has been confirmed working on the **Epson L3210 Series** and
**Canon PIXMA MG2570S**. Future work includes formal testing across a wider range
of flatbed scanner models to build a verified compatibility list.

### 📱 Student Mobile Improvements
Enhanced student-facing features such as score history graphs, notifications when
results are published, and the ability to view scanned answer sheet images alongside
their personal breakdown.

---

## Acknowledgments

- Google Firebase for real-time cloud infrastructure and RTDB
- Cloudinary for free-tier image hosting and CDN delivery
- Expo and the React Native community for the cross-platform mobile framework
- SANE Project for open-source scanner driver support on Linux / Raspberry Pi
- The teachers and students who participated in testing and provided feedback