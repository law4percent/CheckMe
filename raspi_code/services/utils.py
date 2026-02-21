"""
Utility Module
Provides helper functions for file operations, path handling, and validation.
"""

import os
import json
from typing import List, Optional
from pathlib import Path


class PathError(Exception):
    """Raised when path operations fail"""
    pass


class FileError(Exception):
    """Raised when file operations fail"""
    pass


# ===== PATH UTILITIES =====

def normalize_path(path) -> str:
    """
    Ensure we always get a clean string path.
    
    Args:
        path: String path, tuple of path components, or Path object
    
    Returns:
        Absolute path as string
    
    Examples:
        - normalize_path("/home/pi/scans")
        - normalize_path(("home", "pi", "scans"))
        - normalize_path(Path("/home/pi/scans"))
    """
    if isinstance(path, tuple):
        path = os.path.join(*path)
    return os.path.abspath(str(path))


def ensure_directory_exists(path: str, source: str = "") -> None:
    """
    Ensure directory exists, raise error if not.
    
    Args:
        path: Directory path to check
        source: Source/context info for error message
    
    Raises:
        PathError: If directory does not exist
    """
    path = normalize_path(path)
    if not os.path.isdir(path):
        error_msg = f"Directory does not exist: {path}"
        if source:
            error_msg += f" (Source: {source})"
        raise PathError(error_msg)


def ensure_file_exists(path: str, source: str = "") -> None:
    """
    Ensure file exists, raise error if not.
    
    Args:
        path: File path to check
        source: Source/context info for error message
    
    Raises:
        FileError: If file does not exist
    """
    path = normalize_path(path)
    if not os.path.isfile(path):
        error_msg = f"File does not exist: {path}"
        if source:
            error_msg += f" (Source: {source})"
        raise FileError(error_msg)


def create_directories(*paths) -> None:
    """
    Create directories if they don't exist.
    
    Args:
        *paths: Variable number of directory paths to create
    
    Examples:
        create_directories("/home/pi/scans")
        create_directories("/path/one", "/path/two", "/path/three")
    """
    for path in paths:
        path = normalize_path(path)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)


def join_and_ensure_path(
    target_directory: str,
    filename: str,
    source: str = "",
    create_if_missing: bool = True
) -> str:
    """
    Join directory and filename, optionally creating directory.
    
    Args:
        target_directory: Directory path
        filename: Filename to join
        source: Source/context for error messages
        create_if_missing: Create directory if it doesn't exist
    
    Returns:
        Full path (directory + filename)
    
    Raises:
        PathError: If directory doesn't exist and create_if_missing=False
    
    Examples:
        path = join_and_ensure_path("/home/pi/scans", "image.jpg")
        # Returns: "/home/pi/scans/image.jpg" (creates dir if needed)
    """
    target_directory = normalize_path(target_directory)
    
    if not os.path.exists(target_directory):
        if create_if_missing:
            create_directories(target_directory)
        else:
            error_msg = f"Directory does not exist: {target_directory}"
            if source:
                error_msg += f" (Source: {source})"
            raise PathError(error_msg)
    
    return os.path.join(target_directory, filename)


def path_exists(path: str) -> bool:
    """
    Check if path exists (file or directory).
    
    Args:
        path: Path to check
    
    Returns:
        True if exists, False otherwise
    """
    path = normalize_path(path)
    return os.path.exists(path)


def is_directory(path: str) -> bool:
    """
    Check if path is a directory.
    
    Args:
        path: Path to check
    
    Returns:
        True if directory, False otherwise
    """
    path = normalize_path(path)
    return os.path.isdir(path)


def is_file(path: str) -> bool:
    """
    Check if path is a file.
    
    Args:
        path: Path to check
    
    Returns:
        True if file, False otherwise
    """
    path = normalize_path(path)
    return os.path.isfile(path)


# ===== FILE UTILITIES =====

