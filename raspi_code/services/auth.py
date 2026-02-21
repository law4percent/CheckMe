"""
Authentication Module
Manages teacher credentials and authentication state for the grading system.

Authentication Flow:
1. Check if cred.txt exists with valid credentials → Skip login
2. If not authenticated, prompt for temporary 8-digit code from mobile app
3. Validate code against Firebase RTDB
4. Retrieve teacher_uid and username from RTDB
5. Save credentials to cred.txt for persistent session
"""

import os
import json
import requests
from typing import Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from . import utils

class AuthStatus(Enum):
    """Authentication status states"""
    AUTHENTICATED       = "authenticated"
    NOT_AUTHENTICATED   = "not_authenticated"


class CodeValidationStatus(Enum):
    """Temporary code validation results"""
    VALID           = "valid"
    INVALID         = "invalid"
    EXPIRED         = "expired"
    NOT_FOUND       = "not_found"
    NETWORK_ERROR   = "network_error"


@dataclass
class Credentials:
    """Teacher credentials data structure"""
    teacher_uid : Optional[str] = None
    username    : Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if credentials are valid (both fields non-null)"""
        return self.teacher_uid is not None and self.username is not None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "teacher_uid": self.teacher_uid,
            "username": self.username
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Credentials':
        """Create Credentials from dictionary"""
        return cls(
            teacher_uid=data.get("teacher_uid"),
            username=data.get("username")
        )


class AuthenticationError(Exception):
    """Base exception for authentication errors"""
    pass


class CredentialsFileError(AuthenticationError):
    """Raised when credentials file operations fail"""
    pass


class TeacherAuth:
    """
    Manages teacher authentication with temporary 8-digit code validation.
    
    Authentication Flow:
    1. Check cred.txt for existing valid credentials → AUTHENTICATED
    2. If not found/invalid → Prompt for temporary code from mobile app
    3. Teacher generates 8-digit code in mobile app (format: 12345678)
    4. Code is valid for 30 seconds in Firebase RTDB
    5. System validates code against RTDB at: /users_temp_code/{temp_code}/
    6. Retrieves teacher_uid and username from RTDB
    7. Saves credentials to cred.txt for persistent session
    
    Example usage:
        auth = TeacherAuth()
        
        if auth.is_authenticated():
            print("Already logged in!")
        else:
            temp_code = keypad.read_input(
                length=8,
                valid_keys=['0','1','2','3','4','5','6','7','8','9']
            )
            
            success, message = auth.login_with_temp_code(temp_code)
            
            if success:
                print(f"Welcome, {auth.get_current_user().username}!")
            else:
                print(f"Login failed: {message}")
    """
    
    def __init__(
        self,
        credentials_file : str  = "credentials/cred.txt",
        firebase_url     : str  = "https://project-rtdb.asia-southeast1.firebasedatabase.app",
        auto_create      : bool = True
    ):
        """
        Initialize authentication manager.
        
        Args:
            credentials_file: Path to local credentials cache file
            firebase_url: Firebase Realtime Database base URL
            auto_create: Automatically create credentials file if missing
        """
        self.credentials_file   = utils.normalize_path(credentials_file)
        self.firebase_url       = firebase_url.rstrip('/')
        self.auto_create        = auto_create
        self._current_credentials: Optional[Credentials] = None
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(self.credentials_file)
        if parent_dir:
            utils.create_directories(parent_dir)
        
        # Auto-create empty credentials file if needed
        if auto_create and not os.path.exists(self.credentials_file):
            self._create_empty_credentials_file()
    
    def _create_empty_credentials_file(self) -> None:
        """Create a new credentials file with null values"""
        empty_creds = Credentials()
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(empty_creds.to_dict(), f, indent=2)
        except Exception as e:
            raise CredentialsFileError(f"Failed to create credentials file: {e}")
    
    def _load_credentials_from_file(self) -> Optional[Credentials]:
        """Load credentials from local cache file"""
        if not os.path.exists(self.credentials_file):
            return None
        
        try:
            with open(self.credentials_file, 'r') as f:
                data = json.load(f)
            
            if "teacher_uid" not in data or "username" not in data:
                return None
            
            return Credentials.from_dict(data)
        except json.JSONDecodeError:
            return None
        except Exception as e:
            raise CredentialsFileError(f"Failed to load credentials: {e}")
    
    def _save_credentials_to_file(self, credentials: Credentials) -> None:
        """Save credentials to local cache file"""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials.to_dict(), f, indent=2)
        except Exception as e:
            raise CredentialsFileError(f"Failed to save credentials: {e}")
    
    def _validate_temp_code_format(self, temp_code: str) -> bool:
        """
        Validate temporary code format: 8 digits only.
        
        Args:
            temp_code: Code to validate
        
        Returns:
            True if valid (8 digits), False otherwise
        """
        temp_code = temp_code.strip()
        if len(temp_code) != 8:
            return False
        if not temp_code.isdigit():
            return False
        return True
    
    def _fetch_credentials_from_firebase(
        self, temp_code: str
    ) -> Tuple[CodeValidationStatus, Optional[Credentials]]:
        """
        Validate temporary code against Firebase RTDB and retrieve credentials.
        
        Args:
            temp_code: 8-digit temporary code
        
        Returns:
            (validation_status, credentials or None)
        
        Firebase RTDB structure:
        /users_temp_code/{temp_code}/
            ├─ uid: "TCHR-12345"
            └─ username: "prof_smith"
        """
        # Normalize and validate format
        temp_code = temp_code.strip()
        
        if not self._validate_temp_code_format(temp_code):
            return (CodeValidationStatus.INVALID, None)
        
        # Build Firebase URL
        url = f"{self.firebase_url}/users_temp_code/{temp_code}.json"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 404:
                return (CodeValidationStatus.NOT_FOUND, None)
            
            response.raise_for_status()
            data = response.json()
            
            # Check if data exists (null means expired/not found)
            if data is None:
                return (CodeValidationStatus.NOT_FOUND, None)
            
            # Validate required fields
            if "uid" not in data or "username" not in data:
                return (CodeValidationStatus.INVALID, None)
            
            # Check if fields are non-null
            if data["uid"] is None or data["username"] is None:
                return (CodeValidationStatus.EXPIRED, None)
            
            # Create credentials
            credentials = Credentials(
                teacher_uid = data["uid"],
                username    = data["username"]
            )
            
            return (CodeValidationStatus.VALID, credentials)
            
        except requests.Timeout:
            return (CodeValidationStatus.NETWORK_ERROR, None)
        except requests.RequestException:
            return (CodeValidationStatus.NETWORK_ERROR, None)
        except Exception:
            return (CodeValidationStatus.INVALID, None)
    
    def check_authentication(self) -> Tuple[AuthStatus, Optional[Credentials]]:
        """
        Check current authentication status from local cache.
        
        Returns:
            (status, credentials or None)
        
        Flow:
            1. Check if cred.txt exists → Create if missing
            2. Load credentials from file
            3. Check if required keys exist
            4. Check if both values are non-null
            5. Return status + credentials
        """
        if not os.path.exists(self.credentials_file):
            if self.auto_create:
                self._create_empty_credentials_file()
            return (AuthStatus.NOT_AUTHENTICATED, None)
        
        credentials = self._load_credentials_from_file()
        
        if credentials is None:
            return (AuthStatus.NOT_AUTHENTICATED, None)
        
        if not credentials.is_valid():
            return (AuthStatus.NOT_AUTHENTICATED, None)
        
        self._current_credentials = credentials
        return (AuthStatus.AUTHENTICATED, credentials)
    
    def is_authenticated(self) -> bool:
        """
        Quick check if currently authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        status, _ = self.check_authentication()
        return status == AuthStatus.AUTHENTICATED
    
    def login_with_temp_code(self, temp_code: str) -> Tuple[bool, str]:
        """
        Authenticate using 8-digit temporary code from mobile app.
        
        Args:
            temp_code: 8-digit code (e.g., 12345678)
        
        Returns:
            (success: bool, message: str)
        
        Examples:
            success, msg = auth.login_with_temp_code("12345678")
            if success:
                user = auth.get_current_user()
                print(f"Welcome, {user.username}!")
        """
        if not temp_code or not temp_code.strip():
            return (False, "Code cannot be empty")
        
        status, credentials = self._fetch_credentials_from_firebase(temp_code)
        
        if status == CodeValidationStatus.VALID:
            self._save_credentials_to_file(credentials)
            self._current_credentials = credentials
            return (True, "Login successful")
        elif status == CodeValidationStatus.INVALID:
            return (False, "Invalid code. Must be 8 digits.")
        elif status == CodeValidationStatus.NOT_FOUND:
            return (False, "Code not found. Generate new code.")
        elif status == CodeValidationStatus.EXPIRED:
            return (False, "Code expired. Generate new code.")
        elif status == CodeValidationStatus.NETWORK_ERROR:
            return (False, "Network error. Check connection.")
        else:
            return (False, "Unknown error occurred")
    
    def logout(self) -> bool:
        """
        Clear current credentials (logout).
        
        Returns:
            True if logout successful
        """
        empty_creds = Credentials()
        self._save_credentials_to_file(empty_creds)
        self._current_credentials = None
        return True
    
    def get_current_user(self) -> Optional[Credentials]:
        """
        Get current authenticated user credentials.
        
        Returns:
            Credentials object if authenticated, None otherwise
        """
        status, credentials = self.check_authentication()
        if status == AuthStatus.AUTHENTICATED:
            return credentials
        return None
    
    def get_credentials_file_path(self) -> str:
        """Get the path to the credentials file"""
        return self.credentials_file
    
    def credentials_file_exists(self) -> bool:
        """Check if credentials file exists"""
        return os.path.exists(self.credentials_file)
    
    def __repr__(self) -> str:
        status = "authenticated" if self.is_authenticated() else "not authenticated"
        return f"TeacherAuth(status={status})"


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    print("="*70)
    print("Example 1: Check existing session")
    print("="*70)
    
    auth = TeacherAuth(credentials_file="/tmp/test_cred.txt")
    
    status, credentials = auth.check_authentication()
    print(f"Status: {status.value}")
    print(f"Is authenticated: {auth.is_authenticated()}")
    
    
    print("\n" + "="*70)
    print("Example 2: Code format validation (8 digits)")
    print("="*70)
    
    test_codes = [
        ("12345678", True),
        ("00000000", True),
        ("99999999", True),
        (" 12345678 ", True),
        ("1234567", False),   # Too short
        ("123456789", False), # Too long
        ("ABCD1234", False),  # Contains letters
        ("1234 5678", False), # Contains space
        ("", False),          # Empty
    ]
    
    for code, expected in test_codes:
        is_valid = auth._validate_temp_code_format(code)
        symbol = "✅" if is_valid == expected else "❌"
        print(f"{symbol} '{code}' → Valid: {is_valid} (expected: {expected})")
    
    
    print("\n" + "="*70)
    print("Example 3: Main application login flow")
    print("="*70)
    
    def main_app_flow():
        """Complete authentication flow for RaspberryPi system"""
        auth = TeacherAuth(credentials_file="/tmp/app_cred.txt")
        
        # STEP 1: Check existing session
        print("Checking existing session...")
        if auth.is_authenticated():
            user = auth.get_current_user()
            print(f"✅ Already authenticated as: {user.username}")
            return True, user.teacher_uid, user.username
        
        # STEP 2: Login required
        print("❌ Not authenticated - login required")
        print("\n--- Login Screen ---")
        print("1. Open CheckMe mobile app")
        print("2. Tap 'Generate Login Code'")
        print("3. Enter 8-digit code (e.g., 12345678)")
        print("4. Code expires in 30 seconds\n")
        
        # In real system: 
        # temp_code = keypad.read_input(
        #     length=8,
        #     valid_keys=['0','1','2','3','4','5','6','7','8','9']
        # )
        temp_code = input("Enter 8-digit code: ")
        
        success, message = auth.login_with_temp_code(temp_code)
        
        if success:
            user = auth.get_current_user()
            print(f"✅ {message}")
            print(f"   Welcome, {user.username}!")
            return True, user.teacher_uid, user.username
        else:
            print(f"❌ {message}")
            return False, None, None
    
    is_auth, uid, username = main_app_flow()
    
    
    print("\n" + "="*70)
    print("Example 4: RaspberryPi LCD/Keypad integration")
    print("="*70)
    
    def raspi_login_screen():
        """How it would work on actual RaspberryPi"""
        auth = TeacherAuth()
        
        # Check existing session
        if auth.is_authenticated():
            user = auth.get_current_user()
            # lcd.show(f"Welcome, {user.username}!")
            print(f"LCD: Welcome, {user.username}!")
            return True
        
        # Show login screen
        print("\nLCD Display:")
        print("╔════════════════════════════╗")
        print("║    LOGIN REQUIRED          ║")
        print("╠════════════════════════════╣")
        print("║  Open mobile app           ║")
        print("║  Generate 8-digit code     ║")
        print("║                            ║")
        print("║  Enter code:               ║")
        print("║  > ********                ║")
        print("╚════════════════════════════╝")
        
        # Read from keypad (8 digits, masked display)
        # keypad = Keypad3x4()
        # temp_code = keypad.read_input(
        #     length=8,
        #     valid_keys=['0','1','2','3','4','5','6','7','8','9'],
        #     echo_callback=lambda text: lcd.show(f"Code: {'*' * len(text)}")
        # )
        
        temp_code = "12345678"  # Simulated
        print(f"\nKeypad input: {temp_code}")
        
        success, message = auth.login_with_temp_code(temp_code)
        
        if success:
            user = auth.get_current_user()
            print(f"LCD: ✅ Welcome, {user.username}!")
            return True
        else:
            print(f"LCD: ❌ {message}")
            return False
    
    raspi_login_screen()
    
    
    print("\n" + "="*70)
    print("Example 5: Logout and session management")
    print("="*70)
    
    # Manually create session
    creds = Credentials(teacher_uid="TCHR-TEST", username="test_teacher")
    auth._save_credentials_to_file(creds)
    print(f"Before logout: {auth.is_authenticated()}")
    
    auth.logout()
    print(f"After logout: {auth.is_authenticated()}")
    
    
    print("\n" + "="*70)
    print("Example 6: Error scenarios")
    print("="*70)
    
    error_tests = [
        ("", "Empty code"),
        ("1234567", "Too short (7 digits)"),
        ("123456789", "Too long (9 digits)"),
        ("ABCD1234", "Contains letters"),
        ("1234 5678", "Contains space"),
    ]
    
    for code, desc in error_tests:
        success, msg = auth.login_with_temp_code(code)
        print(f"{desc:30} → {msg}")
    
    
    print("\n" + "="*70)
    print("Example 7: Complete login workflow")
    print("="*70)
    
    def complete_login_workflow():
        """Full workflow with keypad simulation"""
        auth = TeacherAuth(credentials_file="/tmp/workflow_cred.txt")
        
        # Check session
        if auth.is_authenticated():
            print("✅ Session exists, skip login")
            return
        
        print("LCD: LOGIN REQUIRED")
        print("LCD: Generate code in app")
        print("LCD: Enter 8-digit code\n")
        
        # Simulate keypad reading 8 digits
        entered_code = ""
        for i in range(8):
            digit = str(i)  # Simulated keypad input
            entered_code += digit
            masked = "*" * len(entered_code)
            print(f"LCD: Code: {masked}")
        
        print(f"\nEntered: {entered_code}")
        
        # Validate
        success, message = auth.login_with_temp_code(entered_code)
        print(f"Result: {message}")
    
    complete_login_workflow()
    
    
    print("\n" + "="*70)
    print("Cleanup")
    print("="*70)
    
    test_files = [
        "/tmp/test_cred.txt",
        "/tmp/app_cred.txt",
        "/tmp/workflow_cred.txt"
    ]
    
    for f in test_files:
        if os.path.exists(f):
            os.remove(f)
            print(f"✅ Removed: {f}")
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)
    print("\nNOTE: Real Firebase connection required for actual login.")
    print("      Examples use simulated data for demonstration.")