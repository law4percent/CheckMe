import base64
import requests
import google.generativeai as genai
from abc import ABC, abstractmethod
import mimetypes
import os
import time
import logging
from typing import Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Categorize errors to determine retry strategy"""
    RETRYABLE = "retryable"  # Network issues, timeouts
    AUTH_ERROR = "auth_error"  # Invalid API key
    CLIENT_ERROR = "client_error"  # Bad request, file not found
    QUOTA_ERROR = "quota_error"  # Rate limit, quota exceeded


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Service is down, fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Trip after N consecutive failures
    recovery_timeout: int = 60  # Wait N seconds before testing recovery
    success_threshold: int = 2  # N successes needed to close circuit in half-open state


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation to prevent resource waste
    during prolonged API outages.
    """
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.now()
    
    def can_proceed(self) -> bool:
        """Check if requests should be allowed through"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            time_since_failure = time.time() - self.last_failure_time
            if time_since_failure > self.config.recovery_timeout:
                logger.info(f"Circuit transitioning to HALF-OPEN (testing recovery)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.last_state_change = datetime.now()
                return True
            
            logger.warning(
                f"Circuit is OPEN. Failing fast. "
                f"Recovery attempt in {self.config.recovery_timeout - time_since_failure:.0f}s"
            )
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record a successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit HALF-OPEN: Success {self.success_count}/{self.config.success_threshold}"
            )
            
            if self.success_count >= self.config.success_threshold:
                logger.info("✓ Circuit recovered! Transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_state_change = datetime.now()
        else:
            # Reset failure count on any success in closed state
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit HALF-OPEN test failed. Reopening circuit.")
            self.state = CircuitState.OPEN
            self.success_count = 0
            self.last_state_change = datetime.now()
        elif self.failure_count >= self.config.failure_threshold:
            logger.error(
                f"!!! CIRCUIT BREAKER TRIPPED !!! "
                f"({self.failure_count} consecutive failures) "
                f"State: {self.state.value} → OPEN"
            )
            self.state = CircuitState.OPEN
            self.last_state_change = datetime.now()
    
    def get_status(self) -> dict:
        """Get current circuit breaker status for monitoring"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_state_change": self.last_state_change.isoformat(),
            "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time else None
        }


class GeminiClient(ABC):
    @abstractmethod
    def send_request(self, prompt: str, image_path: str) -> str:
        pass

    def _get_image_data(self, image_path: str) -> Tuple[bytes, str]:
        """Helper to get bytes and detect mime type automatically"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        mime_type, _ = mimetypes.guess_type(image_path)
        mime_type = mime_type or "image/jpeg"
        
        with open(image_path, "rb") as f:
            return f.read(), mime_type

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error to determine if retry makes sense"""
        error_str = str(error).lower()
        
        # Authentication errors - don't retry
        if any(x in error_str for x in ['401', 'unauthorized', 'invalid api key', '403', 'forbidden']):
            return ErrorType.AUTH_ERROR
        
        # Quota/rate limit errors - may benefit from backoff
        if any(x in error_str for x in ['429', 'quota', 'rate limit', 'resource exhausted']):
            return ErrorType.QUOTA_ERROR
        
        # Client errors - don't retry
        if any(x in error_str for x in ['400', 'bad request', 'invalid', 'not found', '404']):
            return ErrorType.CLIENT_ERROR
        
        # Network/server errors - retry
        return ErrorType.RETRYABLE


# --- SDK Client ---
class GeminiSDKClient(GeminiClient):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)

    def send_request(self, prompt: str, image_path: str) -> str:
        """Send request using the official Gemini SDK"""
        uploaded_file = None
        try:
            # PRO TIP: Get mime_type and pass it to upload_file
            _, mime_type = self._get_image_data(image_path)
            
            logger.info(f"Uploading file: {image_path} (type: {mime_type})")
            uploaded_file = genai.upload_file(image_path, mime_type=mime_type)
            
            logger.info("Generating content with SDK...")
            response = self.model.generate_content([prompt, uploaded_file])
            
            return response.text
            
        except Exception as e:
            logger.error(f"SDK request failed: {type(e).__name__}: {e}")
            raise
        finally:
            # Always clean up uploaded file
            if uploaded_file:
                try:
                    genai.delete_file(uploaded_file.name)
                    logger.debug("Cleaned up uploaded file")
                except Exception as e:
                    logger.warning(f"Failed to delete uploaded file: {e}")


# --- HTTP Client (SECURE VERSION) ---
class GeminiHTTPClient(GeminiClient):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        # SECURITY: Don't put API key in URL
        self.url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent"

    def send_request(self, prompt: str, image_path: str) -> str:
        """Send request using direct HTTP API calls (SECURE)"""
        try:
            image_bytes, mime_type = self._get_image_data(image_path)
            encoded_string = base64.b64encode(image_bytes).decode('utf-8')

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
            
            # SECURITY: Use header instead of URL parameter
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            logger.info("Sending HTTP request...")
            response = requests.post(self.url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
            
        except requests.RequestException as e:
            logger.error(f"HTTP request failed: {type(e).__name__}")
            raise RuntimeError(f"HTTP request failed: {e}") from e
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected response format")
            raise ValueError(f"Unexpected response format") from e


# --- GLOBAL CIRCUIT BREAKERS (one per method) ---
sdk_circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold   = 3,
    recovery_timeout    = 30,
    success_threshold   = 2
))

