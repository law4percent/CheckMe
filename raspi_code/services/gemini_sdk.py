import os
import base64
import mimetypes
import logging
import google.generativeai as genai

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiMediaProcessor:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """Initializes the SDK with your API Key."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def process(self, prompt: str, source: str) -> str:
        """
        Main entry point. Automatically decides between File Upload or Base64.
        :param prompt: The text instructions for Gemini.
        :param source: Either a local path ('path/to/img.png') or a Base64 string.
        """
        uploaded_file = None
        
        try:
            # 1. Check if the source is a valid local file path
            if os.path.exists(source):
                # Get the correct mime_type (e.g., 'image/png')
                mime_type, _ = mimetypes.guess_type(source)
                mime_type = mime_type or "image/jpeg" # Fallback
                
                logger.info(f"File detected. Uploading {source} to Google Cloud...")
                uploaded_file = genai.upload_file(source, mime_type=mime_type)
                
                # Use the uploaded file object for generation
                response = self.model.generate_content([prompt, uploaded_file])
            
            # 2. Otherwise, treat it as a Base64 string
            else:
                logger.info("No file found at path. Treating source as Base64 data...")
                
                # Strip metadata prefix if present (e.g., 'data:image/jpeg;base64,')
                if "base64," in source:
                    source = source.split("base64,")[1]
                
                image_bytes = base64.b64decode(source)
                image_part = {
                    "mime_type": "image/jpeg",
                    "data": image_bytes
                }
                
                response = self.model.generate_content([prompt, image_part])

            return response.text

        except Exception as e:
            logger.error(f"Gemini Request Failed: {e}")
            return f"Error: {str(e)}"

        finally:
            # 3. CRITICAL: Clean up Google Cloud storage immediately
            if uploaded_file:
                try:
                    genai.delete_file(uploaded_file.name)
                    logger.info("Successfully deleted temporary file from Google Cloud.")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to delete cloud file: {cleanup_error}")

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Replace with your actual API Key
    MY_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
    processor = GeminiMediaProcessor(api_key=MY_API_KEY)

    # Example 1: Using your local path
    # Make sure 'scan/image/photo.png' actually exists relative to this script!
    my_prompt = "What is written in this document?"
    my_path = "scan/image/photo.png"
    
    result = processor.process(my_prompt, my_path)
    print(f"\nGemini's Answer:\n{result}")