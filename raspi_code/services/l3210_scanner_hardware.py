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
    GRAY = "Gray"
    COLOR = "Color"


class ScanFormat(Enum):
    """Supported output formats"""
    PNG = "png"
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
        scanner = L3210Scanner(save_directory="/home/pi/scans")
        filepath = scanner.scan()
        print(f"Saved to: {filepath}")
    """
    
    def __init__(
        self,
        resolution          : int           = 300,
        mode                : ScanMode      = ScanMode.LINEART,
        scan_format         : ScanFormat    = ScanFormat.PNG,
        auto_create_subdirs : bool          = True,
        base_dir            : str           = "scans",
        answer_keys_dir     : str           = "answer_keys",
        answer_sheets_dir   : str           = "answer_sheets"
    ):
        """
        Initialize scanner with default settings.
        
        Args:
            resolution          : DPI resolution (75, 150, 300, 600)
            mode                : Scan mode (Lineart, Gray, Color)
            format              : Output file format
            auto_create_subdirs : Automatically create answer_keys and answer_sheets subdirectories
            base_dir            : Directory to save scanned files
            answer_keys_dir     : Sub dirs inside of scan folder
            answer_sheets_dir   : Sub dirs inside of scan folder
        """
        self.base_dir           = base_dir
        self.resolution         = resolution
        self.mode               = mode
        self.format             = scan_format
        self._last_scan_path: Optional[str] = None
        self._is_scanning       = False
        self.answer_keys_dir    = f"{base_dir}/{answer_keys_dir}"
        self.answer_sheets_dir  = f"{base_dir}/{answer_sheets_dir}"
        
        if auto_create_subdirs:
            utils.create_directories(answer_keys_dir, answer_sheets_dir)
    
    def scan(
        self,
        target_directory : str,
        filename         : Optional[str]        = None,
        resolution       : Optional[int]        = None,
        mode             : Optional[ScanMode]   = None
    ) -> str:
        """
        Perform a scan with current or provided settings.
        
        Args:
            target_directory : Director to store the scan images
            filename     : Custom filename (without extension). If None, auto-generates timestamp.
            resolution   : Override default resolution for this scan
            mode         : Override default mode for this scan
        
        Returns:
            str: Full path to the saved scan file
        
        Raises:
            ScannerNotFoundError : If scanner is not connected
            ScanFailedError      : If scan operation fails
            ValueError           : If subdirectory is invalid
        """
        # Use instance defaults if not overridden
        scan_resolution = resolution or self.resolution
        scan_mode       = mode or self.mode
        
        # Determine save directory
        if target_directory not in [self.answer_keys_dir, self.answer_sheets_dir]:
            raise ValueError(
                f"Invalid subdirectory '{target_directory}'. "
                "Must be 'answer_keys' or 'answer_sheets'"
            )
        
        # Generate filename
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_{timestamp}"
        
        # Add extension
        filepath = utils.join_and_ensure_path(
            target_directory    = target_directory, 
            filename            = f"{filename}.{self.format.value}", 
            source              = "l3210_scanner_hardware.py"
        )
        
        # Build scanimage command
        command = [
            "scanimage",
            f"--format={self.format.value}",
            f"--resolution={scan_resolution}",
            f"--mode={scan_mode.value}"
        ]
        
        # Check if scanner is available
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
                    timeout = 60  # 60 second timeout
                )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                raise ScanFailedError(f"Scan failed: {error_msg}")
            
            self._last_scan_path = filepath
            return filepath
            
        except subprocess.TimeoutExpired:
            raise ScanFailedError("Scan operation timed out after 60 seconds")
        
        except Exception as e:
            raise ScanFailedError(f"Unexpected error during scan: {e}")
        
        finally:
            self._is_scanning = False
    
    def is_scanner_available(self) -> bool:
        """
        Check if scanner is connected and ready.
        
        Returns:
            bool: True if scanner is detected, False otherwise
        """
        try:
            result = subprocess.run(
                ["scanimage", "--list-devices"],
                capture_output  = True,
                text            = True,
                timeout         = 5
            )
            return result.returncode == 0 and len(result.stdout.strip()) > 0
        except Exception:
            return False
    
    def get_scanner_info(self) -> Optional[str]:
        """
        Get detailed information about connected scanner.
        
        Returns:
            str: Scanner device information, or None if not available
        """
        try:
            result = subprocess.run(
                ["scanimage", "--list-devices"],
                capture_output  = True,
                text            = True,
                timeout         = 5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
    
    def is_scanning(self) -> bool:
        """
        Check if a scan is currently in progress.
        
        Returns:
            bool: True if scanning, False otherwise
        """
        return self._is_scanning
    
    def get_last_scan(self) -> Optional[str]:
        """
        Get the filepath of the most recent scan.
        
        Returns:
            str: Path to last scanned file, or None if no scans performed
        """
        return self._last_scan_path
    
    def set_resolution(self, resolution: int) -> None:
        """
        Set default resolution for future scans.
        
        Args:
            resolution: DPI value (75, 150, 300, 600)
        """
        if resolution not in [75, 150, 300, 600]:
            raise ValueError("Resolution must be one of: 75, 150, 300, 600")
        self.resolution = resolution
    
    def set_mode(self, mode: ScanMode) -> None:
        """
        Set default scan mode for future scans.
        
        Args:
            mode: ScanMode enum value
        """
        self.mode = mode
    
    def get_scan_count(self, target_directory: str) -> int:
        """
        Get the number of scan files in the save directory.
        
        Args:
            target_directory: Use the self.answer_keys_dir or self.answer_sheets_dir
        
        Returns:
            int: Number of files in save directory
        """
        normalized_path = utils.normalize_path(target_directory)
        if not os.path.exists(normalized_path):
            return 0
        
        files = [
            f for f in os.listdir(normalized_path)
            if f.endswith(f".{self.format.value}")
        ]
        return len(files)
    
    def list_scans(self, target_directory: str) -> list:
        """
        List all scan files in the save directory.
        
        Args:
            target_directory: Use the self.answer_keys_dir or self.answer_sheets_dir
        
        Returns:
            list: List of tuples (filename, full_path, timestamp)
        """
        normalized_path = utils.normalize_path(target_directory)
        if not os.path.exists(normalized_path):
            return []
        
        scans = []
        for filename in os.listdir(normalized_path):
            if filename.endswith(f".{self.format.value}"):
                filepath    = os.path.dirname(utils.join_and_ensure_path(target_directory, filename))
                timestamp   = os.path.getmtime(filepath)
                scans.append((filename, filepath, datetime.fromtimestamp(timestamp)))
        
        # Sort by timestamp, newest first
        scans.sort(key=lambda x: x[2], reverse=True)
        return scans
    
    def delete_scan(self, filepath: str) -> bool:
        """
        Delete a specific scan file.
        
        Args:
            filepath: Full path to the file to delete
        
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            if utils.delete_file(filepath):
                self._last_scan_path = None
                return True
        except Exception as e:
            return False
    
    def clear_all_scans(self, target_directory: str) -> Tuple[int, int]:
        """
        Delete all scan files in the save directory.
        
        Returns:
            tuple: (successful_deletions, failed_deletions)
        """
        # utils.delete_files()
        
        normalized_path = utils.normalize_path(target_directory)
        if not os.path.exists(normalized_path):
            return (0, 0)
        
        success = 0
        failed = 0
        
        for filename in os.listdir(normalized_path):
            filepath = utils.join_and_ensure_path(target_directory, filename)
            if os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                    success += 1
                except Exception:
                    failed += 1
        
        self._last_scan_path = None
        return (success, failed)
    
    def __repr__(self) -> str:
        return (
            f"L3210Scanner(save_directory='{self.base_dir}', "
            f"resolution={self.resolution}, mode={self.mode.value}, "
            f"format={self.format.value})"
        )


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    # Example 1: Initialize with auto-directory creation
    print("="*60)
    print("Example 1: Initialize with auto-directory creation")
    print("="*60)
    
    scanner = L3210Scanner()
    
    # Verify directories were created
    print("\nVerifying directory structure...")
    status = scanner.verify_directories()
    for name, info in status.items():
        symbol = "✅" if info["ready"] else "❌"
        print(f"{symbol} {name}: {info['path']}")
        print(f"   Exists: {info['exists']}, Writable: {info['writable']}")
    
    # Get standard directory paths
    dirs = scanner.get_standard_directories()
    print(f"\nStandard directories:")
    print(f"  Base: {dirs['base']}")
    print(f"  Answer Keys: {dirs['answer_keys']}")
    print(f"  Answer Sheets: {dirs['answer_sheets']}")
    

    # Example 2: Scan directly to answer_keys subdirectory

    print("\n" + "="*60)
    print("Example 2: Scan directly to answer_keys subdirectory")
    print("="*60)
    
    if scanner.is_scanner_available():
        print("✅ Scanner detected")
        
        try:
            # Scan and save to answer_keys folder
            filepath = scanner.scan(
                filename="answer_key_math_001",
                subdirectory="answer_keys"
            )
            print(f"✅ Answer key saved: {filepath}")
        except ScannerError as e:
            print(f"❌ Scan failed: {e}")
    else:
        print("❌ Scanner not detected")
    

    # Example 3: Scan directly to answer_sheets subdirectory

    print("\n" + "="*60)
    print("Example 3: Scan directly to answer_sheets subdirectory")
    print("="*60)
    
    if scanner.is_scanner_available():
        try:
            # Scan and save to answer_sheets folder
            filepath = scanner.scan(
                filename="student_001_sheet",
                subdirectory="answer_sheets"
            )
            print(f"✅ Student sheet saved: {filepath}")
        except ScannerError as e:
            print(f"❌ Scan failed: {e}")
    else:
        print("❌ Scanner not detected")
    

    # Example 4: Disable auto-directory creation

    print("\n" + "="*60)
    print("Example 4: Disable auto-directory creation")
    print("="*60)
    
    scanner_no_auto = L3210Scanner(
        base_dir="/tmp/custom_scans",
        auto_create_subdirs=False
    )
    print("Scanner initialized without auto-subdirectories")
    
    
    # Example 5: Manual directory verification and creation

    print("\n" + "="*60)
    print("Example 5: Manual directory verification and creation")
    print("="*60)
    
    scanner = L3210Scanner()
    
    # Check if directories are ready
    status = scanner.verify_directories()
    
    all_ready = all(info["ready"] for info in status.values())
    if all_ready:
        print("✅ All directories are ready for use")
    else:
        print("⚠ Some directories have issues:")
        for name, info in status.items():
            if not info["ready"]:
                print(f"  ❌ {name}: exists={info['exists']}, writable={info['writable']}")
    

    # Example 6: Basic usage
    
    print("\n" + "="*60)
    print("Example 6: Basic usage (original)")
    print("="*60)
    
    scanner = L3210Scanner()
    
    print("Checking scanner availability...")
    if scanner.is_scanner_available():
        print("✅ Scanner detected")
        print(f"Scanner info: {scanner.get_scanner_info()}")
        
        print("\nStarting scan...")
        try:
            filepath = scanner.scan()
            print(f"✅ Scan completed: {filepath}")
        except ScannerError as e:
            print(f"❌ Scan failed: {e}")
    else:
        print("❌ Scanner not detected")
    
    
    # Example 7: Custom settings (original example 2)
    
    print("\n" + "="*60)
    print("Example 7: Custom settings")
    print("="*60)
    
    scanner = L3210Scanner(
        base_dir="/home/pi/custom_scans",
        resolution=600,
        mode=ScanMode.GRAY
    )
    
    try:
        # Scan with custom filename
        filepath = scanner.scan(filename="answer_key_page1")
        print(f"Saved to: {filepath}")
        
        # Override resolution for one scan
        filepath = scanner.scan(filename="high_res_scan", resolution=600)
        
    except ScannerNotFoundError:
        print("Scanner not connected!")
    except ScanFailedError as e:
        print(f"Scan failed: {e}")
    
    
    # Example 8: Batch scanning (original example 3)
    
    print("\n" + "="*60)
    print("Example 8: Batch scanning")
    print("="*60)
    
    scanner = L3210Scanner()
    
    print("Starting batch scan...")
    for i in range(3):
        input(f"Place page {i+1} and press Enter...")
        
        if scanner.is_scanning():
            print("Scanner busy, waiting...")
        
        try:
            filepath = scanner.scan(filename=f"batch_page_{i+1}")
            print(f"Page {i+1} saved: {filepath}")
        except ScannerError as e:
            print(f"Error on page {i+1}: {e}")
            break
    
    
    # Example 9: List and manage scans (original example 4)
    
    print("\n" + "="*60)
    print("Example 9: List and manage scans")
    print("="*60)
    
    scanner = L3210Scanner()
    
    print(f"Total scans: {scanner.get_scan_count()}")
    
    print("\nRecent scans:")
    for filename, filepath, timestamp in scanner.list_scans()[:5]:
        print(f"  {filename} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get last scan
    last_scan = scanner.get_last_scan()
    if last_scan:
        print(f"\nLast scan: {last_scan}")
    
    # Clean up old scans (optional)
    # success, failed = scanner.clear_all_scans()
    # print(f"Deleted {success} files, {failed} failed")


    # Example 10: Error handling and retry logic (original example 5)
    
    print("\n" + "="*60)
    print("Example 10: Error handling and retry logic")
    print("="*60)
    
    scanner = L3210Scanner()
    max_retries = 3
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Scan attempt {attempt}/{max_retries}...")
            filepath = scanner.scan()
            print(f"✅ Success: {filepath}")
            break
        except ScannerNotFoundError:
            print("❌ Scanner not connected. Exiting.")
            break
        except ScanFailedError as e:
            print(f"⚠ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print("Retrying...")
                import time
                time.sleep(2)
            else:
                print("❌ All attempts failed.")