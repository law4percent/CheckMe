"""
Firebase RTDB Client Module
Provides interface for Firebase Realtime Database operations.
"""

import requests
import json
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from firebase_admin import db


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
    Firebase Realtime Database client.
    
    Example usage:
        db = FirebaseRTDB(
            database_url="https://project-id.firebaseio.com"
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
        database_url: str,
        timeout: int = 10
    ):
        """
        Initialize Firebase RTDB client.
        
        Args:
            database_url: Firebase database URL (e.g., https://project.firebaseio.com)
            timeout: Request timeout in seconds
        """
        self.database_url = database_url.rstrip('/')
        self.timeout = timeout
    
    def _make_request(
        self,
        method  : str,
        path    : str,
        data    : Optional[Dict] = None
    ) -> Any:
        """
        Make HTTP request to Firebase RTDB.
        
        Args:
            method  : HTTP method (GET, POST, PUT, PATCH, DELETE)
            path    : Database path (e.g., /answer_keys/MATH-001)
            data    : Data to send (for POST, PUT, PATCH)
        
        Returns:
            Response data
        
        Raises:
            FirebaseConnectionError: If request fails
        """
        url = f"{self.database_url}{path}.json"
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=self.timeout)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=self.timeout)
            elif method == "PATCH":
                response = requests.patch(url, json=data, timeout=self.timeout)
            elif method == "DELETE":
                response = requests.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.Timeout:
            raise FirebaseConnectionError(f"Request timeout: {path}")
        except requests.RequestException as e:
            raise FirebaseConnectionError(f"Request failed: {e}")
        except Exception as e:
            raise FirebaseError(f"Unexpected error: {e}")
    
    # ===== ANSWER KEY OPERATIONS =====
    
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
        # Validate inputs
        if not assessment_uid or not assessment_uid.strip():
            raise FirebaseDataError("assessment_uid cannot be empty")
        
        if not answer_key or not isinstance(answer_key, dict):
            raise FirebaseDataError("answer_key must be a non-empty dictionary")
        
        if total_questions <= 0:
            raise FirebaseDataError("total_questions must be positive")
        
        # Build data structure
        data = {
            "assessment_uid"    : assessment_uid,
            "answer_key"        : answer_key,
            "total_questions"   : total_questions,
            "image_urls"        : image_urls or [],
            "created_by"        : teacher_uid,
            "created_at"        : db.SERVER_TIMESTAMP,
            "updated_at"        : db.SERVER_TIMESTAMP,
            "section_uid"       : section_uid,
            "subject_uid"       : subject_uid,
        }
        
        path = f"/answer_keys/{teacher_uid}/{assessment_uid}"
        self._make_request("PUT", path, data)
        
        return True
    
    def get_answer_key(self, assessment_uid: str) -> Optional[Dict]:
        """
        Get specific answer key by assessment UID.
        
        Args:
            assessment_uid: Assessment identifier
        
        Returns:
            Answer key data or None if not found
        """
        path = f"/answer_keys/{assessment_uid}"
        data = self._make_request("GET", path)
        return data
    
    def get_answer_keys(self, teacher_uid: Optional[str] = None) -> List[Dict]:
        """
        Get all answer keys, optionally filtered by teacher.
        
        Args:
            teacher_uid: Filter by teacher (None = all keys)
        
        Returns:
            List of answer key dictionaries
        """
        path = "/answer_keys"
        data = self._make_request("GET", path)
        
        if data is None:
            return []
        
        # Convert to list
        answer_keys = []
        for uid, key_data in data.items():
            if teacher_uid is None or key_data.get("created_by") == teacher_uid:
                answer_keys.append(key_data)
        
        return answer_keys
    
    def delete_answer_key(self, assessment_uid: str) -> bool:
        """
        Delete answer key from RTDB.
        
        Args:
            assessment_uid: Assessment identifier
        
        Returns:
            True if deleted
        """
        path = f"/answer_keys/{assessment_uid}"
        self._make_request("DELETE", path)
        return True

    def validate_assessment_exists_get_data(self, assessment_uid: str, teacher_uid: str) -> bool:
        """
        Check if an assessment_uid existence in the database.
        
        Args:
            assessment_uid: Assessment identifier to check
        
        Returns:
            True if exists, False if not found
        
        Raises:
            FirebaseConnectionError: If request fails
        
        Example:
            if firebase.validate_assessment_exists_get_data("MATH-001"):
                print("Assessment existence confirmed!")
        """
        try:
            path = f"/assessments/{teacher_uid}/{assessment_uid}"
            data = self._make_request("GET", path)
            
            # If data is None, assessment doesn't exist
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
            FirebaseConnectionError: If request fails
        
        Example:
            if not firebase.validate_teacher_exists("TCHR-001"):
                raise Exception("Teacher not found in database")
        """
        try:
            # Check if teacher has any answer keys
            path = f"/users/teachers/{teacher_uid}"
            teacher_data = self._make_request("GET", path)
            return teacher_data is not None
            
        except FirebaseConnectionError:
            raise
        except Exception as e:
            raise FirebaseError(f"Failed to validate teacher: {e}")
    
    # ===== STUDENT RESULT OPERATIONS =====
    
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
        # Validate inputs
        if not student_id or not student_id.strip():
            raise FirebaseDataError("student_id cannot be empty")
        
        if not assessment_uid or not assessment_uid.strip():
            raise FirebaseDataError("assessment_uid cannot be empty")
        
        if not answer_sheet or not isinstance(answer_sheet, dict):
            raise FirebaseDataError("answer_sheet must be a non-empty dictionary")
        
        if total_score < 0 or total_score > total_questions:
            raise FirebaseDataError("Invalid total_score")
        
        # Build data structure
        data = {
            "student_id"        : student_id,
            "assessment_uid"    : assessment_uid,
            "answer_sheet"      : answer_sheet,
            "total_score"       : total_score,
            "total_questions"   : total_questions,
            "is_final_score"    : is_final_score,
            "image_urls"        : image_urls or [],
            "checked_by"        : teacher_uid,
            "checked_at"        : db.SERVER_TIMESTAMP,
            "updated_at"        : db.SERVER_TIMESTAMP
        }
        
        # Save to RTDB at /results/{assessment_uid}/{student_id}
        path = f"/results/{assessment_uid}/{student_id}"
        self._make_request("PUT", path, data)
        
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
        path = f"/results/{assessment_uid}/{student_id}"
        data = self._make_request("GET", path)
        return data
    
    def get_assessment_results(self, assessment_uid: str) -> List[Dict]:
        """
        Get all results for a specific assessment.
        
        Args:
            assessment_uid: Assessment identifier
        
        Returns:
            List of student results
        """
        path = f"/results/{assessment_uid}"
        data = self._make_request("GET", path)
        
        if data is None:
            return []
        
        # Convert to list
        results = []
        for student_id, result_data in data.items():
            results.append(result_data)
        
        return results
    
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
        path = f"/results/{assessment_uid}/{student_id}"
        data = {
            "image_urls": image_urls,
            "updated_at": datetime.now().isoformat()
        }
        self._make_request("PATCH", path, data)
        return True
    
    # ===== TEMPORARY CODE OPERATIONS =====
    
    def get_temp_code_data(self, temp_code: str) -> Optional[Dict]:
        """
        Get teacher data from temporary code.
        
        Args:
            temp_code: 8-digit temporary code
        
        Returns:
            Dictionary with uid and username, or None if not found
        """
        path = f"/users_temp_code/{temp_code}"
        data = self._make_request("GET", path)
        return data
    
    # ===== UTILITY OPERATIONS =====
    
    def test_connection(self) -> bool:
        """
        Test connection to Firebase RTDB.
        
        Returns:
            True if connection successful
        """
        try:
            self._make_request("GET", "/.info/connected")
            return True
        except:
            return False
    
    def __repr__(self) -> str:
        return f"FirebaseRTDB(url={self.database_url})"


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    print("="*70)
    print("Example 1: Initialize Firebase client")
    print("="*70)
    
    db = FirebaseRTDB(
        database_url="https://project-rtdb.asia-southeast1.firebasedatabase.app"
    )
    print(f"Initialized: {db}")
    
    # Test connection
    try:
        connected = db.test_connection()
        print(f"Connection test: {'✅ Success' if connected else '❌ Failed'}")
    except Exception as e:
        print(f"Connection test: ❌ {e}")
    
    
    print("\n" + "="*70)
    print("Example 2: Save answer key")
    print("="*70)
    
    try:
        success = db.save_answer_key(
            assessment_uid  = "MATH-2025-001",
            answer_key      = {
                "Q1": "A",
                "Q2": "TRUE",
                "Q3": "CPU",
                "Q4": "FALSE",
                "Q5": "B"
            },
            total_questions = 5,
            image_urls      = [
                "https://res.cloudinary.com/.../page1.jpg",
                "https://res.cloudinary.com/.../page2.jpg"
            ],
            teacher_uid     = "TCHR-12345"
        )
        print(f"✅ Answer key saved: {success}")
    except Exception as e:
        print(f"❌ Failed to save: {e}")
    
    
    print("\n" + "="*70)
    print("Example 3: Get answer key")
    print("="*70)
    
    try:
        answer_key = db.get_answer_key("MATH-2025-001")
        if answer_key:
            print(f"✅ Found answer key:")
            print(f"   Assessment: {answer_key['assessment_uid']}")
            print(f"   Questions: {answer_key['total_questions']}")
            print(f"   Created by: {answer_key['created_by']}")
        else:
            print("❌ Answer key not found")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    
    print("\n" + "="*70)
    print("Example 4: Get all answer keys for teacher")
    print("="*70)
    
    try:
        keys = db.get_answer_keys(teacher_uid="TCHR-12345")
        print(f"✅ Found {len(keys)} answer key(s):")
        for key in keys:
            print(f"   - {key['assessment_uid']} ({key['total_questions']} questions)")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    
    print("\n" + "="*70)
    print("Example 5: Save student result")
    print("="*70)
    
    try:
        success = db.save_student_result(
            student_id      = "STUD-001",
            assessment_uid  = "MATH-2025-001",
            answer_sheet    = {
                "Q1": "A",
                "Q2": "FALSE",  # Wrong answer
                "Q3": "CPU",
                "Q4": "FALSE",
                "Q5": "B"
            },
            total_score     = 4,
            total_questions = 5,
            image_urls      = ["https://res.cloudinary.com/.../student_001.jpg"],
            teacher_uid     = "TCHR-12345",
            is_final_score  = True
        )
        print(f"✅ Student result saved: {success}")
    except Exception as e:
        print(f"❌ Failed to save: {e}")
    
    
    print("\n" + "="*70)
    print("Example 6: Get student result")
    print("="*70)
    
    try:
        result = db.get_student_result(
            assessment_uid="MATH-2025-001",
            student_id="STUD-001"
        )
        if result:
            print(f"✅ Found student result:")
            print(f"   Student: {result['student_id']}")
            print(f"   Score: {result['total_score']}/{result['total_questions']}")
            print(f"   Checked by: {result['checked_by']}")
        else:
            print("❌ Result not found")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    
    print("\n" + "="*70)
    print("Example 7: Get all results for assessment")
    print("="*70)
    
    try:
        results = db.get_assessment_results("MATH-2025-001")
        print(f"✅ Found {len(results)} result(s):")
        for result in results:
            score       = result['total_score']
            total       = result['total_questions']
            percentage  = (score / total * 100) if total > 0 else 0
            print(f"   - {result['student_id']}: {score}/{total} ({percentage:.1f}%)")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    
    print("\n" + "="*70)
    print("Example 8: Update image URLs (background retry)")
    print("="*70)
    
    try:
        success = db.update_image_urls(
            assessment_uid  = "MATH-2025-001",
            student_id      = "STUD-001",
            image_urls      = [
                "https://res.cloudinary.com/.../student_001_retry.jpg"
            ]
        )
        print(f"✅ Image URLs updated: {success}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    
    print("\n" + "="*70)
    print("Example 9: Get temp code data (for authentication)")
    print("="*70)
    
    try:
        code_data = db.get_temp_code_data("12345678")
        if code_data:
            print(f"✅ Found temp code data:")
            print(f"   UID: {code_data.get('uid')}")
            print(f"   Username: {code_data.get('username')}")
        else:
            print("❌ Temp code not found or expired")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    
    print("\n" + "="*70)
    print("Example 10: Complete workflow")
    print("="*70)
    
    def complete_grading_workflow():
        """Simulate complete answer sheet checking workflow"""
        db = FirebaseRTDB(
            database_url="https://project-default-rtdb.asia-southeast1.firebasedatabase.app"
        )
        
        assessment_uid  = "DEMO-WORKFLOW-001"
        teacher_uid     = "TCHR-DEMO"
        
        print("Step 1: Save answer key")
        try:
            db.save_answer_key(
                assessment_uid  = assessment_uid,
                answer_key      = {"Q1": "A", "Q2": "TRUE", "Q3": "C"},
                total_questions = 3,
                image_urls      = ["https://cloudinary.com/key.jpg"],
                teacher_uid     = teacher_uid
            )
            print("✅ Answer key saved")
        except Exception as e:
            print(f"❌ Failed: {e}")
            return
        
        print("\nStep 2: Check if answer key exists")
        try:
            keys = db.get_answer_keys(teacher_uid)
            if any(k['assessment_uid'] == assessment_uid for k in keys):
                print("✅ Answer key found")
            else:
                print("❌ Answer key not found")
                return
        except Exception as e:
            print(f"❌ Failed: {e}")
            return
        
        print("\nStep 3: Save student results")
        students = [
            ("STUD-001", {"Q1": "A", "Q2": "TRUE", "Q3": "C"}, 3),
            ("STUD-002", {"Q1": "B", "Q2": "TRUE", "Q3": "C"}, 2),
            ("STUD-003", {"Q1": "A", "Q2": "FALSE", "Q3": "C"}, 2),
        ]
        
        for student_id, answers, score in students:
            try:
                db.save_student_result(
                    student_id      = student_id,
                    assessment_uid  = assessment_uid,
                    answer_sheet    = answers,
                    total_score     = score,
                    total_questions = 3,
                    image_urls      = [f"https://cloudinary.com/{student_id}.jpg"],
                    teacher_uid     = teacher_uid
                )
                print(f"✅ Saved result for {student_id}: {score}/3")
            except Exception as e:
                print(f"❌ Failed for {student_id}: {e}")
        
        print("\nStep 4: Get all results")
        try:
            results = db.get_assessment_results(assessment_uid)
            print(f"\n📊 Assessment Results ({len(results)} students):")
            for result in results:
                score = result['total_score']
                total = result['total_questions']
                print(f"   {result['student_id']}: {score}/{total}")
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    complete_grading_workflow()
    
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)
    print("\nNOTE: Examples require actual Firebase RTDB connection.")
    print("      Ensure database URL and rules are configured correctly.")