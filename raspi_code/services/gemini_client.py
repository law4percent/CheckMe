import base64
import requests
from abc import ABC, abstractmethod
import mimetypes
import os
import time
from typing import Tuple, Optional, Any
from enum import Enum
import json

from google import genai
from google.genai import types
from google.genai import errors

from .logger import get_logger
log = get_logger("gemini_client.py")

class ErrorType(Enum):
    RETRYABLE    = "retryable"
    AUTH_ERROR   = "auth_error"
    CLIENT_ERROR = "client_error"
    QUOTA_ERROR  = "quota_error"


class GeminiClient(ABC):
    @abstractmethod
    def send_request(self, prompt: str, image_path: str, upload_to_cloud: bool = False) -> str:
        pass

    @abstractmethod
    def _upload_file_to_cloud(self, image_path: str) -> Any:
        pass

    @abstractmethod
    def _validate_response(self, response: Any) -> str:
        pass

    def _get_image_data(self, image_path: str) -> Tuple[bytes, str]:
        """Helper to get bytes and detect mime type automatically"""
        mime_type, _    = mimetypes.guess_type(image_path)
        mime_type       = mime_type or "image/jpeg"
        
        with open(image_path, "rb") as f:
            return f.read(), mime_type

    @staticmethod
    def _classify_error(error: Exception) -> ErrorType:
        status_code = None
        if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
            status_code = error.response.status_code

        if status_code in (401, 403) or (
            status_code is None and any(
                x in str(error).lower()
                for x in ["401", "unauthorized", "invalid api key", "403", "forbidden"]
            )
        ):
            return ErrorType.AUTH_ERROR

        if status_code == 429 or (
            status_code is None and any(
                x in str(error).lower()
                for x in ["429", "quota", "rate limit", "resource exhausted"]
            )
        ):
            return ErrorType.QUOTA_ERROR

        if status_code in (400, 404) or (
            status_code is None and any(
                x in str(error).lower()
                for x in ["400", "bad request", "invalid", "not found", "404"]
            )
        ):
            return ErrorType.CLIENT_ERROR

        return ErrorType.RETRYABLE


