#!/bin/bash

echo "==== Raspberry Pi Camera Project Setup ===="

echo "[1/5] Updating system packages..."
sudo apt update && sudo apt full-upgrade -y

echo "[2/5] Enabling camera interface (libcamera)..."
sudo raspi-config nonint do_camera 0

echo "[3/5] Installing required system packages..."
sudo apt install -y \
    python3-picamera2 \
    python3-libcamera \
    python3-opencv \
    python3-pip

echo "[4/5] Installing Python packages..."

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

# Block pip from installing an x86 OpenCV wheel on ARM
echo "Cleaning requirements.txt (removing opencv-python)..."
grep -v '^opencv-python' requirements.txt > /tmp/req_clean.txt

sudo pip3 install -r /tmp/req_clean.txt --break-system-packages

echo "[5/5] Setup complete! Reboot required."

read -p "Reboot now? (y/n): " answer
if [ "$answer" = "y" ]; then
    sudo reboot
fi
