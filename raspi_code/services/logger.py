"""
Flexible logging system for the Raspberry Pi scanner application.

Usage:
    from services.logger import logger
    
    logger(details="Connection established", file="gemini_client.py", type="info")
    logger(details="API error occurred", file="gemini_client.py", type="error", show_console=True)
    logger(details="Temp debug info", file="main.py", type="debug", save_to_all_logs=False)
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal
import logging
from logging.handlers import RotatingFileHandler

# Define log types (removed "all")
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
    "all": LOGS_DIR / "all.log"  # Special: captures everything by default
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
        
        Raises:
            ValueError: If log type is invalid (but still logs to info.log)
        
        Examples:
            # Standard logging (goes to info.log AND all.log)
            logger(details="API connected", file="gemini_client.py", type="info")
            
            # Error with console output (goes to error.log AND all.log)
            logger(details="Connection failed", file="main.py", type="error", show_console=True)
            
            # Temporary debug info (goes ONLY to debug.log, NOT to all.log)
            logger(details="Temp variable: x=5", file="scanner.py", type="debug", save_to_all_logs=False)
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
            caller_frame = frame.f_back
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


def logger(
    details: str,
    file: str,
    type: LogType = "info",
    show_console: bool = False,
    save_to_all_logs: bool = True
):
    """
    Convenient logger function for easy imports.
    
    Args:
        details: The log message/details
        file: Source file name (e.g., "gemini_client.py")
        type: Log type - "error", "info", "warning", "debug", or "bug"
        show_console: Whether to print to console (default: False)
        save_to_all_logs: Whether to also save to all.log (default: True)
    
    Examples:
        from services.logger import logger
        
        # Standard logs (saved to specific file + all.log)
        logger(details="Starting scan", file="scanner.py", type="info")
        logger(details="Invalid API key", file="gemini_client.py", type="error", show_console=True)
        
        # Temporary debug logs (saved ONLY to debug.log, not all.log)
        logger(details="Loop iteration 5", file="main.py", type="debug", save_to_all_logs=False)
    """
    _logger_instance.log(
        details=details,
        file=file,
        type=type,
        show_console=show_console,
        save_to_all_logs=save_to_all_logs
    )


def get_log_location() -> Path:
    """Get the logs directory path"""
    return _logger_instance.get_log_location()


def get_log_file(log_type: str) -> Path:
    """Get specific log file path"""
    return _logger_instance.get_log_file(log_type)


# Print initialization message when module is imported
if __name__ == "__main__":
    # from services.logger import logger
    
    print("Testing logger with revised parameters...\n")

    # Test 1: Standard logs (all go to specific file + all.log)
    logger(details="This is an info message", file="test_logger.py", type="info")
    logger(details="This is a debug message", file="test_logger.py", type="debug")
    logger(details="This is a warning message", file="test_logger.py", type="warning", show_console=True)
    logger(details="This is an error message", file="test_logger.py", type="error", show_console=True)
    logger(details="This is a bug message", file="test_logger.py", type="bug", show_console=True)

    # Test 2: Logs that DON'T go to all.log (temporary debug info)
    logger(
        details="Temporary debug info - NOT saved to all.log",
        file="test_logger.py",
        type="debug",
        save_to_all_logs=False
    )

    logger(
        details="Another temp log - only in info.log",
        file="test_logger.py",
        type="info",
        save_to_all_logs=False
    )

    # Test 3: Invalid type (defaults to info)
    try:
        logger(details="Invalid type test", file="test_logger.py", type="xyz")
    except ValueError as e:
        print(f"\nCaught expected error: {e}")

    print("\n✓ Test complete! Check your logs/ directory")