"""
Image Uploader Module
Provides Cloudinary upload interface with batch support and retry logic.
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
from typing import List, Dict, Optional, Tuple
import time
import os


class ImageUploaderError(Exception):
    """Base exception for image uploader errors"""
    pass


class UploadError(ImageUploaderError):
    """Raised when upload fails"""
    pass


class DeleteError(ImageUploaderError):
    """Raised when delete fails"""
    pass


class ImageUploader:
    """
    Cloudinary image uploader with batch support.
    
    Example usage:
        uploader = ImageUploader(
            cloud_name  = "your_cloud",
            api_key     = "your_key",
            api_secret  = "your_secret"
        )
        
        # Single upload
        result = uploader.upload_single("image.jpg")
        print(result["url"])
        
        # Batch upload
        results = uploader.upload_batch([
            "scan1.jpg",
            "scan2.jpg",
            "scan3.jpg"
        ])
        
        urls = [r["url"] for r in results]
    """
    
    def __init__(
        self,
        cloud_name  : str,
        api_key     : str,
        api_secret  : str,
        secure      : bool  = True,
        folder      : str   = "answer-sheets"
    ):
        """
        Initialize Cloudinary uploader.
        
        Args:
            cloud_name  : Cloudinary cloud name
            api_key     : Cloudinary API key
            api_secret  : Cloudinary API secret
            secure      : Use HTTPS (default: True)
            folder      : Default upload folder
        """
        self.cloud_name     = cloud_name
        self.api_key        = api_key
        self.api_secret     = api_secret
        self.secure         = secure
        self.default_folder = folder
        
        # Configure Cloudinary
        try:
            cloudinary.config(
                cloud_name  = cloud_name,
                api_key     = api_key,
                api_secret  = api_secret,
                secure      = secure
            )
        except Exception as e:
            raise ImageUploaderError(f"Failed to configure Cloudinary: {e}")
    
    def upload_single(
        self,
        image_path      : str,
        folder          : Optional[str] = None,
        unique_filename : bool          = True
    ) -> Dict[str, str] :
        """
        Upload a single image to Cloudinary.
        
        Args:
            image_path      : Path to image file
            folder          : Upload folder (uses default if None)
            unique_filename : Generate unique filename
        
        Returns:
            Dictionary with 'url' and 'public_id'
        
        Raises:
            UploadError: If upload fails
        """
        # Validate file exists
        if not os.path.exists(image_path):
            raise UploadError(f"File not found: {image_path}")
        
        # Use default folder if not specified
        upload_folder = folder or self.default_folder
        
        try:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                image_path,
                folder          = upload_folder,
                unique_filename = unique_filename
            )
            
            return {
                "url"       : upload_result["secure_url"],
                "public_id" : upload_result["public_id"]
            }
            
        except Exception as e:
            raise UploadError(f"Failed to upload {image_path}: {e}")
    
    def upload_batch(
        self,
        image_paths : List[str],
        folder      : Optional[str] = None,
        max_retries : int = 3,
        retry_delay : float = 1.0
    ) -> List[Dict[str, str]]:
        """
        Upload multiple images to Cloudinary with retry logic.
        
        Args:
            image_paths : List of image file paths
            folder      : Upload folder (uses default if None)
            max_retries : Maximum retry attempts per image
            retry_delay : Delay between retries (seconds)
        
        Returns:
            List of dictionaries with 'url' and 'public_id'
        
        Raises:
            UploadError: If any upload fails after all retries
        """
        results = []
        failed_uploads = []
        
        for image_path in image_paths:
            uploaded = False
            last_error = None
            
            # Retry loop
            for attempt in range(1, max_retries + 1):
                try:
                    result = self.upload_single(
                        image_path=image_path,
                        folder=folder
                    )
                    results.append(result)
                    uploaded = True
                    break
                    
                except UploadError as e:
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
            
            # Track failed uploads
            if not uploaded:
                failed_uploads.append({
                    "path"  : image_path,
                    "error" : str(last_error)
                })
        
        # Raise error if any uploads failed
        if failed_uploads:
            error_msg = f"Failed to upload {len(failed_uploads)} image(s):\n"
            for fail in failed_uploads:
                error_msg += f"  - {fail['path']}: {fail['error']}\n"
            raise UploadError(error_msg)
        
        return results
    
    def upload_with_progress(
        self,
        image_paths         : List[str],
        folder              : Optional[str]         = None,
        progress_callback   : Optional[callable]    = None
    ) -> List[Dict[str, str]]:
        """
        Upload images with progress callback.
        
        Args:
            image_paths         : List of image paths
            folder              : Upload folder
            progress_callback   : Function called with (current, total, filename)
        
        Returns:
            List of upload results
        
        Example:
            def show_progress(current, total, filename):
                print(f"Uploading {current}/{total}: {filename}")
            
            results = uploader.upload_with_progress(
                images,
                progress_callback=show_progress
            )
        """
        results = []
        total = len(image_paths)
        
        for i, image_path in enumerate(image_paths, 1):
            # Call progress callback
            if progress_callback:
                filename = os.path.basename(image_path)
                progress_callback(i, total, filename)
            
            # Upload image
            try:
                result = self.upload_single(image_path, folder)
                results.append(result)
            except UploadError as e:
                raise UploadError(f"Upload failed at {i}/{total}: {e}")
        
        return results
    
    def delete_single(
        self,
        public_id   : str,
        invalidate  : bool = True
    ) -> bool:
        """
        Delete a single image from Cloudinary.
        
        Args:
            public_id   : Cloudinary public ID
            invalidate  : Invalidate CDN cache
        
        Returns:
            True if deleted successfully
        
        Raises:
            DeleteError: If deletion fails
        """
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                invalidate=invalidate
            )
            
            if result.get("result") == "ok":
                return True
            else:
                raise DeleteError(f"Delete failed: {result}")
                
        except Exception as e:
            raise DeleteError(f"Failed to delete {public_id}: {e}")
    
    def delete_batch(
        self,
        public_ids: List[str],
        invalidate: bool = True
    ) -> Tuple[List[str], List[str]]:
        """
        Delete multiple images from Cloudinary.
        
        Args:
            public_ids: List of Cloudinary public IDs
            invalidate: Invalidate CDN cache
        
        Returns:
            (successfully_deleted, failed_to_delete)
        """
        if not public_ids:
            return ([], [])
        
        try:
            result = cloudinary.api.delete_resources(
                public_ids,
                invalidate=invalidate
            )
            
            deleted = result.get("deleted", {})
            
            # Separate successful and failed
            success = []
            failed  = []
            
            for public_id in public_ids:
                if deleted.get(public_id) == "deleted":
                    success.append(public_id)
                else:
                    failed.append(public_id)
            
            return (success, failed)
            
        except Exception as e:
            raise DeleteError(f"Batch delete failed: {e}")
    
    def get_folder_contents(self, folder: str) -> List[Dict]:
        """
        List all images in a folder.
        
        Args:
            folder: Folder path
        
        Returns:
            List of resource dictionaries
        """
        try:
            result = cloudinary.api.resources(
                type        = "upload",
                prefix      = folder,
                max_results = 500
            )
            return result.get("resources", [])
            
        except Exception as e:
            raise ImageUploaderError(f"Failed to list folder: {e}")
    
    def __repr__(self) -> str:
        return f"ImageUploader(cloud={self.cloud_name}, folder={self.default_folder})"


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    # Configuration
    CLOUD_NAME  = "your_cloud_name"
    API_KEY     = "your_api_key"
    API_SECRET  = "your_api_secret"
    
    print("="*70)
    print("Example 1: Initialize uploader")
    print("="*70)
    
    uploader = ImageUploader(
        cloud_name  = CLOUD_NAME,
        api_key     = API_KEY,
        api_secret  = API_SECRET,
        folder      = "grading-system/answer-sheets"
    )
    print(f"Initialized: {uploader}")
    
    
    print("\n" + "="*70)
    print("Example 2: Upload single image")
    print("="*70)
    
    try:
        result = uploader.upload_single("scan_page1.jpg")
        print(f"✅ Uploaded successfully!")
        print(f"   URL: {result['url']}")
        print(f"   Public ID: {result['public_id']}")
    except UploadError as e:
        print(f"❌ Upload failed: {e}")
    
    
    print("\n" + "="*70)
    print("Example 3: Batch upload (safe)")
    print("="*70)
    
    image_files = [
        "scan_page1.jpg",
        "scan_page2.jpg",
        "scan_page3.jpg"
    ]
    
    try:
        results = uploader.upload_batch(
            image_paths = image_files,
            folder      = "grading-system/answer-keys",
            max_retries = 3
        )
        
        print(f"✅ Uploaded {len(results)} images:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['url']}")
        
        # Extract URLs for saving to RTDB
        urls = [r["url"] for r in results]
        public_ids = [r["public_id"] for r in results]
        
    except UploadError as e:
        print(f"❌ Batch upload failed: {e}")
    
    
    print("\n" + "="*70)
    print("Example 4: Upload with progress callback")
    print("="*70)
    
    def show_upload_progress(current, total, filename):
        """Display progress on LCD or console"""
        percentage = (current / total) * 100
        print(f"Uploading {current}/{total} ({percentage:.0f}%): {filename}")
    
    try:
        results = uploader.upload_with_progress(
            image_paths         = image_files,
            progress_callback   = show_upload_progress
        )
        print(f"✅ All uploads complete!")
        
    except UploadError as e:
        print(f"❌ Upload failed: {e}")
    
    
    print("\n" + "="*70)
    print("Example 5: Delete single image")
    print("="*70)
    
    try:
        # Assuming we have a public_id from upload
        public_id = "grading-system/answer-sheets/abc123"
        
        success = uploader.delete_single(public_id)
        if success:
            print(f"✅ Deleted: {public_id}")
        else:
            print(f"❌ Failed to delete: {public_id}")
            
    except DeleteError as e:
        print(f"❌ Delete failed: {e}")
    
    
    print("\n" + "="*70)
    print("Example 6: Batch delete")
    print("="*70)
    
    try:
        public_ids_to_delete = [
            "grading-system/answer-sheets/img1",
            "grading-system/answer-sheets/img2",
            "grading-system/answer-sheets/img3"
        ]
        
        deleted, failed = uploader.delete_batch(public_ids_to_delete)
        
        print(f"✅ Deleted: {len(deleted)}")
        print(f"❌ Failed: {len(failed)}")
        
        if failed:
            print(f"   Failed IDs: {failed}")
            
    except DeleteError as e:
        print(f"❌ Batch delete failed: {e}")
    
    
    print("\n" + "="*70)
    print("Example 7: Integration with grading system")
    print("="*70)
    
    def upload_answer_key_images(scanned_images: List[str]):
        """Upload answer key images safely"""
        uploader = ImageUploader(
            cloud_name  = CLOUD_NAME,
            api_key     = API_KEY,
            api_secret  = API_SECRET,
            folder      = "grading-system/answer-keys"
        )
        
        try:
            print("Uploading images to Cloudinary...")
            results = uploader.upload_batch(
                image_paths = scanned_images,
                max_retries = 3,
                retry_delay = 2.0
            )
            
            # Extract URLs
            urls = [r["url"] for r in results]
            
            print(f"✅ Upload successful!")
            print(f"   Uploaded {len(urls)} image(s)")
            
            return urls
            
        except UploadError as e:
            print(f"❌ Upload failed: {e}")
            return None
    
    # Simulate usage
    scanned_files = ["scan1.jpg", "scan2.jpg"]
    urls = upload_answer_key_images(scanned_files)
    
    
    print("\n" + "="*70)
    print("Example 8: Upload with LCD display integration")
    print("="*70)
    
    def upload_with_lcd_progress(images: List[str]):
        """Upload images with LCD progress display"""
        uploader = ImageUploader(CLOUD_NAME, API_KEY, API_SECRET)
        
        def lcd_progress(current, total, filename):
            # In real system: lcd.show([
            #     f"Uploading {current}/{total}",
            #     f"{filename[:16]}",
            #     f"{'█' * int(current/total*20)}"
            # ])
            print(f"LCD: Uploading {current}/{total} - {filename}")
        
        try:
            results = uploader.upload_with_progress(
                image_paths         = images,
                progress_callback   = lcd_progress
            )
            
            # lcd.show("Upload complete!", duration=2)
            print("LCD: Upload complete!")
            
            return [r["url"] for r in results]
            
        except UploadError as e:
            # lcd.show(["Upload failed!", str(e)[:20]])
            print(f"LCD: Upload failed! {e}")
            return None
    
    upload_with_lcd_progress(scanned_files)
    
    
    print("\n" + "="*70)
    print("Example 9: Background retry upload")
    print("="*70)
    
    def background_upload_retry(images: List[str], assessment_uid: str):
        """Background upload with multiple retries"""
        from multiprocessing import Process
        import time
        
        def retry_upload():
            uploader = ImageUploader(CLOUD_NAME, API_KEY, API_SECRET)
            
            for attempt in range(1, 4):  # 3 attempts
                print(f"Background attempt {attempt}/3...")
                try:
                    results = uploader.upload_batch(images)
                    urls = [r["url"] for r in results]
                    
                    # Update RTDB with URLs
                    # firebase_db.update_image_urls(assessment_uid, urls)
                    print(f"✅ Background upload succeeded!")
                    return
                    
                except UploadError as e:
                    print(f"⚠ Attempt {attempt} failed: {e}")
                    if attempt < 3:
                        time.sleep(5)  # Wait before retry
            
            # All attempts failed
            print("❌ All background attempts failed")
            # firebase_db.update_image_urls(assessment_uid, [])
        
        # Start background process
        p = Process(target=retry_upload)
        p.start()
        print("Background upload process started")
    
    background_upload_retry(scanned_files, "MATH-001")
    
    
    print("\n" + "="*70)
    print("Example 10: List folder contents")
    print("="*70)
    
    try:
        resources = uploader.get_folder_contents("grading-system/answer-keys")
        print(f"✅ Found {len(resources)} images in folder")
        for resource in resources[:5]:  # Show first 5
            print(f"   - {resource['public_id']}")
    except ImageUploaderError as e:
        print(f"❌ Failed: {e}")
    
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)