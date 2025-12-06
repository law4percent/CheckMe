# Firebase Integration Setup Guide

This guide will help you integrate Firebase Realtime Database with your CheckMe system for real-time grade syncing.

## 📋 Prerequisites

- Python 3.8+
- Firebase account (free tier is sufficient)
- Firebase project created

## 🔥 Step 1: Firebase Console Setup

### 1.1 Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add Project"
3. Enter project name (e.g., "CheckMe-Grading")
4. Disable Google Analytics (optional)
5. Click "Create Project"

### 1.2 Enable Realtime Database

1. In your Firebase project, click "Realtime Database" in the left menu
2. Click "Create Database"
3. Choose location (e.g., `us-central1`)
4. Start in **Test Mode** (for development)
   ```json
   {
     "rules": {
       ".read": true,
       ".write": true
     }
   }
   ```
5. Click "Enable"

**⚠️ Important:** For production, update rules to:
```json
{
  "rules": {
    "$teacherUid": {
      ".read": "$teacherUid === auth.uid",
      ".write": "$teacherUid === auth.uid"
    }
  }
}
```

### 1.3 Get Database URL

1. In Realtime Database page, note your database URL
2. It looks like: `https://checkme-grading-default-rtdb.firebaseio.com/`
3. **Save this** - you'll need it for `.env`

### 1.4 Generate Service Account Key

1. Click the gear icon (⚙️) → "Project Settings"
2. Go to "Service Accounts" tab
3. Click "Generate New Private Key"
4. Click "Generate Key" (downloads JSON file)
5. **Save this file** as `firebase-credentials.json` in your project root

**⚠️ Security Warning:** Never commit this file to Git! Add to `.gitignore`:
```
firebase-credentials.json
.env
```

## 📦 Step 2: Install Dependencies

```bash
pip install firebase-admin
```

Or add to your `requirements.txt`:
```txt
firebase-admin==6.3.0
```

## ⚙️ Step 3: Environment Configuration

### 3.1 Update `.env` File

Add these lines to your `.env` file:

```env
# Existing Gemini API key
GEMINI_API_KEY=your_gemini_api_key_here

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
FIREBASE_DATABASE_URL=https://checkme-grading-default-rtdb.firebaseio.com/
```

**Replace with your actual values:**
- `FIREBASE_DATABASE_URL`: Your database URL from Step 1.3
- `FIREBASE_CREDENTIALS_PATH`: Path to your service account JSON file

### 3.2 Verify File Structure

```
checkme/
├── firebase-credentials.json    # Your service account key
├── .env                         # Environment variables
├── .gitignore                   # Add firebase-credentials.json here
├── main.py
├── lib/
│   ├── processes/
│   │   ├── process_a.py
│   │   ├── process_b.py
│   │   └── ...
│   └── services/
│       ├── firebase_service.py  # New file
│       ├── gemini.py
│       └── ...
└── ...
```

## 🔧 Step 4: Configure main.py

Update your `main.py` with Firebase settings:

```python
# main.py
from lib.processes import process_a, process_b, process_c
from multiprocessing import Process, Queue, Event

def main(**kargs):
    # ... existing code ...
    
    # Configure Process B with Firebase
    process_B_args = {
        "task_name": "Process B",
        "pc_mode": pc_mode,
        "save_logs": save_logs,
        "poll_interval": 2,
        "teacher_uid": "gbRaC4u7MSRWWRi9LerDQyjVzg22",  # ⚠️ CHANGE THIS to your teacher UID
        "firebase_enabled": True,  # Set to False to disable Firebase
        "status_checker": None
    }
    
    # ... rest of code ...

if __name__ == "__main__":
    pc_mode = True
    save_logs = False
    
    main(
        process_A_args = {
            # ... existing config ...
        },
        process_B_args = {
            "task_name": "Process B",
            "pc_mode": pc_mode,
            "save_logs": save_logs,
            "poll_interval": 2,
            "teacher_uid": "YOUR_TEACHER_UID_HERE",  # ⚠️ CHANGE THIS
            "firebase_enabled": True,
            "answer_key_json_path": "answer_keys/json"
        },
        process_C_args = {
            # ... existing config ...
        }
    )
```

### Where to get Teacher UID?

The `teacher_uid` is from your Firebase Authentication. You have two options:

**Option 1: Use Firebase Authentication**
1. Enable Authentication in Firebase Console
2. Create a user account
3. Copy the UID from Authentication → Users tab

**Option 2: Use a custom string**
For now, you can use any unique string (like your example):
```python
"teacher_uid": "gbRaC4u7MSRWWRi9LerDQyjVzg22"
```

## ✅ Step 5: Test Firebase Connection

### 5.1 Run Test Script

```bash
python -c "from lib.services.firebase_service import FirebaseService; fb = FirebaseService(); print('✅ Success!' if fb.initialized else '❌ Failed')"
```

### 5.2 Test Upload

```python
# test_firebase.py
from lib.services.firebase_service import FirebaseService

firebase = FirebaseService()

if firebase.initialized:
    print("✅ Firebase initialized")
    
    # Test upload
    result = firebase.upload_graded_result(
        teacher_uid="gbRaC4u7MSRWWRi9LerDQyjVzg22",
        assessment_uid="TEST001",
        student_id="123456",
        score=85,
        is_final_score=True
    )
    
    print(f"Upload result: {result}")
    
    # Test retrieval
    get_result = firebase.get_student_result(
        teacher_uid="gbRaC4u7MSRWWRi9LerDQyjVzg22",
        assessment_uid="TEST001",
        student_id="123456"
    )
    
    print(f"Retrieved data: {get_result}")
else:
    print("❌ Firebase initialization failed")
```

