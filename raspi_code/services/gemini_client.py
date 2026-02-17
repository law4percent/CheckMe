import base64
import requests
import google.generativeai as genai
from abc import ABC, abstractmethod
import mimetypes
import os
import time
from typing import Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json

from .logger import get_logger
log = get_logger("gemini_client.py")

class ErrorType(Enum):
    RETRYABLE    = "retryable"
    AUTH_ERROR   = "auth_error"
    CLIENT_ERROR = "client_error"
    QUOTA_ERROR  = "quota_error"


class CircuitState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold : int = 3
    recovery_timeout  : int = 30
    success_threshold : int = 2


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config            = config or CircuitBreakerConfig()
        self.failure_count     = 0
        self.success_count     = 0
        self.last_failure_time = 0
        self.state             = CircuitState.CLOSED
        self.last_state_change = datetime.now()

    def can_proceed(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            time_since_failure = time.time() - self.last_failure_time
            if time_since_failure > self.config.recovery_timeout:
                log(f"Circuit transitioning to HALF-OPEN (testing recovery)", type="info")
                self.state             = CircuitState.HALF_OPEN
                self.success_count     = 0
                self.last_state_change = datetime.now()
                return True

            log(
                f"Circuit is OPEN. Failing fast. "
                f"Recovery attempt in {self.config.recovery_timeout - time_since_failure:.0f}s",
                type="warning"
            )
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            log(
                f"Circuit HALF-OPEN: Success {self.success_count}/{self.config.success_threshold}",
                type="info"
            )
            if self.success_count >= self.config.success_threshold:
                log("Circuit recovered! Transitioning to CLOSED", type="info")
                self.state             = CircuitState.CLOSED
                self.failure_count     = 0
                self.success_count     = 0
                self.last_state_change = datetime.now()
        else:
            self.failure_count = 0

    def record_failure(self):
        self.failure_count     += 1
        self.last_failure_time  = time.time()

        if self.state == CircuitState.HALF_OPEN:
            log("Circuit HALF-OPEN test failed. Reopening circuit.", type="warning")
            self.state             = CircuitState.OPEN
            self.success_count     = 0
            self.last_state_change = datetime.now()

        elif self.failure_count >= self.config.failure_threshold:
            log(
                f"CIRCUIT BREAKER TRIPPED! "
                f"({self.failure_count} consecutive failures) "
                f"→ OPEN",
                type="error"
            )
            self.state             = CircuitState.OPEN
            self.last_state_change = datetime.now()

    def get_status(self) -> dict:
        return {
            "state"                  : self.state.value,
            "failure_count"          : self.failure_count,
            "success_count"          : self.success_count,
            "last_state_change"      : self.last_state_change.isoformat(),
            "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time else None
        }


class GeminiClient(ABC):
    @abstractmethod
    def send_request(self, prompt: str, image_path: str, upload_to_cloud: bool = True) -> str:
        pass

    def _upload_file_to_cloud(self, image_path: str) -> Any:
        raise NotImplementedError

    def _validate_response(self, response: Any) -> str:
        raise NotImplementedError

    def _get_image_data(self, image_path: str) -> Tuple[bytes, str]:
        """Helper to get bytes and detect mime type automatically"""
        mime_type, _    = mimetypes.guess_type(image_path)
        mime_type       = mime_type or "image/jpeg"
        
        with open(image_path, "rb") as f:
            return f.read(), mime_type
    
    def _encode_image_to_base64(self, image_path: str) -> Tuple[str, str]:
        image_bytes, mime_type  = self._get_image_data(image_path)
        encoded_string          = base64.b64encode(image_bytes).decode('utf-8')
        return encoded_string, mime_type

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

        # TARGET: model_name
        # POTENTIAL/CRITICAL ERROR: Mispelled or Invalid mode_name
        # SOLUTION: Validate it first, before sending it here in the __init__() function
        # STATUS: Not yet implemented or On going
        self.model      = genai.GenerativeModel(model_name)

    def _upload_file_to_cloud(self, image_path) -> genai.File:
        """Uploads a file to Google Cloud and returns the file object"""
        # PRO TIP: Get mime_type and pass it to upload_file to ensure correct handling in Gemini
        mime_type, _    = mimetypes.guess_type(image_path)
        mime_type       = mime_type or "image/jpeg"
        return genai.upload_file(image_path, mime_type=mime_type)
    
    def _validate_response(self, response: genai.types.GenerateContentResponse) -> str:
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

    def send_request(self, prompt: str, image_path: str, upload_to_cloud: bool = True) -> str:
        """Send request using the official Gemini SDK"""
        # TARGET: image_path
        # POTENTIAL/CRITICAL ERROR: File cannot be found or not exist.
        # SOLUTION: Validate it first when using this in the your code somewhere, before sending it here in the send_request() function
        # STATUS: Not yet implemented or On going

        # If upload_to_cloud is True, we will upload the file to Google Cloud and reference it in the request
        if upload_to_cloud:
            uploaded_file = None
            try:
                log(f"Uploading {image_path} via SDK...", type="debug")
                uploaded_file = self._upload_file_to_cloud(image_path)
                log("Generating content with SDK (Upload/Referencing Version)", type="debug")
                response = self.model.generate_content([prompt, uploaded_file])
                return self._validate_response(response)
                
            except Exception as e:
                log(f"SDK request failed: {type(e).__name__}: {e}", type= "error")
                raise RuntimeError(f"SDK request failed: {e}") from e
            
            finally:
                # Always clean up uploaded file
                if uploaded_file:
                    try:
                        genai.delete_file(uploaded_file.name)
                        log("Cleaned up uploaded file", type="debug")
                    except Exception as cleanup_error:
                        log(
                            f"Failed to delete the uploaded file: {cleanup_error}"
                            f"You can delete the file manually at google cloud: {uploaded_file.name}", 
                            type="warning"
                        )
        
        # Else, we will encode the image as Base64 and send it inline (no cloud upload)
        else:
            log("Uploading file as Base64 inline data...", type="debug")
            encoded_string, mime_type = self._encode_image_to_base64(image_path)
            image_part = {
                "mime_type": mime_type,
                "data": encoded_string
            }
            
            try:
                log("Generating content with SDK (Base64)...", type="debug")
                response = self.model.generate_content([prompt, image_part])
                return self._validate_response(response)
            
            except Exception as e:
                log(f"SDK request with Base64 failed: {type(e).__name__}: {e}", type="error")
                raise RuntimeError(f"SDK request with Base64 failed: {e}") from e


class GeminiHTTPClient(GeminiClient):
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    def _upload_file_to_cloud(self, image_path) -> Tuple[str, str]:
        """Uploads an image file to Google Cloud"""
        mime_type, _    = mimetypes.guess_type(image_path)
        mime_type       = mime_type or "image/jpeg"
        upload_url      = "https://generativelanguage.googleapis.com/upload/v1beta/files"
        upload_headers  = {
            "x-goog-api-key": self.api_key,
            "X-Goog-Upload-Protocol": "multipart",
        }
        metadata        = {"file": {"display_name": os.path.basename(image_path)}}
        
        upload_response = None
        with open(image_path, 'rb') as f:
            files           = {
                'metadata': (None, json.dumps(metadata), 'application/json'),
                'file': (os.path.basename(image_path), f, mime_type)
            }
            upload_response = requests.post(
                upload_url, 
                headers = upload_headers, 
                files   = files, 
                timeout = 60
            )
            upload_response.raise_for_status()

        file_info = upload_response.json()
        file_uri = file_info['file']['uri'] # This is the "reference" to your cloud file
        return file_uri, mime_type

    def _validate_response(self, response: dict) -> str:
        # CHECK: Did the AI actually return a response? 
        # (Safety filters often return 200 OK but 0 candidates)
        if "candidates" not in response or not response["candidates"]:
            reason = response.get("promptFeedback", {}).get("blockReason", "Safety Filter")
            log(f"Gemini blocked this request: {reason}", type="warning")
            raise ValueError(f"Gemini blocked this request: {reason}")

        candidate   = response["candidates"][0]
        parts       = candidate.get("content", {}).get("parts", [])
        if parts and "text" in parts[0]:
            return parts[0]["text"]
        else:
            # Handle cases where AI returns something other than text (like a finishReason)
            finish_reason = candidate.get("finishReason")
            log(f"No text returned. Finish reason: {finish_reason}", type="warning")
            raise ValueError(f"No text returned. Finish reason: {finish_reason}")

    def send_request(self, prompt: str, image_path: str, upload_to_cloud: bool = True) -> str:
        """Send request using direct HTTP API calls (SECURE)"""
        # TARGET: image_path
        # POTENTIAL/CRITICAL ERROR: File cannot be found or not exist.
        # SOLUTION: Validate it first when using this in the your code somewhere, before sending it here in the send_request() function
        # STATUS: Not yet implemented or On going

        # If upload_to_cloud is True, we will upload the file to Google Cloud and reference it in the request
        if upload_to_cloud:
            try:
                log(f"Uploading {image_path} via HTTP...", type="debug")
                file_uri, mime_type = self._upload_file_to_cloud(image_path)        
                gen_payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"file_data": {"mime_type": mime_type, "file_uri": file_uri}}
                        ]
                    }]
                }
                headers = {
                    "Content-Type": "application/json", 
                    "x-goog-api-key": self.api_key
                }
                log("Generating content...", type="debug")
                response = requests.post(
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
                log(
                    "NOTE: Uploaded file cannot be deleted via HTTP API."
                    "In a production system, you would want to implement a scheduled cleanup process for orphaned files in Google Cloud Storage."
                    "Please manage your cloud storage to avoid orphaned files.",
                    type="warning"
                )
        
        # Else, we will encode the image as Base64 and send it inline (no cloud upload)
        else:
            try:
                log("Encoding image to Base64 for HTTP request...", type="debug")
                encoded_string, mime_type = self._encode_image_to_base64(image_path)
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": encoded_string
                                }
                            }
                        ]
                    }]
                }
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                }
                
                log("Sending HTTP request...", type="debug")
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
# GLOBAL CIRCUIT BREAKERS
# ============================================================

