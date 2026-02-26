# CheckMe — Automated Answer Sheet Checker

A mobile application for teachers and students that automates the grading of paper-based multiple-choice assessments using a Raspberry Pi scanner system and Firebase Realtime Database.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Firebase Database Structure](#firebase-database-structure)
- [Teacher Portal](#teacher-portal)
- [Student Portal](#student-portal)
- [Answer Sheet Scanning Flow](#answer-sheet-scanning-flow)
- [Score Management](#score-management)
- [Enrollment System](#enrollment-system)
- [Troubleshooting](#troubleshooting)

---

## Overview

CheckMe is a two-portal mobile app (built with React Native / Expo) that works in tandem with a Raspberry Pi-based answer sheet scanner. Teachers create assessments, the Raspberry Pi scans physical answer sheets and performs OCR, and results are pushed to Firebase in real time. The app then displays scores, breakdowns, and allows manual correction of any OCR errors.

The system eliminates the need for manual checking of bubble sheets and provides instant per-question score breakdowns, essay grading queues, and class-wide statistics.

---

## System Architecture

```
┌──────────────────────────────────────────────────────┐
│                 Raspberry Pi Scanner                  │
│  Camera → OCR → scorer.py → Firebase RTDB push       │
└──────────────────────┬───────────────────────────────┘
                       │ answer_keys / answer_sheets
                       ▼
┌──────────────────────────────────────────────────────┐
│           Firebase Realtime Database (RTDB)           │
│  /assessments  /enrollments  /answer_keys             │
│  /answer_sheets  /users                               │
└────────────┬─────────────────────┬────────────────────┘
             │                     │
             ▼                     ▼
   ┌─────────────────┐   ┌──────────────────────┐
   │  Teacher Portal  │   │   Student Portal      │
   │  (Mobile App)   │   │   (Mobile App)        │
   │  View scores    │   │   View own results    │
   │  Edit/Grade     │   │   Per-question view   │
   │  Manage classes │   │   Check enrollment    │
   └─────────────────┘   └──────────────────────┘
```

---

## Features

### Teacher
- Register and log in with a teacher account
- Create and manage **Sections** and **Subjects**
- Approve or reject student enrollment requests
- View scanned **Answer Keys** per assessment (OCR results from Raspberry Pi)
- Edit individual answers in the key if OCR made an error
- Delete answer keys to trigger a re-scan
- View all **student scores** per assessment in a ranked list
- Drill into a **per-question breakdown** for any student
- Edit student answers inline to correct OCR mistakes — score recalculates live
- Toggle scores between **Final** and **Pending** (for essay questions)
- Manually grade essay-type questions with ✓ / ✗ / ⏳ controls
- Reassign an answer sheet to a different student ID (in case of mis-scan)
- See which enrolled students have **not yet been scanned** per assessment
- Cascade-delete assessments (removes answer key + all student sheets together)

### Student
- Register and log in with a student account
- Browse available subjects and request enrollment
- View personal scores and per-question breakdowns
- See which answers were correct, wrong, or pending

---

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile App | React Native (Expo SDK 52) |
| Language | TypeScript |
| Navigation | React Navigation v6 (Native Stack) |
| Backend / Database | Firebase Realtime Database (RTDB) |
| Authentication | Firebase Authentication |
| Image Storage | Cloudinary (answer sheet images) |
| Scanner | Raspberry Pi + Python (separate repo: `raspi_code/`) |
| Build | EAS Build (Expo Application Services) |

---

## Project Structure

```
checkme/
├── src/
│   ├── screens/
│   │   ├── teacher/
│   │   │   ├── TeacherDashboardScreen.tsx
│   │   │   ├── TeacherSectionDashboardScreen.tsx
│   │   │   ├── SubjectDashboardScreen.tsx
│   │   │   ├── ViewScoresScreen.tsx
│   │   │   ├── AssessmentScoreTableScreen.tsx
│   │   │   └── AnswerKeysScreen.tsx
│   │   ├── student/
│   │   │   ├── StudentDashboardScreen.tsx
│   │   │   └── StudentSubjectScreen.tsx
│   │   └── auth/
│   │       ├── TeacherLoginScreen.tsx
│   │       ├── TeacherRegisterScreen.tsx
│   │       ├── StudentLoginScreen.tsx
│   │       └── StudentRegisterScreen.tsx
│   ├── services/
│   │   ├── answerSheetService.ts
│   │   ├── answerKeyService.ts
│   │   ├── assessmentService.ts
│   │   └── enrollmentService.ts
│   ├── contexts/
│   │   └── AuthContext.tsx
│   ├── config/
│   │   └── firebase.ts
│   ├── navigation/
│   │   └── AppNavigator.tsx
│   └── types/
│       └── index.ts
├── assets/
│   ├── icon.png
│   ├── splash.png
│   └── adaptive-icon.png
├── app.json
├── eas.json
├── package.json
├── tsconfig.json
└── README.md
```

---

## Prerequisites

- **Node.js** 18 or later
- **npm** 9 or later (or yarn)
- **Expo CLI** — `npm install -g expo-cli`
- **EAS CLI** — `npm install -g eas-cli` (for production builds)
- An **Expo account** at [expo.dev](https://expo.dev)
- A **Firebase project** with Realtime Database and Authentication enabled
- A **Cloudinary account** for answer sheet image storage
- The **Raspberry Pi scanner** set up separately (see `raspi_code/README.md`)

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/yourname/checkme.git
cd checkme
```

**2. Install dependencies**

```bash
npm install
```

**3. Set up environment variables**

Create a `.env` file in the project root:

```env
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_APP_ID=your-app-id
```

**4. Start the development server**

```bash
npx expo start
```

Scan the QR code with **Expo Go** (Android) to preview on your device during development.

> To build a distributable APK, see [BUILDING_APP.md](./BUILDING_APP.md).

---

## Configuration

### Firebase Setup

1. Go to the [Firebase Console](https://console.firebase.google.com)
2. Create a new project (or use an existing one)
3. Enable **Authentication** → Email/Password sign-in
4. Enable **Realtime Database** → Start in test mode (set rules before going live)
5. Go to Project Settings → Add an Android app → Download `google-services.json` and place it in the project root
6. Copy your Firebase config into your `.env` file

**Recommended Firebase RTDB Rules:**

```json
{
  "rules": {
    "users": {
      "$uid": {
        ".read": "$uid === auth.uid",
        ".write": "$uid === auth.uid"
      }
    },
    "assessments": {
      "$teacherUid": {
        ".read": "auth != null",
        ".write": "$teacherUid === auth.uid"
      }
    },
    "answer_sheets": {
      "$teacherUid": {
        ".read": "auth != null",
        ".write": "auth != null"
      }
    },
    "answer_keys": {
      "$teacherUid": {
        ".read": "auth != null",
        ".write": "auth != null"
      }
    },
    "enrollments": {
      ".read": "auth != null",
      ".write": "auth != null"
    }
  }
}
```

---

## Firebase Database Structure

```
/
├── users/
│   ├── teachers/
│   │   └── {teacherUid}/
│   │       ├── fullName: string
│   │       └── email: string
│   └── students/
│       └── {studentUid}/
│           ├── fullName: string
│           ├── email: string
│           └── studentId: string          ← school-provided ID (e.g. "4201400")
│
├── assessments/
│   └── {teacherUid}/
│       └── {assessmentUid}/
│           ├── name: string
│           ├── subjectUid: string
│           └── createdAt: number
│
├── answer_keys/
│   └── {teacherUid}/
│       └── {assessmentUid}/
│           ├── assessment_uid: string
│           ├── total_questions: number
│           ├── scanned_at: number
│           └── answers/
│               ├── Q1: "A"
│               ├── Q2: "essay_answer"
│               └── Q3: "C"
│
├── answer_sheets/
│   └── {teacherUid}/
│       └── {assessmentUid}/
│           └── {studentSchoolId}/         ← key is the school-provided student ID
│               ├── student_id: string
│               ├── assessment_uid: string
│               ├── total_score: number
│               ├── total_questions: number
│               ├── is_final_score: boolean
│               ├── checked_at: number
│               ├── updated_at: number
│               ├── image_urls: string[]
│               └── breakdown/
│                   └── Q1/
│                       ├── student_answer: string
│                       ├── correct_answer: string
│                       └── checking_result: boolean | "pending"
│
└── enrollments/
    └── {teacherUid}/
        └── {subjectUid}/
            └── {studentFirebaseUid}/
                ├── studentId: string      ← Firebase UID
                ├── schoolId: string       ← school-provided ID
                ├── studentName: string
                ├── status: "pending" | "approved" | "rejected"
                └── enrolledAt: number
```

---

## Teacher Portal

### Navigation Flow

```
ChoosePortal
  └── TeacherLogin / TeacherRegister
        └── TeacherDashboard
              └── TeacherSectionDashboard  (per section)
                    └── SubjectDashboard   (per subject)
                          ├── 🗝️ Answer Keys
                          │     └── AnswerKeysScreen
                          └── 📊 View Scores  (per assessment)
                                └── AssessmentScoreTableScreen  (per student)
```

### Key Screens

**SubjectDashboardScreen** — Lists all assessments for a subject. Provides access to answer key management and per-assessment score views. Supports cascade-delete of assessments (removes assessment record, answer key, and all student sheets atomically).

**ViewScoresScreen** — Shows all scanned student results for an assessment, ranked by score. Includes a **Not Yet Scanned** section at the bottom listing enrolled students who have no answer sheet for the current assessment. Supports student ID reassignment via a modal.

**AssessmentScoreTableScreen** — Full per-student breakdown with live inline editing. All student answer cells are `TextInput` fields — changes highlight purple and a sticky **Save & Re-score** bar appears at the bottom. The **Final/Pending toggle** is permanently visible in the header so teachers can flip it at any time in either direction.

**AnswerKeysScreen** — Lists all assessments for the subject. Shows whether an answer key has been scanned for each. Teachers can view all Q1–Qn answers, edit individual answers, or delete the entire key. Editing an answer key that already has student sheets prompts a warning recommending a re-scan.

---

## Student Portal

### Navigation Flow

```
ChoosePortal
  └── StudentLogin / StudentRegister
        └── StudentDashboard
              └── StudentSubjectScreen  (view scores per subject)
```

Students can view their own scores and per-question breakdowns. They request enrollment into subjects created by teachers, and the teacher approves or rejects the request.

---

## Answer Sheet Scanning Flow

1. Teacher creates an **Assessment** in the app and notes the **Assessment UID** (8-character code printed on the answer key sheet)
2. Teacher places the **Answer Key sheet** in the Raspberry Pi scanner and starts the scan
3. Raspberry Pi OCR reads the assessment UID and all answers → pushes to `/answer_keys/{teacherUid}/{assessmentUid}/`
4. Students complete the test on their answer sheets
5. Teacher feeds student sheets through the scanner one at a time
6. Raspberry Pi reads the student school ID + bubble answers → scores against the answer key → pushes to `/answer_sheets/{teacherUid}/{assessmentUid}/{studentSchoolId}/`
7. The mobile app reflects new results in real time — pull down to refresh

---

## Score Management

### Final vs Pending

A score is marked **Pending** (`is_final_score: false`) when the answer key contains essay questions (`correct_answer: "essay_answer"`) requiring manual grading, or when the teacher has not yet confirmed the grade. A score becomes **Final** when all questions are auto-graded or the teacher explicitly flips the toggle.

### Correcting OCR Errors

If the scanner misread a student answer (e.g. read `C` instead of `B`):
1. Open the student's breakdown in `AssessmentScoreTableScreen`
2. Tap the answer cell for the affected question and type the correct answer
3. The result icon updates live — ✓ green if now correct, ✗ red if still wrong
4. Tap **Save & Re-score** — Firebase is updated and the score recalculates

### Essay Grading

Essay questions display a three-button toggle in the breakdown row: **✓** correct, **✗** wrong, **⏳** pending. After grading all essays, the teacher flips the **Final Score** switch in the header to lock in the grade.

---

## Enrollment System

Students enroll in subjects by finding the teacher's subject and submitting a request. Teachers see pending requests and approve or reject them from the subject dashboard.

When a student enrolls, their school-provided ID (stored at `/users/students/{uid}/studentId`) is fetched and saved in the enrollment record as `schoolId`. This value is used to match scanned answer sheets — which are keyed by school ID — to student names automatically.

> Students enrolled before the `schoolId` field was added will appear as **Unknown Student** until they re-enroll or the teacher uses **👤 Reassign** to manually correct the ID on their answer sheet.

---

## Troubleshooting

**Scanned results don't appear in the app**
- Verify the Assessment UID on the answer sheet exactly matches the UID in `/assessments/`
- Check that the Raspberry Pi has network access and that Firebase credentials in `raspi_code/config.py` are correct
- Inspect `/answer_sheets/{teacherUid}/{assessmentUid}/` directly in the Firebase console

**Student shows as "Unknown Student"**
- The scanned school ID on the answer sheet doesn't match any enrolled student's `schoolId`
- Use **👤 Reassign** on the score card to correct it, or have the student re-enroll

**Score stuck as Pending after grading all questions**
- Check the breakdown for any remaining ⏳ rows — set each to ✓ or ✗
- Then flip the **Final Score** toggle in the header to confirm

**App won't start / dependency error**
```bash
rm -rf node_modules
npm install
npx expo start --clear
```

**Firebase "Permission Denied" errors**
- Confirm the user is authenticated before any database read/write
- Check that your RTDB rules are not in locked mode
- Verify the `teacherUid` in the path matches the authenticated user's UID

**Building an APK**
See [BUILD_APP.md](docs/app/BUILD_APP.md) for full instructions including EAS setup, `eas.json` configuration, and common build error fixes.