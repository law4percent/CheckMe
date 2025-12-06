#!/bin/bash

echo "==== Raspberry Pi Project Setup ===="

# -----------------------------
# 1. Update system packages
# -----------------------------
echo "[1/5] Updating system packages..."
sudo apt update && sudo apt upgrade -y


# -----------------------------
# 2. Install system-level dependencies
# -----------------------------
echo "[2/5] Installing Raspberry Pi camera libraries..."

sudo apt install -y \
    python3-picamera2 \
    python3-libcamera \
    python3-kms++ \
    python3-opencv \
    python3-pip


# -----------------------------
# 3. Create Python virtual environment
# -----------------------------
echo "[3/5] Creating Python virtual environment..."

python3 -m venv venv
source venv/bin/activate

echo "Virtual environment activated."


# -----------------------------
# 4. Upgrade pip
# -----------------------------
echo "[4/5] Upgrading pip..."
pip install --upgrade pip


# -----------------------------
# 5. Install Python packages from requirements.txt
# -----------------------------
echo "[5/5] Installing Python packages from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

pip install -r requirements.txt

echo "==== INSTALLATION COMPLETE ===="
echo "To activate the environment later, run:"
echo "source venv/bin/activate"
