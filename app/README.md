# CheckMe 📱

**A comprehensive attendance management system for educational institutions.**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Android%20%7C%20iOS-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 🎯 Project Overview

CheckMe is a modern, full-featured mobile application developed using **Agile methodology** with **React Native (Expo)** and **TypeScript**. The app provides separate portals for teachers and students to manage attendance efficiently with real-time synchronization.

### Current Status
- ✅ **Phase 1 Complete**: Teacher Portal with Authentication
- ⏳ **Phase 2**: Student Portal (Coming Soon)
- ⏳ **Phase 3**: Attendance Management
- ⏳ **Phase 4**: Reports & Analytics

---

## ✨ Features

### 🎓 Teacher Portal (Phase 1 - Complete)

#### Authentication System
- ✅ **Sign Up**
  - Full name, email (Gmail only), username, employee ID, password
  - Email validation with Gmail restriction
  - Form validation with helpful error messages
  - Secure password handling
  
- ✅ **Login**
  - Email and password authentication
  - Persistent sessions (stays logged in)
  - Auto-redirect to dashboard
  
- ✅ **Dashboard**
  - View complete profile information
  - Quick actions menu
  - Sign out functionality

#### Security Features
- ✅ Firebase Email/Password authentication
- ✅ Gmail-only registration for Google Drive integration
- ✅ Custom persistence solution for Expo Go compatibility
- ✅ Encrypted password storage (Firebase automatic)
- ✅ Secure token management

#### Technical Features
- ✅ **Custom Firebase Persistence** - Fixes Firebase v12.x Expo Go compatibility
- ✅ **Type-Safe Implementation** - Full TypeScript coverage
- ✅ **Environment Variables** - Secure configuration with .env
- ✅ **Modern UI Design** - Dark purple theme with gradient buttons
- ✅ **Responsive Layout** - Works on various screen sizes
- ✅ **Form Validation** - Client-side validation with user-friendly errors

### 🎓 Student Portal (Phase 2 - Coming Soon)
- Student registration and authentication
- Student dashboard
- View attendance history
- Attendance notifications

---

## 🚀 Tech Stack

| Category | Technology |
|----------|-----------|
| **Framework** | React Native (Expo SDK 54) |
| **Language** | TypeScript 5.9 |
| **Authentication** | Firebase Authentication 12.3 |
| **Database** | Firebase Realtime Database |
| **Navigation** | React Navigation v7 |
| **Storage** | AsyncStorage 2.2 |
| **State Management** | React Context API |
| **UI Components** | React Native Core + Expo Linear Gradient |
| **Methodology** | Agile / Scrum |

---

## 📋 Prerequisites

Before you begin, ensure you have installed:

- **Node.js** v18 or higher
- **npm** or **yarn**
- **Expo Go** app (for testing on physical device)
- **Android Studio** (optional, for emulator)
- **Firebase account**

---

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/CheckMe.git
cd CheckMe
```

## 📁 Project Structure
```
CheckMe/
├── .env                              # Environment variables (git-ignored)
├── .env.example                      # Environment template
├── App.tsx                           # Main entry point
├── app.json                          # Expo configuration
├── package.json                      # Dependencies
├── tsconfig.json                     # TypeScript configuration
├── assets/
│   └── images/
│       └── checkme-logo.png         # App logo
└── src/
    ├── lib/                         # Custom implementations
    │   ├── reactNativeAsyncStorageTypes.ts
    │   └── reactNativeAsyncStorage.ts
    ├── config/
    │   └── firebase.ts              # Firebase configuration
    ├── types/
    │   └── index.ts                 # TypeScript type definitions
    ├── contexts/
    │   └── AuthContext.tsx          # Authentication context
    ├── screens/
    │   ├── ChoosePortalScreen.tsx   # Portal selection
    │   └── teacher/
    │       ├── LoginScreen.tsx      # Teacher login
    │       ├── RegisterScreen.tsx   # Teacher registration
    │       └── DashboardScreen.tsx  # Teacher dashboard
    ├── navigation/
    │   └── AppNavigator.tsx         # Navigation setup
    ├── services/
    │   └── authService.ts           # Firebase auth operations
    └── utils/
        └── validation.ts            # Form validation utilities
```