http_circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold   = 3,
    recovery_timeout    = 30,
    success_threshold   = 2
))


# --- ENTERPRISE-GRADE RETRY LOGIC ---
def try_gemini_with_retry(
    api_key: str,
    image_path: str,
    prompt: str,
    model: str = "gemini-1.5-flash",
    max_attempts: int = 3,
    use_exponential_backoff: bool = True,
    prefer_method: str = "sdk"  # "sdk" or "http"
) -> Optional[str]:
    """
    Try both Gemini methods with circuit breaker protection.
    
    Args:
        api_key: Gemini API key
        image_path: Path to image file
        prompt: Text prompt for the model
        model: Model name to use
        max_attempts: Maximum retry attempts
        use_exponential_backoff: Use exponential backoff (2^n seconds)
        prefer_method: Which method to try first ("sdk" or "http")
    
    Returns:
        str: Response text if successful
        None: If all attempts failed
    """
    
    # OPTIMIZATION: Configure SDK once, globally
    genai.configure(api_key=api_key)
    
    # Pre-validate file to avoid wasting API calls
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return None
    
    # Determine method order
    if prefer_method == "http":
        methods = [
            ("HTTP Client", lambda: GeminiHTTPClient(api_key, model), http_circuit_breaker),
            ("SDK Client", lambda: GeminiSDKClient(api_key, model), sdk_circuit_breaker)
        ]
    else:
        methods = [
            ("SDK Client", lambda: GeminiSDKClient(api_key, model), sdk_circuit_breaker),
            ("HTTP Client", lambda: GeminiHTTPClient(api_key, model), http_circuit_breaker)
        ]
    
    for attempt in range(1, max_attempts + 1):
        logger.info(f"{'='*60}")
        logger.info(f"ATTEMPT {attempt}/{max_attempts}")
        logger.info(f"{'='*60}")
        
        # Try each method in order
        for method_name, client_factory, breaker in methods:
            # Check circuit breaker
            if not breaker.can_proceed():
                logger.warning(f"⊗ {method_name} circuit is OPEN. Skipping.")
                continue
            
            logger.info(f"→ {method_name}...")
            logger.debug(f"   Circuit state: {breaker.state.value}")
            
            try:
                client = client_factory()
                result = client.send_request(prompt, image_path)
                
                # SUCCESS!
                breaker.record_success()
                logger.info(f"✓ {method_name} succeeded!")
                return result
                
            except Exception as e:
                error_type = client._classify_error(e)
                logger.warning(f"✗ {method_name} failed ({error_type.value})")
                
                # Record failure in circuit breaker
                breaker.record_failure()
                
                # Don't retry on auth or client errors
                if error_type in [ErrorType.AUTH_ERROR, ErrorType.CLIENT_ERROR]:
                    logger.error("Non-retryable error detected. Stopping all attempts.")
                    return None
        
        # Both methods failed - decide if we should retry
        if attempt < max_attempts:
            if use_exponential_backoff:
                wait_time = 2 ** attempt  # 2, 4, 8 seconds
            else:
                wait_time = 2
            
            logger.info(f"⚠ Both methods failed. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
        else:
            logger.error(f"⚠ All {max_attempts} attempts exhausted.")
            
            # Log circuit breaker status
            logger.info("Circuit Breaker Status:")
            logger.info(f"  SDK: {sdk_circuit_breaker.get_status()}")
            logger.info(f"  HTTP: {http_circuit_breaker.get_status()}")
    
    return None


# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    # SECURITY: Use environment variable
    MY_KEY = os.getenv("GEMINI_API_KEY")
    
    if not MY_KEY:
        logger.error("Please set GEMINI_API_KEY environment variable!")
        logger.info("Example: export GEMINI_API_KEY='your-key-here'")
        exit(1)
    
    IMAGE = "test_image.png"
    PROMPT = "Role: You are an expert. Summarize this image."
    MODEL = "gemini-1.5-flash"
    
    result = try_gemini_with_retry(
        api_key                 = MY_KEY,
        image_path              = IMAGE,
        prompt                  = PROMPT,
        model                   = MODEL,
        max_attempts            = 3,
        use_exponential_backoff = True,
        prefer_method           = "sdk"  # Try SDK first, fallback to HTTP
    )
    
    logger.info(f"{'='*60}")
    if result:
        logger.info("✓ SUCCESS: Result obtained!")
        logger.info(f"\nResult preview:\n{result[:200]}...")
        logger.info(f"\nTotal length: {len(result)} characters")
    else:
        logger.error("✗ FAILURE: Could not get result after all attempts.")
        logger.info("\nTroubleshooting:")
        logger.info("1. Verify GEMINI_API_KEY environment variable is set")
        logger.info("2. Check image file exists and is readable")
        logger.info("3. Ensure internet connection is active")
        logger.info("4. Verify model name is correct")
        logger.info("5. Check API quota at https://aistudio.google.com")
        logger.info("\nCircuit Breaker Status:")
        logger.info(f"  SDK: {sdk_circuit_breaker.get_status()}")
        logger.info(f"  HTTP: {http_circuit_breaker.get_status()}")
    logger.info(f"{'='*60}")