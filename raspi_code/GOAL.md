## **Overview Goal**

```bash
        1. Load all images
        2. Pre-resize each input image to a standard size
        3. Try different grid layouts:
        - 1×N (horizontal)
        - 2×2
        - 3×3
        - 4×4
        4. For each layout:
        a. Build a grid preview
        b. Compute per-image resolution
        c. If width < 300px → reject layout
        5. Choose the best grid (largest pages → highest accuracy)
        6. Compress final grid until size < target (ex. 1.5 MB)
        7. Convert to base64 → ready for Gemini API

```


***Teacher procedure towards the system (Answer Key Procedure)***
```bash
        1. Turn on the system
        2. The system will ask the user about the number of pages 
        3. The system will ask the user if there is an essay.
        4. Scan/Capture the answer key. (One-by-One) [Put the first page, second page, …, n page]
        5. If the number of pages is greater than 1 THEN
        6. Combine all the images (Applying the combination algorithm)
        7. The system will save the combined images
        8. The system will send the image to Gemini with a prompt (make sure to include in the prompt if there is an essay in the sheet, because if there is, we will apply another algorithm)


        Solution 1: Combine all the images into one (Just like iLovePDF)
        The system will ask the user about the number of pages
        If the number of pages is greater than 1 THEN
        Combine all the images
        Convert the combined images into base64
        Send the base64 to Gemini with the prompt (You are the converter that will analyze the answer key, then convert it into JSON Format)
        Get the JSON Format

        Solution 2: Adding a page number in the sheet
        {
        “Student_name”: “LAWRENCE ROBLE”,
        “Student_id”: “4201400”,

        “Q1”: “A”,
        “Q2”: “D”,
        .
        .
        .
        “Qn”: “C”,

        “Page”: 1
        }
```


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

```bash
        Procedure A
        1. Capture image
        2. Send image to Gen AI
        3. Tell procedure B about fetching data for the image by sharing the image ID. The ID will be saved to the local database
        4. Repeat from step 1 to capture a new image

        Procedure B
        1. Wait for procedure A to provide the image ID in the local database
        2. If there is an ID in the local database, then get the image DATA via the ID
        3. If step 2 is true, then send the image data to Gen AI
        4. Wait to fetch JSON data from Gen AI
        5. Tell procedure C about fetching data for the image via image ID. The image will be saved to the local database
        6. Repeat from step 1

        Procedure C
        1. Wait for procedure C to provide the image ID in the local database
        2. If there is an ID in the local database, then get the image DATA via the ID
        3. If step 2 is True, then fetch JSON data from Gen AI
        4. then send the JSON data to RTDB so app can use it
        5. Repeat step 1
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