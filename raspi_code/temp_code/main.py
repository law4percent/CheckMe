#!/usr/bin/env python3
"""
Answer Sheet Checker System for Raspberry Pi 4B
Components: 2 Buttons (Pull-up), Camera Module (PiCamera2)

Button A (GPIO 17): Capture Answer Key
Button B (GPIO 27): Capture Answer Sheet

NEW: Live camera preview with positioning guides!
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
import threading

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

# Gemini API Key
GEMINI_API_KEY = "AIzaSyDvYrAvyHQ3N9MMLWtOKaU-G2BJQZN70WU"

# Two-Button GPIO Configuration
BUTTON_A_PIN = 17  # Answer Key button
BUTTON_B_PIN = 27  # Answer Sheet button

# Firebase Configuration
FIREBASE_URL = "https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app"
TEACHER_UID = "GKVi81kM8dhoHra1zvM4EZJF9VC3"

# Image storage paths
IMAGE_DIR = os.path.expanduser("~/answer_checker/images")
os.makedirs(IMAGE_DIR, exist_ok=True)

# Camera Configuration
CAMERA_CONFIG = {
    "resolution": (1920, 1080),
    "preview_size": (1280, 720),  # Smaller for preview
    "format": "RGB888",
    "rotation": 0
}

# Button debounce settings
DEBOUNCE_TIME = 0.05  # 50ms

# Preview settings
SHOW_PREVIEW = True
PREVIEW_WINDOW = "Camera Preview - Position Your Paper"

# ==================== BUTTON SETUP ====================

class ButtonController:
    """Handles two-button input with debouncing"""
    
    def __init__(self, button_a_pin=BUTTON_A_PIN, button_b_pin=BUTTON_B_PIN):
        self.button_a_pin = button_a_pin
        self.button_b_pin = button_b_pin
        self.last_button_a_state = True
        self.last_button_b_state = True
        self.button_a_pressed_time = 0
        self.button_b_pressed_time = 0
        
    def setup(self):
        """Initialize GPIO for buttons with pull-up resistors"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup buttons as inputs with pull-up resistors
        GPIO.setup(self.button_a_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.button_b_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print("✓ Buttons initialized")
        print(f"  Button A (Answer Key): GPIO {self.button_a_pin}")
        print(f"  Button B (Answer Sheet): GPIO {self.button_b_pin}")
    
    def read_button(self):
        """
        Read button state with debouncing
        Returns:
            'A' - Button A pressed (Answer Key)
            'B' - Button B pressed (Answer Sheet)
            None - No button pressed
        """
        current_time = time.time()
        
        # Read current button states (LOW = pressed with pull-up)
        button_a_state = GPIO.input(self.button_a_pin)
        button_b_state = GPIO.input(self.button_b_pin)
        
        # Check Button A with debouncing
        if button_a_state == GPIO.LOW and self.last_button_a_state == GPIO.HIGH:
            if current_time - self.button_a_pressed_time > DEBOUNCE_TIME:
                self.button_a_pressed_time = current_time
                self.last_button_a_state = button_a_state
                
                # Wait for button release
                while GPIO.input(self.button_a_pin) == GPIO.LOW:
                    time.sleep(0.01)
                
                self.last_button_a_state = GPIO.HIGH
                return 'A'
        
        # Check Button B with debouncing
        if button_b_state == GPIO.LOW and self.last_button_b_state == GPIO.HIGH:
            if current_time - self.button_b_pressed_time > DEBOUNCE_TIME:
                self.button_b_pressed_time = current_time
                self.last_button_b_state = button_b_state
                
                # Wait for button release
                while GPIO.input(self.button_b_pin) == GPIO.LOW:
                    time.sleep(0.01)
                
                self.last_button_b_state = GPIO.HIGH
                return 'B'
        
        # Update states
        self.last_button_a_state = button_a_state
        self.last_button_b_state = button_b_state
        
        return None

# ==================== CAMERA FUNCTIONS (PiCamera2) ====================

class CameraController:
    """Handles PiCamera2 operations with live preview"""

    def __init__(self):
        """Initialize camera"""
        self.picam2 = Picamera2()
        self.preview_active = False
        self.current_mode = "READY"
        self.preview_thread = None
        self.stop_preview = False

        # Configure camera
        config = self.picam2.create_still_configuration(
            main={
                "size": CAMERA_CONFIG["resolution"],
                "format": CAMERA_CONFIG["format"]
            },
            lores={
                "size": CAMERA_CONFIG["preview_size"]
            },
            display="lores",
            transform=Transform(hflip=False, vflip=False)
        )

        self.picam2.configure(config)
        logger.info("✓ Camera initialized")

    def start(self):
        """Start camera and preview"""
        self.picam2.start()
        time.sleep(2)  # Camera warm-up
        logger.info("✓ Camera started")
        
        if SHOW_PREVIEW:
            self.start_preview()

    def stop(self):
        """Stop camera and preview"""
        self.stop_preview_thread()
        self.picam2.stop()
        cv2.destroyAllWindows()
        logger.info("✓ Camera stopped")

    def start_preview(self):
        """Start live preview in separate thread"""
        if not self.preview_active:
            self.stop_preview = False
            self.preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
            self.preview_thread.start()
            self.preview_active = True
            logger.info("✓ Camera preview started")

    def stop_preview_thread(self):
        """Stop preview thread"""
        if self.preview_active:
            self.stop_preview = True
            if self.preview_thread:
                self.preview_thread.join(timeout=2)
            self.preview_active = False

    def _preview_loop(self):
        """Preview loop running in separate thread"""
        while not self.stop_preview:
            try:
                # Capture preview frame (low resolution)
                frame = self.picam2.capture_array()
                
                # Convert RGB to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Resize to preview size
                preview_frame = cv2.resize(frame_bgr, CAMERA_CONFIG["preview_size"])
                
                # Apply rotation if configured
                if CAMERA_CONFIG["rotation"] == 90:
                    preview_frame = cv2.rotate(preview_frame, cv2.ROTATE_90_CLOCKWISE)
                elif CAMERA_CONFIG["rotation"] == 180:
                    preview_frame = cv2.rotate(preview_frame, cv2.ROTATE_180)
                elif CAMERA_CONFIG["rotation"] == 270:
                    preview_frame = cv2.rotate(preview_frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                
                # Add overlay with guides
                preview_frame = self._add_preview_overlay(preview_frame)
                
                # Display
                cv2.imshow(PREVIEW_WINDOW, preview_frame)
                cv2.waitKey(1)
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                logger.error(f"Preview error: {e}")
                break

    def _add_preview_overlay(self, frame):
        """Add positioning guides and status overlay to preview"""
        h, w = frame.shape[:2]
        
        # Draw center crosshair
        center_x, center_y = w // 2, h // 2
        cv2.line(frame, (center_x - 50, center_y), (center_x + 50, center_y), (0, 255, 0), 2)
        cv2.line(frame, (center_x, center_y - 50), (center_x, center_y + 50), (0, 255, 0), 2)
        
        # Draw corner guides (paper positioning)
        margin = 50
        corner_size = 30
        # Top-left
        cv2.line(frame, (margin, margin), (margin + corner_size, margin), (0, 255, 255), 3)
        cv2.line(frame, (margin, margin), (margin, margin + corner_size), (0, 255, 255), 3)
        # Top-right
        cv2.line(frame, (w - margin, margin), (w - margin - corner_size, margin), (0, 255, 255), 3)
        cv2.line(frame, (w - margin, margin), (w - margin, margin + corner_size), (0, 255, 255), 3)
        # Bottom-left
        cv2.line(frame, (margin, h - margin), (margin + corner_size, h - margin), (0, 255, 255), 3)
        cv2.line(frame, (margin, h - margin), (margin, h - margin - corner_size), (0, 255, 255), 3)
        # Bottom-right
        cv2.line(frame, (w - margin, h - margin), (w - margin - corner_size, h - margin), (0, 255, 255), 3)
        cv2.line(frame, (w - margin, h - margin), (w - margin, h - margin - corner_size), (0, 255, 255), 3)
        
        # Draw recommended paper area
        paper_margin = 100
        cv2.rectangle(frame, 
                     (paper_margin, paper_margin), 
                     (w - paper_margin, h - paper_margin), 
                     (255, 0, 0), 2)
        
        # Status text background
        cv2.rectangle(frame, (0, 0), (w, 80), (0, 0, 0), -1)
        cv2.rectangle(frame, (0, 0), (w, 80), (0, 255, 0), 2)
        
        # Mode text
        mode_text = f"MODE: {self.current_mode}"
        cv2.putText(frame, mode_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Instructions
        instructions = "Position paper within blue rectangle | Button A: Answer Key | Button B: Answer Sheet"
        cv2.putText(frame, instructions, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame

    def set_mode(self, mode):
        """Update current mode for display"""
        self.current_mode = mode

    def capture_image(self, image_type):
        """
        Capture high-resolution image
        Args:
            image_type: 'answer_key' or 'answer_sheet'
        Returns:
            Path to saved image
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{image_type}_{timestamp}.jpg"
        filepath = os.path.join(IMAGE_DIR, filename)

        print(f"📷 Capturing {image_type}...")
        
        # Flash effect on preview
        self.set_mode(f"CAPTURING {image_type.upper()}...")

        try:
            # Capture FULL RESOLUTION image
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
            
            # Reset mode
            self.set_mode("READY")
            
            return filepath

        except Exception as e:
            logger.error(f"Camera capture error: {e}")
            self.set_mode("ERROR")
            return None

# ==================== REST OF THE CODE (UNCHANGED) ====================
# [Include all the previous code: create_collage, GeminiChecker, upload_to_firebase, etc.]

def create_collage(answer_key_path, answer_sheet_path):
    """Create horizontal collage of answer key and answer sheet"""
    print("🖼️  Creating collage...")
    try:
        img_key = Image.open(answer_key_path)
        img_sheet = Image.open(answer_sheet_path)
        max_height = max(img_key.height, img_sheet.height)
        if img_key.height != max_height:
            ratio = max_height / img_key.height
            img_key = img_key.resize((int(img_key.width * ratio), max_height), Image.Resampling.LANCZOS)
        if img_sheet.height != max_height:
            ratio = max_height / img_sheet.height
            img_sheet = img_sheet.resize((int(img_sheet.width * ratio), max_height), Image.Resampling.LANCZOS)
        total_width = img_key.width + img_sheet.width
        collage = Image.new('RGB', (total_width, max_height))
        collage.paste(img_key, (0, 0))
        collage.paste(img_sheet, (img_key.width, 0))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        collage_path = os.path.join(IMAGE_DIR, f"collage_{timestamp}.jpg")
        collage.save(collage_path, quality=95)
        print(f"✓ Collage created: {collage_path}")
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
- LEFT SIDE: Answer key with assessment UID at the top (THIS IS THE SOURCE OF TRUTH / GROUND TRUTH)
- RIGHT SIDE: Student's answer sheet with student ID at the top

CRITICAL RULES:
1. The ANSWER KEY (left image) is the GROUND TRUTH and SOURCE OF TRUTH for:
   - Total number of questions
   - Correct answers for each question
   - Assessment structure
2. Count the TOTAL number of questions from the ANSWER KEY ONLY
3. The student's answer sheet must be compared against this ground truth

Your task:
1. Extract the Assessment UID from the top of the answer key (left image)
2. Count the TOTAL number of questions from the ANSWER KEY (left image) - this is your ground truth
3. Extract the Student ID from the top of the answer sheet (right image)
4. Compare EACH answer on the student's sheet with the corresponding answer in the ANSWER KEY
5. Calculate the score (number of correct matches)
6. Identify which questions were answered correctly and incorrectly

CRITICAL: Return ONLY valid JSON with NO markdown formatting, NO code blocks, NO explanations.

Format:
{
  "assessmentUid": "extracted_assessment_uid",
  "studentId": "extracted_student_id",
  "score": 17,
  "totalQuestions": 20,
  "correctAnswers": 17,
  "incorrectAnswers": 3,
  "details": [
    {"question": 1, "studentAnswer": "B", "correctAnswer": "B", "isCorrect": true},
    {"question": 2, "studentAnswer": "C", "correctAnswer": "A", "isCorrect": false}
  ],
  "timestamp": "current_timestamp_iso_format"
}

IMPORTANT: 
- "totalQuestions" MUST be counted from the ANSWER KEY (left image) - it is the ground truth
- "score" must be the RAW NUMBER of correct answers (e.g., 17), NOT a percentage
- Compare student answers ONLY against the answer key's answers
- If student has more/fewer answers than the answer key, mark extras as incorrect
- Be accurate in reading both the UIDs and comparing answers
"""

    def __init__(self):
        self.api_key = GEMINI_API_KEY

        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            raise RuntimeError("GEMINI_API_KEY not set. Please edit the script and add your API key.")

        if GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                "gemini-2.0-flash-exp",
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "max_output_tokens": 8192,
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
            image_bytes = base64.b64decode(image_base64)

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
                    "temperature": 0.1,
                    "topP": 0.8,
                    "maxOutputTokens": 8192
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=90)

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
        """Safely parse JSON from response with multiple cleanup strategies"""
        try:
            cleaned = response_text.strip()

            # Remove markdown code blocks if present
            if cleaned.startswith('```'):
                first_newline = cleaned.find('\n')
                if first_newline != -1:
                    cleaned = cleaned[first_newline + 1:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]

            cleaned = cleaned.strip()

            # Try direct parse
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

            # Find JSON object boundaries
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}')

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = cleaned[start_idx:end_idx + 1]
                return json.loads(json_str)

            raise json.JSONDecodeError("No valid JSON found", cleaned, 0)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response text (first 500 chars): {response_text[:500]}")
            logger.error(f"Response text (last 200 chars): {response_text[-200:]}")
            return None

    def check_collage(self, collage_path: str, max_retries: int = 3) -> dict:
        """
        Check answer sheet using collage image with retry logic
        
        Args:
            collage_path: Path to collage image
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with results or None on failure
        """
        logger.info("Sending collage to Gemini API...")

        for attempt in range(max_retries):
            try:
                image_base64 = self._encode_image(collage_path)

                if GENAI_AVAILABLE and self.model:
                    response_text = self._call_gemini_sdk(image_base64, self.CHECKING_PROMPT)
                else:
                    response_text = self._call_gemini_rest(image_base64, self.CHECKING_PROMPT)

                result = self._safe_parse_json(response_text)

                if result:
                    logger.info("✓ Gemini API response received and parsed")
                    return result
                else:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to parse JSON, retrying...")
                    time.sleep(2)

            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{max_retries}: Gemini check failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    logger.error("All retry attempts exhausted")

        return None

# ==================== FIREBASE ====================

def upload_to_firebase(result_data, collage_path):
    """
    Upload result to Firebase Realtime Database with CORRECT format
    
    Correct Firebase structure:
    assessmentScoresAndImages/
      {teacher_uid}/
        {assessment_uid}/
          {student_id}: {
            score: int,
            perfectScore: int,
            isPartialScore: bool,
            assessmentUid: str,
            scannedAt: str
          }
    
    Args:
        result_data: JSON data from Gemini
        collage_path: Path to collage image
    """
    print("☁️  Uploading to Firebase...")

    try:
        assessment_uid = result_data.get('assessmentUid')
        student_id = result_data.get('studentId')
        score = result_data.get('score', 0)  # Raw score (e.g., 17)
        total_questions = result_data.get('totalQuestions', 0)  # Perfect score (e.g., 20)

        if not assessment_uid or not student_id:
            print("✗ Missing assessmentUid or studentId")
            logger.error(f"Result data: {result_data}")
            return False

        # CORRECT FORMAT: Nested object structure
        upload_data = {
            "score": int(score),                    # Raw score (e.g., 17)
            "perfectScore": int(total_questions),   # Total possible (e.g., 20)
            "isPartialScore": False,                # No essay questions
            "assessmentUid": assessment_uid,
            "scannedAt": datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        }

        # CORRECT PATH: Use student_id as the key, not in path with .json
        firebase_path = f"{FIREBASE_URL}/assessmentScoresAndImages/{TEACHER_UID}/{assessment_uid}/{student_id}.json"

        logger.info(f"Uploading to path: /assessmentScoresAndImages/{TEACHER_UID}/{assessment_uid}/{student_id}")
        logger.info(f"Data: {json.dumps(upload_data, indent=2)}")

        response = requests.put(firebase_path, json=upload_data)

        if response.status_code == 200:
            print(f"✓ Data uploaded to Firebase")
            print(f"  Assessment: {assessment_uid}")
            print(f"  Student: {student_id}")
            print(f"  Score: {score}/{total_questions}")
            return True
        else:
            print(f"✗ Firebase upload error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Firebase exception: {e}")
        return False


# ==================== MAIN SYSTEM ====================

def main():
    """Main system loop"""
    print("=" * 60)
    print("ANSWER SHEET CHECKER - WITH LIVE PREVIEW!")
    print("=" * 60)
    print("Controls:")
    print("  Button A (GPIO 17) = Capture Answer Key")
    print("  Button B (GPIO 27) = Capture Answer Sheet")
    print("  Live Preview: Position your paper within the guides")
    print("=" * 60)

    button_controller = ButtonController()
    button_controller.setup()

    camera = CameraController()
    camera.start()

    try:
        gemini_checker = None  # Will initialize when needed
    except RuntimeError as e:
        logger.error(f"Failed to initialize Gemini: {e}")

    answer_key_path = None
    answer_sheet_path = None

    try:
        print("\n✓ System ready! Live preview active - Position your papers and press buttons...")
        
        while True:
            button = button_controller.read_button()
            
            if button == 'A':
                print("\n📋 ANSWER KEY MODE")
                camera.set_mode("ANSWER KEY MODE")
                time.sleep(0.5)  # Show mode change
                answer_key_path = camera.capture_image('answer_key')

                if answer_key_path:
                    print("✓ Answer key captured successfully")
                    if answer_sheet_path:
                        camera.set_mode("PROCESSING...")
                        # Initialize Gemini if not done yet
                        if gemini_checker is None:
                            gemini_checker = GeminiChecker()
                        process_assessment(answer_key_path, answer_sheet_path, gemini_checker)
                        answer_key_path = None
                        answer_sheet_path = None
                        camera.set_mode("READY")
                    else:
                        camera.set_mode("WAITING FOR ANSWER SHEET")
                        print("  Waiting for answer sheet (press Button B)...")

            elif button == 'B':
                print("\n📝 ANSWER SHEET MODE")
                camera.set_mode("ANSWER SHEET MODE")
                time.sleep(0.5)  # Show mode change
                answer_sheet_path = camera.capture_image('answer_sheet')

                if answer_sheet_path:
                    print("✓ Answer sheet captured successfully")
                    if answer_key_path:
                        camera.set_mode("PROCESSING...")
                        # Initialize Gemini if not done yet
                        if gemini_checker is None:
                            gemini_checker = GeminiChecker()
                        process_assessment(answer_key_path, answer_sheet_path, gemini_checker)
                        answer_key_path = None
                        answer_sheet_path = None
                        camera.set_mode("READY")
                    else:
                        camera.set_mode("WAITING FOR ANSWER KEY")
                        print("  Waiting for answer key (press Button A)...")

            time.sleep(0.05)

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
    collage_base64, collage_path = create_collage(answer_key_path, answer_sheet_path)
    if not collage_path:
        print("✗ Failed to create collage")
        return
    result_data = gemini_checker.check_collage(collage_path)
    if not result_data:
        print("✗ Failed to get Gemini response")
        return
    score = result_data.get('score', 0)
    total = result_data.get('totalQuestions', 0)
    percentage = (score / total * 100) if total > 0 else 0
    print("\n📊 RESULTS:")
    print(f"  Assessment UID: {result_data.get('assessmentUid')}")
    print(f"  Student ID: {result_data.get('studentId')}")
    print(f"  Score: {score}/{total} ({percentage:.1f}%)")
    print(f"  Correct: {result_data.get('correctAnswers')}")
    print(f"  Incorrect: {result_data.get('incorrectAnswers')}")
    success = upload_to_firebase(result_data, collage_path)
    if success:
        print("\n✓ Assessment processed successfully!")
    else:
        print("\n✗ Failed to upload to Firebase")
    print("=" * 60)

if __name__ == "__main__":
    main()