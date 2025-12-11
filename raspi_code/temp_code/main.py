"""
✓ Collage created: /home/checkme2025/answer_checker/images/collage_20251211_075115.jpg
INFO:__main__:Sending collage to Gemini API...
ERROR:__main__:JSON parse error: Unterminated string starting at: line 20 column 6 (char 1237)
ERROR:__main__:Response text: ```json
{
  "assessmentUid": "QWER1234",
  "studentId": "232080",
  "score": 95,
  "totalQuestions": 22,
  "correctAnswers": 21,
  "incorrectAnswers": 1,
  "details": [
    {"question": 1, "studentAnswer": "b", "correctAnswer": "b", "isCorrect": true},
    {"question": 2, "studentAnswer": "c", "correctAnswer": "c", "isCorrect": true},
    {"question": 3, "studentAnswer": "d", "correctAnswer": "c", "isCorrect": false},
    {"question": 4, "studentAnswer": "d", "correctAnswer": "d", "isCorrect": true},
    {"question": 5, "studentAnswer": "b", "correctAnswer": "b", "isCorrect": true},
    {"question": 6, "studentAnswer": "c", "correctAnswer": "c", "isCorrect": true},
    {"question": 7, "studentAnswer": "c", "correctAnswer": "c", "isCorrect": true},
    {"question": 1, "studentAnswer": "Hardware interrupt", "correctAnswer": "Hardware interrupt", "isCorrect": true},
    {"question": 2, "studentAnswer": "Interrupt Service Routine", "correctAnswer": "Interrupt Service Routine", "isCorrect": true},
    {"question": 3, "studentAnswer": "Polling", "correctAnswer": "Polling", "isCorrect": true},
    {"question": 4, "studentAnswer": "Interrupt Priority Register", "correctAnswer": "Interrupt Priority Register", "isCorrect": true},
    {"question
✗ Failed to get Gemini response
"""

#!/usr/bin/env python3
"""
Answer Sheet Checker System for Raspberry Pi 4B
Components: 3x4 Keypad, Camera Module (PiCamera2)
"""

import RPi.GPIO as GPIO
from picamera2 import Picamera2
from libcamera import Transform
import cv2
import time
import base64
import json
import requests
from PIL import Image
import numpy as np
from io import BytesIO
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try SDK first, fallback to REST API
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai SDK not available, using REST API fallback")

# ==================== CONFIGURATION ====================

# Gemini API Key - SET THIS DIRECTLY
GEMINI_API_KEY = "AIzaSyDvYrAvyHQ3N9MMLWtOKaU-G2BJQZN70WU"  # Replace with your actual key

# 3x4 Keypad GPIO Configuration (adjust pins as needed)
ROW_PINS = [5, 6, 13, 19]  # GPIO pins for rows
COL_PINS = [12, 16, 20]     # GPIO pins for columns

# Keypad layout
KEYPAD = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#']
]

# Firebase Configuration
FIREBASE_URL = "https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app"
TEACHER_UID = "GKVi81kM8dhoHra1zvM4EZJF9VC3"

# Gemini API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

# Image storage paths - Use current user's home directory
IMAGE_DIR = os.path.expanduser("~/answer_checker/images")
os.makedirs(IMAGE_DIR, exist_ok=True)

# Camera Configuration
CAMERA_CONFIG = {
    "resolution": (1920, 1080),
    "format": "RGB888",
    "rotation": 0  # Adjust if needed (0, 90, 180, 270)
}

# ==================== GPIO SETUP ====================