class GeminiSDKClient(GeminiClient):
    def __init__(self, api_key: str, model_name: str):
        self.api_key    = api_key
        self.model_name = model_name
        self.client     = genai.Client(api_key=api_key)
        # REFERENCE 1: https://github.com/googleapis/python-genai?tab=readme-ov-file#using-types
        # REFERENCE 2: https://github.com/googleapis/python-genai?tab=readme-ov-file#system-instructions-and-other-configs
        self.config     = types.GenerateContentConfig(
            temperature = 0,
            top_p       = 0.95,
            top_k       = 20,
            max_output_tokens = 8192
        )

    def _upload_file_to_cloud(self, image_path) -> Tuple[Any, str]:
        """Uploads a file to Google Cloud and returns the file object"""
        # PRO TIP: Get mime_type and pass it to upload_file to ensure correct handling in Gemini
        mime_type, _    = mimetypes.guess_type(image_path)
        mime_type       = mime_type or "image/jpeg"
        
        # REFERENCE: https://github.com/googleapis/python-genai?tab=readme-ov-file#upload
        file = self.client.files.upload(file=image_path)
        return file, mime_type
    
    # Comment: To be tested if this works
    def _validate_response(self, response: Any) -> str:
        # Safer return logic inside send_request
        if response.candidates:
            # Check if the first candidate actually has text
            if response.candidates[0].content.parts:
                return response.text
            else:
                finish_reason = response.candidates[0].finish_reason
                raise ValueError(f"No text returned. Finish reason: {finish_reason}")
        else:
            # This happens if the prompt itself was blocked
            raise ValueError("Request was blocked by safety filters.")

    def send_request(self, prompt: str, image_path: str, upload_to_cloud: bool = False) -> str:
        """Send request using the official Gemini SDK"""
        # TARGET: image_path
        # POTENTIAL/CRITICAL ERROR: File cannot be found or not exist.
        # SOLUTION: Validate it first when using this in the your code somewhere, before sending it here in the send_request() function

        if upload_to_cloud:
            file = None
            try:
                log(f"Uploading {image_path} via SDK...", type="info")
                file, mime_type = self._upload_file_to_cloud(image_path)
                log("Generating content with SDK (Upload/Referencing Version)", type="info")
                
                # Possible for Better or Optimization.
                # Explore and try this approach.
                # Comment: I think  this ain't work for this case.
                # Check this link: https://github.com/googleapis/python-genai?tab=readme-ov-file#json-schema-support
                response = self.client.models.generate_content(
                    model       = self.model_name,
                    contents    = [
                        # REFERENCE: https://github.com/googleapis/python-genai?tab=readme-ov-file#provide-a-list-of-non-function-call-parts    
                        types.Part.from_text(prompt),
                        types.Part.from_uri(file.uri, mime_type)
                    ],
                    config      = self.config
                )
                return self._validate_response(response) # To be confirm if this works or not
                
            except errors.APIError as e:
                log(f"SDK request failed: {e.code} {e.message}", type="error")
                raise RuntimeError(f"SDK request failed: {e.code} {e.message}") from e
            
            finally:
                # Always clean up uploaded file
                if file:
                    try:
                        # REFERENCE: https://github.com/googleapis/python-genai?tab=readme-ov-file#delete
                        self.client.files.delete(name=file.name)
                        log("Cleaned up uploaded file", type="info")
                    except Exception as cleanup_error:
                        log(
                            f"\nFailed to delete the uploaded file: {cleanup_error}\n"
                            f"You can delete the file manually at google cloud: {file.name}\n" 
                            f"Or just wait 48 hours because it auto deleted after the time.", 
                            type="warning"
                        )
        
        else:
            try:
                log("Get file as bytes inline data...", type="info")
                # REFERENCE: https://github.com/googleapis/python-genai?tab=readme-ov-file#streaming-for-image-content
                image_bytes, mime_type = self._get_image_data(image_path)
                log("Generating content with SDK (bytes)...", type="info")
                response = self.client.models.generate_content(
                    model       = self.model_name,
                    contents    = [
                        prompt, 
                        types.Part.from_bytes(
                            data        = image_bytes, 
                            mime_type   = mime_type)
                    ],
                    config      = self.config
                )
                return self._validate_response(response)
            
            except errors.APIError as e:
                log(f"SDK request failed: {e.code} {e.message}", type="error")
                raise RuntimeError(f"SDK request failed: {e.code} {e.message}") from e


