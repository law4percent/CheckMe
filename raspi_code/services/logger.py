"""
Flexible logging system for the Raspberry Pi scanner application.

Usage:
    from services.logger import get_logger
    
    # Initialize logger with filename once
    log = get_logger("gemini_client.py")
    
    # Then use it throughout the file
    log(details="Connection established", type="info")
    log(details="API error occurred", type="error", show_console=True)
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Callable
import logging
from logging.handlers import RotatingFileHandler

# Define log types
LogType = Literal["error", "info", "warning", "debug", "bug"]

# Valid log types
VALID_LOG_TYPES = {"error", "info", "warning", "debug", "bug"}

# Get project root directory (assuming logger.py is in services/)
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(exist_ok=True)

# Log file configuration
LOG_FILES = {
    "error": LOGS_DIR / "error.log",
    "info": LOGS_DIR / "info.log",
    "warning": LOGS_DIR / "warning.log",
    "debug": LOGS_DIR / "debug.log",
    "bug": LOGS_DIR / "bug.log",
    "all": LOGS_DIR / "all.log"
}

# Rotation settings: 10MB max per file, keep last 5 files
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

# Color codes for console output
COLORS = {
    "error": "\033[91m",    # Red
    "warning": "\033[93m",  # Yellow
    "info": "\033[92m",     # Green
    "debug": "\033[94m",    # Blue
    "bug": "\033[95m",      # Magenta
    "reset": "\033[0m"      # Reset
}


class LoggerSystem:
    """Custom logging system with flexible file routing and console output"""
    
    def __init__(self):
        self._handlers = {}
        self._setup_handlers()
        self._print_log_location()
    
    def _setup_handlers(self):
        """Initialize rotating file handlers for each log type"""
        for log_type, log_path in LOG_FILES.items():
            handler = RotatingFileHandler(
                filename=log_path,
                maxBytes=MAX_BYTES,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            
            # Set format: [2025-02-16 14:23:01.123] [ERROR] [gemini_client.py:45] Message
            formatter = logging.Formatter(
                fmt='[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            
            self._handlers[log_type] = handler
    
    def _print_log_location(self):
        """Print log directory location on initialization"""
        print(f"\n{'='*60}")
        print(f"📁 Log Directory: {LOGS_DIR.absolute()}")
        print(f"{'='*60}")
        print("Available log files:")
        for log_type, log_path in LOG_FILES.items():
            print(f"  • {log_type.upper()}: {log_path.name}")
        print(f"{'='*60}\n")
    
    def _validate_type(self, log_type: str) -> str:
        """Validate log type and default to 'info' if invalid"""
        if log_type not in VALID_LOG_TYPES:
            # Raise error AND default to info
            print(
                f"\n⚠️  WARNING: Invalid log type '{log_type}'. "
                f"Valid types: {', '.join(VALID_LOG_TYPES)}"
            )
            print(f"Defaulting to 'info' log type.\n")
            raise ValueError(
                f"Invalid log type: '{log_type}'. "
                f"Valid types: {', '.join(VALID_LOG_TYPES)}"
            )
        return log_type
    
    def _write_to_file(self, log_type: str, message: str, filename: str, lineno: int, save_to_all: bool):
        """Write log message to appropriate file(s)"""
        # Create a temporary LogRecord for formatting
        record = logging.LogRecord(
            name="raspi_logger",
            level=logging.INFO,
            pathname=filename,
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # Map log type to logging level
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "bug": logging.CRITICAL
        }
        record.levelno = level_map.get(log_type, logging.INFO)
        record.levelname = log_type.upper()
        
        # Write to specific log file
        handler = self._handlers[log_type]
        handler.emit(record)
        
        # Write to all.log if requested (default: True)
        if save_to_all:
            all_handler = self._handlers["all"]
            all_handler.emit(record)
    
    def _print_to_console(self, log_type: str, message: str, filename: str):
        """Print formatted log message to console with colors"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        color = COLORS.get(log_type, COLORS["reset"])
        reset = COLORS["reset"]
        
        console_msg = (
            f"{color}[{timestamp}] [{log_type.upper()}] "
            f"[{filename}] {message}{reset}"
        )
        print(console_msg)
    
    def log(
        self,
        details: str,
        file: str,
        type: LogType = "info",
        show_console: bool = False,
        save_to_all_logs: bool = True
    ):
        """
        Main logging function with flexible parameters.
        
        Args:
            details: The log message/details
            file: Source file name (e.g., "gemini_client.py")
            type: Log type - "error", "info", "warning", "debug", or "bug"
            show_console: Whether to print to console (default: False)
            save_to_all_logs: Whether to also save to all.log (default: True)
        """
        try:
            # Validate log type (raises error but continues with default)
            try:
                validated_type = self._validate_type(type)
            except ValueError:
                validated_type = "info"  # Default fallback
            
            # Get caller information for line number
            import inspect
            frame = inspect.currentframe()
            caller_frame = frame.f_back.f_back  # Go back two frames (through get_logger wrapper)
            lineno = caller_frame.f_lineno if caller_frame else 0
            
            # Write to file(s)
            self._write_to_file(validated_type, details, file, lineno, save_to_all_logs)
            
            # Optionally print to console
            if show_console:
                self._print_to_console(validated_type, details, file)
        
        except Exception as e:
            # Fallback: print to console if logging system fails
            print(f"LOGGER ERROR: {e}")
            print(f"Original message: [{type.upper()}] {file}: {details}")
    
    def get_log_location(self) -> Path:
        """Return the logs directory path"""
        return LOGS_DIR
    
    def get_log_file(self, log_type: str) -> Path:
        """Get specific log file path"""
        if log_type not in LOG_FILES:
            raise ValueError(f"Invalid log type: {log_type}")
        return LOG_FILES[log_type]


# Global logger instance
_logger_instance = LoggerSystem()


def get_logger(filename: str) -> Callable:
    """
    Get a logger function bound to a specific filename.
    
    Args:
        filename: Source file name (e.g., "gemini_client.py")
    
    Returns:
        A logging function that doesn't require the 'file' parameter
    
    Example:
        from services.logger import get_logger
        
        log = get_logger("gemini_client.py")
        log(details="Starting process", type="info")
        log(details="Error occurred", type="error", show_console=True)
    """
    def bound_logger(
        details: str,
        type: LogType = "info",
        show_console: bool = False,
        save_to_all_logs: bool = True
    ):
        """
        Log a message with pre-bound filename.
        
        Args:
            details: The log message/details
            type: Log type - "error", "info", "warning", "debug", or "bug"
            show_console: Whether to print to console (default: False)
            save_to_all_logs: Whether to also save to all.log (default: True)
        """
        _logger_instance.log(
            details=details,
            file=filename,
            type=type,
            show_console=show_console,
            save_to_all_logs=save_to_all_logs
        )
    
    return bound_logger


def get_log_location() -> Path:
    """Get the logs directory path"""
    return _logger_instance.get_log_location()


def get_log_file(log_type: str) -> Path:
    """Get specific log file path"""
    return _logger_instance.get_log_file(log_type)


if __name__ == "__main__":
    # Initialize once
    log = get_logger("test_logger.py")

    print("Testing logger with file initialization...\n")

    # Sample usage
    log(details="This is an info message", type="info")
    log(details="This is a debug message", type="debug")
    log(details="This is a warning message", type="warning", show_console=True)
    log(details="This is an error message", type="error", show_console=True)
    log(details="This is a bug message", type="bug", show_console=True)

    # Temporary debug - not saved to all.log
    log(details="Temporary debug info", type="debug", save_to_all_logs=False)

    print("\n✓ Test complete! Check your logs/ directory")