Run the test:
```bash
python test_firebase.py
```

## 📊 Step 6: Verify Data in Firebase Console

1. Go to Firebase Console → Realtime Database
2. You should see data structure:
   ```
   gbRaC4u7MSRWWRi9LerDQyjVzg22/
     └── TEST001/
           └── 123456/
                 ├── assessmentUid: "TEST001"
                 ├── studentId: "123456"
                 ├── score: 85
                 ├── isPartialScore: false
                 ├── capturedAt: "12/05/2025 10:30:45"
                 └── uploadedToGdriveAt: null
   ```

## 🚀 Step 7: Run Full System

```bash
python main.py
```

You should see:
```
Process B - OCR Worker is now Running ✅
Firebase sync enabled for teacher: gbRaC4u7MSRWWRi9LerDQyjVzg22
Gemini OCR Engine initialized successfully
✅ Firebase service initialized
```

## 📝 Data Structure Explanation

```json
{
  "teacherUid": {
    "assessmentUid": {
      "studentId": {
        "assessmentUid": "EXAM2025A",
        "studentId": "202512345",
        "score": 23,
        "isPartialScore": false,
        "capturedAt": "12/05/2025 10:30:45",
        "uploadedToGdriveAt": null
      }
    }
  }
}
```

### Fields:
- **teacherUid**: Firebase UID of the teacher
- **assessmentUid**: Unique exam/test identifier
- **studentId**: Student ID extracted from answer sheet
- **score**: Number of correct answers
- **isPartialScore**: `true` if has essay (needs manual review), `false` if final
- **capturedAt**: When the sheet was scanned and graded
- **uploadedToGdriveAt**: When uploaded to Google Drive (set by Process C)

## 🔍 Troubleshooting

### Error: "Firebase not initialized"

**Solution:**
1. Check `.env` file has correct paths
2. Verify `firebase-credentials.json` exists
3. Check Firebase console credentials are valid

```bash
# Test credentials
python -c "import json; print(json.load(open('firebase-credentials.json'))['project_id'])"
```

### Error: "Permission denied"

**Solution:**
1. Check Firebase Database Rules
2. For testing, use open rules:
   ```json
   {
     "rules": {
       ".read": true,
       ".write": true
     }
   }
   ```

### Error: "Module not found: firebase_admin"

**Solution:**
```bash
pip install firebase-admin
```

### Firebase sync failing but system still works

**This is normal!** The system is designed to work with or without Firebase:
- Local database still saves all data
- OCR and grading continues normally
- Firebase is optional cloud sync

To disable Firebase:
```python
process_B_args = {
    # ...
    "firebase_enabled": False
}
```

## 🎯 Usage Examples

### Get All Results for an Assessment

```python
from lib.services.firebase_service import get_firebase_service

firebase = get_firebase_service()
results = firebase.get_assessment_results(
    teacher_uid="gbRaC4u7MSRWWRi9LerDQyjVzg22",
    assessment_uid="EXAM2025A"
)

print(f"Total students: {results['count']}")
for student_id, data in results['data'].items():
    print(f"Student {student_id}: Score {data['score']}")
```

### Update GDrive Upload Timestamp (Process C)

```python
from lib.services.firebase_service import get_firebase_service

firebase = get_firebase_service()
firebase.update_gdrive_timestamp(
    teacher_uid="gbRaC4u7MSRWWRi9LerDQyjVzg22",
    assessment_uid="EXAM2025A",
    student_id="202512345"
)
```

### Delete a Student Result

```python
firebase.delete_student_result(
    teacher_uid="gbRaC4u7MSRWWRi9LerDQyjVzg22",
    assessment_uid="EXAM2025A",
    student_id="202512345"
)
```

## 📚 Next Steps

1. **Secure your rules** - Update Firebase Database Rules for production
2. **Add Firebase Authentication** - Implement proper teacher login
3. **Build Process C** - Implement Google Drive upload with timestamp updates
4. **Mobile App** - Build a mobile app to view real-time grades
5. **Web Dashboard** - Create web interface to monitor Firebase data

## 🔒 Security Best Practices

1. **Never commit credentials**
   ```bash
   echo "firebase-credentials.json" >> .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use environment variables**
   - Never hardcode API keys or paths
   - Always use `.env` file

3. **Implement proper Firebase Rules**
   ```json
   {
     "rules": {
       "$teacherUid": {
         ".read": "$teacherUid === auth.uid || auth.uid === 'admin_uid'",
         ".write": "$teacherUid === auth.uid"
       }
     }
   }
   ```

4. **Rotate credentials periodically**
   - Generate new service account keys every 90 days
   - Update `.env` and restart system

## 📞 Support

If you encounter issues:
1. Check Firebase Console logs
2. Review `process_b.py` logs
3. Test with the provided test scripts
4. Verify all configuration files are in place

---

**You're all set!** Your CheckMe system now syncs grades to Firebase in real-time! 🎉