class GeminiHTTPClient(GeminiClient):
    def __init__(self, api_key: str, model_name: str):
        self.api_key    = api_key
        self.model_name = model_name
        self.url        = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    def _upload_file_to_cloud(self, image_path) -> Tuple[str, str]:
        """Uploads an image file to Google Cloud"""
        mime_type, _   = mimetypes.guess_type(image_path)
        mime_type      = mime_type or "image/jpeg"
        upload_url     = "https://generativelanguage.googleapis.com/upload/v1beta/files"
        upload_headers = {
            "x-goog-api-key"        : self.api_key,
            "X-Goog-Upload-Protocol": "multipart",
        }
        metadata       = {"file": {"display_name": os.path.basename(image_path)}}
        with open(image_path, 'rb') as f:
            files = {
                'metadata': (None, json.dumps(metadata), 'application/json'),
                'file'    : (os.path.basename(image_path), f, mime_type)
            }
            upload_response = requests.post(
                upload_url,
                headers = upload_headers,
                files   = files,
                timeout = 60
            )
            upload_response.raise_for_status()

        file_uri = upload_response.json()['file']['uri']
        return file_uri, mime_type

    def _validate_response(self, response: dict) -> str:
        # CHECK: Did the AI actually return a response? 
        # (Safety filters often return 200 OK but 0 candidates)
        if "candidates" not in response or not response["candidates"]:
            reason = response.get("promptFeedback", {}).get("blockReason", "Safety Filter")
            log(f"Gemini blocked this request: {reason}", type="warning")
            raise ValueError(f"Gemini blocked this request: {reason}")

        candidate = response["candidates"][0]
        parts     = candidate.get("content", {}).get("parts", [])

        if parts and "text" in parts[0]:
            return parts[0]["text"]
        else:
            # Handle cases where AI returns something other than text (like a finishReason)
            finish_reason = candidate.get("finishReason")
            log(f"No text returned. Finish reason: {finish_reason}", type="warning")
            raise ValueError(f"No text returned. Finish reason: {finish_reason}")

    def _encode_image_to_base64(self, image_path: str) -> Tuple[str, str]:
        image_bytes, mime_type  = self._get_image_data(image_path)
        encoded_string          = base64.b64encode(image_bytes).decode('utf-8')
        return encoded_string, mime_type

    def send_request(self, prompt: str, image_path: str, upload_to_cloud: bool = False) -> str:
        """Send request using direct HTTP API calls (SECURE)"""
        # TARGET: image_path
        # POTENTIAL/CRITICAL ERROR: File cannot be found or not exist.
        # SOLUTION: Validate it first when using this in the your code somewhere, before sending it here in the send_request() function
        # STATUS: Not yet implemented or On going

        if upload_to_cloud:
            upload_succeeded = False
            try:
                log(f"Uploading {image_path} via HTTP...", type="info")
                file_uri, mime_type = self._upload_file_to_cloud(image_path)
                upload_succeeded    = True  # Only reaches here if upload didn't throw
                gen_payload         = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"file_data": {"mime_type": mime_type, "file_uri": file_uri}}
                        ]
                    }]
                }
                headers             = {
                    "Content-Type"  : "application/json",
                    "x-goog-api-key": self.api_key
                }
                log("Generating content...", type="info")
                response            = requests.post(
                    self.url,
                    headers = headers,
                    json    = gen_payload,
                    timeout = 30
                )
                response.raise_for_status()
                return self._validate_response(response.json())

            except requests.RequestException as e:
                log(f"HTTP request failed: {type(e).__name__}", type="error")
                raise RuntimeError(f"HTTP request failed: {e}") from e

            except (KeyError, IndexError) as e:
                log(f"Unexpected response format: {e}", type="error")
                raise ValueError(f"Unexpected response format: {e}") from e

            finally:
                if upload_succeeded:
                    log(
                        "\nNOTE: Uploaded file cannot be deleted via HTTP API.\n"
                        "In a production system, you would want to implement a scheduled cleanup process for orphaned files in Google Cloud Storage.\n"
                        "Please manage your cloud storage to avoid orphaned files.",
                        type="warning"
                    )

        else:
            try:
                log(f"Encoding {image_path} to Base64 for HTTP request...", type="info")
                encoded_string, mime_type = self._encode_image_to_base64(image_path)
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data"     : encoded_string
                                }
                            }
                        ]
                    }]
                }
                headers = {
                    "Content-Type"  : "application/json",
                    "x-goog-api-key": self.api_key
                }
                log("Generating content...", type="info")
                response = requests.post(
                    self.url,
                    json    = payload,
                    headers = headers,
                    timeout = 30
                )
                response.raise_for_status()
                return self._validate_response(response.json())

            except requests.RequestException as e:
                log(f"HTTP request failed: {type(e).__name__}", type="error")
                raise RuntimeError(f"HTTP request failed: {e}") from e

            except (KeyError, IndexError) as e:
                log(f"Unexpected response format: {e}", type="error")
                raise ValueError(f"Unexpected response format: {e}") from e


# ============================================================
# RETRY ORCHESTRATOR
# ============================================================

