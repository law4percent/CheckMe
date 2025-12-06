import cv2

def initialize_camera(camera_index: int) -> dict:
    """Initialize camera capture."""
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        return {
            "status"    : "error", 
            "message"   : f"Cannot open camera. Source: {__name__}."
        }
    return {
        "status"    : "success", 
        "capture"   : capture
    }
    

def cleanup(capture: any, show_windows: bool) -> None:
    """Release camera and close all OpenCV windows."""
    capture.release()
    if show_windows:
        cv2.destroyAllWindows()