"""
Path: lib/hardware/camera_controller.py
Camera controller module for configuring and cleaning up the Raspberry Pi camera.
"""

from picamera2 import Picamera2
from libcamera import Transform
import cv2
import logging

logger = logging.getLogger(__name__)


def cleanup_camera(capture: any) -> dict:
    """
    Cleanup and release camera resources.
    
    Args:
        capture: Picamera2 instance
    
    Returns:
        dict: Status dictionary
    """
    try:
        if capture:
            capture.stop()
            capture.close()
            logger.info("Camera cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up camera: {e}")
        cv2.destroyAllWindows()
        return {
            "status"  : "error",
            "message" : f"{e} Error cleaning up camera. Source: {__name__}"
        }
    finally:
        cv2.destroyAllWindows()
        return {"status": "success"}


def config_camera(FRAME_DIMENSION: dict) -> dict:
    """
    Configure Raspberry Pi camera with specified dimensions.
    
    Args:
        FRAME_DIMENSION: Dictionary with 'width' and 'height' keys
    
    Returns:
        dict: Status dictionary with capture instance if successful
    """
    try:
        picam2 = Picamera2()

        config = picam2.create_still_configuration(
            main      = {
                "size"    : (FRAME_DIMENSION["width"], FRAME_DIMENSION["height"]),
                "format"  : "RGB888",
                "rotation": 90
            },
            lores     = {"size": (640, 480)},
            display   = "lores",
            transform = Transform(hflip=False, vflip=False)
        )

        picam2.configure(config)
        
        logger.info(f"Camera configured: {FRAME_DIMENSION['width']}x{FRAME_DIMENSION['height']}")

        return {
            "status"  : "success",
            "capture" : picam2
        }

    except Exception as e:
        logger.error(f"Failed to configure camera: {e}")
        return {
            "status"  : "error",
            "message" : f"{e}. Failed to configure raspi-camera. Source: {__name__}"
        }