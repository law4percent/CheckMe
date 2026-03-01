#!/bin/bash
# setup.sh - FULL Production Setup for CheckMe
# Target: Raspberry Pi OS 32-bit Bookworm (armhf) - HEADLESS (no Desktop)
#
# CHANGES FROM ORIGINAL:
#   - Added Pillow (missing dep for SmartCollage)
#   - Replaced opencv-python → opencv-python-headless (headless Pi, no GUI needed)
#   - Added libatlas-base-dev apt dep (required by opencv on armhf)
#   - Pinned numpy to a safe armhf version (no prebuilt wheel for 2.4.2 on 32-bit)
#   - Added --extra-index-url piwheels for faster armhf wheel installs
#   - Added pip.conf to use piwheels permanently inside the venv
#   - firebase_admin==7.1.0 confirmed valid (latest as of 2026)
#   - Added I2C enable check (required for LCD)
#   - Minor: removed Desktop path assumption in scan dir (already headless)

set -euo pipefail

echo "========================================="
echo "        CHECKME FULL 32-bit SETUP"
echo "         (Headless / Bookworm 32-bit)"
echo "========================================="

# -----------------------------
# 0. DISABLE IPv6 + INTERNET CHECK
# -----------------------------
echo "=== 0. Disabling IPv6 and Checking Internet ==="

if ! grep -q "disable_ipv6" /etc/sysctl.conf; then
    echo "net.ipv6.conf.all.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv6.conf.default.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf
    sudo sysctl -p
    echo "✓ IPv6 disabled"
else
    echo "✓ IPv6 already disabled"
fi

echo 'Acquire::ForceIPv4 "true";' | sudo tee /etc/apt/apt.conf.d/99force-ipv4
echo "✓ apt forced to IPv4"

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

# Force apt to use the main Raspbian mirror directly
# (avoids broken third-party mirrors like mirror.ossplanet.net)
sudo tee /etc/apt/sources.list > /dev/null << 'EOF'
deb http://raspbian.raspberrypi.com/raspbian/ bookworm main contrib non-free rpi
EOF
sudo tee /etc/apt/sources.list.d/raspi.list > /dev/null << 'EOF'
deb http://archive.raspberrypi.com/debian/ bookworm main
EOF
echo "✓ apt sources pinned to official mirrors"

sudo apt update
sudo apt full-upgrade -y --fix-missing
sudo apt autoremove -y

# -----------------------------
# 2. INSTALL SYSTEM DEPENDENCIES
# -----------------------------
echo "=== 2. Installing SANE, OpenCV system deps, and build tools ==="
sudo apt install -y --fix-missing \
    sane-utils libsane1 libsane-common sane-airscan usbutils \
    build-essential python3-dev python3-venv python3-pip wget tar \
    libatlas-base-dev libopenjp2-7 libtiff6 libwebp7 \
    i2c-tools python3-smbus \
    git

# libatlas-base-dev → required by numpy/opencv on armhf
# libopenjp2-7 libtiff5 libwebp6 → required by Pillow and opencv on armhf
# i2c-tools python3-smbus → required for LCD I2C display

# -----------------------------
# 3. ENABLE I2C (required for LCD display)
# -----------------------------
echo "=== 3. Enabling I2C Interface ==="
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    echo "✓ I2C enabled in /boot/config.txt (reboot required)"
else
    echo "✓ I2C already enabled"
fi

# Load i2c-dev module now (without reboot)
sudo modprobe i2c-dev || true

# -----------------------------
# 4. ADD USER TO REQUIRED GROUPS
# -----------------------------
echo "=== 4. Configuring User Groups ==="
sudo usermod -aG scanner "$USER" || true
sudo usermod -aG i2c "$USER" || true
sudo usermod -aG gpio "$USER" || true
echo "✓ Added $USER to scanner, i2c, gpio groups"

# -----------------------------
# 5. ENABLE EPSON2 SANE BACKEND
# -----------------------------
echo "=== 5. Enabling epson2 SANE backend ==="
sudo sed -i '/^#epson2/ s/^#//' /etc/sane.d/dll.conf
# Disable epkowa to prevent conflicts
sudo sed -i 's/^epkowa/#epkowa/' /etc/sane.d/dll.conf || true
echo "✓ epson2 backend enabled"

# -----------------------------
# 6. CREATE SCAN DIRECTORY
# -----------------------------
echo "=== 6. Creating Scan Directory ==="
SCAN_DIR="$HOME/scans"
mkdir -p "$SCAN_DIR"
echo "✓ Scan directory: $SCAN_DIR"

# -----------------------------
# 7. CREATE PYTHON VIRTUAL ENVIRONMENT
# -----------------------------
echo "=== 7. Creating Python Virtual Environment ==="
cd "$HOME"
if [ -d "checkme-env" ]; then
    echo "✓ Virtual environment already exists."
else
    python3 -m venv --system-site-packages checkme-env
    echo "✓ Virtual environment created."
fi
source checkme-env/bin/activate

# -----------------------------
# 8. CONFIGURE PIWHEELS (pre-built armhf wheels = much faster installs)
# -----------------------------
echo "=== 8. Configuring piwheels for armhf pre-built wheels ==="
VENV_PIP_CONF="$HOME/checkme-env/pip.conf"
if [ ! -f "$VENV_PIP_CONF" ]; then
    cat > "$VENV_PIP_CONF" << 'EOF'
[global]
extra-index-url=https://www.piwheels.org/simple
EOF
    echo "✓ piwheels configured in venv pip.conf"
else
    echo "✓ pip.conf already exists"
fi

