#!/bin/bash

echo "==== Raspberry Pi Project Setup ===="

echo "[1/3] Updating system packages..."
sudo apt update && sudo apt full-upgrade -y

echo "[2/3] Installing Raspberry Pi camera and system libraries..."
sudo apt install -y \
    python3-picamera2 \
    python3-libcamera \
    python3-opencv \
    python3-pip

# kms++ is usually not needed unless you're doing low-level display work
# If required, uncomment this:
# sudo apt install -y python3-kms++

echo "[3/3] Installing Python packages from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

# Prevent corrupted OpenCV installs from pip
# (pip install of opencv-python causes invalid ELF header on Raspberry Pi)
echo "Blocking opencv-python from being installed via pip..."
grep -v '^opencv-python' requirements.txt > /tmp/req_clean.txt

sudo pip3 install -r /tmp/req_clean.txt --break-system-packages

echo "==== INSTALLATION COMPLETE ===="
