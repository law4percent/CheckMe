answer_key = {
    "Q1": "A",
    "Q2": "B",
    "Q3": "C",
    "Q4": "a",
    "Q5": "D",
    }


answer_sheet = {
    "Q1": "A",
    "Q2": "D",
    "Q3": "D ",
    "Q4": "a",
    "Q5": " D",
    }

for n in range(1, 5+1):
    # if f"Q{n}" not in answer_sheet["answers"]:
    #     print("missing")
    # else:
    #     print(f"Q{n}")
    
    if answer_sheet.get(f"Q{n}").strip() != answer_key.get(f"Q{n}"):
        print(f"{n}. X")
    else:
        print(f"{n}. /")