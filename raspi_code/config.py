# config.py
"""
Centralized configuration management for the Answer Sheet Scanner system.
Loads settings from environment variables with validation and defaults.
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required values"""
    pass


class Config:
    """Application configuration with validation"""
    
    # ============================================================
    # SYSTEM SETTINGS
    # ============================================================
    PRODUCTION_MODE: bool = os.getenv("PRODUCTION_MODE", "true").lower() == "true"
    SAVE_LOGS: bool = os.getenv("SAVE_LOGS", "true").lower() == "true"
    
    # ============================================================
    # PATH SETTINGS
    # ============================================================
    ANSWER_KEY_IMAGE_PATH: str = os.getenv("ANSWER_KEY_IMAGE_PATH", "answer_keys/images")
    ANSWER_KEY_JSON_PATH: str = os.getenv("ANSWER_KEY_JSON_PATH", "answer_keys/json")
    ANSWER_SHEET_IMAGE_PATH: str = os.getenv("ANSWER_SHEET_IMAGE_PATH", "answer_sheets/images")
    ANSWER_SHEET_JSON_PATH: str = os.getenv("ANSWER_SHEET_JSON_PATH", "answer_sheets/json")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "database")
    
    # ============================================================
    # CAMERA SETTINGS
    # ============================================================
    CAMERA_WIDTH: int = int(os.getenv("CAMERA_WIDTH", "1920"))
    CAMERA_HEIGHT: int = int(os.getenv("CAMERA_HEIGHT", "1080"))
    SHOW_WINDOWS: bool = os.getenv("SHOW_WINDOWS", "true").lower() == "true"
    
    # ============================================================
    # IMAGE PROCESSING SETTINGS
    # ============================================================
    IMAGE_EXTENSION: str = os.getenv("IMAGE_EXTENSION", "jpg")
    TILE_WIDTH: int = int(os.getenv("TILE_WIDTH", "600"))
    
    # ============================================================
    # API SETTINGS
    # ============================================================
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MAX_RETRY: int = int(os.getenv("MAX_RETRY", "3"))
    
    # ============================================================
    # FIREBASE SETTINGS
    # ============================================================
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL", "")
    TEACHER_UID: str = os.getenv("TEACHER_UID", "")
    
    # ============================================================
    # PROCESS B SETTINGS
    # ============================================================
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "5"))
    PROCESS_B_INTERVAL: int = int(os.getenv("PROCESS_B_INTERVAL", "5"))
    
    # ============================================================
    # HARDWARE SETTINGS
    # ============================================================
    KEYPAD_ROW_PINS: list = [19, 21, 20, 16]
    KEYPAD_COL_PINS: list = [12, 13, 6]
    
    @classmethod
    def validate(cls) -> None:
        """
        Validate critical configuration values.
        Raises ConfigurationError if validation fails.
        """
        errors = []
        
        # Check Gemini API Key
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is required but not set")
        
        # Check Firebase settings
        if not cls.FIREBASE_CREDENTIALS_PATH:
            errors.append("FIREBASE_CREDENTIALS_PATH is required but not set")
        
        if not cls.FIREBASE_DATABASE_URL:
            errors.append("FIREBASE_DATABASE_URL is required but not set")
        
        if not cls.TEACHER_UID:
            errors.append("TEACHER_UID is required but not set")
        
        # Validate paths
        if cls.FIREBASE_CREDENTIALS_PATH and not os.path.exists(cls.FIREBASE_CREDENTIALS_PATH):
            errors.append(f"Firebase credentials file not found: {cls.FIREBASE_CREDENTIALS_PATH}")
        
        # Validate numeric ranges
        if cls.BATCH_SIZE < 1 or cls.BATCH_SIZE > 100:
            errors.append(f"BATCH_SIZE must be between 1 and 100, got {cls.BATCH_SIZE}")
        
        if cls.MAX_RETRY < 1 or cls.MAX_RETRY > 10:
            errors.append(f"MAX_RETRY must be between 1 and 10, got {cls.MAX_RETRY}")
        
        if cls.CAMERA_WIDTH < 640 or cls.CAMERA_HEIGHT < 480:
            errors.append(f"Camera resolution too low: {cls.CAMERA_WIDTH}x{cls.CAMERA_HEIGHT}")
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ConfigurationError(error_message)
    
    @classmethod
    def get_process_a_args(cls) -> Dict[str, Any]:
        """Get Process A configuration arguments"""
        return {
            "TASK_NAME": "Process A",
            "IMAGE_EXTENSION": cls.IMAGE_EXTENSION,
            "TILE_WIDTH": cls.TILE_WIDTH,
            "PRODUCTION_MODE": cls.PRODUCTION_MODE,
            "SAVE_LOGS": cls.SAVE_LOGS,
            "SHOW_WINDOWS": cls.SHOW_WINDOWS,
            "PATHS": {
                "answer_key_path": {
                    "json_path": cls.ANSWER_KEY_JSON_PATH,
                    "image_path": cls.ANSWER_KEY_IMAGE_PATH
                },
                "answer_sheet_path": {
                    "json_path": cls.ANSWER_SHEET_JSON_PATH,
                    "image_path": cls.ANSWER_SHEET_IMAGE_PATH
                }
            },
            "FRAME_DIMENSIONS": {
                "width": cls.CAMERA_WIDTH,
                "height": cls.CAMERA_HEIGHT
            },
            "MAX_RETRY": cls.MAX_RETRY
        }
    
    @classmethod
    def get_process_b_args(cls) -> Dict[str, Any]:
        """Get Process B configuration arguments"""
        return {
            "TASK_NAME": "Process B",
            "BATCH_SIZE": cls.BATCH_SIZE,
            "TEACHER_UID": cls.TEACHER_UID,
            "PRODUCTION_MODE": cls.PRODUCTION_MODE,
            "SAVE_LOGS": cls.SAVE_LOGS,
            "MAX_RETRY": cls.MAX_RETRY,
            "PROCESS_INTERVAL": cls.PROCESS_B_INTERVAL
        }
    
    @classmethod
    def get_process_c_args(cls) -> Dict[str, Any]:
        """Get Process C configuration arguments (placeholder for future)"""
        return {
            "task_name": "Process C",
            "PRODUCTION_MODE": cls.PRODUCTION_MODE,
            "save_logs": cls.SAVE_LOGS
        }
    
    @classmethod
    def display_config(cls) -> None:
        """Display current configuration (for debugging)"""
        print("\n" + "="*60)
        print("SYSTEM CONFIGURATION")
        print("="*60)
        print(f"Production Mode: {cls.PRODUCTION_MODE}")
        print(f"Save Logs: {cls.SAVE_LOGS}")
        print(f"\nCamera Resolution: {cls.CAMERA_WIDTH}x{cls.CAMERA_HEIGHT}")
        print(f"Batch Size: {cls.BATCH_SIZE}")
        print(f"Max Retry: {cls.MAX_RETRY}")
        print(f"\nAnswer Key Path: {cls.ANSWER_KEY_IMAGE_PATH}")
        print(f"Answer Sheet Path: {cls.ANSWER_SHEET_IMAGE_PATH}")
        print(f"Database Path: {cls.DATABASE_PATH}")
        print(f"\nFirebase URL: {cls.FIREBASE_DATABASE_URL}")
        print(f"Teacher UID: {cls.TEACHER_UID}")
        print("="*60 + "\n")


def load_and_validate_config() -> Config:
    """
    Load configuration and validate it.
    Returns Config instance if valid.
    Raises ConfigurationError if validation fails.
    """
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
        return Config
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during configuration: {e}")
        raise ConfigurationError(f"Failed to load configuration: {e}")


# Auto-load and validate on import (optional - can be disabled)
if __name__ != "__main__":
    try:
        load_and_validate_config()
    except ConfigurationError as e:
        print(f"\n⚠️  WARNING: Configuration validation failed!")
        print(f"{e}\n")
        print("Please check your .env file and ensure all required variables are set.")
        print("See .env.example for reference.\n")