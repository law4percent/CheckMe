# Epson L3210 Scanner Control with Raspberry Pi

## 🎯 Overview

This guide provides complete instructions for controlling an Epson L3210 scanner using a Raspberry Pi. You'll be able to:

- ✅ Trigger scans manually via command line or Python
- ✅ Save scans as PNG files to custom directories
- ✅ Control resolution and scan modes
- ✅ Use hardware button triggers
- ✅ Automate scanning workflows with Python scripts

---

## 🧰 Requirements

### Hardware
- Raspberry Pi (models 3, 4, or 5 recommended)
- Epson L3210 scanner (connected via USB)

### Software
- Raspberry Pi OS (64-bit recommended)
- SANE scanner utilities
- Python 3 (pre-installed on Raspberry Pi OS)

---

## 📦 Installation

### Step 1: Update System

First, ensure your Raspberry Pi is up to date:

```bash
sudo apt update
sudo apt upgrade -y
```

### Step 2: Install SANE Scanner Utilities

SANE (Scanner Access Now Easy) provides the driver interface for your scanner:

```bash
sudo apt install sane-utils -y
```

---

## 🔎 Scanner Detection & Verification

### Verify USB Connection

Check if the scanner is detected via USB:

```bash
lsusb
```

**Expected output includes:**
```
Seiko Epson Corp. L3210 Series
```

### Verify SANE Detection

Check if SANE can communicate with your scanner:

```bash
scanimage -L
```

**Expected output:**
```
device `epson2:libusb:001:004' is a Epson PID 1188 flatbed scanner
```

✅ If you see this output, your scanner is ready to use!

---

## 📁 Setup Scan Directory

Create a dedicated directory for storing scans:

```bash
mkdir -p ~/Desktop/l3210_test/scans
```

---

## 🧪 Basic Scan Test (Command Line)

### Perform a Test Scan

Run this command to verify everything works:

```bash
scanimage --format=png --resolution 300 > ~/Desktop/l3210_test/scans/test.png
```

### Command Breakdown

| Parameter | Meaning |
|-----------|---------|
| `--format=png` | Output file format (PNG for lossless quality) |
| `--resolution 300` | Scan resolution in DPI (dots per inch) |
| `>` | Redirects output to file |
| `test.png` | Output filename |

### Verify the Scan

Check that the file was created:

```bash
ls ~/Desktop/l3210_test/scans
```

You should see: `test.png`

---

## 🐍 Python Automation

### Create the Scan Script

Create a new Python file:

```bash
nano scan.py
```

### Script Contents

Copy and paste this code:

```python
import subprocess
import os
from datetime import datetime

# ===== CONFIGURATION =====
SAVE_DIRECTORY = "/home/checkme2025/Desktop/l3210_test/scans"
RESOLUTION = 300
MODE = "Color"  # Options: Lineart, Gray, Color
# ==========================

# Ensure directory exists
os.makedirs(SAVE_DIRECTORY, exist_ok=True)

# Create timestamped filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"scan_{timestamp}.png"
filepath = os.path.join(SAVE_DIRECTORY, filename)

# Build scan command
command = [
    "scanimage",
    "--format=png",
    f"--resolution={RESOLUTION}",
    f"--mode={MODE}"
]

print("Starting scan...")
with open(filepath, "wb") as file:
    subprocess.run(command, stdout=file)