sdk_circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold = 3,
    recovery_timeout  = 30,
    success_threshold = 2
))

http_circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold = 3,
    recovery_timeout  = 30,
    success_threshold = 2
))


# ============================================================
# RETRY ORCHESTRATOR
# ============================================================

def gemini_engine(
    api_key       : str,
    image_path    : str,
    prompt        : str,
    model         : str,
    max_attempts  : int            = 3,
    use_exponential_backoff : bool = True,
    prefer_method : str            = "sdk",
    sdk_breaker   : CircuitBreaker = sdk_circuit_breaker,
    http_breaker  : CircuitBreaker = http_circuit_breaker,
) -> Optional[str]:

    genai.configure(api_key=api_key)

    if not os.path.exists(image_path):
        log(f"Image file not found: {image_path}", type="error")
        return None

    if prefer_method == "http":
        methods = [
            ("HTTP Client", lambda: GeminiHTTPClient(api_key, model), http_breaker),
            ("SDK Client",  lambda: GeminiSDKClient(api_key, model),  sdk_breaker),
        ]
    else:
        methods = [
            ("SDK Client",  lambda: GeminiSDKClient(api_key, model),  sdk_breaker),
            ("HTTP Client", lambda: GeminiHTTPClient(api_key, model), http_breaker),
        ]

    for attempt in range(1, max_attempts + 1):
        log(f"{'='*50}", type="info")
        log(f"ATTEMPT {attempt}/{max_attempts}", type="info")
        log(f"{'='*50}", type="info")

        last_error_type = ErrorType.RETRYABLE

        for method_name, client_factory, breaker in methods:
            if not breaker.can_proceed():
                log(f"⊗ {method_name} circuit is OPEN. Skipping.", type="warning")
                continue

            log(f"→ Trying {method_name}...", type="info")

            client = None
            try:
                client = client_factory()
                result = client.send_request(prompt, image_path)
                breaker.record_success()
                log(f"✓ {method_name} succeeded on attempt {attempt}!", type="info")
                return result

            except Exception as e:
                error_type      = GeminiClient._classify_error(e)
                last_error_type = error_type
                log(f"✗ {method_name} failed ({error_type.value}): {e}", type="warning")
                breaker.record_failure()

                if error_type == ErrorType.CLIENT_ERROR:
                    log("Client error is not retryable. Aborting.", type="error")
                    return None

                if error_type == ErrorType.AUTH_ERROR:
                    log(f"Auth error on {method_name}. Skipping to next client.", type="error")
                    continue

        if attempt < max_attempts:
            if last_error_type == ErrorType.QUOTA_ERROR:
                wait_time = 30
            elif use_exponential_backoff:
                wait_time = 2 ** attempt
            else:
                wait_time = 2

            log(f"All methods failed. Waiting {wait_time}s before attempt {attempt + 1}...", type="info")
            time.sleep(wait_time)

    log(f"All {max_attempts} attempts exhausted.", type="error")
    log(f"SDK  circuit: {sdk_breaker.get_status()}",  type="info")
    log(f"HTTP circuit: {http_breaker.get_status()}", type="info")
    return None


