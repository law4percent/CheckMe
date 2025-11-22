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


## **Phase 1: Answer Key Process**

| **Step** | **Action** | **Critical Improvement** |
| --- | --- | --- |
| 1 | **Capture Image** | Capture a high-resolution image of the master answer sheet. |
| 2 | **Prepare Payload** | Base64 encode the image. Define the systemInstruction and the responseSchema. |
| 3 | **Define System Instruction** | "Set the model's persona: ""You are an OMR grading expert. Your task is to identify the single, clearest marked bubble for each question and return only the results as a JSON object.""" |
| 4 | **Define JSON Schema** | "This is mandatory for predictable output. The schema must specify the exact keys (question numbers) and value types (e.g., 0 for A, 1 for B)." |
| 5 | **Call Gemini API** | "Send the payload (Image, System Instruction, Schema, and text prompt) to the generateContent endpoint. Implement exponential backoff for reliability." |
| 6 | **Save JSON** | Parse the response text as JSON and save the Answer Key object. |


## **Phase 2: Checking the Answer Sheet**

| **Step** | **Action** | **Critical Improvement** |
| --- | --- | --- |
| 1 | **Capture Image** | Capture a high-resolution image of the student's sheet. |
| 2 | **Prepare Payload** | Base64 encode the image. Use the exact same systemInstruction and responseSchema as the Answer Key process. |
| 3 | **Call Gemini API** | Send the payload. Implement exponential backoff. |
| 4 | **Get Student JSON** | Parse the response text to get the Student Answer JSON. |
| 5 | **Compare and Score** | "Load the saved Answer Key JSON. Iterate through the keys (questions) in both JSON objects, compare the marked options, and calculate the final score and grade." |