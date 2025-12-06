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
# 3. Upgrade pip globally (allow override)
# -----------------------------
echo "[3/4] Upgrading pip..."
sudo pip3 install --upgrade pip --break-system-packages

# -----------------------------
# 4. Install Python packages from requirements.txt
# -----------------------------
echo "[4/4] Installing Python packages globally from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

sudo pip3 install -r requirements.txt --break-system-packages

echo "==== INSTALLATION COMPLETE ===="
echo "All Python packages were installed globally using --break-system-packages."
