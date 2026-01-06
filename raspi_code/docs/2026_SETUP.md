# Migration Guide - Applying Core System Updates

## 📋 Overview

This guide helps you migrate from your current code to the improved version with:
- ✅ Centralized configuration management
- ✅ Fixed bugs (SQL, parameter naming, scoring logic)
- ✅ Firebase RTDB integration
- ✅ Better error handling
- ✅ Validation system

---

## 🚀 Quick Start (Step-by-Step)

### **Copy this file for .env**
[PROCEED WITH THIS LINK](https://drive.google.com/file/d/1c1AN54nHgAN3NNydtlho3ubkHpiLsRri/view?usp=sharing)

### **Step 1: Backup Your Current Code**

```bash
# Create a backup of your entire project
cp -r /path/to/your/project /path/to/your/project_backup_$(date +%Y%m%d)
```

### **Step 2: Install New Dependencies**

```bash
pip install firebase-admin google-generativeai python-dotenv opencv-python picamera2
```

### **Step 3: Create New Files**

Create these **NEW** files in your project:

#### A. `config.py` (Root directory)
- Copy from artifact: **config.py - Centralized Configuration Management**
- This centralizes all configuration settings

#### B. `lib/services/firebase_rtdb.py` (New service)
- Copy from artifact: **firebase_rtdb.py - Firebase Service**
- Handles all Firebase RTDB operations

#### C. `lib/processes/process_c.py` (Placeholder)
- Copy from artifact: **process_c.py - Placeholder for Future Implementation**
- Empty implementation for future GDrive upload

#### D. `test_setup.py` (Root directory)
- Copy from artifact: **test_setup.py - System Validation Script**
- Tests your entire setup before running

### **Step 4: Update Existing Files**

Replace these files with the **FIXED** versions:

#### A. `main.py`
- **Replace with**: **main.py - Improved with Config & Error Handling**
- **Key changes**:
  - Uses `Config` class for settings
  - Fixed typo: `heght` → `height`
  - Better error handling
  - Process C commented out (not ready yet)

#### B. `lib/processes/process_b.py`
- **Replace with**: **process_b.py - Fixed Version**
- **Key changes**:
  - Fixed SQL syntax (removed trailing comma)
  - Fixed scoring loop iteration
  - Implemented `_update_firebase_rtdb()`
  - Better error handling

#### C. `lib/model/answer_sheet_model.py`
- **Replace with**: **answer_sheet_model.py - Fixed SQL & New Functions**
- **Key changes**:
  - Fixed SQL syntax in `update_answer_key_scores_by_student_id`
  - Added `get_fields_by_processed_rtdb_is_1()`
  - Added `update_processed_rtdb_by_student_id()`

#### D. `lib/processes/process_a_workers/scan_answer_sheet.py`
- **Replace with**: **scan_answer_sheet.py - Fixed Parameter Names**
- **Key changes**:
  - Fixed parameter naming: `current_count_page` → `current_page_count`

#### E. `lib/hardware/camera_controller.py`
- **Replace with**: **camera_controller.py - Fixed Typo**
- **Key changes**:
  - Minor logging improvements

### **Step 5: Update .env File**

```bash
# Copy the updated example
cp .env.example .env

# Edit with your actual credentials
nano .env
```

Update your `.env` with all the new variables from **.env.example**:
- System settings
- Path settings
- Camera settings
- Image processing settings
- API credentials
- Process B settings

### **Step 6: Download Firebase Credentials**

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** → **Service Accounts**
4. Click **Generate New Private Key**
5. Save as `firebase-credentials.json` in your project root
6. Update path in `.env`: `FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json`

### **Step 7: Update .gitignore**

Add these lines to `.gitignore`:

```
# Environment
.env

# Firebase
firebase-credentials.json

# Python
__pycache__/
*.py[cod]
*.log

# Database
*.db
database/
```

### **Step 8: Test Your Setup**

```bash
# Run the validation script
python test_setup.py
```

This will test:
- ✅ Environment variables
- ✅ Firebase credentials
- ✅ Configuration validation
- ✅ Database creation
- ✅ Gemini API
- ✅ Firebase connection
- ✅ Hardware components (optional)

If all tests pass, you're ready!

### **Step 9: Run the Application**

```bash
# Start the application
python main.py
```

---

## 📁 File Structure (After Migration)

```
project_root/
├── .env                                    # ✅ UPDATED - Your environment variables
├── .env.example                            # ✅ NEW - Template for environment variables
├── .gitignore                              # ✅ UPDATED - Add new entries
├── config.py                               # ✅ NEW - Centralized configuration
├── main.py                                 # ✅ UPDATED - Improved with config & error handling
├── test_setup.py                           # ✅ NEW - System validation script
├── firebase-credentials.json               # ✅ NEW - Download from Firebase Console
├── SETUP_GUIDE.md                          # ✅ NEW - Setup instructions
├── MIGRATION_GUIDE.md                      # ✅ NEW - This file
│
├── lib/
│   ├── processes/
│   │   ├── process_a.py                    # ⚪ NO CHANGE
│   │   ├── process_b.py                    # ✅ UPDATED - Fixed bugs + Firebase
│   │   ├── process_c.py                    # ✅ NEW - Placeholder
│   │   └── process_a_workers/
│   │       └── scan_answer_sheet.py        # ✅ UPDATED - Fixed parameter names
│   │
│   ├── model/
│   │   ├── models.py                       # ⚪ NO CHANGE
│   │   ├── answer_key_model.py             # ⚪ NO CHANGE
│   │   └── answer_sheet_model.py           # ✅ UPDATED - Fixed SQL + new functions
│   │
│   ├── services/
│   │   ├── gemini.py                       # ⚪ NO CHANGE
│   │   ├── firebase_rtdb.py                # ✅ NEW - Firebase RTDB service
│   │   ├── utils.py                        # ⚪ NO CHANGE
│   │   └── image_combiner.py               # ⚪ NO CHANGE
│   │
│   ├── hardware/
│   │   ├── camera_controller.py            # ✅ UPDATED - Minor improvements
│   │   ├── keypad_controller.py            # ⚪ NO CHANGE
│   │   └── lcd_controller.py               # ⚪ NO CHANGE
│   │
│   └── logger_config.py                    # ⚪ NO CHANGE
```

**Legend:**
- ✅ UPDATED - Replace with new version
- ✅ NEW - Create new file
- ⚪ NO CHANGE - Keep as is

---

## 🔍 What Changed (Detailed)

### **Bug Fixes:**

1. **process_b.py**:
   - Line 164: Removed trailing comma in SQL query
   - Line 119-125: Fixed iteration logic in scoring update
   - Line 123: Fixed score extraction from nested dict

2. **scan_answer_sheet.py**:
   - Lines 156, 248: Fixed parameter naming consistency

3. **answer_sheet_model.py**:
   - Line 215: Removed trailing comma in SQL query

4. **main.py**:
   - Line 50: Fixed typo `heght` → `height`

### **New Features:**

1. **Centralized Configuration** (`config.py`):
   - All settings in one place
   - Validation on startup
   - Environment variable loading
   - Easy to add new settings

2. **Firebase RTDB Integration** (`firebase_rtdb.py`):
   - Upload student scores
   - Batch processing
   - Error handling
   - Singleton pattern

3. **Complete Firebase Upload** (`process_b.py`):
   - `_update_firebase_rtdb()` fully implemented
   - Groups by assessment_uid
   - Updates processed_rtdb flags
   - Comprehensive error handling

4. **New Database Functions** (`answer_sheet_model.py`):
   - `get_fields_by_processed_rtdb_is_1()` - Fetch records ready for Firebase
   - `update_processed_rtdb_by_student_id()` - Update upload status

5. **System Validation** (`test_setup.py`):
   - Pre-flight checks
   - Tests all components
   - Clear error messages
   - Color-coded output

---

## ⚠️ Breaking Changes

### **1. Configuration Format**

**Old way:**
```python
PRODUCTION_MODE = True
SAVE_LOGS = True
# ... hardcoded in main.py
```

**New way:**
```python
from config import Config

Config.PRODUCTION_MODE  # True/False from .env
Config.SAVE_LOGS        # True/False from .env
```

### **2. Process Arguments**

**Old way:**
```python
process_A_args = {
    "TASK_NAME": "Process A",
    "FRAME_DIMENSIONS": {"width": 1920, "heght": 1080},  # typo!
    # ... many hardcoded values
}
```

**New way:**
```python
from config import Config

process_A_args = Config.get_process_a_args()  # All from config/env
```

### **3. Environment Variables Required**

You **MUST** now set these in `.env`:
- `GEMINI_API_KEY`
- `FIREBASE_CREDENTIALS_PATH`
- `FIREBASE_DATABASE_URL`
- `TEACHER_UID`

The application will **fail to start** if these are missing.

---

## 🧪 Testing Checklist

After migration, test these workflows:

### **1. System Validation**
```bash
python test_setup.py
```
- ✅ All tests should pass

### **2. Answer Key Scanning**
1. Start application: `python main.py`
2. Press `1` to scan answer key
3. Scan a test answer key
4. Check database: `sqlite3 database/checkme.db "SELECT * FROM answer_keys;"`

### **3. Answer Sheet Scanning**
1. Press `2` to scan answer sheets
2. Select an answer key
3. Enter number of sheets and pages
4. Scan test answer sheets
5. Check database: `sqlite3 database/checkme.db "SELECT * FROM answer_sheets;"`

### **4. Background Processing (Process B)**
1. Wait for Process B to pick up sheets
2. Check logs for OCR extraction
3. Check logs for scoring
4. Check Firebase Console for uploaded data

### **5. Firebase Verification**
1. Open Firebase Console
2. Navigate to Realtime Database
3. Check `assessmentScoresAndImages/{your_teacher_uid}/`
4. Verify student scores are present

---

## 🆘 Troubleshooting

### **Problem: "Configuration validation failed"**
**Solution**: 
- Check `.env` file exists
- Verify all required variables are set
- Run `python test_setup.py` to see specific errors

### **Problem: "Firebase not initialized"**
**Solution**:
- Check `firebase-credentials.json` exists
- Verify `FIREBASE_CREDENTIALS_PATH` in `.env` is correct
- Check Firebase Database URL is correct

### **Problem: "Module not found"**
**Solution**:
```bash
pip install firebase-admin google-generativeai python-dotenv
```

### **Problem: "Camera not found" (on Raspberry Pi)**
**Solution**:
- Enable camera in `raspi-config`
- Check camera connection
- Try: `libcamera-hello` to test camera

### **Problem: "Keypad not responding"**
**Solution**:
- Check GPIO pins in `keypad_controller.py`
- Verify physical connections
- Test with: `gpio readall`

---

## 📞 Need Help?

If you encounter issues during migration:

1. **Check logs**: Look in your log files for detailed error messages
2. **Run validation**: `python test_setup.py` shows exactly what's wrong
3. **Check Firebase Console**: Verify your Firebase setup
4. **Review .env**: Make sure all variables are set correctly

---

## ✅ Migration Complete!

Once you've:
- ✅ Created all new files
- ✅ Updated existing files
- ✅ Configured `.env`
- ✅ Downloaded Firebase credentials
- ✅ Passed `test_setup.py`
- ✅ Tested workflows

**You're done!** Your system is now running with:
- Fixed bugs
- Centralized configuration
- Firebase RTDB integration
- Better error handling
- Comprehensive validation

Enjoy your automated answer sheet scanning! 🎉