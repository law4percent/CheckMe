"""
L3210 Scanner Module
Provides a class-based interface for controlling the L3210 document scanner.
"""

import subprocess
import os
from datetime import datetime
from typing import Optional, Tuple
from enum import Enum

from . import utils


class ScanMode(Enum):
    """Available scan modes"""
    LINEART = "Lineart"
    GRAY    = "Gray"
    COLOR   = "Color"


class ScanFormat(Enum):
    """Supported output formats"""
    PNG  = "png"
    JPEG = "jpeg"
    TIFF = "tiff"


class ScannerError(Exception):
    """Base exception for scanner-related errors"""
    pass


class ScannerNotFoundError(ScannerError):
    """Raised when scanner device is not detected"""
    pass


class ScanFailedError(ScannerError):
    """Raised when scan operation fails"""
    pass


class L3210Scanner:
    """
    Interface for L3210 document scanner using SANE scanimage backend.
    
    Example usage:
        scanner = L3210Scanner()
        filepath = scanner.scan(target_directory="scans/answer_keys")
        print(f"Saved to: {filepath}")
    """
    
    def __init__(
        self,
        resolution          : int        = 300,
        mode                : ScanMode   = ScanMode.LINEART,
        scan_format         : ScanFormat = ScanFormat.PNG,
        auto_create_subdirs : bool       = True,
        base_dir            : str        = "scans",
        answer_keys_dir     : str        = "answer_keys",
        answer_sheets_dir   : str        = "answer_sheets"
    ):
        self.base_dir           = base_dir
        self.resolution         = resolution
        self.mode               = mode
        self.scan_format        = scan_format
        self._last_scan_path: Optional[str] = None
        self._is_scanning       = False

        # Store as relative sub-names AND as full joined paths
        self._answer_keys_subdir   = answer_keys_dir
        self._answer_sheets_subdir = answer_sheets_dir
        self.answer_keys_dir    = os.path.join(base_dir, answer_keys_dir)
        self.answer_sheets_dir  = os.path.join(base_dir, answer_sheets_dir)

        if auto_create_subdirs:
            utils.create_directories(
                self.answer_keys_dir,
                self.answer_sheets_dir
            )

    def scan(
        self,
        target_directory : str,
        filename         : Optional[str]      = None,
        resolution       : Optional[int]      = None,
        mode             : Optional[ScanMode] = None
    ) -> str:
        """
        Perform a scan and save to target_directory.

        Args:
            target_directory : Path to save the scan (absolute or relative).
                               Does NOT need to match answer_keys_dir /
                               answer_sheets_dir exactly — any writable path
                               is accepted.
            filename         : Custom filename without extension.
                               Auto-generates timestamp if None.
            resolution       : Override default resolution for this scan.
            mode             : Override default mode for this scan.

        Returns:
            str: Full path to the saved scan file.

        Raises:
            ScannerNotFoundError : Scanner not connected or not detected.
            ScanFailedError      : Scan operation failed.
        """
        scan_resolution = resolution or self.resolution
        scan_mode       = mode or self.mode

        # Generate filename
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename  = f"scan_{timestamp}"

        # Build full filepath
        filepath = utils.join_and_ensure_path(
            target_directory = target_directory,
            filename         = f"{filename}.{self.scan_format.value}",
            source           = "l3210_scanner_hardware.py"
        )

        # Build scanimage command
        command = [
            "scanimage",
            f"--format={self.scan_format.value}",
            f"--resolution={scan_resolution}",
            f"--mode={scan_mode.value}"
        ]

        # Check scanner availability BEFORE opening the file
        if not self.is_scanner_available():
            raise ScannerNotFoundError(
                "Scanner not detected. Check USB connection and power."
            )

        # Perform scan
        self._is_scanning = True
        try:
            with open(filepath, "wb") as file:
                result = subprocess.run(
                    command,
                    stdout  = file,
                    stderr  = subprocess.PIPE,
                    timeout = 60
                )

            if result.returncode != 0:
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                raise ScanFailedError(f"Scan failed: {error_msg}")

            self._last_scan_path = filepath
            return filepath

        except subprocess.TimeoutExpired:
            raise ScanFailedError("Scan operation timed out after 60 seconds")

        except ScanFailedError:
            raise  # re-raise without wrapping

        except Exception as e:
            raise ScanFailedError(f"Unexpected error during scan: {e}")

        finally:
            self._is_scanning = False

    def is_scanner_available(self) -> bool:
        """
        Check if scanner is connected and ready.

        Uses  scanimage -L  (the correct flag — not --list-devices which
        is invalid and always returns a non-zero exit code).

        Returns:
            bool: True if scanner is detected, False otherwise.
        """
        try:
            result = subprocess.run(
                ["scanimage", "-L"],        # ← FIXED: was --list-devices
                capture_output = True,
                text           = True,
                timeout        = 10         # increased from 5s — detection can be slow
            )
            # returncode 0 AND at least one device line in output
            return result.returncode == 0 and len(result.stdout.strip()) > 0
        except Exception:
            return False

    def get_scanner_info(self) -> Optional[str]:
        """
        Get detailed information about connected scanner.

        Returns:
            str: Scanner device string, or None if not available.
        """
        try:
            result = subprocess.run(
                ["scanimage", "-L"],        # ← FIXED: was --list-devices
                capture_output = True,
                text           = True,
                timeout        = 10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def is_scanning(self) -> bool:
        """Check if a scan is currently in progress."""
        return self._is_scanning

    def get_last_scan(self) -> Optional[str]:
        """Get filepath of the most recent scan, or None."""
        return self._last_scan_path

    def set_resolution(self, resolution: int) -> None:
        """Set default resolution. Must be one of: 75, 150, 300, 600."""
        if resolution not in [75, 150, 300, 600]:
            raise ValueError("Resolution must be one of: 75, 150, 300, 600")
        self.resolution = resolution

    def set_mode(self, mode: ScanMode) -> None:
        """Set default scan mode."""
        self.mode = mode

    def get_scan_count(self, target_directory: str) -> int:
        """
        Count scan files in target_directory.

        Returns:
            int: Number of files matching current scan format extension.
        """
        normalized_path = utils.normalize_path(target_directory)
        if not os.path.exists(normalized_path):
            return 0
        return sum(
            1 for f in os.listdir(normalized_path)
            if f.endswith(f".{self.scan_format.value}")
        )

    def list_scans(self, target_directory: str) -> list:
        """
        List all scan files in target_directory.

        Returns:
            list of (filename, full_path, datetime) tuples, newest first.
        """
        normalized_path = utils.normalize_path(target_directory)
        if not os.path.exists(normalized_path):
            return []

        scans = []
        for filename in os.listdir(normalized_path):
            if filename.endswith(f".{self.scan_format.value}"):
                full_path = os.path.join(normalized_path, filename)
                timestamp = os.path.getmtime(full_path)
                scans.append((filename, full_path, datetime.fromtimestamp(timestamp)))

        scans.sort(key=lambda x: x[2], reverse=True)
        return scans

    def delete_scan(self, filepath: str) -> bool:
        """
        Delete a specific scan file.

        Returns:
            bool: True if deleted successfully.
        """
        try:
            if utils.delete_file(filepath):
                if self._last_scan_path == filepath:
                    self._last_scan_path = None
                return True
        except Exception:
            pass
        return False

    def clear_all_scans(self, target_directory: str) -> Tuple[int, int]:
        """
        Delete all scan files in target_directory.

        Returns:
            tuple: (successful_deletions, failed_deletions)
        """
        normalized_path = utils.normalize_path(target_directory)
        if not os.path.exists(normalized_path):
            return (0, 0)

        success = 0
        failed  = 0

        for filename in os.listdir(normalized_path):
            full_path = os.path.join(normalized_path, filename)
            if os.path.isfile(full_path):
                try:
                    os.remove(full_path)
                    success += 1
                except Exception:
                    failed += 1

        self._last_scan_path = None
        return (success, failed)

    def __repr__(self) -> str:
        return (
            f"L3210Scanner(base_dir='{self.base_dir}', "
            f"resolution={self.resolution}, mode={self.mode.value}, "
            f"format={self.scan_format.value})"
        )