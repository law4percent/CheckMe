import os

def normalize_path(path) -> str:
    """Ensure we always get a clean string path."""
    if isinstance(path, tuple):
        path = os.path.join(*path)
    return str(path)


def path_existence_checkpoint(PATH: str, SOURCE: str) -> dict:
    PATH = normalize_path(PATH)

    if not os.path.exists(PATH):
        return {
            "status": "error",
            "message": f"{PATH} does not exist. Source: {SOURCE}"
        }
    return {"status": "success"}


def file_existence_checkpoint(PATH: str, SOURCE: str) -> dict:
    PATH = normalize_path(PATH)

    if not os.path.isfile(PATH):
        return {
            "status": "error",
            "message": f"{PATH} file does not exist. Source: {SOURCE}"
        }
    return {"status": "success"}


def path_exist_else_create_checkpoint(*paths) -> None:
    for path in paths:
        path = normalize_path(path)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)


def join_path_with_os_adaptability(TARGET_PATH: str, FILE_NAME: str, SOURCE: str, create_one: bool = True) -> str:
    TARGET_PATH = normalize_path(TARGET_PATH)

    if not os.path.exists(TARGET_PATH):
        if create_one:
            path_exist_else_create_checkpoint(TARGET_PATH)
        else:
            raise FileNotFoundError(f"{TARGET_PATH} does not exist. Source: {SOURCE}")

    return os.path.join(TARGET_PATH, FILE_NAME)


def cleanup_temporary_images(image_paths: list[str]) -> None:
    """
    Delete temporary image files.
    
    Args:
        image_paths: List of image file paths to delete
    """
    for img_path in image_paths:
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
                print(f"Cleaned up temporary image: {img_path}")
        except Exception as e:
            print(f"Warning: Could not delete {img_path}: {e}")