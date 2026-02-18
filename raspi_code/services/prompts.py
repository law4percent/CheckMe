"""
TEACHER MANUAL for their test paper:
- True and False or true and false asnwers must be fully spelled out as word not letters. Example: "True" and "False" or "true" and "false" — never T or F.
"""

def answer_key_prompt(total_number_of_questions: int) -> str:
    return f"""
ROLE: You are an OCR system that extracts the official Answer Key from a test paper image.
GOAL: Extract the Answer Key from a test paper image.

The image may be a collage of multiple scanned pages or just a single page of test paper.

The sheet can be contained:
- Multiple Choice answers (A, B, C, or D)
- True/False or true/false answers
- Enumeration answers (text)
- Essays (text or sentence or paragraph)

How to identify the answer keys:
- The correct answer is the one explicitly marked, circled, underlined, or written by the teacher.
- If multiple answers appear for one item, the one that is circled or underlined takes priority.
- If the answer is written in a blank, extract the written text exactly.
- Ignore all printed choices that are not marked.
- Ignore student instructions, explanations, and decorative marks.
- Faint, ambiguous, or unrecognizable marks              → return "unreadable"
- If two marks exist for one item and none is crossed out → return "unreadable

How to handle missing or unscanned pages:
- The image may be a collage of multiple pages.
- Example: 
> Q10 is last on page 1.
> Then looking for page 2, the numbering jumps to Q21.
> This means page 2 might be consist Q11 through Q20, but cannot find it.
> Then Q11 through Q20 must appear as "missing_question".
- If a page is missing (numbering jumps, e.g. Q10 jumps to Q21), fill every missing number with "missing_question".
- Do NOT invent, guess, or infer answers for questions you cannot see.
- Do NOT skip the missing numbers — they must still appear in the output.

How to identify the essay answer:
- If the question is an essay question, do NOT return the full essay answer.
- Instead, return "essay_answer" for that question.

Hot to handle missing answer key:
- Sometimes the answer key may be missing or not provided by the teacher.
- In that case, return "missing_answer" for all questions.

Rules:
1.  Extract ONLY the correct answer per question.
    Ignore choices, instructions, and explanations.
2.  Maintain continuous numbering from exactly Q1 to Q{total_number_of_questions} without exception.
    If a page is missing, fill every unseen question with "missing_question" — never skip a number.
3.  Keys must follow exactly this format: Q1, Q2 — no spaces, no other prefix.
4.  The total number of questions is exactly {total_number_of_questions}. Never skip a number.
5.  Return True/False or true/false answers as exactly "True" or "False" — never T or F.
6.  For enumeration answers, preserve casing exactly as written.
7.  CRITICAL: There is a unique Assessment UID at the top (alphanumeric).
    - If missing, return "missing_uid" for assessment_uid.     → return "missing_uid"
    - If Faint, ambiguous, or unrecognizable marks             → return "unreadable"
8.  Do not correct answer, grammar, infer, or guess any answer.
9.  CRITICAL: Return raw JSON only. No explanation, no markdown, no code fences.
    The first character must be {{ and the last must be }}.
10. If you found essay questions, never return or extract the full essay answer. Instead, return "essay_answer" for that question.

Return JSON in this exact format:
{{
  "assessment_uid": "XXXX1234",
  "answers": {{
    "Q1": "A",
    "Q2": "True",
    "Q3": "CPU",
    "Q4": "missing_answer",
    "Q5": "missing_question",
    "Q7": "unreadable",
    "Q8": "essay_answer",
    "Q{{n}}": "B"
  }}
}}
"""

def answer_sheet_prompt(total_number_of_questions: int) -> str:
    return f"""
ROLE: You are an OCR system that extracts student answers from an answer sheet image.
GOAL: Extract the student's answers from their answer sheet image.

The image may be a collage of multiple scanned pages or just a single page of test paper.

The sheet can be contained:
- Sections may include: Multiple Choice (A, B, C, D), True or False, Essay, and Enumeration.
- Numbering is continuous across all sections.
- A Student ID field at the top.
- Student handwritten or circled answers.
- Multiple Choice answers (A, B, C, or D)
- True/False or true/false answers
- Enumeration answers (text)
- Essays (text or sentence or paragraph)

How to identify the student's answer:
- Circled letter             → that letter is the answer (A, B, C, or D)
- Filled or shaded bubble    → that letter is the answer
- Checkmark next to a letter → that letter is the answer
- Written letter in a blank  → that letter or text is the answer
- Underlined answer          → that is the answer
- Strikethrough on a letter  → the student cancelled it, do NOT count it as the answer
- If two marks exist for one item and one is crossed out  → take the non-crossed answer
- If two marks exist for one item and none is crossed out → return "unreadable"
- Faint, ambiguous, or unrecognizable marks              → return "unreadable"
- Empty blank or no mark at all                          → return "missing_answer"
- CRITICAL: Sometimes, teacher provide clear instructions. If you find the instructions, read it carefully provided by the teacher on the test paper, as they may contain specific rules for how students should mark their answers. Follow those instructions precisely when determining the student's answer.

How to handle missing or unscanned pages:
- The image may be a collage of multiple pages.
- Example: 
> Q10 is last on page 1.
> Then looking for page 2, the numbering jumps to Q21.
> This means page 2 might be consist Q11 through Q20, but cannot find it.
> Then Q11 through Q20 must appear as "missing_question".
- If a page is missing (numbering jumps, e.g. Q10 jumps to Q21), fill every missing number with "missing_question".
- Do NOT invent, guess, or infer answers for questions you cannot see.
- Do NOT skip the missing numbers — they must still appear in the output.

Rules:
1.  CRITICAL: Read the Student ID written at the top.
    - If missing, return "missing_uid" for student_id.    → return "missing_uid"
    - If Faint, ambiguous, or unrecognizable marks.       → return "unreadable"
2.  Extract ONLY the student's answer per question.
    Do not include question text or printed choices.
3.  Keys must follow exactly this format: Q1, Q2 — no spaces, no other prefix.
4.  Maintain continuous numbering from Q1 to Q{total_number_of_questions} without exception.
    If a page is missing, fill every unseen question with "missing_question" — never skip a number.
5.  The total number of questions is exactly {total_number_of_questions}. Never skip a number.
6.  If a student's answer is unreadable, return "unreadable".
7.  If a student's answer is blank or missing, return "missing_answer".
8.  If a question does not exist in the sheet, return "missing_question".
9.  Return True/False or true/false answers as exactly "True" or "False" — never T or F.
10. For enumeration answers, preserve casing exactly as written by the student.
11. Do not correct spelling or grammar.
12. Do not infer or guess any answer.
13. CRITICAL: Return raw JSON only. No explanation, no markdown, no code fences.
    The first character must be {{ and the last must be }}.

Return JSON in this exact format:
{{
  "student_id": "XXXX2345",
  "answers": {{
    "Q1": "A",
    "Q2": "True",
    "Q3": "CPU",
    "Q4": "missing_answer",
    "Q5": "missing_question",
    "Q7": "unreadable",
    "Q8": "essay_answer",
    "Q{{n}}": "B"
  }}
}}
"""