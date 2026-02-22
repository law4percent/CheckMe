import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

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
            raise RuntimeError(f"Failed to configure: {e}") from e

    def upload_and_get_url(self, image_path: str) -> dict:
        try:
            # 1. Upload the image
            upload_result = cloudinary.uploader.upload(image_path, unique_filename=True)
        
            # We use the dynamic 'public_id' instead of hardcoded "shoes"
            # optimize_url, _ = cloudinary_url(public_id, fetch_format="auto", quality="auto")
            
            # 4. Return the standard secure URL for now
            return {
                "url"       : upload_result["secure_url"],
                "public_id" : upload_result["public_id"]
            }
        
        except Exception as e:
            raise RuntimeError(f"Failed to upload {image_path} : {e}") from e

    def delete_image(self, public_ids: str | list[str], invalidate: bool = True) -> bool:
        """Delete one or more images from Cloudinary"""
        try:
            if isinstance(public_ids, str):
                public_ids = [public_ids]
            
            result = cloudinary.api.delete_resources(public_ids, invalidate=invalidate)
            
            # Check if all IDs were successfully deleted
            deleted = result.get("deleted", {})
            all_deleted = all(deleted.get(pid) == "deleted" for pid in public_ids)

            if all_deleted:
                return True
            else:
                return False
        
        except Exception as e:
            raise RuntimeError(f"Failed to delete {public_ids} : {e}") from e


# --- Usage Example ---
if __name__ == "__main__":
    # Note: Make sure these are your real credentials from the dashboard!
    CLOUD_NAME  = "DhsaiaE"
    API_KEY     = "3131324341"
    API_SECRET  = "jnsdg&7398faFA3"

    # Upload
    try:
        image_uploader = ImageUploader(CLOUD_NAME, API_KEY, API_SECRET)
    
        result = image_uploader.upload_and_get_url("landscape.jpg")
        print(f"Success! Link: {result['url']}")
        print(f"Success! Public Id: {result['public_id']}")
    except Exception as e:
        print(f"Failed to upload: {e}")

    # Delete
    try:
        image_uploader.delete_image(result['public_id'])
        print(f"Deletion Success!")
    except Exception as e:
        print(f"Failed to delete: {e}")
