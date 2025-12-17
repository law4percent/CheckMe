# lib/services/gemini.py
"""
Complete Gemini OCR System for Answer Keys and Student Sheets
Extracts answer keys and grades student answer sheets.
"""

import os
import time
import random
import base64
import json
import logging
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Try SDK first
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    import requests


class GeminiOCREngine:
    """Main OCR engine for extracting answer keys and student answers."""

    TEACHER_INSTRUCTION = """
You are an OCR system that extracts the official Answer Key from a test paper image.
The image contains ONLY the teacher's answer key.

The sheet contains:
- Multiple Choice (A, B, C, D)
- True or False (T/F or True/False)
- Enumeration (text answers)

Important Rules:
1. Ignore instructions for students.
2. Ignore explanations or choices.
3. Extract ONLY the correct answer.
4. Keep continuous numbering: 1, 2, 3...N Exactly as in the test.
5. If unreadable, return `"unreadable"`
6. At the top, there is a unique Assessment UID code (alphanumeric).

Return JSON EXACTLY like this:
{
  "assessment_uid": "XXXX1234",
  "answers": {
    "Q1": "A",
    "Q2": "CPU",
    "Q3": "unreadable",
    continue...
    "Qn": "no_answer"
  }
}
"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

        if GENAI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)

            self.model = genai.GenerativeModel(
                "gemini-2.5-flash",
                generation_config   = {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_output_tokens": 1024,
                },
            )

            logger.info("Using google-generativeai SDK for OCR")
        else:
            self.model = None
            logger.info("Using REST API fallback for OCR")

    # ============================================================
    # ANSWER KEY EXTRACTION
    # ============================================================

    def extract_answer_key(self, image_path: str, MAX_RETRY: int) -> Dict:
        """
            Extract teacher's answer key from image.
            
            Args:
                image_path: Path to the answer key image
                MAX_RETRY: Maximum number of retry attempts
                
            Returns:
                - Dictionary with extracted data or error status
                - Success: {"status": "success", "result": {assessment_uid: XXXX, asnwers: {...}}}
                - Error: {"status": "error", "message": "..."}
        """
        # Check API key
        if not self.api_key:
            return {
                "status": "error",
                "message": "GEMINI_API_KEY not set in environment",
                "error_type": "missing_api_key"
            }

        # Encode image
        try:
            image_base64 = self._encode_image(image_path)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read image: {str(e)}"
            }

        if GENAI_AVAILABLE and self.model:
            response_text = self._call_gemini_sdk(image_base64, self.TEACHER_INSTRUCTION, MAX_RETRY)
        else:
            response_text = self._call_gemini_rest(image_base64, self.TEACHER_INSTRUCTION, MAX_RETRY)

        parse_result = self._safe_parse_json(response_text)
        if parse_result["status"] == "error":
            return parse_result
        result = parse_result["result"]

        # Validate required fields
        if "answers" not in result:
            return {
                "status": "error",
                "message": f"Missing 'answers' field in API response.\nraw_response: {str(result)[:200]} Source: {__name__}"
            }
        
        if "assessment_uid" not in result:
            logger.warning("Missing 'assessment_uid' field in response")
            return {
                "status": "error",
                "message": f"Missing 'assessment_uid' field in API response.\nraw_response: {str(result)[:200]} Source: {__name__}"
            }

        return {
            "status": "success",
            "result": result
        }
    # ============================================================
    # STUDENT ANSWER EXTRACTION
    # ============================================================

    def extract_answer_sheet(self, image_path: str, total_number_of_questions: int, MAX_RETRY: int) -> Dict:
        """
            Extract student answers from answer sheet image.
            
            Args:
                image_path: Path to the student answer sheet image
                total_number_of_questions: Expected number of questions
                MAX_RETRY: Maximum number of retry attempts
                
            Returns:
                - Dictionary with extracted data or error status
                - Success: {"status": "success", "result": {student_id: XXXX, asnwers: {...}}}
                - Error: {"status": "error", "message": "..."}
        """
        # Check API key
        if not self.api_key:
            return {
                "status": "error",
                "message": f"Missing API Key. GEMINI_API_KEY not set in environment. Source: {__name__}"
            }

        # Encode image
        try:
            image_base64 = self._encode_image(image_path)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read image and encode image to base64: {str(e)} Source: {__name__}"
            }

        STUDENT_INSTRUCTION = self._format_answer_sheet_prompt(total_number_of_questions)

        if GENAI_AVAILABLE and self.model:
            response_text = self._call_gemini_sdk(image_base64, STUDENT_INSTRUCTION, MAX_RETRY)
        else:
            response_text = self._call_gemini_rest(image_base64, STUDENT_INSTRUCTION, MAX_RETRY)

        parse_result = self._safe_parse_json(response_text)
        if parse_result["status"] == "error":
            return parse_result
        result = parse_result["result"]
        
        # Validate required fields
        if "answers" not in result:
            return {
                "status": "error",
                "message": f"Missing 'answers' field in API response.\nraw_response: {str(result)[:200]} Source: {__name__}"
            }
        
        answers = result["answers"]
        for n in range(1, total_number_of_questions + 1):
            if f"Q{n}" not in answers:
                return {
                    "status"    : "error",
                    "message"   : f"Missing: Q{n}. \nraw_response: {str(result)[:200]} Source: {__name__}"
                }

        if "student_id" not in result:
            logger.warning("Missing 'student_id' field in response")
            result["student_id"] = "unknown"
        
        return {
            "status": "success",
            "result": result
        }

    # ============================================================
    # HELPER METHODS
    # ============================================================

    @staticmethod
    def _format_answer_sheet_prompt(total_number_of_questions: int) -> str:
        """Generate the prompt for student answer sheet extraction."""
        return f"""
