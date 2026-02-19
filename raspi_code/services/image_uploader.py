import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

from .logger import get_log_file

log = get_log_file("image_uploader.py")

class ImageUploader:
    def __init__(self, cloud_name: str, api_key: str, api_secret: str, secure: bool = True):
        # Setting the global config
        try:
            cloudinary.config( 
                cloud_name = cloud_name, 
                api_key    = api_key, 
                api_secret = api_secret,
                secure     = secure
            )
        except Exception as e:
            log(f"Failed to configure: {e}", type="error")
            raise RuntimeError(f"Failed to configure: {e}") from e

    def upload_and_get_url(self, image_path) -> str:
        try:
            # 1. Upload the image
            upload_result = cloudinary.uploader.upload(image_path, unique_filename=True)
        except Exception as e:
            log(f"Failed to upload {image_path} : {e}", type="error")
            raise RuntimeError(f"Failed to upload {image_path} : {e}") from e
        
        # 2. Get the Public ID (needed for transformations later)
        public_id = upload_result["public_id"]

        # 3. This is how you'll generate optimized URLs later:
        # We use the dynamic 'public_id' instead of hardcoded "shoes"
        optimize_url, _ = cloudinary_url(public_id, fetch_format="auto", quality="auto")
        
        # 4. Return the standard secure URL for now
        return upload_result["secure_url"]

if __name__ == "__main__":
    # Note: Make sure these are your real credentials from the dashboard!
    CLOUD_NAME  = "DhsaiaE"
    API_KEY     = "3131324341"
    API_SECRET  = "jnsdg&7398faFA3"

    try:
        image_uploader = ImageUploader(CLOUD_NAME, API_KEY, API_SECRET)
    
        img_cloud_url = image_uploader.upload_and_get_url("landscape.jpg")
        print(f"Success! Link: {img_cloud_url}")
    except Exception as e:
        print(f"Failed to upload: {e}")