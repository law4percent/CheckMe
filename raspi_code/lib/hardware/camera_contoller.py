from picamera2 import Picamera2
from libcamera import Transform
import cv2
  

def cleanup_camera(capture: any) -> dict:
    try:
        if capture:
            capture.stop()
            capture.close()
    except Exception as e:
      cv2.destroyAllWindows()
      return {
        "status"  : "error",
        "message" : f"{e} Error cleaning up camera. Source: {__name__}"
      }
    finally:
      cv2.destroyAllWindows()
      return {"status": "success"}
    
    
def config_camera(FRAME_DIMENSION: dict) -> dict:
  try:
    picam2 = Picamera2()

    config = picam2.create_still_configuration(
        main        = {
           "size"       : (FRAME_DIMENSION["width"], FRAME_DIMENSION["height"]),    # HD resolution
           "format"     : "RGB888",
           "rotation"   : 90
        },
        lores       = {"size": (640, 480)},                                         # Lower resolution for previews/processing
        display     = "lores",                                                      # Use the low-res for viewing
        transform   = Transform(hflip=False, vflip=False)
    )

    picam2.configure(config)

    return {
      "status"  : "success",
      "capture" : picam2
    }
  
  except Exception as e:
    return {
      "status"  : "error",
      "message" : f"{e}. Failed to configure raspi-camera. Source: {__name__}"
    }