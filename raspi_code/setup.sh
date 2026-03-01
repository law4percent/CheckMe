#!/bin/bash
# setup.sh - FULL Production Setup for CheckMe
# Optimized for Raspberry Pi OS 32-bit (Bookworm / armhf)

set -euo pipefail

echo "========================================="
echo "        CHECKME FULL 32-bit SETUP"
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
sudo apt full-upgrade -y
sudo apt autoremove -y

# -----------------------------
# 2. INSTALL SANE + DEPENDENCIES
# -----------------------------
echo "=== 2. Installing SANE and Dependencies ==="
sudo apt install -y sane-utils libsane1 libsane-common sane-airscan usbutils build-essential \
    python3-dev python3-venv python3-pip wget tar

# -----------------------------
# 3. ADD USER TO SCANNER GROUP
# -----------------------------
echo "=== 3. Configuring User Groups ==="
sudo usermod -aG scanner "$USER" || true

# -----------------------------
# 4. INSTALL EPSON OFFICIAL DRIVER (EPKOWA / ISCAN) - 32-bit
# -----------------------------
echo "=== 4. Installing Epson L3210 Driver (32-bit) ==="
DRIVER_DIR="$HOME/checkme_drivers"
mkdir -p "$DRIVER_DIR"
cd "$DRIVER_DIR"

EPSON_ISCAN="iscan-bundle-2.30.4-deb.tar.gz"

if [ ! -f "$EPSON_ISCAN" ]; then
    echo "Downloading Epson driver..."
    wget https://download.ebz.epson.net/dsc/f/03/00/00/90/iscan-bundle-2.30.4-deb.tar.gz
fi

echo "Extracting driver..."
tar -xvzf "$EPSON_ISCAN"
cd iscan-bundle-*/Debian

echo "Installing driver..."
sudo dpkg -i *.deb || sudo apt -f install -y

# -----------------------------
# 5. ENABLE EPSON BACKEND
# -----------------------------
echo "=== 5. Enabling epkowa backend ==="
sudo sed -i '/^#epkowa/ s/^#//' /etc/sane.d/dll.conf
sudo sed -i '/^epson2/ s/^/#/' /etc/sane.d/dll.conf

# -----------------------------
# 6. CREATE SCAN DIRECTORY
# -----------------------------
echo "=== 6. Creating Scan Directory ==="
SCAN_DIR="$HOME/Desktop/l3210_test/scans"
mkdir -p "$SCAN_DIR"

# -----------------------------
# 7. CREATE PYTHON VENV
# -----------------------------
echo "=== 7. Creating Python Virtual Environment ==="
cd "$HOME"
if [ -d "checkme-env" ]; then
    echo "✓ Virtual environment exists."
else
    python3 -m venv --system-site-packages checkme-env
    echo "✓ Virtual environment created."
fi
source checkme-env/bin/activate

# -----------------------------
# 8. INSTALL PYTHON DEPENDENCIES
# -----------------------------
echo "=== 8. Installing Python Packages ==="
pip install --upgrade pip setuptools wheel --no-cache-dir

safe_pip_install() {
    PACKAGE=$1
    echo "Installing $PACKAGE ..."
    for i in 1 2 3; do
        if pip install "$PACKAGE" --no-cache-dir; then
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
# 9. VERIFY SCANNER
# -----------------------------
echo "=== 9. Verifying Epson Scanner ==="
echo "--- USB Detection ---"
lsusb | grep -i epson || echo "⚠ Epson not detected via USB"

echo "--- SANE Detection ---"
scanimage -L || echo "⚠ Scanner not detected by SANE"

# -----------------------------
# 10. TEST SCAN
# -----------------------------
echo "=== 10. Test Scan ==="
TEST_FILE="$SCAN_DIR/test_scan.png"
scanimage --format=png --resolution 300 --mode Color > "$TEST_FILE" && echo "✅ Test scan saved at $TEST_FILE" || echo "✗ Test scan failed!"

echo "-----------------------------------------"
echo "✓ FULL 32-bit Setup Complete!"
echo ""
echo "IMPORTANT:"
echo "1. Reboot required for driver and group changes:"
echo "   sudo reboot"
echo ""
echo "2. After reboot:"
echo "   source checkme-env/bin/activate"
echo "   python main.py"
echo ""
echo "3. Scanner test:"
echo "   scanimage --format=png --resolution 300 > ~/Desktop/l3210_test/scans/test.png"
echo "-----------------------------------------"