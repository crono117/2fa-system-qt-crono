#!/bin/bash
# ==============================================================
#  2FA Merchant Verification System (PySide2)
#  Linux build script — produces a standalone Linux binary
#
#  Usage:  ./build_exe.sh
#
#  Output:
#    dist/2FA_System_Distribution/
#      2FA_System   <- Linux binary
#      config.ini   <- edit server URL before distributing
# ==============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=============================================="
echo "  2FA System (Qt) - Building Linux Executable"
echo "=============================================="
echo ""

# --- Virtual environment ---
if [ ! -d "venv_build" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv_build
fi

echo "Activating virtual environment..."
source venv_build/bin/activate

# --- Dependencies ---
echo ""
echo "Installing / updating dependencies..."
pip install --upgrade pip --quiet
pip install "PySide2>=5.15.0" requests cryptography keyring loguru --quiet
pip install pyinstaller --quiet

# --- Clean ---
echo "Cleaning previous build artefacts..."
rm -rf build/ dist/

# --- Build ---
echo ""
echo "Running PyInstaller (this takes a few minutes)..."
echo ""
pyinstaller 2fa_system_qt.spec --clean

# --- Result ---
if [ -f "dist/2FA_System" ]; then
    echo ""
    echo "=============================================="
    echo "  BUILD SUCCESSFUL!"
    echo "=============================================="
    echo ""

    DIST_DIR="dist/2FA_System_Distribution"
    mkdir -p "$DIST_DIR"
    cp dist/2FA_System "$DIST_DIR/"
    cp config.ini      "$DIST_DIR/"

    echo "Distribution package ready:"
    echo "  $DIST_DIR/2FA_System"
    echo "  $DIST_DIR/config.ini"
    echo ""
    echo "IMPORTANT — edit config.ini before distributing:"
    echo "  Production server:  api_base_url = http://10.5.96.4:8000/api"
    echo "  Local testing:      api_base_url = http://127.0.0.1:8000/api"
    echo ""
else
    echo ""
    echo "BUILD FAILED — check the output above for errors."
    exit 1
fi
