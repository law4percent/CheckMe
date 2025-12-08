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
from typing import Dict, Optional
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
4. Keep continuous numbering: 1, 2, 3...N Exacltly as in the test.
5. If unreadable, return `"unreadable"`
6. At the top, there is a unique Assessment UID code (alphanumeric).

Return JSON EXACTLY like this:
{
  "assessment_uid": "XXXX1234",
  "answers": {
    "question_1": "A",
    "question_2": "CPU",
    "question_3": "unreadable",
    ...
    question_N": "no_answer",
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

    def extract_answer_key(self, image_path: str) -> Dict:
        """Extract teacher's answer key from image."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")

        image_base64 = self._encode_image(image_path)

        if GENAI_AVAILABLE and self.model:
            response_text = self._call_gemini_sdk(image_base64, self.TEACHER_INSTRUCTION)
        else:
            response_text = self._call_gemini_rest(image_base64, self.TEACHER_INSTRUCTION)

        return self._safe_parse_json(response_text)

    # ============================================================
    # STUDENT ANSWER EXTRACTION
    # ============================================================

    def extract_answer_sheet(self, image_path: str, total_number_of_questions: int) -> Dict:
        """Extract student answers from answer sheet image."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")

        image_base64 = self._encode_image(image_path)

        STUDENT_INSTRUCTION = self._format_answer_sheet_prompt(total_number_of_questions)

        if GENAI_AVAILABLE and self.model:
            response_text = self._call_gemini_sdk(image_base64, STUDENT_INSTRUCTION)
        else:
            response_text = self._call_gemini_rest(image_base64, STUDENT_INSTRUCTION)

        return self._safe_parse_json(response_text)

    # ============================================================
    # GRADING LOGIC
    # ============================================================

    def grade_student_sheet(
        self,
        student_answers: Dict,
        answer_key: Dict,
        treat_essay_as_partial: bool = True
    ) -> Dict:
        """
        Compare student answers against answer key.
        
        Args:
            student_answers: Extracted student answers dict
            answer_key: Teacher's answer key dict
            treat_essay_as_partial: If True, mark essays as partial (⚠️)
        
        Returns:
            Graded results with scores
        """

        student_id = student_answers.get("student_id", "UNKNOWN")
        student_ans = student_answers.get("answers", {})
        key_ans = answer_key.get("answers", {})

        graded = {}
        correct = 0
        partial = 0
        incorrect = 0

        # Determine if there's an essay question
        has_essay = key_ans.get("essay") == "True"

        # Get max question number
        max_q_num = 0
        for key in list(student_ans.keys()) + list(key_ans.keys()):
            if key.startswith("question_"):
                try:
                    num = int(key.replace("question_", ""))
                    max_q_num = max(max_q_num, num)
                except ValueError:
                    pass

        # Grade each question
        for i in range(1, max_q_num + 1):
            q_key = f"question_{i}"
            student_ans_val = student_ans.get(q_key, "NO_ANSWER")
            key_ans_val = key_ans.get(q_key)

            # Handle essay/partial scoring (last question)
            if i == max_q_num and has_essay and treat_essay_as_partial:
                if student_ans_val == "NO_ANSWER":
                    graded[q_key] = "❌"
                    incorrect += 1
                else:
                    graded[q_key] = "⚠️"  # Partial - teacher will score
                    partial += 1
            else:
                # Standard grading
                if student_ans_val == "NO_ANSWER":
                    graded[q_key] = "❌"
                    incorrect += 1
                elif self._normalize_answer(student_ans_val) == self._normalize_answer(key_ans_val):
                    graded[q_key] = "✅"
                    correct += 1
                else:
                    graded[q_key] = "❌"
                    incorrect += 1

        # Calculate score
        total_questions = correct + partial + incorrect
        percentage = (correct / (total_questions - partial) * 100) if (total_questions - partial) > 0 else 0

        return {
            "student_id": student_id,
            "assessment_uid": answer_key.get("assessment_uid", "UNKNOWN"),
            "graded_answers": graded,
            "summary": {
                "correct": correct,
                "partial": partial,
                "incorrect": incorrect,
                "total": total_questions,
                "scorable_total": total_questions - partial,
                "percentage": round(percentage, 2)
            },
            "has_essay": has_essay
        }

    def complete_grading_pipeline(
        self,
        student_sheet_path: str,
        answer_key_path: str
    ) -> Dict:
        """
        Complete pipeline: Extract key, extract student answers, and grade.
        
        Args:
            student_sheet_path: Path to student answer sheet image
            answer_key_path: Path to answer key image
        
        Returns:
            Complete grading result
        """
        # Extract answer key
        logger.info(f"Extracting answer key from {answer_key_path}")
        answer_key = self.extract_answer_key(answer_key_path)

        # Extract student answers
        logger.info(f"Extracting student answers from {student_sheet_path}")
        student_answers = self.extract_student_answers(student_sheet_path)

        # Grade
        logger.info(f"Grading student {student_answers.get('student_id', 'UNKNOWN')}")
        graded_result = self.grade_student_sheet(student_answers, answer_key)

        return graded_result

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _format_answer_sheet_prompt(total_number_of_questions: int) -> str:
        
        STUDENT_INSTRUCTION_init_1 = f"""
You are an OCR system that extracts answers from an answer sheet image.

The sheet contains:
- A Student ID field at the top.
- Student’s handwritten or circled answers.
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
9. If the number of questions is not exactly {total_number_of_questions}:
    You MUST still produce questions up to {total_number_of_questions}, and return JSON in this exact format:
"""
        STUDENT_INSTRUCTION_init_2 = """
       {
           "student_id": "XXXX2345",
           "answers": {
               "question_1": "A",
               "question_2": "no_answer",
               "question_3": "unreadable",
               ...
               "question_12": "no_answer",  <-- missing: mark as no_answer
               "question_13": "no_answer",  <-- missing: mark as no_answer
               ...
               "question_30": "B",
               "question_31": "D",
               "question_32": "C",
               ...
               "question_N": "CPU"
           }
       }

   ELSE (when the number of questions matches exactly):
       Return JSON in this exact format:

       {
           "student_id": "XXXX2345",
           "answers": {
               "question_1": "A",
               "question_2": "no_answer",
               "question_3": "unreadable",
               ...
               "question_N": "CPU"
           }
       }
"""
        return STUDENT_INSTRUCTION_init_1 + STUDENT_INSTRUCTION_init_2

    def _encode_image(self, path: str) -> str:
        """Encode image to base64."""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_gemini_sdk(self, image_b64: str, instruction: str) -> str:
        """Call Gemini API using SDK with retry logic."""
        contents = [
            instruction,
            {
                "mime_type": "image/jpeg",
                "data": image_b64
            }
        ]

        for attempt in range(3):
            try:
                response = self.model.generate_content(
                    contents=contents,
                    generation_config={"temperature": 0.2}
                )

                if not response.text.strip():
                    raise ValueError("Empty response from Gemini")

                return response.text

            except Exception as e:
                logger.error(f"Gemini SDK error (attempt {attempt+1}/3): {e}")

                if "429" in str(e).lower():
                    wait = 8 + random.randint(2, 10)
                    logger.warning(f"Rate limit hit. Waiting {wait}s")
                    time.sleep(wait)
                    continue

                time.sleep(2)

        return '{"error": "Gemini SDK failed after retries"}'

    def _call_gemini_rest(self, image_b64: str, instruction: str) -> str:
        """Call Gemini API using REST endpoint."""
        # Use v1 stable endpoint instead of v1beta
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

        for attempt in range(3):
            try:
                response = requests.post(
                    url, 
                    params={"key": self.api_key},
                    json=payload, 
                    headers=headers, 
                    timeout=30
                )

                response.raise_for_status()

                try:
                    return response.json()["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Bad REST response format: {e}")
                    return json.dumps({"error": "Bad REST response format"})
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"REST API error (attempt {attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(2 + random.randint(1, 3))
                    continue
                return json.dumps({"error": f"REST API failed: {str(e)}"})

    @staticmethod
    def _normalize_answer(answer: str) -> str:
        """Normalize answer for comparison (case-insensitive, stripped)."""
        if answer is None:
            return ""
        return answer.strip().upper()

    @staticmethod
    def _safe_parse_json(text: str) -> Dict:
        """Safely parse JSON response from Gemini."""
        try:
            cleaned = text.strip("```json").strip("```").strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {"error": "JSON parsing failed", "raw_response": text[:200]}
