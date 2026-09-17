#!/usr/bin/env bash
set -e
python3 -m pip install --upgrade pip
python3 -m pip install PySide6 qrcode Pillow
if [ ! -d pyside-setup ]; then
  git clone --depth 1 https://code.qt.io/pyside/pyside-setup
fi
python3 pyside-setup/tools/cross_compile_android/main.py --download-only --skip-update --auto-accept-license
mkdir -p android-wheels
cd android-wheels
qtpip download PySide6 --android --arch aarch64
cd ..
PYSIDE=$(find android-wheels -name 'PySide6-*-android_aarch64.whl' | head -n1)
SHIBOKEN=$(find android-wheels -name 'shiboken6-*-android_aarch64.whl' | head -n1)
pyside6-android-deploy --name "QR Master Grid" \
  --wheel-pyside="$PYSIDE" --wheel-shiboken="$SHIBOKEN" --force --verbose
