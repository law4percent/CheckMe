# Convert Expo App to APK (2026 Updated Method)

To distribute your CheckMe app outside of Expo Go, you need to create a production build using **EAS Build** (Expo Application Services). This replaces the old `expo build:android` command which has been fully deprecated.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step 1 — Install EAS CLI](#step-1--install-eas-cli)
- [Step 2 — Log In to Your Expo Account](#step-2--log-in-to-your-expo-account)
- [Step 3 — Configure EAS in Your Project](#step-3--configure-eas-in-your-project)
- [Step 4 — Set Build Profile for APK](#step-4--set-build-profile-for-apk)
- [Step 5 — Configure app.json / app.config.js](#step-5--configure-appjson--appconfigjs)
- [Step 6 — Run the Build](#step-6--run-the-build)
- [Step 7 — Download the APK](#step-7--download-the-apk)
- [Build Locally (Optional)](#build-locally-optional)
- [AAB vs APK](#aab-vs-apk)
- [Common Errors and Fixes](#common-errors-and-fixes)
- [Tips](#tips)

---

## Overview

**Expo Go** is a development client — it lets you preview your app quickly but cannot be installed standalone on a device. To get a real installable `.apk` file that you can share or sideload, you need to go through EAS Build.

EAS Build is a cloud build service provided by Expo. It compiles your JavaScript/TypeScript React Native project into a native Android binary without requiring Android Studio or a local Java environment.

---

## Prerequisites

Before you begin, make sure you have:

- Node.js **18 or later** installed
- An **Expo account** — sign up free at [expo.dev](https://expo.dev)
- Your project using **Expo SDK 49 or later** (SDK 52 as of 2026)
- `package.json` includes `expo` as a dependency
- Internet connection (builds run on Expo's cloud servers)

Check your current SDK version:

```bash
cat package.json | grep '"expo"'
```

---

## Step 1 — Install EAS CLI

Install the EAS CLI globally:

```bash
npm install -g eas-cli
```

Verify the installation:

```bash
eas --version
```

You should see something like `eas-cli/10.x.x` or later.

---

## Step 2 — Log In to Your Expo Account

```bash
eas login
```

Enter your Expo credentials. If you don't have an account:

```bash
# Create one at https://expo.dev/signup
# or via CLI:
eas register
```

Verify you're logged in:

```bash
eas whoami
```

---

## Step 3 — Configure EAS in Your Project

Navigate to your project root (where `package.json` lives) and run:

```bash
eas build:configure
```

This will:
- Create an `eas.json` file in your project root
- Ask whether you want to build for Android, iOS, or both
- Select **Android** for APK generation

A basic `eas.json` will be generated automatically. You'll customize it in the next step.

---

## Step 4 — Set Build Profile for APK

By default, EAS builds an **AAB** (Android App Bundle) for the `production` profile, which is intended for the Play Store. To get a plain `.apk` file you can sideload directly onto a device, you need to set `buildType` to `apk`.

Edit your `eas.json`:

```json
{
  "cli": {
    "version": ">= 10.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "android": {
        "buildType": "apk"
      },
      "distribution": "internal"
    },
    "production": {
      "android": {
        "buildType": "apk"
      }
    }
  },
  "submit": {
    "production": {}
  }
}
```

> **`preview` profile** — best for sharing a testable APK with your team or teachers without going through the Play Store.
>
> **`production` profile** — for your final release APK. Requires a keystore (EAS will generate one for you automatically on first build).

---

## Step 5 — Configure app.json / app.config.js

Make sure your `app.json` has the required Android fields:

```json
{
  "expo": {
    "name": "CheckMe",
    "slug": "checkme",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#171443"
    },
    "android": {
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#171443"
      },
      "package": "com.yourname.checkme",
      "versionCode": 1,
      "permissions": [
        "CAMERA",
        "READ_EXTERNAL_STORAGE",
        "WRITE_EXTERNAL_STORAGE",
        "INTERNET"
      ]
    },
    "extra": {
      "eas": {
        "projectId": "your-eas-project-id-here"
      }
    }
  }
}
```

> **Important:** The `android.package` field must be a unique reverse-domain identifier (e.g. `com.yourname.checkme`). This cannot be changed after your first build without creating a new keystore.

To get your EAS project ID, run:

```bash
eas project:info
```

Or find it at [expo.dev](https://expo.dev) under your project dashboard.

---

## Step 6 — Run the Build

To build a **preview APK** (recommended for testing and sharing):

```bash
eas build --platform android --profile preview
```

To build a **production APK**:

```bash
eas build --platform android --profile production
```

What happens next:
1. EAS CLI will validate your configuration
2. If this is your first build, EAS will generate a **keystore** automatically and store it securely in the cloud
3. Your project is uploaded to Expo's build servers
4. The build runs in the cloud (typically takes **5–15 minutes**)
5. You receive a download link when it's complete

You can monitor the build progress in the terminal or at [expo.dev/accounts/[username]/projects/[slug]/builds](https://expo.dev).

---

## Step 7 — Download the APK

When the build completes, the CLI will print a download URL:

```
✔ Build finished.
Download the build artifact: https://expo.dev/artifacts/eas/xxxxx.apk
```

You can also download it from your Expo dashboard under **Builds**.

**To install on a device:**

1. Transfer the `.apk` file to your Android device (via USB, Google Drive, or direct link)
2. On the device, go to **Settings → Security → Install Unknown Apps** and enable it for your file manager or browser
3. Open the `.apk` file and tap **Install**

---

## Build Locally (Optional)

If you prefer to build locally without uploading to Expo's servers (requires Android Studio and Java 17 installed):

```bash
# Install dependencies for local builds
eas build --platform android --profile preview --local
```

Requirements for local builds:
- **Android Studio** with Android SDK installed
- **Java Development Kit (JDK) 17**
- Environment variables set: `ANDROID_HOME`, `JAVA_HOME`
- At least **8 GB RAM** recommended

Local builds are slower to set up but give you full control and don't consume EAS build credits.

---

## AAB vs APK

| Format | Use Case | Installable Directly? |
|---|---|---|
| `.apk` | Sideloading, sharing, testing | ✅ Yes |
| `.aab` | Google Play Store submission | ❌ No (Play Store converts it) |

For the CheckMe app used in a school environment, an **APK** is the correct choice since you are sideloading it to teachers' devices directly, not publishing to the Play Store.

---

## Common Errors and Fixes

**Error: `eas-cli` version mismatch**
```
Your project requires eas-cli >= 10.x.x
```
Fix: Update EAS CLI
```bash
npm install -g eas-cli@latest
```

---

**Error: `Missing android.package in app.json`**

Fix: Add the `android.package` field to your `app.json` as shown in Step 5.

---

**Error: `Gradle build failed — SDK version not found`**

Fix: Make sure your `compileSdkVersion` in `app.json` matches your Expo SDK. For Expo SDK 52:
```json
"android": {
  "compileSdkVersion": 34,
  "targetSdkVersion": 34,
  "buildToolsVersion": "34.0.0"
}
```

---

**Error: `Google Services file (google-services.json) is missing`**

Since CheckMe uses Firebase, you must include `google-services.json` in your project root. Download it from:
> Firebase Console → Your Project → Project Settings → Android App → Download `google-services.json`

Place it at the root of your Expo project. EAS will automatically detect and include it.

---

**Error: `expo-modules-core build error`**

Fix: Make sure you're using a compatible Expo SDK. Run:
```bash
npx expo install --fix
```

---

**Build stuck at "Uploading..."**

This usually means a slow internet connection. Try:
```bash
eas build --platform android --profile preview --no-wait
```
The build will continue in the cloud. Check status at expo.dev.

---

## Tips

- **Free tier** — Expo's free plan includes **30 build credits per month**. A preview APK build typically uses 1–2 credits. Production builds use more.

- **Keystore backup** — EAS manages your keystore automatically in the cloud. You can download a copy from your project settings. **Never lose your production keystore** — losing it means you cannot update the app on the Play Store.

- **Environment variables** — If your app uses `.env` secrets (Firebase API keys, etc.), add them to EAS:
  ```bash
  eas secret:create --scope project --name FIREBASE_API_KEY --value your-key-here
  ```

- **OTA Updates** — After your first APK is installed, you can push JavaScript-only updates without rebuilding using `eas update`. This is useful for quick bug fixes without redistributing the APK.

- **Testing before production** — Always build and test with the `preview` profile first. The `preview` APK behaves identically to production but doesn't require a signed release keystore setup.