def delete_file(filepath: str, silent: bool = False) -> bool:
    """
    Delete a single file.
    
    Args:
        filepath: Path to file
        silent: Suppress error messages
    
    Returns:
        True if deleted, False if failed
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            if not silent:
                print(f"✅ Deleted: {filepath}")
            return True
        return False
    except Exception as e:
        if not silent:
            print(f"⚠ Failed to delete {filepath}: {e}")
        return False


def delete_files(filepaths: List[str], silent: bool = False) -> tuple:
    """
    Delete multiple files.
    
    Args:
        filepaths: List of file paths
        silent: Suppress messages
    
    Returns:
        (success_count, failed_count)
    """
    success = 0
    failed = 0
    
    for filepath in filepaths:
        if delete_file(filepath, silent=True):
            success += 1
        else:
            failed += 1
    
    if not silent:
        print(f"Deleted {success} file(s), {failed} failed")
    
    return (success, failed)


def cleanup_temporary_images(image_paths: List[str]) -> None:
    """
    Delete temporary image files (alias for delete_files).
    
    Args:
        image_paths: List of image file paths to delete
    """
    delete_files(image_paths, silent=False)


def get_file_size(filepath: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        filepath: Path to file
    
    Returns:
        File size in bytes
    
    Raises:
        FileError: If file doesn't exist
    """
    filepath = normalize_path(filepath)
    ensure_file_exists(filepath)
    return os.path.getsize(filepath)


def list_files_in_directory(
    directory: str,
    extension: Optional[str] = None
) -> List[str]:
    """
    List all files in a directory.
    
    Args:
        directory: Directory path
        extension: Filter by extension (e.g., ".jpg")
    
    Returns:
        List of file paths
    """
    directory = normalize_path(directory)
    ensure_directory_exists(directory)
    
    files = []
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            if extension is None or filename.lower().endswith(extension.lower()):
                files.append(filepath)
    
    return files


# ===== JSON UTILITIES =====

def save_to_json(data: dict, output_path: str) -> None:
    """
    Save dictionary to formatted JSON file.
    
    Args:
        data: Dictionary to save
        output_path: Output file path
    
    Raises:
        FileError: If save fails
    """
    try:
        output_path = normalize_path(output_path)
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            create_directories(parent_dir)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved to: {output_path}")
        
    except Exception as e:
        raise FileError(f"Failed to save JSON: {e}")


def load_from_json(filepath: str) -> dict:
    """
    Load JSON file into dictionary.
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        Dictionary from JSON
    
    Raises:
        FileError: If file doesn't exist or is invalid JSON
    """
    try:
        filepath = normalize_path(filepath)
        ensure_file_exists(filepath)
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data
        
    except json.JSONDecodeError as e:
        raise FileError(f"Invalid JSON in {filepath}: {e}")
    except Exception as e:
        raise FileError(f"Failed to load JSON: {e}")


# ===== VALIDATION UTILITIES =====

def validate_image_path(filepath: str) -> None:
    """
    Validate that file is an image.
    
    Args:
        filepath: Path to image file
    
    Raises:
        FileError: If not a valid image file
    """
    filepath = normalize_path(filepath)
    ensure_file_exists(filepath, source="validate_image_path")
    
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
    if not filepath.lower().endswith(valid_extensions):
        raise FileError(f"Not a valid image file: {filepath}")


