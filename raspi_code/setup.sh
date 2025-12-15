#!/bin/bash
set -e

echo "========================================"
echo " Raspberry Pi Camera Project Setup"
echo "========================================"

echo "[1/5] Updating system packages..."
sudo apt update && sudo apt full-upgrade -y

echo "[2/5] Enabling camera interface (libcamera)..."
sudo raspi-config nonint do_camera 0

echo "[3/5] Installing required system packages..."
sudo apt install -y \
    python3-pip \
    python3-opencv \
    python3-libcamera \
    python3-picamera2

echo "[4/5] Installing Python dependencies..."

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

# Ensure opencv-python is never installed via pip
echo "Sanitizing requirements.txt..."
grep -v '^opencv-python' requirements.txt > /tmp/requirements.clean.txt

pip3 install --upgrade pip --break-system-packages
pip3 install -r /tmp/requirements.clean.txt --break-system-packages

echo "[5/5] Setup completed successfully."

read -rp "Reboot now? (y/n): " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    sudo reboot
fi
