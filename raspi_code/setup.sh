#!/bin/bash
# setup.sh - FULL Production Setup for CheckMe
# Optimized for Raspberry Pi OS 13 (Bookworm / Trixie)

set -e

echo "========================================="
echo "        CHECKME FULL RPI SETUP"
echo "========================================="

# -----------------------------
# 0. INTERNET CHECK
# -----------------------------
echo "=== 0. Checking Internet ==="
if ping -c 2 8.8.8.8 > /dev/null 2>&1; then
    echo "✓ Internet OK"
else
    echo "✗ No internet. Aborting."
    exit 1
fi

# -----------------------------
# 1. SYSTEM UPDATE
# -----------------------------
echo "=== 1. Updating System ==="
sudo apt update
sudo apt upgrade -y

# -----------------------------
# 2. ENABLE I2C
# -----------------------------
echo "=== 2. Enabling I2C Interface ==="
sudo raspi-config nonint do_i2c 0 || true
sudo apt install -y i2c-tools

# -----------------------------
# 3. INSTALL SYSTEM DEPENDENCIES
# -----------------------------
echo "=== 3. Installing System Dependencies ==="

sudo apt install -y \
    build-essential cmake git pkg-config \
    python3-dev python3-venv python3-pip \
    libjpeg-dev zlib1g-dev libtiff-dev libpng-dev \
    libopenblas-dev gfortran \
    libssl-dev libffi-dev \
    libopencv-dev ffmpeg \
    libi2c-dev sane-utils libsane-dev usbutils

# -----------------------------
# 4. GROUP PERMISSIONS
# -----------------------------
echo "=== 4. Configuring User Groups ==="
sudo usermod -aG i2c $USER || true
sudo usermod -aG scanner $USER || true
sudo usermod -aG gpio $USER || true

# -----------------------------
# 5. CREATE VENV
# -----------------------------
echo "=== 5. Creating Virtual Environment ==="

if [ -d "checkme-env" ]; then
    echo "✓ Virtual environment exists."
else
    python3 -m venv --system-site-packages checkme-env
    echo "✓ Virtual environment created."
fi

source checkme-env/bin/activate

# -----------------------------
# 6. STABLE PIP CONFIG
# -----------------------------
echo "=== 6. Configuring Pip ==="

export PIP_DEFAULT_TIMEOUT=120
export PIP_RETRIES=5

pip install --upgrade pip setuptools wheel \
    --index-url https://pypi.org/simple \
    --no-cache-dir

# -----------------------------
# 7. SAFE INSTALL FUNCTION
# -----------------------------
safe_pip_install() {
    PACKAGE=$1
    echo "Installing $PACKAGE ..."
    for i in 1 2 3; do
        if pip install "$PACKAGE" --index-url https://pypi.org/simple --no-cache-dir; then
            echo "✓ $PACKAGE installed"
            return 0
        else
            echo "Retry $i failed for $PACKAGE"
            sleep 3
        fi
    done
    echo "✗ Failed to install $PACKAGE"
    exit 1
}

# -----------------------------
# 8. INSTALL PYTHON STACK
# -----------------------------
echo "=== 8. Installing Python Stack ==="

safe_pip_install cloudinary==1.44.1
safe_pip_install firebase_admin==7.1.0
safe_pip_install google-genai==1.63.0
safe_pip_install numpy==2.4.2
safe_pip_install opencv-python
safe_pip_install smbus2==0.6.0
safe_pip_install RPi.GPIO
safe_pip_install python-dotenv==1.2.1
safe_pip_install requests==2.32.5
safe_pip_install pydantic==2.12.5
safe_pip_install websockets==15.0.1
safe_pip_install tenacity==9.1.4

# -----------------------------
# 9. CREATE .ENV FILE (IF MISSING)
# -----------------------------
echo "=== 9. Checking .env File ==="

if [ ! -f ".env" ]; then
    echo "Creating .env template..."
    cat <<EOF > .env
# ===== CHECKME ENVIRONMENT VARIABLES =====


# Get your API key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

CLOUDINARY_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

FIREBASE_RTDB_BASE_REFERENCE=
FIREBASE_CREDENTIALS_PATH=config/firebase-credentials.json

USER_CREDENTIALS_FILE=credentials/cred.txt

ANSWER_KEYS_PATH=scans/answer_keys
ANSWER_SHEETS_PATH=scans/answer_sheets
EOF

    chmod 600 .env
    echo "✓ .env template created."
    echo "⚠ IMPORTANT: Edit .env and fill in your real credentials."
else
    echo "✓ .env already exists."
fi

# -----------------------------
# 10. VERIFY SCANNER
# -----------------------------
echo "=== 10. Verifying Epson Scanner ==="

echo "--- USB Detection ---"
lsusb | grep -i epson || echo "⚠ Epson not detected via USB"

echo "--- SANE Detection ---"
scanimage -L || echo "⚠ Scanner not detected by SANE"

# -----------------------------
# 11. VERIFY PYTHON STACK
# -----------------------------
echo "=== 11. Verifying Python Modules ==="

python3 -c "import cv2; print('✓ OpenCV', cv2.__version__)" || echo "✗ OpenCV failed"
python3 -c "import numpy; print('✓ NumPy', numpy.__version__)" || echo "✗ NumPy failed"
python3 -c "import firebase_admin; print('✓ Firebase OK')" || echo "✗ Firebase failed"
python3 -c "import cloudinary; print('✓ Cloudinary OK')" || echo "✗ Cloudinary failed"
python3 -c "import smbus2; print('✓ I2C OK')" || echo "✗ smbus2 failed"
python3 -c "import RPi.GPIO; print('✓ GPIO OK')" || echo "✗ GPIO failed"
python3 -c "from google import genai; print('✓ Google GenAI OK')" || echo "✗ GenAI failed"

echo "-----------------------------------------"
echo "✓ FULL Setup Complete!"
echo ""
echo "IMPORTANT:"
echo "1. Reboot required for I2C & group changes."
echo "   Run: sudo reboot"
echo ""
echo "2. After reboot:"
echo "   source checkme-env/bin/activate"
echo "   python main.py"
echo ""
echo "3. Scanner test:"
echo "   scanimage --format=png --resolution 300 > test.png"
echo "-----------------------------------------"