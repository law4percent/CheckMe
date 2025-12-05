# lib/services/firebase_rtdb.py
"""
Firebase Realtime Database Service
Syncs graded answer sheets to Firebase for real-time access
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Try to import Firebase SDK
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase Admin SDK not installed. Run: pip install firebase-admin")


class FirebaseService:
    """Firebase Realtime Database service for syncing graded results."""
    
    def __init__(self):
        """Initialize Firebase connection."""
        self.initialized = False
        self.db_ref = None
        
        if not FIREBASE_AVAILABLE:
            logger.error("Firebase SDK not available")
            return
        
        try:
            # Check if already initialized
            try:
                firebase_admin.get_app()
                self.initialized = True
                logger.info("Firebase already initialized")
            except ValueError:
                # Not initialized, do it now
                self._initialize_firebase()
                
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
    
    def _initialize_firebase(self):
        """Initialize Firebase app with credentials."""
        try:
            # Get credentials path from environment
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            database_url = os.getenv("FIREBASE_DATABASE_URL")
            
            if not cred_path:
                logger.error("FIREBASE_CREDENTIALS_PATH not set in .env")
                return
            
            if not database_url:
                logger.error("FIREBASE_DATABASE_URL not set in .env")
                return
            
            if not os.path.exists(cred_path):
                logger.error(f"Firebase credentials file not found: {cred_path}")
                return
            
            # Initialize Firebase
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            
            self.initialized = True
            logger.info("✅ Firebase initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.initialized = False
    
    def upload_graded_result(
        self,
        teacher_uid: str,
        assessment_uid: str,
        student_id: str,
        score: int,
        is_final_score: bool,
        graded_at: Optional[str] = None
    ) -> Dict:
        """
        Upload graded result to Firebase.
        
        Structure: {teacher_uid}/{assessment_uid}/{student_id}
        
        Args:
            teacher_uid: Teacher's Firebase UID
            assessment_uid: Assessment identifier
            student_id: Student ID
            score: Student's score
            is_final_score: Whether this is final or needs manual review
            graded_at: Timestamp (optional, defaults to now)
        
        Returns:
            Status dictionary
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized"
            }
        
        try:
            # Default timestamp
            if not graded_at:
                graded_at = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            
            # Prepare data
            student_data = {
                "assessmentUid": assessment_uid,
                "studentId": str(student_id),
                "score": score,
                "isPartialScore": not is_final_score,
                "capturedAt": graded_at,
                "uploadedToGdriveAt": None  # Will be updated by Process C
            }
            
            # Build reference path
            ref_path = f"{teacher_uid}/{assessment_uid}/{student_id}"
            
            # Upload to Firebase
            ref = db.reference(ref_path)
            ref.set(student_data)
            
            logger.info(f"✅ Uploaded to Firebase: {ref_path}")
            
            return {
                "status": "success",
                "ref_path": ref_path,
                "data": student_data
            }
            
        except Exception as e:
            logger.error(f"Failed to upload to Firebase: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def update_gdrive_timestamp(
        self,
        teacher_uid: str,
        assessment_uid: str,
        student_id: str,
        uploaded_at: Optional[str] = None
    ) -> Dict:
        """
        Update Google Drive upload timestamp for a student record.
        
        Args:
            teacher_uid: Teacher's Firebase UID
            assessment_uid: Assessment identifier
            student_id: Student ID
            uploaded_at: Timestamp (optional, defaults to now)
        
        Returns:
            Status dictionary
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized"
            }
        
        try:
            if not uploaded_at:
                uploaded_at = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            
            ref_path = f"{teacher_uid}/{assessment_uid}/{student_id}/uploadedToGdriveAt"
            ref = db.reference(ref_path)
            ref.set(uploaded_at)
            
            logger.info(f"✅ Updated GDrive timestamp: {ref_path}")
            
            return {
                "status": "success",
                "ref_path": ref_path,
                "uploaded_at": uploaded_at
            }
            
        except Exception as e:
            logger.error(f"Failed to update GDrive timestamp: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_student_result(
        self,
        teacher_uid: str,
        assessment_uid: str,
        student_id: str
    ) -> Dict:
        """
        Get a specific student's graded result from Firebase.
        
        Args:
            teacher_uid: Teacher's Firebase UID
            assessment_uid: Assessment identifier
            student_id: Student ID
        
        Returns:
            Student data or error
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized"
            }
        
        try:
            ref_path = f"{teacher_uid}/{assessment_uid}/{student_id}"
            ref = db.reference(ref_path)
            data = ref.get()
            
            if data:
                return {
                    "status": "success",
                    "data": data
                }
            else:
                return {
                    "status": "error",
                    "message": "Student result not found"
                }
                
        except Exception as e:
            logger.error(f"Failed to get student result: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_assessment_results(
        self,
        teacher_uid: str,
        assessment_uid: str
    ) -> Dict:
        """
        Get all student results for an assessment.
        
        Args:
            teacher_uid: Teacher's Firebase UID
            assessment_uid: Assessment identifier
        
        Returns:
            All student results or error
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized"
            }
        
        try:
            ref_path = f"{teacher_uid}/{assessment_uid}"
            ref = db.reference(ref_path)
            data = ref.get()
            
            if data:
                return {
                    "status": "success",
                    "data": data,
                    "count": len(data)
                }
            else:
                return {
                    "status": "success",
                    "data": {},
                    "count": 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get assessment results: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def delete_student_result(
        self,
        teacher_uid: str,
        assessment_uid: str,
        student_id: str
    ) -> Dict:
        """
        Delete a student's result from Firebase.
        
        Args:
            teacher_uid: Teacher's Firebase UID
            assessment_uid: Assessment identifier
            student_id: Student ID
        
        Returns:
            Status dictionary
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized"
            }
        
        try:
            ref_path = f"{teacher_uid}/{assessment_uid}/{student_id}"
            ref = db.reference(ref_path)
            ref.delete()
            
            logger.info(f"🗑️ Deleted from Firebase: {ref_path}")
            
            return {
                "status": "success",
                "ref_path": ref_path
            }
            
        except Exception as e:
            logger.error(f"Failed to delete student result: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def batch_upload_results(
        self,
        teacher_uid: str,
        assessment_uid: str,
        students_data: Dict
    ) -> Dict:
        """
        Batch upload multiple student results at once.
        
        Args:
            teacher_uid: Teacher's Firebase UID
            assessment_uid: Assessment identifier
            students_data: Dictionary of {student_id: result_data}
        
        Returns:
            Status dictionary
        """
        if not self.initialized:
            return {
                "status": "error",
                "message": "Firebase not initialized"
            }
        
        try:
            ref_path = f"{teacher_uid}/{assessment_uid}"
            ref = db.reference(ref_path)
            ref.update(students_data)
            
            logger.info(f"✅ Batch uploaded {len(students_data)} results to Firebase")
            
            return {
                "status": "success",
                "count": len(students_data),
                "ref_path": ref_path
            }
            
        except Exception as e:
            logger.error(f"Failed to batch upload: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

# Global Firebase service instance
_firebase_service = None

def get_firebase_service() -> FirebaseService:
    """Get or create Firebase service singleton."""
    global _firebase_service
    if _firebase_service is None:
        _firebase_service = FirebaseService()
    return _firebase_service


def upload_result_to_firebase(
    teacher_uid: str,
    assessment_uid: str,
    student_id: str,
    score: int,
    is_final_score: bool
) -> Dict:
    """Convenience function to upload a single result."""
    service = get_firebase_service()
    return service.upload_graded_result(
        teacher_uid=teacher_uid,
        assessment_uid=assessment_uid,
        student_id=student_id,
        score=score,
        is_final_score=is_final_score
    )


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Test Firebase connection
    logging.basicConfig(level=logging.INFO)
    
    firebase = FirebaseService()
    
    if firebase.initialized:
        print("✅ Firebase initialized successfully")
        
        # Test upload
        result = firebase.upload_graded_result(
            teacher_uid="gbRaC4u7MSRWWRi9LerDQyjVzg22",
            assessment_uid="QWER1234",
            student_id="2352352",
            score=23,
            is_final_score=True
        )
        print(f"Upload result: {result}")
        
        # Test get
        get_result = firebase.get_student_result(
            teacher_uid="gbRaC4u7MSRWWRi9LerDQyjVzg22",
            assessment_uid="QWER1234",
            student_id="2352352"
        )
        print(f"Get result: {get_result}")
    else:
        print("❌ Firebase initialization failed")