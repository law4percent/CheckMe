# lib/services/firebase_rtdb.py
"""
Firebase Realtime Database Service
Handles uploading student scores and assessment data to Firebase RTDB
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("firebase-admin not installed. Install with: pip install firebase-admin")


class FirebaseRTDBService:
    """Firebase Realtime Database service for uploading assessment scores"""
    
    def __init__(self):
        """Initialize Firebase Admin SDK"""
        self.initialized = False
        
        if not FIREBASE_AVAILABLE:
            logger.error("Firebase Admin SDK not available")
            return
        
        try:
            # Check if already initialized
            firebase_admin.get_app()
            self.initialized = True
            logger.info("Firebase app already initialized")
            return
        except ValueError:
            pass
        
        # Initialize new app
        try:
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            database_url = os.getenv("FIREBASE_DATABASE_URL")
            
            if not cred_path:
                logger.error("FIREBASE_CREDENTIALS_PATH not set in environment")
                return
            
            if not database_url:
                logger.error("FIREBASE_DATABASE_URL not set in environment")
                return
            
            if not os.path.exists(cred_path):
                logger.error(f"Firebase credentials file not found: {cred_path}")
                return
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            
            self.initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.initialized = False
    
    def upload_student_scores(
        self, 
        teacher_uid: str, 
        assessment_uid: str, 
        student_records: List[Dict]
    ) -> Dict:
        """
        Upload student scores to Firebase RTDB
        
        Args:
            teacher_uid: Teacher's unique identifier
            assessment_uid: Assessment unique identifier
            student_records: List of student score dictionaries
                Each record should contain:
                - student_id: str
                - score: int
                - perfect_score: int
                - is_partial_score: bool
                - scanned_at: str (timestamp)
        
        Returns:
            Dictionary with status and results
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized. Check credentials and environment variables.",
                "uploaded_count": 0,
                "failed_count": len(student_records)
            }
        
        if not student_records:
            return {
                "status": "success",
                "message": "No records to upload",
                "uploaded_count": 0,
                "failed_count": 0
            }
        
        try:
            # Reference to the assessment scores node
            ref = db.reference(f'assessmentScoresAndImages/{teacher_uid}/{assessment_uid}')
            
            uploaded_count = 0
            failed_records = []
            
            for record in student_records:
                try:
                    student_id = str(record["student_id"])
                    
                    # Prepare data for upload
                    upload_data = {
                        "score": int(record["score"]),
                        "perfectScore": int(record["perfect_score"]),
                        "isPartialScore": bool(record.get("is_partial_score", False)),
                        "assessmentUid": assessment_uid,
                        "scannedAt": record.get("scanned_at", datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
                    }
                    
                    # Upload to Firebase
                    ref.child(student_id).set(upload_data)
                    uploaded_count += 1
                    
                    logger.info(f"Uploaded score for student {student_id} to Firebase")
                    
                except Exception as e:
                    logger.error(f"Failed to upload student {record.get('student_id', 'unknown')}: {e}")
                    failed_records.append({
                        "student_id": record.get("student_id", "unknown"),
                        "error": str(e)
                    })
            
            failed_count = len(failed_records)
            
            if failed_count == 0:
                return {
                    "status": "success",
                    "message": f"Successfully uploaded {uploaded_count} student records",
                    "uploaded_count": uploaded_count,
                    "failed_count": 0
                }
            elif uploaded_count > 0:
                return {
                    "status": "partial",
                    "message": f"Uploaded {uploaded_count}, failed {failed_count}",
                    "uploaded_count": uploaded_count,
                    "failed_count": failed_count,
                    "failed_records": failed_records
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to upload all {failed_count} records",
                    "uploaded_count": 0,
                    "failed_count": failed_count,
                    "failed_records": failed_records
                }
                
        except Exception as e:
            logger.error(f"Firebase upload error: {e}")
            return {
                "status": "error",
                "message": f"Firebase upload failed: {str(e)}",
                "uploaded_count": 0,
                "failed_count": len(student_records)
            }
    
    def get_assessment_scores(self, teacher_uid: str, assessment_uid: str) -> Dict:
        """
        Retrieve all scores for a specific assessment
        
        Args:
            teacher_uid: Teacher's unique identifier
            assessment_uid: Assessment unique identifier
        
        Returns:
            Dictionary with status and data
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized"
            }
        
        try:
            ref = db.reference(f'assessmentScoresAndImages/{teacher_uid}/{assessment_uid}')
            data = ref.get()
            
            if data is None:
                return {
                    "status": "success",
                    "message": "No data found",
                    "data": {}
                }
            
            return {
                "status": "success",
                "data": data
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve scores: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def delete_student_score(
        self, 
        teacher_uid: str, 
        assessment_uid: str, 
        student_id: str
    ) -> Dict:
        """
        Delete a specific student's score
        
        Args:
            teacher_uid: Teacher's unique identifier
            assessment_uid: Assessment unique identifier
            student_id: Student's unique identifier
        
        Returns:
            Dictionary with status
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized"
            }
        
        try:
            ref = db.reference(f'assessmentScoresAndImages/{teacher_uid}/{assessment_uid}/{student_id}')
            ref.delete()
            
            logger.info(f"Deleted score for student {student_id}")
            return {
                "status": "success",
                "message": f"Deleted score for student {student_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete student score: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# Singleton instance
_firebase_service = None

def get_firebase_service() -> FirebaseRTDBService:
    """Get or create Firebase service singleton"""
    global _firebase_service
    if _firebase_service is None:
        _firebase_service = FirebaseRTDBService()
    return _firebase_service