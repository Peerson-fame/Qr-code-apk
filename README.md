# QR Master Grid — Android build

This is the supplied QR Master Grid PySide6 application packaged as an Android-build project.

## Fastest build

Use the GitHub Actions workflow in `.github/workflows/android.yml`.

1. Create a GitHub repository.
2. Upload this entire folder.
3. Push the files.
4. Open **Actions → Build Android APK**.
5. When it finishes, download the `QR-Master-Grid-debug-apk` artifact.

The build targets ARM64 (`aarch64`), which is the normal architecture for modern Android phones.

The Android deployment is based on Qt for Python's official `pyside6-android-deploy` tool.
