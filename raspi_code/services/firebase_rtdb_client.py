"""
Firebase RTDB Client Module
Provides interface for Firebase Realtime Database operations.
Uses Firebase Admin SDK internally — public interface is unchanged.
"""

import os
import json
from typing import Optional, Dict, Any, List

import firebase_admin
from firebase_admin import credentials, db


class FirebaseError(Exception):
    """Base exception for Firebase operations"""
    pass


class FirebaseConnectionError(FirebaseError):
    """Raised when connection to Firebase fails"""
    pass


class FirebaseDataError(FirebaseError):
    """Raised when data validation fails"""
    pass


class FirebaseRTDB:
    """
    Firebase Realtime Database client (Admin SDK).

    Initializes the Firebase Admin SDK once per process. If the app is already
    initialized (e.g. called from multiple modules), it reuses the existing app.

    Example usage:
        db = FirebaseRTDB(
            database_url        = "https://project-id.firebaseio.com",
            credentials_path    = "firebase-credentials.json"
        )

        # Save answer key
        db.save_answer_key(
            assessment_uid  = "MATH-001",
            answer_key      = {"Q1": "A", "Q2": "TRUE"},
            total_questions = 50,
            image_urls      = ["https://..."],
            teacher_uid     = "TCHR-001",
            section_uid     = "-Fkk3f-..",
            subject_uid     = "-SFkk3f-.."
        )

        # Get answer keys
        keys = db.get_answer_keys(teacher_uid="TCHR-001")

        # Save student result
        db.save_student_result(
            student_id      = "STUD-001",
            assessment_uid  = "MATH-001",
            answer_sheet    = {"Q1": "A", "Q2": "FALSE"},
            total_score     = 45,
            total_questions = 50,
            image_urls      = ["https://..."],
            teacher_uid     = "TCHR-001"
        )
    """

    def __init__(
        self,
        database_url        : str,
        credentials_path    : str   = "firebase-credentials.json",
        timeout             : int   = 10
    ):
        """
        Initialize Firebase RTDB client.

        Args:
            database_url        : Firebase RTDB URL (e.g. https://project.firebaseio.com)
            credentials_path    : Path to Firebase service account JSON file
            timeout             : Unused — kept for backwards compatibility
        """
        self.database_url   = database_url.rstrip('/')
        self.timeout        = timeout   # kept for API compatibility

        self._initialize_app(credentials_path)

    def _initialize_app(self, credentials_path: str) -> None:
        """
        Initialize Firebase Admin SDK once per process.
        Safely skips if already initialized.
        """
        if firebase_admin._apps:
            return  # Already initialized — reuse existing app

        try:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred, {
                "databaseURL": self.database_url
            })
        except Exception as e:
            raise FirebaseConnectionError(f"Failed to initialize Firebase app: {e}")

    def _ref(self, path: str):
        """Return a database reference for the given path."""
        try:
            return db.reference(path)
        except Exception as e:
            raise FirebaseConnectionError(f"Failed to get DB reference: {e}")

    def _get(self, path: str) -> Any:
        """GET a value from the database."""
        try:
            return self._ref(path).get()
        except Exception as e:
            raise FirebaseConnectionError(f"GET failed at {path}: {e}")

    def _set(self, path: str, data: Dict) -> None:
        """SET (PUT) a value at the given path."""
        try:
            self._ref(path).set(data)
        except Exception as e:
            raise FirebaseConnectionError(f"SET failed at {path}: {e}")

    def _update(self, path: str, data: Dict) -> None:
        """PATCH (update) fields at the given path."""
        try:
            self._ref(path).update(data)
        except Exception as e:
            raise FirebaseConnectionError(f"UPDATE failed at {path}: {e}")

    def _delete(self, path: str) -> None:
        """DELETE the node at the given path."""
        try:
            self._ref(path).delete()
        except Exception as e:
            raise FirebaseConnectionError(f"DELETE failed at {path}: {e}")

    # =========================================================================
    # ANSWER KEY OPERATIONS
    # =========================================================================

    def save_answer_key(
        self,
        assessment_uid  : str,
        answer_key      : Dict[str, str],
        total_questions : int,
        image_urls      : List[str],
        teacher_uid     : str,
        section_uid     : str,
        subject_uid     : str
    ) -> bool:
        """
        Save answer key to Firebase RTDB.

        Args:
            assessment_uid  : Unique assessment identifier
            answer_key      : Dictionary of answers (e.g., {"Q1": "A", "Q2": "TRUE"})
            total_questions : Total number of questions
            image_urls      : List of Cloudinary URLs
            teacher_uid     : Teacher identifier
            section_uid     : Section identifier
            subject_uid     : Subject identifier

        Returns:
            True if successful

        Raises:
            FirebaseDataError       : If validation fails
            FirebaseConnectionError : If save fails
        """
        if not assessment_uid or not assessment_uid.strip():
            raise FirebaseDataError("assessment_uid cannot be empty")

        if not answer_key or not isinstance(answer_key, dict):
            raise FirebaseDataError("answer_key must be a non-empty dictionary")

        if total_questions <= 0:
            raise FirebaseDataError("total_questions must be positive")

        now = db.SERVER_TIMESTAMP

        data = {
            "assessment_uid"    : assessment_uid,
            "answer_key"        : answer_key,
            "total_questions"   : total_questions,
            "image_urls"        : image_urls or [],
            "created_by"        : teacher_uid,
            "created_at"        : now,
            "updated_at"        : now,
            "section_uid"       : section_uid,
            "subject_uid"       : subject_uid,
        }

        self._set(f"/answer_keys/{teacher_uid}/{assessment_uid}", data)
        return True

    def get_answer_key(self, assessment_uid: str, teacher_uid: str) -> Optional[Dict]:
        """
        Get a specific answer key by assessment UID and teacher UID.

        Args:
            assessment_uid  : Assessment identifier
            teacher_uid     : Teacher identifier

        Returns:
            Answer key data or None if not found
        """
        return self._get(f"/answer_keys/{teacher_uid}/{assessment_uid}")

    def get_answer_keys(self, teacher_uid: Optional[str] = None) -> List[Dict]:
        """
        Get all answer keys, optionally filtered by teacher.

        Args:
            teacher_uid: Filter by teacher (None = all keys)

        Returns:
            List of answer key dictionaries
        """
        data = None
        if teacher_uid:
            data = self._get(f"/answer_keys/{teacher_uid}")

        if data is None:
            return []

        answer_keys = []
        if teacher_uid:
            for uid, key_data in data.items():
                answer_keys.append(key_data)

        return answer_keys

    def delete_answer_key(self, assessment_uid: str, teacher_uid: str) -> bool:
        """
        Delete answer key from RTDB.

        Args:
            assessment_uid  : Assessment identifier
            teacher_uid     : Teacher identifier

        Returns:
            True if deleted
        """
        self._delete(f"/answer_keys/{teacher_uid}/{assessment_uid}")
        return True

    def validate_assessment_exists_get_data(
        self,
        assessment_uid  : str,
        teacher_uid     : str
    ) -> Optional[Dict]:
        """
        Check if an assessment_uid exists and return its metadata.

        Args:
            assessment_uid  : Assessment identifier to check
            teacher_uid     : Teacher identifier

        Returns:
            Dict with section_uid and subject_uid if exists, False if not found

        Raises:
            FirebaseConnectionError : If request fails
        """
        try:
            data = self._get(f"/assessments/{teacher_uid}/{assessment_uid}")

            if data is not None:
                return {
                    "section_uid" : data.get("section_uid"),
                    "subject_uid" : data.get("subject_uid")
                }
            return False

        except FirebaseConnectionError:
            raise
        except Exception as e:
            raise FirebaseError(f"Failed to validate assessment: {e}")

    def validate_teacher_exists(self, teacher_uid: str) -> bool:
        """
        Check if a teacher_uid exists in the database.

        Args:
            teacher_uid: Teacher identifier to check

        Returns:
            True if teacher exists, False if not found

        Raises:
            FirebaseConnectionError : If request fails
        """
        try:
            teacher_data = self._get(f"/users/teachers/{teacher_uid}")
            return teacher_data is not None

        except FirebaseConnectionError:
            raise
        except Exception as e:
            raise FirebaseError(f"Failed to validate teacher: {e}")

    # =========================================================================
    # STUDENT RESULT OPERATIONS
    # =========================================================================

    def save_student_result(
        self,
        student_id      : str,
        assessment_uid  : str,
        answer_sheet    : Dict[str, str],
        total_score     : int,
        total_questions : int,
        image_urls      : List[str],
        teacher_uid     : str,
        is_final_score  : bool = True
    ) -> bool:
        """
        Save student result to Firebase RTDB.

        Args:
            student_id      : Student identifier
            assessment_uid  : Assessment identifier
            answer_sheet    : Student's answers
            total_score     : Score achieved
            total_questions : Total possible score
            image_urls      : List of Cloudinary URLs
            teacher_uid     : Teacher who checked
            is_final_score  : Whether this is the final score

        Returns:
            True if successful
        """
        if not student_id or not student_id.strip():
            raise FirebaseDataError("student_id cannot be empty")

        if not assessment_uid or not assessment_uid.strip():
            raise FirebaseDataError("assessment_uid cannot be empty")

        if not answer_sheet or not isinstance(answer_sheet, dict):
            raise FirebaseDataError("answer_sheet must be a non-empty dictionary")

        if total_score < 0 or total_score > total_questions:
            raise FirebaseDataError("Invalid total_score")

        now = db.SERVER_TIMESTAMP

        data = {
            "student_id"        : student_id,
            "assessment_uid"    : assessment_uid,
            "answer_sheet"      : answer_sheet,
            "total_score"       : total_score,
            "total_questions"   : total_questions,
            "is_final_score"    : is_final_score,
            "image_urls"        : image_urls or [],
            "checked_by"        : teacher_uid,
            "checked_at"        : now,
            "updated_at"        : now,
        }

        self._set(f"/results/{assessment_uid}/{student_id}", data)
        return True

    def get_student_result(
        self,
        assessment_uid  : str,
        student_id      : str
    ) -> Optional[Dict]:
        """
        Get specific student result.

        Args:
            assessment_uid  : Assessment identifier
            student_id      : Student identifier

        Returns:
            Student result data or None if not found
        """
        return self._get(f"/results/{assessment_uid}/{student_id}")

    def get_assessment_results(self, assessment_uid: str) -> List[Dict]:
        """
        Get all results for a specific assessment.

        Args:
            assessment_uid: Assessment identifier

        Returns:
            List of student results
        """
        data = self._get(f"/results/{assessment_uid}")

        if data is None:
            return []

        return list(data.values())

    def update_image_urls(
        self,
        assessment_uid  : str,
        student_id      : str,
        image_urls      : List[str]
    ) -> bool:
        """
        Update image URLs for a student result (for background retry).

        Args:
            assessment_uid  : Assessment identifier
            student_id      : Student identifier
            image_urls      : Updated list of URLs

        Returns:
            True if successful
        """
        self._update(f"/results/{assessment_uid}/{student_id}", {
            "image_urls": image_urls,
            "updated_at": db.SERVER_TIMESTAMP
        })
        return True

    # =========================================================================
    # TEMPORARY CODE OPERATIONS
    # =========================================================================

    def get_temp_code_data(self, temp_code: str) -> Optional[Dict]:
        """
        Get teacher data from temporary code.

        Args:
            temp_code: 8-digit temporary code

        Returns:
            Dictionary with uid and username, or None if not found
        """
        return self._get(f"/users_temp_code/{temp_code}")

    # =========================================================================
    # UTILITY OPERATIONS
    # =========================================================================

    def test_connection(self) -> bool:
        """
        Test connection to Firebase RTDB.

        Returns:
            True if connection successful
        """
        try:
            self._get("/.info/connected")
            return True
        except:
            return False

    def __repr__(self) -> str:
        return f"FirebaseRTDB(url={self.database_url})"


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from services.utils import normalize_path

    load_dotenv(normalize_path("config/.env"))

    FIREBASE_RTDB_BASE_REFERENCE    = os.getenv("FIREBASE_RTDB_BASE_REFERENCE")
    FIREBASE_CREDENTIALS_PATH       = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

    firebase = FirebaseRTDB(
        database_url        = FIREBASE_RTDB_BASE_REFERENCE,
        credentials_path    = FIREBASE_CREDENTIALS_PATH
    )

    print("=" * 60)
    print("Example 1: Test connection")
    print("=" * 60)
    connected = firebase.test_connection()
    print(f"Connected: {connected}")


    print("\n" + "=" * 60)
    print("Example 2: Validate teacher exists")
    print("=" * 60)
    teacher_uid = "TCHR-001"
    exists = firebase.validate_teacher_exists(teacher_uid)
    print(f"Teacher {teacher_uid} exists: {exists}")


    print("\n" + "=" * 60)
    print("Example 3: Validate assessment exists")
    print("=" * 60)
    assessment_uid  = "MATH-001"
    assessment_data = firebase.validate_assessment_exists_get_data(assessment_uid, teacher_uid)
    print(f"Assessment data: {assessment_data}")


    print("\n" + "=" * 60)
    print("Example 4: Save answer key")
    print("=" * 60)
    success = firebase.save_answer_key(
        assessment_uid  = "MATH-001",
        answer_key      = {"Q1": "A", "Q2": "B", "Q3": "C", "Q4": "TRUE", "Q5": "FALSE"},
        total_questions = 5,
        image_urls      = ["https://res.cloudinary.com/demo/image/upload/sample.jpg"],
        teacher_uid     = "TCHR-001",
        section_uid     = "-SectionUID123",
        subject_uid     = "-SubjectUID456"
    )
    print(f"Save answer key success: {success}")


    print("\n" + "=" * 60)
    print("Example 5: Get answer keys by teacher")
    print("=" * 60)
    keys = firebase.get_answer_keys(teacher_uid="TCHR-001")
    print(f"Found {len(keys)} answer key(s):")
    for k in keys:
        print(f"  - {k.get('assessment_uid')} | {k.get('total_questions')} questions")


    print("\n" + "=" * 60)
    print("Example 6: Save student result")
    print("=" * 60)
    success = firebase.save_student_result(
        student_id      = "STUD-001",
        assessment_uid  = "MATH-001",
        answer_sheet    = {"Q1": "A", "Q2": "B", "Q3": "D", "Q4": "TRUE", "Q5": "TRUE"},
        total_score     = 3,
        total_questions = 5,
        image_urls      = ["https://res.cloudinary.com/demo/image/upload/student_sheet.jpg"],
        teacher_uid     = "TCHR-001"
    )
    print(f"Save student result success: {success}")


    print("\n" + "=" * 60)
    print("Example 7: Get student result")
    print("=" * 60)
    result = firebase.get_student_result("MATH-001", "STUD-001")
    print(f"Student result: {result}")


    print("\n" + "=" * 60)
    print("Example 8: Get all results for an assessment")
    print("=" * 60)
    results = firebase.get_assessment_results("MATH-001")
    print(f"Found {len(results)} result(s) for MATH-001:")
    for r in results:
        print(f"  - {r.get('student_id')} | Score: {r.get('total_score')}/{r.get('total_questions')}")


    print("\n" + "=" * 60)
    print("Example 9: Update image URLs (background retry)")
    print("=" * 60)
    success = firebase.update_image_urls(
        assessment_uid  = "MATH-001",
        student_id      = "STUD-001",
        image_urls      = ["https://res.cloudinary.com/demo/image/upload/updated_sheet.jpg"]
    )
    print(f"Update image URLs success: {success}")


    print("\n" + "=" * 60)
    print("Example 10: Get temp code data")
    print("=" * 60)
    temp_data = firebase.get_temp_code_data("12345678")
    print(f"Temp code data: {temp_data}")


    print("\n" + "=" * 60)
    print("Example 11: Delete answer key")
    print("=" * 60)
    success = firebase.delete_answer_key("MATH-001", "TCHR-001")
    print(f"Delete answer key success: {success}")

    print("\n✅ All examples completed!")