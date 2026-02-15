# Project Title: `CheckMe`

**Devices and Tools:**

**1. In Production:**
- Raspi 4GB 4B model
- Keypad 3x4
- LCD I2C 2x16

**In Development:**
- Raspi 4GB 4B model
- RealVNC
- Raspi Terminal

**Dictionary:**

- **Answer Sheets** - the paper where the answer of the students can be found
- **Answer Key** - the paper where the ground truth for answer sheets, so hallucination can be avoid


**DIR Structure:**
```bash
  raspi_code/
  │
  ├── scans/                      # Scanner output directory
  │   ├── tests/                   # For testing scans only
  │   ├── answer_keys/
  │   └── answer_sheets/
  │
  ├── services/                   # Core service modules
  │   ├── __init__.py             # Package initializer
  │   ├── logger.py
  │   ├── keypad.py
  │   ├── lcd.py
  │   ├── pair_device.py
  │   ├── internet_checker.py
  │   ├── scanner.py              # Scanner control
  │   ├── encoder.py              # Base64 conversion
  │   ├── gemini_client.py        # Gemini API interface
  │   └── firebase_client.py      # Firebase operations
  │
  ├── config/                             # Configuration files
  │   ├── .env                            # ⚠️ Dont commit
  │   ├── .env.example                    # Environment variables
  │   ├── serviceAccountKey.json          # ⚠️ Dont commit
  │   └── serviceAccountKey.json.example  # Firebase credentials
  │
  ├── logs/                       # Application logs
  │   ├── error.log
  │   ├── info.log
  │   ├── warning.log
  │   └── debug.log               # Where I can see the logs during debugging
  │
  ├── main.py                     # Main pipeline orchestrator
  ├── requirements.txt            # Python dependencies
  ├── .gitignore                  # Git exclusion rules
  └── README.md                   # Project overview
```

---

## SPRINT 1: AUTHENTICATION AND PAIRING DEVICE



In Development Pipeline:

1. Teacher will write the sheets and answer key. 

2. Teacher will gathered all the sheets once the students done answering it. 

3. Teacher will now use the system thru terminal console: python main.py (raspi desktop with custom python-script). 

4. System will ask for the specific task by Displaying like in the following via terminal console:

The console will shows choices for options:

Options:
1. Scan new answer key
2. Check answer sheets
3. Shutdown

Definition:





If the teacher pick up the 1. Scan new answer key, this means the system will create and store new data for answer key in RTDB



If teacher will pick up the 2. Check answer sheets, this means the system will give the list of the existing answer keys (List of titles of Answer Keys).  The teacher will must pick one choice before proceeding in checking pipeline. 



If RTDB does not consist any answer keys yet, then it will warns the teacher about it and will tell the teacher to go to Option 1 first.



Shutdown meaning turn of the raspi.



Further explanation for 1 and 2 will be discuss later.



Scene 1: Teacher chose the option 1 Scan new answer key





Teacher pick the option 1



Then system will show this:

Press 1 to scan  
Press 2 to exit





IF teacher press 1 THEN





System trigger the L3210 Epson to scan the answer key to image PNG



System will 





System will trigger to scan when teacher type the 1



Then, 





System will ask the teacher, via terminal console, about:





The number of the pages per of the sheet - because sometimes, sheets can be one or many pages in real-life. It's very accurate if we manually this.