def gemini_with_retry(
    api_key         : str,
    image_path      : str,
    prompt          : str,
    model           : str,
    max_attempts    : int           = 3,
    use_exponential_backoff : bool  = True,
    prefer_method   : str           = "sdk",
    upload_to_cloud : bool          = False
) -> str | None:

    if not os.path.exists(image_path):
        log(f"Image file not found: {image_path}", type="error")
        return None

    client_option = ("SDK Client",  lambda: GeminiSDKClient(api_key, model)) if prefer_method == "sdk" else ("HTTP Client", lambda: GeminiHTTPClient(api_key, model))
    method_name, client_factory = client_option
    for attempt in range(1, max_attempts + 1):
        log(
            f"\n{'='*50}\n"
            f"ATTEMPT {attempt}/{max_attempts}\n"
            f"{'='*50}\n",
            type="info"
        )
        last_error_type = ErrorType.RETRYABLE

        try:
            client = client_factory()
            result = client.send_request(prompt, image_path, upload_to_cloud)
            log(f"✓ {method_name} succeeded on attempt {attempt}!", type="info")
            return result

        except Exception as e:
            error_type      = GeminiClient._classify_error(e)
            last_error_type = error_type

            if error_type == ErrorType.CLIENT_ERROR:
                # Bad file or bad prompt — no client or retry can fix this
                log(f"Client error on {method_name} ({error_type.value}). Aborting.", type="error")
                return None

            if error_type == ErrorType.AUTH_ERROR:
                # This client cannot authenticate — skip it, let the other client try
                log(f"Auth error on {method_name} ({error_type.value}). Aborting — check your API key.", type="error")
                return None
            
            log(f"✗ {method_name} failed ({error_type.value}): {e}", type="warning")

        # This method was tried but all failed — apply normal backoff
        if attempt < max_attempts:
            if last_error_type == ErrorType.QUOTA_ERROR:
                wait_time = 30  # Quota limits need longer recovery than network blips
            elif use_exponential_backoff:
                wait_time = 2 ** attempt  # 2, 4, 8 seconds
            else:
                wait_time = 3

            log(f"Failed attempt. Waiting {wait_time}s before attempt {attempt + 1}...", type="info")
            time.sleep(wait_time)

    log(f"All {max_attempts} attempts exhausted.", type="error")
    return None

# ============================================================
# USAGE
# ============================================================

if __name__ == "__main__":
    API_KEY    = "YOUR_API_KEY"
    IMAGE_PATH = "sample.jpg"
    PROMPT     = "Describe what you see in this image."
    MODEL      = "gemini-2.5-flash"  # Replace with your desired model

    # ============================================================
    # Sample usage with gemini_with_retry()
    # ============================================================

    # --- 1. Basic usage with SDK default settings ---
    result = gemini_with_retry(
        api_key    = API_KEY,
        image_path = IMAGE_PATH,
        prompt     = PROMPT,
        model      = MODEL
    )
    print(f"SDK result: {result}")


    # --- 2. Prefer HTTP over SDK ---
    result = gemini_with_retry(
        api_key       = API_KEY,
        image_path    = IMAGE_PATH,
        prompt        = PROMPT,
        model         = MODEL,
        prefer_method = "http",
    )
    print(f"HTTP result: {result}")


    # --- 3. More attempts, no exponential backoff ---
    result = gemini_with_retry(
        api_key                 = API_KEY,
        image_path              = IMAGE_PATH,
        prompt                  = PROMPT,
        model                   = MODEL,
        max_attempts            = 5,
        use_exponential_backoff = False,
    )
    print(f"Fixed-wait result: {result}")


    # --- 4. Upload to cloud ---
    result = gemini_with_retry(
        api_key         = API_KEY,
        image_path      = IMAGE_PATH,
        prompt          = PROMPT,
        model           = MODEL,
        upload_to_cloud = True
    )
    print(f"Save image to cloud result: {result}")

    # ============================================================
    # Direct usage samples without any retry logic
    # ============================================================

    # --- 1. SDK Client — upload to cloud (default) ---
    sdk_client = GeminiSDKClient(API_KEY, MODEL)
    result     = sdk_client.send_request(PROMPT, IMAGE_PATH)
    print(f"SDK (cloud upload): {result}")


    # --- 2. SDK Client — Base64 inline (cloud upload) ---
    sdk_client = GeminiSDKClient(API_KEY, MODEL)
    result     = sdk_client.send_request(PROMPT, IMAGE_PATH, upload_to_cloud=True)
    print(f"SDK (image in bytes): {result}")


    # --- 3. HTTP Client — upload to cloud (default) ---
    http_client = GeminiHTTPClient(API_KEY, MODEL)
    result      = http_client.send_request(PROMPT, IMAGE_PATH)
    print(f"HTTP (cloud upload): {result}")


    # --- 4. HTTP Client — Base64 inline (cloud upload) ---
    http_client = GeminiHTTPClient(API_KEY, MODEL)
    result      = http_client.send_request(PROMPT, IMAGE_PATH, upload_to_cloud=True)
    print(f"HTTP (base64): {result}")