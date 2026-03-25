"""
Build script for SimTelemetry Pro.

Usage:
    python build.py              # Build .exe (PyInstaller)
    python build.py --installer  # Build .exe + Inno Setup installer
    python build.py --clean      # Clean build artifacts

Requirements:
    pip install pyinstaller
    Inno Setup 6 (for --installer): https://jrsoftware.org/isinfo.php
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

PROJECT_DIR  = Path(__file__).parent.resolve()
DIST_DIR     = PROJECT_DIR / "dist"
BUILD_DIR    = PROJECT_DIR / "build"
OUTPUT_DIR   = DIST_DIR / "SimTelemetryPro"
EXE_PATH     = OUTPUT_DIR / "SimTelemetryPro.exe"
SPEC_FILE    = PROJECT_DIR / "SimTelemetryPro.spec"
INSTALLER_SCRIPT = PROJECT_DIR / "installer.iss"

INNO_PATHS = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
]


def find_pyinstaller():
    """Find the pyinstaller executable."""
    candidates = [
        sys.executable.replace("python.exe", "pyinstaller.exe"),
        shutil.which("pyinstaller"),
        str(Path(sys.executable).parent / "Scripts" / "pyinstaller.exe"),
        # User-local install path
        str(Path.home() / "AppData" / "Local" / "Packages" /
            "PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0" /
            "LocalCache" / "local-packages" / "Python311" / "Scripts" /
            "pyinstaller.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    # Try running as module
    return None


def find_iscc():
    for path in INNO_PATHS:
        if Path(path).exists():
            return path
    return shutil.which("iscc")


def clean():
    print("Cleaning build artifacts...")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Removed: {d}")
    print("Clean done.")


def build_exe():
    print("=" * 60)
    print("Building SimTelemetry Pro executable...")
    print("=" * 60)

    os.chdir(PROJECT_DIR)

    pyinstaller = find_pyinstaller()
    if pyinstaller:
        cmd = [pyinstaller, str(SPEC_FILE), "--noconfirm", "--clean"]
    else:
        # Fallback: run as Python module
        cmd = [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm", "--clean"]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))

    if result.returncode != 0:
        print("\nERROR: PyInstaller build failed.")
        sys.exit(1)

    if EXE_PATH.exists():
        size_mb = EXE_PATH.stat().st_size / (1024 * 1024)
        print(f"\nBuild successful!")
        print(f"  Executable: {EXE_PATH}")
        print(f"  Size: {size_mb:.1f} MB")
    else:
        print("\nERROR: .exe not found after build.")
        sys.exit(1)


def build_installer():
    iscc = find_iscc()
    if not iscc:
        print("\nInno Setup not found. Download from: https://jrsoftware.org/isinfo.php")
        print("Skipping installer creation.")
        return

    if not INSTALLER_SCRIPT.exists():
        print(f"Installer script not found: {INSTALLER_SCRIPT}")
        return

    print("\nBuilding installer...")
    result = subprocess.run([iscc, str(INSTALLER_SCRIPT)], cwd=str(PROJECT_DIR))

    if result.returncode == 0:
        installer_path = DIST_DIR / "SimTelemetryPro_Setup.exe"
        if installer_path.exists():
            size_mb = installer_path.stat().st_size / (1024 * 1024)
            print(f"\nInstaller created: {installer_path} ({size_mb:.1f} MB)")
        else:
            print("Installer created (check dist/ folder).")
    else:
        print("ERROR: Inno Setup compilation failed.")


def main():
    parser = argparse.ArgumentParser(description="Build SimTelemetry Pro")
    parser.add_argument("--installer", action="store_true", help="Also build Inno Setup installer")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts and exit")
    args = parser.parse_args()

    if args.clean:
        clean()
        return

    build_exe()

    if args.installer:
        build_installer()

    print("\nDone!")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
