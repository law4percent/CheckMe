**Recommend Directory Structure**

```
raspi_code/
├─ logs/
├─ README.md
├─ GOAL.md
├─ .env
├─ test/
├─ main.py                     
├─ venv/                       
└─ lib/
   ├─ services/
   |  ├─ firebase_rtdb.py
   |  ├─ handle_pairing.py
   |  └─ handle_hardware.py
   └─ processes/
      ├─ process_a.py
      ├─ process_b.py
      └─ process_c.py
```