# ============================================================
# USAGE
# ============================================================

if __name__ == "__main__":
    API_KEY    = "YOUR_API_KEY"
    IMAGE_PATH = "sample.jpg"
    PROMPT     = "Describe what you see in this image."
    MODEL      = "gemini-2.5-flash"  # Replace with your desired model

    # --- 1. Basic usage (SDK first, default settings) ---
    result = gemini_engine(
        api_key    = API_KEY,
        image_path = IMAGE_PATH,
        prompt     = PROMPT,
        model      = MODEL
    )
    print(f"Basic result: {result}")


    # --- 2. Prefer HTTP over SDK ---
    result = gemini_engine(
        api_key       = API_KEY,
        image_path    = IMAGE_PATH,
        prompt        = PROMPT,
        model         = MODEL,
        prefer_method = "http",
    )
    print(f"HTTP-first result: {result}")


    # --- 3. More attempts, no exponential backoff ---
    result = gemini_engine(
        api_key                 = API_KEY,
        image_path              = IMAGE_PATH,
        prompt                  = PROMPT,
        model                   = MODEL,
        max_attempts            = 5,
        use_exponential_backoff = False,
    )
    print(f"Fixed-wait result: {result}")


    # --- 4. Custom circuit breaker config (stricter settings) ---
    custom_sdk_breaker  = CircuitBreaker(CircuitBreakerConfig(
        failure_threshold = 2,
        recovery_timeout  = 60,
        success_threshold = 3
    ))
    custom_http_breaker = CircuitBreaker(CircuitBreakerConfig(
        failure_threshold = 2,
        recovery_timeout  = 60,
        success_threshold = 3
    ))

    result = gemini_engine(
        api_key      = API_KEY,
        image_path   = IMAGE_PATH,
        prompt       = PROMPT,
        model        = MODEL,
        sdk_breaker  = custom_sdk_breaker,
        http_breaker = custom_http_breaker,
    )
    print(f"Custom breaker result: {result}")


    # --- 5. Isolated breakers for independent pipelines ---
    pipeline_a = gemini_engine(
        api_key      = API_KEY,
        image_path   = IMAGE_PATH,
        prompt       = "Pipeline A: summarize this image.",
        model        = MODEL,
        sdk_breaker  = CircuitBreaker(),
        http_breaker = CircuitBreaker(),
    )

    pipeline_b = gemini_engine(
        api_key      = API_KEY,
        image_path   = IMAGE_PATH,
        prompt       = "Pipeline B: extract text from this image.",
        model        = MODEL,
        sdk_breaker  = CircuitBreaker(),
        http_breaker = CircuitBreaker(),
    )

    print(f"Pipeline A: {pipeline_a}")
    print(f"Pipeline B: {pipeline_b}")