def validate_image_paths(filepaths: List[str]) -> None:
    """
    Validate multiple image paths.
    
    Args:
        filepaths: List of image file paths
    
    Raises:
        FileError: If any path is invalid
    """
    for filepath in filepaths:
        validate_image_path(filepath)


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    print("="*70)
    print("Example 1: Path normalization")
    print("="*70)
    
    # Different path formats
    path1 = normalize_path("/home/pi/scans")
    path2 = normalize_path(("home", "pi", "scans"))
    path3 = normalize_path("./scans")
    
    print(f"String path: {path1}")
    print(f"Tuple path: {path2}")
    print(f"Relative path: {path3}")
    
    
    print("\n" + "="*70)
    print("Example 2: Create directories")
    print("="*70)
    
    create_directories("/tmp/test_scans", "/tmp/test_output")
    print("✅ Directories created")
    
    
    print("\n" + "="*70)
    print("Example 3: Path existence checks")
    print("="*70)
    
    # Using exceptions for validation
    try:
        ensure_directory_exists("/tmp/test_scans")
        print("✅ Directory exists")
    except PathError as e:
        print(f"❌ {e}")
    
    try:
        ensure_file_exists("/tmp/nonexistent.txt")
    except FileError as e:
        print(f"✅ Caught expected error: {e}")
    
    
    print("\n" + "="*70)
    print("Example 4: Join paths with auto-creation")
    print("="*70)
    
    filepath = join_and_ensure_path(
        "/tmp/auto_created_dir",
        "scan.jpg",
        create_if_missing=True
    )
    print(f"Created path: {filepath}")
    
    
    print("\n" + "="*70)
    print("Example 5: Boolean checks")
    print("="*70)
    
    print(f"Path exists: {path_exists('/tmp')}")
    print(f"Is directory: {is_directory('/tmp')}")
    print(f"Is file: {is_file('/tmp/test.txt')}")
    
    
    print("\n" + "="*70)
    print("Example 6: Save and load JSON")
    print("="*70)
    
    data = {
        "assessment_uid": "TEST-001",
        "answers": {"Q1": "A", "Q2": "TRUE", "Q3": "CPU"}
    }
    
    json_path = "/tmp/test_data.json"
    save_to_json(data, json_path)
    
    loaded = load_from_json(json_path)
    print(f"Loaded: {loaded}")
    
    
    print("\n" + "="*70)
    print("Example 7: File deletion")
    print("="*70)
    
    # Create test files
    test_files = [
        "/tmp/test1.txt",
        "/tmp/test2.txt",
        "/tmp/test3.txt"
    ]
    
    for f in test_files:
        with open(f, "w") as file:
            file.write("test")
    
    # Delete them
    success, failed = delete_files(test_files)
    print(f"Deleted {success}, failed {failed}")
    
    
    print("\n" + "="*70)
    print("Example 8: List files in directory")
    print("="*70)
    
    # Create some test images
    create_directories("/tmp/test_images")
    for i in range(3):
        with open(f"/tmp/test_images/image{i}.jpg", "w") as f:
            f.write("fake image")
    
    jpg_files = list_files_in_directory("/tmp/test_images", extension=".jpg")
    print(f"Found {len(jpg_files)} JPG files:")
    for f in jpg_files:
        print(f"  - {f}")
    
    
    print("\n" + "="*70)
    print("Example 9: Image validation")
    print("="*70)
    
    try:
        validate_image_path("/tmp/test_images/image0.jpg")
        print("✅ Valid image path")
    except FileError as e:
        print(f"❌ {e}")
    
    
    print("\n" + "="*70)
    print("Example 10: Integration with grading system")
    print("="*70)
    
    # Setup directory structure
    base_dir = "/tmp/grading_system"
    create_directories(
        join_and_ensure_path(base_dir, "scans/answer_keys", create_if_missing=True),
        join_and_ensure_path(base_dir, "scans/answer_sheets", create_if_missing=True),
        join_and_ensure_path(base_dir, "outputs", create_if_missing=True)
    )
    
    print("✅ Grading system directory structure ready")
    
    # Save sample answer key
    answer_key = {
        "assessment_uid": "MATH-2025-001",
        "answers": {f"Q{i}": "A" for i in range(1, 51)}
    }
    
    output_path = join_and_ensure_path(
        base_dir + "/outputs",
        "answer_key.json"
    )
    save_to_json(answer_key, output_path)
    
    
    print("\n" + "="*70)
    print("Cleanup")
    print("="*70)
    
    # Clean up test directories
    import shutil
    for path in ["/tmp/test_scans", "/tmp/test_output", "/tmp/test_images", "/tmp/grading_system"]:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"✅ Removed: {path}")
    
    # Clean up test files
    for f in ["/tmp/test_data.json", "/tmp/auto_created_dir"]:
        if os.path.exists(f):
            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.remove(f)
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)