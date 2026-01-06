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

class GeminiChecker:
    """Handles Gemini API interactions (code unchanged from previous version)"""
    # ... [Include full GeminiChecker class from previous artifact]
    pass

def upload_to_firebase(result_data, collage_path):
    """Upload to Firebase (code unchanged from previous version)"""
    # ... [Include full upload_to_firebase from previous artifact]
    pass

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