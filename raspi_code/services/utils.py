
import json
from .logger import get_logger

log = get_logger("utils.py")

def save_to_json(data: dict, output_path: str) -> None:
    """Saves a dict to a formatted JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Saved to {output_path}", type="info")