You are an OCR system that extracts answers from an answer sheet image.

The sheet contains:
- A Student ID field at the top.
- Student's handwritten or circled answers.
- Multiple possible sections:
  - Section Number: Multiple Choice – Circle the correct answer (A, B, C, D)
  - Section Number: True or False – Fill in the blank (T or F)
  - Section Number: Multiple Choice – Fill in the blank (A, B, C, D)
  - Section Number: Enumeration – Fill in the blank (text answers)

Important Rules:
1. Read the Student ID written at the top.
2. Detect whether each answer is circled or written.
3. For enumeration items, extract the text exactly as written.
4. Maintain continuous numbering across sections (1, 2, 3, …).
5. Do NOT include explanations or the question text.
6. Only extract the student's answer.
7. If a student's answer is unreadable, return "unreadable".
8. If a student's answer is blank or missing, return "no_answer".
9. The total number of questions (Qn) must be exactly {total_number_of_questions}.
10. If the number of questions is not exactly {total_number_of_questions}:
    You MUST still produce questions up to {total_number_of_questions} and give no_question value for the missing questoins.

Return JSON in this exact format:
{{
    "student_id": "XXXX2345",
    "answers": {{
        "Q1": "A",
        "Q2": "no_answer",
        "Q3": "unreadable",
        "Q4": "no_question",
        continue...
        "Q{total_number_of_questions}": "CPU"
    }}
}}
"""

    def _encode_image(self, path: str) -> str:
        """Encode image to base64."""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_gemini_sdk(self, image_b64: str, instruction: str, MAX_RETRY: int) -> str:
        """Call Gemini API using SDK with retry logic."""
        contents = [
            instruction,
            {
                "mime_type": "image/jpeg",
                "data": image_b64
            }
        ]

        last_error = None
        
        for attempt in range(MAX_RETRY):
            try:
                response = self.model.generate_content(
                    contents = contents,
                    generation_config = {"temperature": 0.2}
                )

                if not response.text.strip():
                    raise ValueError("Empty response from Gemini")

                return response.text

            except Exception as e:
                last_error = e
                logger.error(f"Gemini SDK error (attempt {attempt+1}/{MAX_RETRY}): {e}")

                if "429" in str(e).lower() or "quota" in str(e).lower():
                    wait = 8 + random.randint(2, 10)
                    logger.warning(f"Rate limit hit. Waiting {wait}s")
                    time.sleep(wait)
                    continue

                if attempt < MAX_RETRY - 1:
                    time.sleep(2)

        # All retries failed
        return json.dumps({
            "status"    : "error",
            "message"   : f"Gemini SDK failed after {MAX_RETRY} retries: {str(last_error)}"
        })

    def _call_gemini_rest(self, image_b64: str, instruction: str, MAX_RETRY: int) -> str:
        """Call Gemini API using REST endpoint."""
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"parts": [{"text": instruction}]},
                {
                    "parts": [{
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64
                        }
                    }]
                }
            ]
        }

        last_error = None

        for attempt in range(MAX_RETRY):
            try:
                response = requests.post(
                    url, 
                    params = {"key": self.api_key},
                    json = payload, 
                    headers = headers, 
                    timeout = 30
                )

                response.raise_for_status()

                try:
                    return response.json()["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Bad REST response format: {e}")
                    return json.dumps({
                        "status"    : "error",
                        "message"   : f"Bad REST response format: {str(e)}"
                    })
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.error(f"REST API error (attempt {attempt+1}/{MAX_RETRY}): {e}")
                
                # Check for rate limiting
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 429:
                        wait = 8 + random.randint(2, 10)
                        logger.warning(f"Rate limit hit. Waiting {wait}s")
                        time.sleep(wait)
                        continue
                
                if attempt < MAX_RETRY - 1:
                    time.sleep(2 + random.randint(1, 3))
                    continue

        # All retries failed
        return json.dumps({
            "status"    : "error", 
            "message"   : f"REST API failed after {MAX_RETRY} retries: {str(last_error)}"
        })

    @staticmethod
    def _normalize_answer(answer: str) -> str:
        """Normalize answer for comparison (case-insensitive, stripped)."""
        if answer is None:
            return ""
        return answer.strip().upper()

    @staticmethod
    def _safe_parse_json(text: str) -> Dict:
        """
        Safely parse JSON response from Gemini.
        
        Returns:
            Parsed dictionary or error dictionary
        """
        try:
            cleaned = text.strip("```json").strip("```").strip()
            parsed = json.loads(cleaned)
            return {
                "status": "success",
                "result": parsed
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return {
                "status"    : "error", 
                "message"   : f"JSON parsing failed: {str(e)}\nraw_response: {text[:200]} Source: {__name__}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during JSON parsing: {e}")
            return {
                "status"    : "error",
                "message"   : f"Unexpected parsing error: {str(e)}\nraw_response: {text[:200]} Source: {__name__}"
            }