def setup_keypad():
    """Initialize GPIO for keypad"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Set row pins as output
    for row_pin in ROW_PINS:
        GPIO.setup(row_pin, GPIO.OUT)
        GPIO.output(row_pin, GPIO.HIGH)
    
    # Set column pins as input with pull-up resistors
    for col_pin in COL_PINS:
        GPIO.setup(col_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("✓ Keypad initialized")

def get_key():
    """Read key press from 3x4 keypad"""
    key = None
    
    for row_idx, row_pin in enumerate(ROW_PINS):
        GPIO.output(row_pin, GPIO.LOW)
        
        for col_idx, col_pin in enumerate(COL_PINS):
            if GPIO.input(col_pin) == GPIO.LOW:
                key = KEYPAD[row_idx][col_idx]
                
                # Wait for key release (debounce)
                while GPIO.input(col_pin) == GPIO.LOW:
                    time.sleep(0.01)
                time.sleep(0.1)  # Additional debounce delay
        
        GPIO.output(row_pin, GPIO.HIGH)
        
        if key:
            break
    
    return key

# ==================== CAMERA FUNCTIONS (PiCamera2) ====================

class CameraController:
    """Handles PiCamera2 operations"""
    
    def __init__(self):
        """Initialize camera"""
        self.picam2 = Picamera2()
        
        # Configure camera
        config = self.picam2.create_still_configuration(
            main={
                "size": CAMERA_CONFIG["resolution"],
                "format": CAMERA_CONFIG["format"]
            },
            transform=Transform(hflip=False, vflip=False)
        )

        
        self.picam2.configure(config)
        logger.info("✓ Camera initialized")
    
    def start(self):
        """Start camera"""
        self.picam2.start()
        time.sleep(2)  # Camera warm-up
        logger.info("✓ Camera started")
    
    def stop(self):
        """Stop camera"""
        self.picam2.stop()
        logger.info("✓ Camera stopped")
    
    def capture_image(self, image_type):
        """
        Capture image using PiCamera2
        Args:
            image_type: 'answer_key' or 'answer_sheet'
        Returns:
            Path to saved image
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{image_type}_{timestamp}.jpg"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        print(f"📷 Capturing {image_type}...")
        
        try:
            # Capture image as numpy array
            image_array = self.picam2.capture_array()
            
            # Convert RGB to BGR for OpenCV
            image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # Apply rotation if configured
            if CAMERA_CONFIG["rotation"] == 90:
                image_bgr = cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)
            elif CAMERA_CONFIG["rotation"] == 180:
                image_bgr = cv2.rotate(image_bgr, cv2.ROTATE_180)
            elif CAMERA_CONFIG["rotation"] == 270:
                image_bgr = cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # Save image
            cv2.imwrite(filepath, image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            print(f"✓ Image saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Camera capture error: {e}")
            return None
    
    def preview(self, duration=3):
        """
        Show preview for a duration (optional - useful for alignment)
        Args:
            duration: Preview duration in seconds
        """
        print(f"👁️  Showing preview for {duration} seconds...")
        time.sleep(duration)

# ==================== IMAGE PROCESSING ====================

def create_collage(answer_key_path, answer_sheet_path):
    """
    Create horizontal collage of answer key and answer sheet
    Returns:
        Base64 encoded collage image, collage path
    """
    print("🖼️  Creating collage...")
    
    try:
        # Load images using PIL
        img_key = Image.open(answer_key_path)
        img_sheet = Image.open(answer_sheet_path)
        
        # Resize to same height if needed
        max_height = max(img_key.height, img_sheet.height)
        
        if img_key.height != max_height:
            ratio = max_height / img_key.height
            img_key = img_key.resize((int(img_key.width * ratio), max_height), Image.Resampling.LANCZOS)
        
        if img_sheet.height != max_height:
            ratio = max_height / img_sheet.height
            img_sheet = img_sheet.resize((int(img_sheet.width * ratio), max_height), Image.Resampling.LANCZOS)
        
        # Create collage
        total_width = img_key.width + img_sheet.width
        collage = Image.new('RGB', (total_width, max_height))
        
        collage.paste(img_key, (0, 0))
        collage.paste(img_sheet, (img_key.width, 0))
        
        # Save collage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        collage_path = os.path.join(IMAGE_DIR, f"collage_{timestamp}.jpg")
        collage.save(collage_path, quality=95)
        
        print(f"✓ Collage created: {collage_path}")
        
        # Convert to base64
        buffered = BytesIO()
        collage.save(buffered, format="JPEG", quality=95)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return img_base64, collage_path
        
    except Exception as e:
        logger.error(f"Collage creation error: {e}")
        return None, None

# ==================== GEMINI API CLASS ====================

class GeminiChecker:
    """Handles Gemini API interactions for answer checking"""
    
    CHECKING_PROMPT = """
You are an automated answer sheet checker. You will receive a horizontal collage image containing:
- LEFT SIDE: Answer key with assessment UID at the top
- RIGHT SIDE: Student's answer sheet with student ID at the top

Your task:
1. Extract the Assessment UID from the top of the answer key (left image)
2. Extract the Student ID from the top of the answer sheet (right image)
3. Compare each answer on the student's sheet with the answer key
4. Calculate the total score (correct answers / total questions * 100)
5. Identify which questions were answered correctly and incorrectly

Return ONLY a JSON object in this exact format (no markdown, no explanation):
{
  "assessmentUid": "extracted_assessment_uid",
  "studentId": "extracted_student_id",
  "score": 85,
  "totalQuestions": 20,
  "correctAnswers": 17,
  "incorrectAnswers": 3,
  "details": [
    {"question": 1, "studentAnswer": "B", "correctAnswer": "B", "isCorrect": true},
    {"question": 2, "studentAnswer": "C", "correctAnswer": "A", "isCorrect": false}
  ],
  "timestamp": "current_timestamp_iso_format"
}

Be accurate in reading both the UIDs and comparing answers.
"""
    
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            raise RuntimeError("GEMINI_API_KEY not set. Please edit the script and add your API key.")
        
        if GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                "gemini-2.5-flash",
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_output_tokens": 2048,
                }
            )
            logger.info("Using google-generativeai SDK")
        else:
            self.model = None
            logger.info("Using REST API fallback")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    
    def _call_gemini_sdk(self, image_base64: str, prompt: str) -> str:
        """Call Gemini using official SDK"""
        try:
            # Decode base64 to bytes for SDK
            image_bytes = base64.b64decode(image_base64)
            
            # Create image part
            image_part = {
                "mime_type": "image/jpeg",
                "data": image_bytes
            }
            
            response = self.model.generate_content([prompt, image_part])
            return response.text
            
        except Exception as e:
            logger.error(f"SDK call failed: {e}")
            raise
    
    def _call_gemini_rest(self, image_base64: str, prompt: str) -> str:
        """Call Gemini using REST API fallback"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.api_key}"
            
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "topP": 0.9,
                    "maxOutputTokens": 2048
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                logger.error(f"REST API error: {response.status_code}")
                raise RuntimeError(f"API call failed: {response.text}")
                
        except Exception as e:
            logger.error(f"REST call failed: {e}")
            raise
    
    def _safe_parse_json(self, response_text: str) -> dict:
        """Safely parse JSON from response"""
        try:
            # Remove markdown code blocks if present
            cleaned = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response text: {response_text}")
            return None
    
    def check_collage(self, collage_path: str) -> dict:
        """Check answer sheet using collage image"""
        logger.info("Sending collage to Gemini API...")
        
        try:
            image_base64 = self._encode_image(collage_path)
            
            if GENAI_AVAILABLE and self.model:
                response_text = self._call_gemini_sdk(image_base64, self.CHECKING_PROMPT)
            else:
                response_text = self._call_gemini_rest(image_base64, self.CHECKING_PROMPT)
            
            result = self._safe_parse_json(response_text)
            
            if result:
                logger.info("✓ Gemini API response received")
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini check failed: {e}")
            return None

# ==================== FIREBASE ====================

def upload_to_firebase(result_data, collage_path):
    """
    Upload result to Firebase Realtime Database
    Args:
        result_data: JSON data from Gemini
        collage_path: Path to collage image
    """
    print("☁️  Uploading to Firebase...")
    
    try:
        assessment_uid = result_data.get('assessmentUid')
        student_id = result_data.get('studentId')
        
        if not assessment_uid or not student_id:
            print("✗ Missing assessmentUid or studentId")
            return False
        
        # Prepare data matching your RTDB structure
        upload_data = {
            "assessmentUid": assessment_uid,
            "studentId": student_id,
            "score": result_data.get('score', 0),
            "scannedAt": datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            "uploadedtoGdriveAt": datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            "isPartialScore": False
        }
        
        # Firebase path matching your structure
        firebase_path = f"{FIREBASE_URL}/assessmentScoresAndImages/{TEACHER_UID}/{assessment_uid}/{student_id}.json"
        
        response = requests.put(firebase_path, json=upload_data)
        
        if response.status_code == 200:
            print(f"✓ Data uploaded to Firebase")
            print(f"  Path: /assessmentScoresAndImages/{TEACHER_UID}/{assessment_uid}/{student_id}/")
            return True
        else:
            print(f"✗ Firebase upload error: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Firebase exception: {e}")
        return False

# ==================== MAIN SYSTEM ====================

def main():
    """Main system loop"""
    print("=" * 60)
    print("ANSWER SHEET CHECKER SYSTEM (PiCamera2)")
    print("=" * 60)
    print("Commands:")
    print("  * = Capture Answer Key")
    print("  # = Capture Answer Sheet")
    print("=" * 60)
    
    setup_keypad()
    
    # Initialize camera
    camera = CameraController()
    camera.start()
    
    # Initialize Gemini checker
    try:
        gemini_checker = GeminiChecker()
    except RuntimeError as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        print("\n✗ ERROR: GEMINI_API_KEY not set")
        print("Please edit the script and replace 'YOUR_GEMINI_API_KEY_HERE' with your actual API key")
        camera.stop()
        return
    
    answer_key_path = None
    answer_sheet_path = None
    
    try:
        while True:
            print("\n⌨️  Waiting for key press...")
            key = get_key()
            print("key ===>", key)
            if key == '*':
                print("📋 ANSWER KEY MODE")
                answer_key_path = camera.capture_image('answer_key')
                
                if answer_key_path:
                    print("✓ Answer key captured successfully")
                    
                    # Check if we can process
                    if answer_sheet_path:
                        process_assessment(answer_key_path, answer_sheet_path, gemini_checker)
                        answer_key_path = None
                        answer_sheet_path = None
                
            elif key == '#':
                print("📝 ANSWER SHEET MODE")
                answer_sheet_path = camera.capture_image('answer_sheet')
                
                if answer_sheet_path:
                    print("✓ Answer sheet captured successfully")
                    
                    # Check if we can process
                    if answer_key_path:
                        process_assessment(answer_key_path, answer_sheet_path, gemini_checker)
                        answer_key_path = None
                        answer_sheet_path = None
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n🛑 System shutdown")
    finally:
        camera.stop()
        GPIO.cleanup()

def process_assessment(answer_key_path, answer_sheet_path, gemini_checker):
    """Process complete assessment"""
    print("\n" + "=" * 60)
    print("PROCESSING ASSESSMENT")
    print("=" * 60)
    
    # Create collage
    collage_base64, collage_path = create_collage(answer_key_path, answer_sheet_path)
    
    if not collage_path:
        print("✗ Failed to create collage")
        return
    
    # Send to Gemini
    result_data = gemini_checker.check_collage(collage_path)
    
    if not result_data:
        print("✗ Failed to get Gemini response")
        return
    
    # Display results
    print("\n📊 RESULTS:")
    print(f"  Assessment UID: {result_data.get('assessmentUid')}")
    print(f"  Student ID: {result_data.get('studentId')}")
    print(f"  Score: {result_data.get('score')}%")
    print(f"  Correct: {result_data.get('correctAnswers')}/{result_data.get('totalQuestions')}")
    
    # Upload to Firebase
    success = upload_to_firebase(result_data, collage_path)
    
    if success:
        print("\n✓ Assessment processed successfully!")
    else:
        print("\n✗ Failed to upload to Firebase")
    
    print("=" * 60)

if __name__ == "__main__":
    main()