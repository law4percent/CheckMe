## **Overview Goal**

```
[User scans Answer Key] 
        ↓
[Raspberry Pi captures image → converts to Base64] 
        ↓
[Send Base64 + system instruction → Gemini AI] 
        ↓
[Gemini AI returns JSON answer key] 
        ↓
[User scans Student Answer Sheet → convert to Base64] 
        ↓
[Send to Gemini AI → returns JSON student answers] 
        ↓
[Compare student answers JSON vs answer key JSON → generate score/result]
```


## **Two separate AI instructions**

```bash
AI_INSTRUCTION_for_answer_key = """
You are an OCR system that extracts the official Answer Key from a test paper image.

The image contains ONLY the teacher’s answer key. There are NO student answers and NO student ID.

The test may contain multiple sections:
- Section Number: Multiple Choice – Circle the right answer (A, B, C, D)
- Section Number: True or False – Fill in the blank (T or F)
- Section Number: Multiple Choice – Fill in the blank (A, B, C, D)
- Section Number: Enumeration – Fill in the blank (text answers)

Important Rules:
1. Ignore instructions intended for students.
2. Ignore explanations or question choices.
3. Extract ONLY the official correct answer for each question.
4. Follow continuous numbering across sections (1, 2, 3, …).

Return JSON in this exact format:

{
  "paper_type": "answer_key"
  "answers": {
    "question_1": "A",
    "question_2": "C",
    "question_3": "True",
    "question_4": "CPU",
    ...
  }
}

If an answer cannot be read, return:
"unreadable"
"""
```

``` bash
AI_INSTRUCTION_for_answer_sheet = """
You are an OCR system that extracts student answers from their answer sheet.

The sheet contains:
- A Student ID field at the top.
- Student's handwritten or circled answers.
- Multiple possible sections:
    - Section Number: Multiple Choice – Circle the right answer (A, B, C, D)
    - Section Number: True or False – Fill in the blank (T or F)
    - Section Number: Multiple Choice – Fill in the blank (A, B, C, D)
    - Section Number: Enumeration – Fill in the blank (text answers)

Important Rules:
1. READ the Student ID written at the top.
2. Detect whether each answer is circled or written.
3. For enumerations, extract the text exactly as written.
4. Follow continuous numbering across sections (1, 2, 3, …).
5. DO NOT include explanations or the question text.
6. Only extract the student's answer.

Return JSON in this exact format:

{
  "student_id": "202512345",
  "answers": {
    "question_1": "B",
    "question_2": "C",
    "question_3": "True",
    "question_4": "CPU",
    ...
  }
}

If a student’s answer is unreadable or blank, return:
"unreadable"

"""
```

## Phases
### **Phase 1: Answer Key Process**

| **Step** | **Action** | **Critical Improvement** |
| --- | --- | --- |
| 1 | **Capture Image** | Capture a high-resolution image of the master answer sheet. |
| 2 | **Prepare Payload** | Base64 encode the image. Define the systemInstruction and the responseSchema. |
| 3 | **Define System Instruction** | "Set the model's persona: ""You are an OMR grading expert. Your task is to identify the single, clearest marked bubble for each question and return only the results as a JSON object.""" |
| 4 | **Define JSON Schema** | "This is mandatory for predictable output. The schema must specify the exact keys (question numbers) and value types (e.g., 0 for A, 1 for B)." |
| 5 | **Call Gemini API** | "Send the payload (Image, System Instruction, Schema, and text prompt) to the generateContent endpoint. Implement exponential backoff for reliability." |
| 6 | **Save JSON** | Parse the response text as JSON and save the Answer Key object. |


### **Phase 2: Checking the Answer Sheet**

| **Step** | **Action** | **Critical Improvement** |
| --- | --- | --- |
| 1 | **Capture Image** | Capture a high-resolution image of the student's sheet. |
| 2 | **Prepare Payload** | Base64 encode the image. Use the exact same systemInstruction and responseSchema as the Answer Key process. |
| 3 | **Call Gemini API** | Send the payload. Implement exponential backoff. |
| 4 | **Get Student JSON** | Parse the response text to get the Student Answer JSON. |
| 5 | **Compare and Score** | "Load the saved Answer Key JSON. Iterate through the keys (questions) in both JSON objects, compare the marked options, and calculate the final score and grade." |