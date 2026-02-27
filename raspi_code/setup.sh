#!/bin/bash
# setup.sh - CheckMe Full Raspberry Pi Setup
# Optimized for Raspberry Pi OS (Bookworm / Trixie)

set -e

echo "======================================"
echo "     CHECKME INSTALLATION STARTING"
echo "======================================"

# -------------------------------
# 1️⃣ System Update
# -------------------------------
echo "=== Updating System Packages ==="
sudo apt update && sudo apt upgrade -y

# -------------------------------
# 2️⃣ Install Core System Packages
# -------------------------------
echo "=== Installing System Dependencies ==="
sudo apt install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    python3-dev \
    python3-venv \
    python3-pip \
    libjpeg-dev \
    zlib1g-dev \
    libtiff-dev \
    libpng-dev \
    libopenblas-dev \
    gfortran \
    libssl-dev \
    libffi-dev \
    libopencv-dev \
    ffmpeg \
    libi2c-dev \
    i2c-tools \
    sane-utils \
    libsane-dev \
    usbutils

# -------------------------------
# 3️⃣ Enable Interfaces (I2C)
# -------------------------------
echo "=== Enabling Raspberry Pi Interfaces ==="
sudo raspi-config nonint do_i2c 0

# Add user to required groups
sudo usermod -a -G i2c $USER
sudo usermod -a -G scanner $USER
sudo usermod -a -G gpio $USER

# -------------------------------
# 4️⃣ Create Virtual Environment
# -------------------------------
echo "=== Creating Virtual Environment ==="
if [ -d "checkme-env" ]; then
    echo "Virtual environment already exists."
else
    python3 -m venv checkme-env
    echo "Virtual environment created."
fi

source checkme-env/bin/activate

# -------------------------------
# 5️⃣ Upgrade Pip Tools
# -------------------------------
echo "=== Upgrading Pip ==="
pip install --upgrade pip setuptools wheel

# -------------------------------
# 6️⃣ Install Python Dependencies
# -------------------------------
echo "=== Installing Python Dependencies ==="

pip install \
cloudinary==1.44.1 \
firebase_admin==7.1.0 \
google-genai==1.63.0 \
numpy==2.4.2 \
opencv-python==4.13.0.92 \
smbus2==0.6.0 \
RPi.GPIO \
python-dotenv==1.2.1 \
requests==2.32.5 \
pydantic==2.12.5 \
websockets==15.0.1 \
tenacity==9.1.4

# -------------------------------
# 7️⃣ Verify Epson Scanner
# -------------------------------
echo "=== Verifying Epson L3210 Scanner ==="

echo "--- USB Detection ---"
lsusb | grep -i epson || echo "⚠ Epson not detected via USB"

echo "--- SANE Detection ---"
scanimage -L || echo "⚠ Scanner not detected by SANE"

# -------------------------------
# 8️⃣ Verify Python Stack
# -------------------------------
echo "=== Verifying Python Modules ==="

python3 - <<EOF
import cv2
import numpy
import firebase_admin
import cloudinary
import smbus2
import RPi.GPIO
from google import genai
print("OpenCV:", cv2.__version__)
print("NumPy:", numpy.__version__)
print("Firebase Admin: OK")
print("Cloudinary: OK")
print("I2C (smbus2): OK")
print("GPIO: OK")
print("Google GenAI: OK")
EOF

# -------------------------------
# 9️⃣ Final Message
# -------------------------------
echo ""
echo "======================================"
echo "   CHECKME SETUP COMPLETE!"
echo "======================================"
echo ""
echo "⚠ IMPORTANT: Please REBOOT your Raspberry Pi:"
echo "sudo reboot"
echo ""
echo "After reboot:"
echo "source checkme-env/bin/activate"
echo "python main.py"
echo ""
echo "Scanner test command:"
echo "scanimage --format=png --resolution 300 > test.png"