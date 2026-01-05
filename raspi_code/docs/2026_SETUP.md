# Setup Guide - Answer Sheet Scanner with Firebase Integration

## 📋 Prerequisites

- Python 3.8 or higher
- Raspberry Pi (or compatible hardware)
- Camera module
- Keypad (4x4 or similar)
- LCD display
- Firebase account
- Google Cloud account (for Gemini API)

## 🔧 Installation Steps

### 1. Install Python Dependencies

```bash
# Install required packages
pip install firebase-admin google-generativeai python-dotenv opencv-python picamera2 requests

# Or use requirements.txt if you have one
pip install -r requirements.txt
```

### 2. Setup Firebase

#### A. Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Enable **Realtime Database**

#### B. Get Firebase Credentials
1. Go to **Project Settings** → **Service Accounts**
2. Click **Generate New Private Key**
3. Download the JSON file
4. Save it in your project directory (e.g., `firebase-credentials.json`)
5. **IMPORTANT**: Add this file to `.gitignore`

#### C. Get Database URL
1. Go to **Realtime Database** in Firebase Console
2. Copy the database URL (e.g., `https://your-project-default-rtdb.firebaseio.com`)

### 3. Setup Gemini API

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create an API key
3. Save the API key for your `.env` file

### 4. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Fill in the following values in `.env`:

```bash
GEMINI_API_KEY=AIza...your_actual_key
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com
TEACHER_UID=your_teacher_uid_here
MAX_RETRY=3
BATCH_SIZE=5
```

### 5. Setup .gitignore

Create or update `.gitignore`:

```
# Environment variables
.env

# Firebase credentials
firebase-credentials.json
*.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Logs
*.log

# Database
*.db
*.sqlite
*.sqlite3

# IDE
.vscode/
.idea/
*.swp
*.swo
```

### 6. File Structure

Ensure your project structure looks like this:

```
project_root/
├── .env                              # Your environment variables (not in git)
├── .env.example                      # Template for environment variables
├── .gitignore                        # Git ignore file
├── firebase-credentials.json         # Firebase credentials (not in git)
├── lib/
│   ├── processes/
│   │   ├── process_a.py
│   │   ├── process_b.py              # ✅ UPDATED
│   │   └── process_a_workers/
│   │       └── scan_answer_sheet.py  # ✅ UPDATED
│   ├── model/
│   │   ├── answer_key_model.py
│   │   └── answer_sheet_model.py     # ✅ UPDATED
│   ├── services/
│   │   ├── gemini.py
│   │   ├── firebase_rtdb.py          # ✅ NEW FILE
│   │   └── utils.py
│   └── hardware/
│       ├── camera_controller.py
│       ├── keypad_controller.py
│       └── lcd_controller.py
```

## 🚀 Running the Application

### Test Firebase Connection

Create a test script `test_firebase.py`:

```python
from lib.services.firebase_rtdb import get_firebase_service

# Test Firebase connection
firebase_service = get_firebase_service()

if firebase_service.initialized:
    print("✅ Firebase connected successfully!")
    
    # Test upload
    test_data = [{
        "student_id": "TEST001",
        "score": 23,
        "perfect_score": 30,
        "is_partial_score": False,
        "scanned_at": "01/05/2026 10:30:00"
    }]
    
    result = firebase_service.upload_student_scores(
        teacher_uid="test_teacher",
        assessment_uid="TEST_ASSESSMENT",
        student_records=test_data
    )
    
    print(f"Upload result: {result}")
else:
    print("❌ Firebase connection failed")
```

Run the test:
```bash
python test_firebase.py
```

### Start Main Application

```bash
# Start the main application
python main.py

# Or if you have separate processes
python -m lib.processes.process_a &
python -m lib.processes.process_b &
```

## 🔍 Troubleshooting

### Firebase Issues

**Problem**: `Firebase not initialized`
- **Solution**: Check if `FIREBASE_CREDENTIALS_PATH` points to the correct JSON file
- Verify the file exists and is readable
- Check Firebase Database URL is correct

**Problem**: `Permission denied` when accessing Firebase
- **Solution**: Check Firebase Rules in Firebase Console
- For testing, you can use:
```json
{
  "rules": {
    ".read": "auth != null",
    ".write": "auth != null"
  }
}
```

### Gemini API Issues

**Problem**: `GEMINI_API_KEY not set`
- **Solution**: Check `.env` file has the correct API key
- Make sure you're loading `.env` with `python-dotenv`

**Problem**: Rate limit errors
- **Solution**: The code already handles rate limiting with retries
- Increase `MAX_RETRY` in `.env` if needed
- Add delays between API calls

### Database Issues

**Problem**: SQL syntax errors
- **Solution**: The fixed version removes trailing commas in SQL queries
- Make sure you're using the updated `answer_sheet_model.py`

## 📊 Firebase Data Structure

After running the application, your Firebase RTDB will have this structure:

```json
{
  "assessmentScoresAndImages": {
    "teacher_uid_123": {
      "ASSESSMENT_001": {
        "STUDENT_001": {
          "score": 23,
          "perfectScore": 30,
          "isPartialScore": false,
          "assessmentUid": "ASSESSMENT_001",
          "scannedAt": "01/05/2026 10:30:00"
        },
        "STUDENT_002": {
          "score": 28,
          "perfectScore": 30,
          "isPartialScore": false,
          "assessmentUid": "ASSESSMENT_001",
          "scannedAt": "01/05/2026 10:32:15"
        }
      }
    }
  }
}
```

## 🔐 Security Best Practices

1. **Never commit credentials**:
   - Add `.env` to `.gitignore`
   - Add `firebase-credentials.json` to `.gitignore`

2. **Use environment variables**:
   - All sensitive data should be in `.env`
   - Use `python-dotenv` to load them

3. **Restrict Firebase access**:
   - Set proper Firebase Rules
   - Use authentication for production

4. **Rotate API keys regularly**:
   - Update Gemini API key periodically
   - Regenerate Firebase credentials if compromised

## 📝 What's New in This Update

### Fixed Issues:
- ✅ SQL syntax errors (trailing commas removed)
- ✅ Parameter naming inconsistencies in `scan_answer_sheet.py`
- ✅ Scoring logic errors in `process_b.py`
- ✅ Missing `processed_rtdb` field handling

### New Features:
- ✅ Firebase RTDB integration
- ✅ Complete `_update_firebase_rtdb()` function
- ✅ New database functions for RTDB upload tracking
- ✅ Proper error handling for Firebase operations

### New Files:
- ✅ `lib/services/firebase_rtdb.py` - Firebase service
- ✅ `.env.example` - Environment variables template

## 🎯 Next Steps

1. Test the scan answer sheet workflow with real papers
2. Monitor Process B logs for any errors
3. Verify Firebase uploads in Firebase Console
4. Test with your mobile app to ensure data appears correctly
5. Adjust `BATCH_SIZE` based on your hardware performance

## 📞 Support

If you encounter issues:
1. Check the logs in your application
2. Verify all environment variables are set correctly
3. Test Firebase connection with the test script
4. Check Firebase Console for uploaded data