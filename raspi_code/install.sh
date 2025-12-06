#!/bin/bash

echo "==== Raspberry Pi Project Setup ===="

echo "[1/3] Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "[2/3] Installing Raspberry Pi camera and system libraries..."
sudo apt install -y \
    python3-picamera2 \
    python3-libcamera \
    python3-kms++ \
    python3-opencv \
    python3-pip

echo "[3/3] Installing Python packages from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

sudo pip3 install -r requirements.txt --break-system-packages

echo "==== INSTALLATION COMPLETE ===="
