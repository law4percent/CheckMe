import json
import re
from .logger import get_log_file

log = get_log_file("sanitizer.py")

def sanitize_gemini_json(raw: str) -> dict:
    """
    Cleans a Gemini response string and parses it into a dict.
    Handles markdown code fences, leading/trailing whitespace,
    and normalizes answer values.
    """

    # Step 1: Strip markdown code fences if present
    # Gemini often wraps JSON in ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.replace("```", "").strip()

    # Step 2: Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        log(f"\nFailed to parse Gemini response as JSON: {e}\nRaw:\n{cleaned}", type="error")
        raise ValueError(f"Failed to parse Gemini response as JSON: {e}\nRaw:\n{cleaned}")

    # Step 3: Normalize answer values
    # Uppercase all single-letter MC answers (a → A)
    # Uppercase True/False answers
    # Lowercase special sentinels
    if "answers" in data:
        normalized = {}
        for key, value in data["answers"].items():
            if isinstance(value, str):
                stripped = value.strip()

                # Normalize MC answers: single letter
                if len(stripped) == 1 and stripped.isalpha():
                    stripped = stripped.upper()

                # Normalize True/False — decide: "True" or "TRUE"?
                elif stripped.lower() in ("true", "t"):
                    stripped = "TRUE"
                elif stripped.lower() in ("false", "f"):
                    stripped = "FALSE"

                # Normalize sentinels
                elif stripped.lower() == "unreadable":
                    stripped = "unreadable"
                elif stripped.lower() == "missing_uid":
                    stripped = "missing_uid"
                elif stripped.lower() == "missing_answer":
                    stripped = "missing_answer"
                elif stripped.lower() == "missing_question":
                    stripped = "missing_question"
                elif stripped.lower() == "essay_answer":
                    stripped = "essay_answer"

                normalized[key] = stripped
            else:
                normalized[key] = value

        data["answers"] = normalized

    return data


if __name__ == "__main__":
    from .gemini_client import gemini_with_retry
    from .utils import save_to_json

    API_KEY    = "YOUR_API_KEY"
    MODEL      = "gemini-2.5-flash"

    TOTAL_QUESTIONS = 39

    PROMPT_1 = """..."""  # Your answer key prompt
    PROMPT_2 = """..."""  # Your student sheet prompt


    # --- Answer Key (PROMPT_1) ---
    answer_key_image = "answer_key.jpg"

    raw = gemini_with_retry(
        api_key    = API_KEY,
        image_path = answer_key_image,
        prompt     = PROMPT_1,
        model      = MODEL
    )

    if raw:
        data = sanitize_gemini_json(raw)
        save_to_json(data, "answer_key.json")
        print(f"Assessment UID : {data.get('assessment_uid')}")
        print(f"Total answers  : {len(data.get('answers', {}))}")
    else:
        print("Failed to extract answer key.")


    # --- Student Sheet (PROMPT_2) ---
    student_image = "student_001.jpg"

    # Fill in the placeholder before sending
    prompt_2_filled = PROMPT_2.format(total_number_of_questions=TOTAL_QUESTIONS)

    raw = gemini_with_retry(
        api_key    = API_KEY,
        image_path = student_image,
        prompt     = prompt_2_filled,
        model      = MODEL
    )

    if raw:
        data = sanitize_gemini_json(raw)
        save_to_json(data, f"{data.get('student_id', 'unknown')}.json")
        print(f"Student ID    : {data.get('student_id')}")
        print(f"Total answers : {len(data.get('answers', {}))}")
    else:
        print("Failed to extract student sheet.")