print(f"✅ Scan completed. File saved at:\n{filepath}")
```

### Save the File

Press:
1. `CTRL + X`
2. `Y` (to confirm)
3. `ENTER`

### Run the Script

```bash
python3 scan.py
```

**Expected output:**
```
Starting scan...
✅ Scan completed. File saved at:
/home/checkme2025/Desktop/l3210_test/scans/scan_20260214_142233.png
```

---

## ⚙️ Scan Modes & Settings

### Available Scan Modes

The Epson L3210 supports three scan modes:

| Mode | Description | Use Case | File Size |
|------|-------------|----------|-----------|
| `Lineart` | Black & White (1-bit) | Text documents, OCR | Smallest |
| `Gray` | Grayscale (8-bit) | Documents with shading | Medium |
| `Color` | Full RGB color | Photos, colored forms | Largest |

### Mode Examples

**Black & White (Lineart):**
```bash
scanimage --mode Lineart --resolution 300 --format=png > bw.png
```

**Grayscale:**
```bash
scanimage --mode Gray --resolution 300 --format=png > gray.png
```

**Color:**
```bash
scanimage --mode Color --resolution 300 --format=png > color.png
```

---

## 🎚️ Advanced Controls

### Resolution Settings

| Resolution | Quality | Speed | Recommended For |
|------------|---------|-------|-----------------|
| 150 DPI | Low | Fast | Quick previews |
| 300 DPI | Medium | ⭐ Balanced | Most documents |
| 600 DPI | High | Slow | OCR, detailed text |
| 1200 DPI | Very High | Very Slow | Professional archiving |

⚠️ **Warning:** 1200 DPI is very slow on Raspberry Pi. Use only when necessary.

### Threshold Control (Lineart Mode Only)

Adjust the black/white threshold for Lineart scans:

```bash
scanimage --mode Lineart --threshold 150 --resolution 300 --format=png > bw_adjusted.png
```

- **Higher threshold (e.g., 200):** More white, lighter scan
- **Lower threshold (e.g., 100):** More black, darker scan
- **Default:** 128

---

## 🔘 Hardware Button Trigger

Your scanner supports physical button triggering:

```bash
scanimage --wait-for-button=yes --mode Gray --resolution 300 --format=png > button_scan.png
```

This command will:
1. Wait for you to press the scan button on the L3210
2. Automatically start scanning when pressed
3. Save the result to `button_scan.png`

---

## 📊 Recommended Settings by Use Case

| Use Case | Mode | Resolution | Notes |
|----------|------|------------|-------|
| Plain text documents | Lineart | 300 DPI | Small file size, sharp text |
| OCR pipeline | Lineart | 600 DPI | Better character recognition |
| Documents with stamps/signatures | Gray | 300 DPI | Preserves detail and shading |
| Colored forms/certificates | Color | 300 DPI | Full color fidelity |
| Photo archiving | Color | 600 DPI | High quality preservation |

---

## 🔄 System Workflow

```
Raspberry Pi
     ↓
Python Script / Command Line
     ↓
scanimage command
     ↓
SANE driver (epson2)
     ↓
Epson L3210 scanner
     ↓
PNG file saved to directory
```

---

## ✅ Success Checklist

Before considering your setup complete, verify:

- [ ] `lsusb` detects Epson device
- [ ] `scanimage -L` lists the scanner
- [ ] Terminal scan command works
- [ ] Python script executes successfully
- [ ] PNG files are saved to the correct directory
- [ ] Different scan modes produce expected results

---

## 🏆 System Status Overview

| Component | Status |
|-----------|--------|
| USB Connection | ✅ |
| SANE Driver | ✅ |
| Mode Control | ✅ |
| Threshold Control | ✅ |
| Button Trigger | ✅ |
| Resolution Control | ✅ |
| Python Automation | ✅ |

---

## 🐛 Troubleshooting

### Scanner Not Detected

If `scanimage -L` shows no devices:

1. Check USB cable connection
2. Try a different USB port
3. Restart the scanner
4. Reboot Raspberry Pi

### Permission Denied Errors

Add your user to the scanner group:

```bash
sudo usermod -a -G scanner $USER
```

Then log out and log back in.

### Slow Scanning

- Reduce resolution (use 300 DPI instead of 600+)
- Use Lineart mode instead of Color
- Consider overclocking your Raspberry Pi (advanced)

---

## 📝 Notes

- **File Format:** PNG is recommended for lossless quality
- **Directory Path:** Update the `SAVE_DIRECTORY` variable in the Python script to match your username
- **Automation:** You can schedule scans using `cron` or trigger via GPIO buttons
- **Remote Access:** Works over SSH for headless operation

---

## 🎓 Next Steps

Now that you have basic scanning working, you can:

1. Create automated scanning workflows
2. Implement OCR with Tesseract
3. Set up network scanning via web interface
4. Build a document management system
5. Trigger scans with GPIO buttons or web APIs

Happy scanning! 🖨️✨