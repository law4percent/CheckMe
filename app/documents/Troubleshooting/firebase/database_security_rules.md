# Firebase Realtime Database Security Rules for CheckMe

## Problem

When navigating to SubjectDashboardScreen, you get a "Permission denied" error when trying to fetch enrollments:

```
ERROR  ❌ [getSubjectEnrollments] Error: [Error: Permission denied]
Path: enrollments/gbRaC4u7MSRWWRi9LerDQyjVzg22/-ObU44PyUobZIgZNY5GI
```

This occurs because the **Firebase Realtime Database security rules** don't allow teachers to read/write enrollment data at the current path structure.

## Root Cause

The app uses this database structure:
```
enrollments/
  {teacherId}/
    {subjectId}/
      {studentId}/
        - status
        - joinedAt
        - studentName
        - studentEmail
```

However, Firebase security rules likely don't have proper rules to allow:
1. Teachers to read enrollments for their subjects
2. Students to create enrollment requests
3. Teachers to approve/reject enrollments

## Solution: Update Firebase Security Rules

### Step 1: Access Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Navigate to **Realtime Database** → **Rules** tab

### Step 2: Add Security Rules

Replace or update your rules with the following:

```json
{
  "rules": {
    "users": {
      "$uid": {
        ".read": "$uid === auth.uid",
        ".write": "$uid === auth.uid"
      }
    },
    "sections": {
      "$teacherId": {
        ".read": "$teacherId === auth.uid",
        ".write": "$teacherId === auth.uid",
        "$sectionId": {
          ".read": "$teacherId === auth.uid",
          ".write": "$teacherId === auth.uid"
        }
      }
    },
    "subjects": {
      "$teacherId": {
        "$sectionId": {
          "$subjectId": {
            ".read": "$teacherId === auth.uid",
            ".write": "$teacherId === auth.uid"
          }
        }
      }
    },
    "enrollments": {
      "$teacherId": {
        "$subjectId": {
          ".read": "$teacherId === auth.uid",
          "$studentId": {
            ".write": "$teacherId === auth.uid || $studentId === auth.uid",
            ".validate": "newData.hasChildren(['studentId', 'subjectId', 'status', 'joinedAt'])"
          }
        }
      }
    }
  }
}
```

### Step 3: Publish Rules

Click **Publish** button in the Firebase Console to apply the rules.

## Rules Explanation

### Users
```json
"users": {
  "$uid": {
    ".read": "$uid === auth.uid",
    ".write": "$uid === auth.uid"
  }
}
```
- Users can only read/write their own profile data

### Sections
```json
"sections": {
  "$teacherId": {
    ".read": "$teacherId === auth.uid",
    ".write": "$teacherId === auth.uid"
  }
}
```
- Teachers can only read/write sections they created

### Subjects
```json
"subjects": {
  "$teacherId": {
    "$sectionId": {
      "$subjectId": {
        ".read": "$teacherId === auth.uid",
        ".write": "$teacherId === auth.uid"
      }
    }
  }
}
```
- Teachers can only read/write subjects they created
- Path includes teacherId, sectionId, and subjectId

### Enrollments (The Key Fix)
```json
"enrollments": {
  "$teacherId": {
    "$subjectId": {
      ".read": "$teacherId === auth.uid",
      "$studentId": {
        ".write": "$teacherId === auth.uid || $studentId === auth.uid"
      }
    }
  }
}
```

**Critical Rules:**
1. **Read Permission**: Only the teacher who owns the subject can read enrollments
   - `".read": "$teacherId === auth.uid"`
   
2. **Write Permission**: Either the teacher or the student can write
   - `".write": "$teacherId === auth.uid || $studentId === auth.uid"`
   - Teacher can approve/reject enrollments
   - Student can create enrollment requests

3. **Data Validation**: Ensures required fields are present
   - `".validate": "newData.hasChildren(['studentId', 'subjectId', 'status', 'joinedAt'])"`

## Testing After Applying Rules

1. **Restart your app** (close and reopen)
2. **Navigate to SubjectDashboardScreen**
3. **Check console logs** - you should see:
   ```
   LOG  📚 [getSubjectEnrollments] Fetching enrollments
   LOG    - Snapshot exists: true/false
   LOG  ✅ [SubjectDashboard] Enrollments fetched successfully: 0
   ```

## Enhanced Security Rules (Optional)

For production, consider adding more granular rules:

```json
{
  "rules": {
    "enrollments": {
      "$teacherId": {
        "$subjectId": {
          ".read": "$teacherId === auth.uid",
          "$studentId": {
            ".write": "$teacherId === auth.uid || $studentId === auth.uid",
            ".validate": "newData.hasChildren(['studentId', 'subjectId', 'status', 'joinedAt'])",
            "status": {
              ".validate": "newData.isString() && (newData.val() === 'pending' || newData.val() === 'approved' || newData.val() === 'rejected')"
            },
            "studentId": {
              ".validate": "newData.isString() && newData.val() === $studentId"
            },
            "subjectId": {
              ".validate": "newData.isString() && newData.val() === $subjectId"
            },
            "joinedAt": {
              ".validate": "newData.isNumber()"
            },
            "approvedAt": {
              ".validate": "newData.isNumber()"
            },
            "rejectedAt": {
              ".validate": "newData.isNumber()"
            },
            "studentName": {
              ".validate": "newData.isString()"
            },
            "studentEmail": {
              ".validate": "newData.isString()"
            },
            "$other": {
              ".validate": false
            }
          }
        }
      }
    }
  }
}
```

This adds:
- Status must be one of: 'pending', 'approved', 'rejected'
- IDs must match the path parameters
- Timestamps must be numbers
- No additional fields allowed

## Common Issues

### Issue 1: Rules not taking effect
**Solution:** Wait 30-60 seconds after publishing rules, then restart your app

### Issue 2: Still getting permission denied
**Solution:** Check that:
1. User is authenticated (`auth.uid` is not null)
2. TeacherId in path matches logged-in user's UID
3. Subject exists and belongs to the teacher

### Issue 3: Students can't enroll
**Solution:** Ensure student authentication is implemented and the write rule includes `$studentId === auth.uid`

## Database Structure Overview

```
firebase-realtime-database/
├── users/
│   └── {uid}/
│       ├── email
│       ├── fullName
│       ├── role
│       └── ...
├── sections/
│   └── {teacherId}/
│       └── {sectionId}/
│           ├── year
│           ├── sectionName
│           └── ...
├── subjects/
│   └── {teacherId}/
│       └── {sectionId}/
│           └── {subjectId}/
│               ├── subjectName
│               ├── subjectCode
│               └── ...
└── enrollments/
    └── {teacherId}/
        └── {subjectId}/
            └── {studentId}/
                ├── status
                ├── joinedAt
                ├── studentName
                └── studentEmail
```

## Summary

1. **Problem**: Permission denied when accessing enrollments
2. **Cause**: Missing or incorrect Firebase Security Rules
3. **Solution**: Add proper rules allowing teachers to read/write their enrollments
4. **Key Rule**: `".read": "$teacherId === auth.uid"` at enrollments/{teacherId}/{subjectId}/

After applying these rules, the SubjectDashboardScreen will be able to fetch and manage enrollments successfully.