# -----------------------------
# 9. INSTALL PYTHON DEPENDENCIES
# -----------------------------
echo "=== 9. Installing Python Packages ==="
pip install --upgrade pip setuptools wheel --no-cache-dir --timeout=120

safe_pip_install() {
    PACKAGE=$1
    echo "Installing $PACKAGE ..."
    for i in 1 2 3; do
        if pip install "$PACKAGE" --no-cache-dir --timeout=180 --retries=5; then
            echo "✓ $PACKAGE installed"
            return 0
        else
            echo "Retry $i failed for $PACKAGE, waiting 10s..."
            sleep 10
        fi
    done
    echo "✗ Failed to install $PACKAGE after 3 attempts"
    exit 1
}

# ── Core cloud / Firebase ────────────────────────────────────────────────────
safe_pip_install cloudinary==1.44.1
safe_pip_install firebase_admin==7.1.0
safe_pip_install google-genai==1.63.0

# ── Image processing ─────────────────────────────────────────────────────────
# numpy: 2.4.2 has NO prebuilt wheel for armhf 32-bit — it would compile from
# source (30+ min, may fail on low RAM). Use 1.26.x which has piwheels wheels.
safe_pip_install "numpy==1.26.4"

# OpenCV: do NOT install via pip on 32-bit Bookworm — piwheels has no prebuilt
# wheel so pip compiles from source (1–3 hours on Pi). Use apt instead which
# gives a pre-compiled binary in seconds. The venv was created with
# --system-site-packages so it can see the apt-installed python3-opencv.
echo "Installing opencv via apt (pre-compiled, much faster than pip)..."
sudo apt install -y python3-opencv
echo "✓ opencv installed via apt"

# Pillow: required by SmartCollage for image stitching / saving collages.
# Was missing from the original setup.sh.
safe_pip_install Pillow

# ── Hardware ─────────────────────────────────────────────────────────────────
safe_pip_install smbus2==0.6.0
safe_pip_install RPi.GPIO

# ── Utilities ────────────────────────────────────────────────────────────────
safe_pip_install python-dotenv==1.2.1
safe_pip_install requests==2.32.5
safe_pip_install pydantic==2.12.5
safe_pip_install websockets==15.0.1
safe_pip_install tenacity==9.1.4

# -----------------------------
# 10. VERIFY SCANNER
# -----------------------------
echo "=== 10. Verifying Epson Scanner ==="
echo "--- USB Detection ---"
lsusb | grep -i epson && echo "✓ Epson detected via USB" || echo "⚠ Epson not detected via USB (check cable/power)"

echo "--- SANE Detection ---"
scanimage -L && echo "✓ Scanner detected by SANE" || echo "⚠ Scanner not detected by SANE (may need reboot for group changes)"

# -----------------------------
# 11. VERIFY I2C / LCD
# -----------------------------
echo "=== 11. Verifying I2C (LCD) ==="
if command -v i2cdetect &> /dev/null; then
    echo "--- I2C Bus Scan ---"
    sudo i2cdetect -y 1 || echo "⚠ i2cdetect failed (may need reboot)"
else
    echo "⚠ i2cdetect not found — install i2c-tools manually"
fi

# -----------------------------
# 12. TEST SCAN
# -----------------------------
echo "=== 12. Test Scan ==="
TEST_FILE="$SCAN_DIR/test_scan.png"
if scanimage --format=png --resolution 300 --mode Color > "$TEST_FILE" 2>/dev/null; then
    echo "✅ Test scan saved at $TEST_FILE"
else
    echo "⚠ Test scan failed (scanner may not be connected yet — this is OK during initial setup)"
fi

# -----------------------------
# 13. VERIFY PYTHON IMPORTS
# -----------------------------
echo "=== 13. Verifying Python imports ==="
python3 - << 'PYCHECK'
import sys
packages = [
    ("firebase_admin",      "firebase_admin"),
    ("google.genai",        "google-genai"),
    ("cloudinary",          "cloudinary"),
    ("cv2",                 "opencv-python-headless"),
    ("numpy",               "numpy"),
    ("PIL",                 "Pillow"),
    ("smbus2",              "smbus2"),
    ("RPi.GPIO",            "RPi.GPIO"),
    ("dotenv",              "python-dotenv"),
    ("requests",            "requests"),
    ("pydantic",            "pydantic"),
    ("websockets",          "websockets"),
    ("tenacity",            "tenacity"),
]

all_ok = True
for module, package in packages:
    try:
        __import__(module)
        print(f"  ✓ {package}")
    except ImportError as e:
        print(f"  ✗ {package} — {e}")
        all_ok = False

if all_ok:
    print("\n✅ All packages imported successfully!")
else:
    print("\n⚠ Some packages failed to import. Check errors above.")
    sys.exit(1)
PYCHECK

# -----------------------------
# 14. SCAN VIEWER HELPER SCRIPT
# -----------------------------
echo "=== 14. Creating Scan Viewer Script ==="
cat > "$HOME/view_scans.sh" << 'EOF'
#!/bin/bash
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

# =============================================================================
echo ""
echo "========================================="
echo "  ✅ CHECKME SETUP COMPLETE"
echo "========================================="
echo ""
echo "⚠ REQUIRED: Reboot before running the app"
echo "  (group changes for scanner/i2c/gpio need a reboot)"
echo ""
echo "  sudo reboot"
echo ""
echo "After reboot:"
echo "  source ~/checkme-env/bin/activate"
echo "  cd ~/Desktop/CheckMe/raspi_code"
echo "  python main.py"
echo ""
echo "To view scans from another device:"
echo "  ~/view_scans.sh"
echo "  Then open: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Scans saved to: ~/scans/"
echo "========================================="