#!/bin/bash

echo "==== Raspberry Pi Project Setup ===="

# -----------------------------
# 1. Update system packages
# -----------------------------
echo "[1/4] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# -----------------------------
# 2. Install system-level dependencies
# -----------------------------
echo "[2/4] Installing Raspberry Pi camera and system libraries..."
sudo apt install -y \
    python3-picamera2 \
    python3-libcamera \
    python3-kms++ \
    python3-opencv \
    python3-pip

# -----------------------------
# 3. Upgrade pip globally
# -----------------------------
echo "[3/4] Upgrading pip..."
sudo pip3 install --upgrade pip

# -----------------------------
# 4. Install Python packages from requirements.txt
# -----------------------------
echo "[4/4] Installing Python packages globally from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

sudo pip3 install -r requirements.txt

echo "==== INSTALLATION COMPLETE ===="
echo "All dependencies were installed globally. No virtual environment used."
