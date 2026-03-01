#!/bin/bash
# setup.sh - FULL Production Setup for CheckMe
# Optimized for Raspberry Pi OS 32-bit Bullseye (armhf) - HEADLESS (no Desktop)

set -euo pipefail

echo "========================================="
echo "        CHECKME FULL 32-bit SETUP"
echo "         (Headless / No Desktop)"
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
# 4. ENABLE EPSON2 BACKEND (no proprietary driver needed)
# -----------------------------
echo "=== 4. Enabling epson2 backend ==="
sudo sed -i '/^#epson2/ s/^#//' /etc/sane.d/dll.conf
# Make sure epkowa is NOT interfering
sudo sed -i 's/^epkowa/#epkowa/' /etc/sane.d/dll.conf || true
echo "✓ epson2 backend enabled"

# -----------------------------
# 5. CREATE SCAN DIRECTORY (headless path, no Desktop)
# -----------------------------
echo "=== 5. Creating Scan Directory ==="
SCAN_DIR="$HOME/scans"
mkdir -p "$SCAN_DIR"
echo "✓ Scan directory: $SCAN_DIR"

# -----------------------------
# 6. CREATE PYTHON VENV
# -----------------------------
echo "=== 6. Creating Python Virtual Environment ==="
cd "$HOME"
if [ -d "checkme-env" ]; then
    echo "✓ Virtual environment exists."
else
    python3 -m venv --system-site-packages checkme-env
    echo "✓ Virtual environment created."
fi
source checkme-env/bin/activate

# -----------------------------
# 7. INSTALL PYTHON DEPENDENCIES
# -----------------------------
echo "=== 7. Installing Python Packages ==="
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
# 8. VERIFY SCANNER
# -----------------------------
echo "=== 8. Verifying Epson Scanner ==="
echo "--- USB Detection ---"
lsusb | grep -i epson || echo "⚠ Epson not detected via USB"

echo "--- SANE Detection ---"
scanimage -L || echo "⚠ Scanner not detected by SANE"

# -----------------------------
# 9. TEST SCAN
# -----------------------------
echo "=== 9. Test Scan ==="
TEST_FILE="$SCAN_DIR/test_scan.png"
if scanimage --format=png --resolution 300 --mode Color > "$TEST_FILE"; then
    echo "✅ Test scan saved at $TEST_FILE"
else
    echo "✗ Test scan failed! Check USB connection and scanner power."
fi

# -----------------------------
# 10. SETUP SCAN VIEWER (Python HTTP server)
# -----------------------------
echo "=== 10. Creating Scan Viewer Script ==="
cat > "$HOME/view_scans.sh" << 'EOF'
#!/bin/bash
# Simple HTTP server to view scans from Windows browser
SCAN_DIR="$HOME/scans"
PORT=8080
echo "========================================="
echo "  Scan Viewer running on port $PORT"
echo "  Open on Windows browser:"
echo "  http://$(hostname -I | awk '{print $1}'):$PORT"
echo "  Press CTRL+C to stop"
echo "========================================="
cd "$SCAN_DIR"
python3 -m http.server $PORT
EOF
chmod +x "$HOME/view_scans.sh"
echo "✓ Scan viewer script created at ~/view_scans.sh"

echo "-----------------------------------------"
echo "✓ FULL 32-bit Headless Setup Complete!"
echo ""
echo "IMPORTANT:"
echo "1. Reboot required for group changes:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, activate environment:"
echo "   source checkme-env/bin/activate"
echo "   python main.py"
echo ""
echo "3. To view scans from Windows browser:"
echo "   ~/view_scans.sh"
echo "   Then open: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "4. Scans are saved to: ~/scans/"
echo "-----------------------------------------"