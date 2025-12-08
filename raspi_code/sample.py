import os
import json

full_path = "raspi_code/answer_sheets"
with open(full_path, 'w') as f:
      json.dump({"hello": "lawrence roble"}, f, indent=2, ensure_ascii=False)