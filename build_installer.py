"""Build step: zip the app bundle, then PyInstaller the installer."""
import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

PROJECT    = Path(__file__).parent
DIST_APP   = PROJECT / "dist" / "SimTelemetryPro"
BUNDLE_ZIP = PROJECT / "app_bundle.zip"
DIST_DIR   = PROJECT / "dist"


def create_bundle_zip():
    print("Creating app_bundle.zip...")
    if BUNDLE_ZIP.exists():
        BUNDLE_ZIP.unlink()
    with zipfile.ZipFile(BUNDLE_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in DIST_APP.rglob("*"):
            if f.is_file():
                arcname = f.relative_to(DIST_APP)
                zf.write(f, arcname)
    size_mb = BUNDLE_ZIP.stat().st_size / (1024 * 1024)
    print(f"  Bundle: {BUNDLE_ZIP}  ({size_mb:.1f} MB)")


def build_installer_exe():
    icon = PROJECT / "assets" / "icon.ico"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "installer_app.py",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "SimTelemetryPro_Setup",
        "--add-data", f"{BUNDLE_ZIP};.",
        "--distpath", str(DIST_DIR),
        "--workpath", str(PROJECT / "build" / "installer"),
        "--specpath", str(PROJECT / "build" / "installer"),
    ]
    if icon.exists():
        cmd += ["--icon", str(icon)]

    cmd += [
        "--hidden-import", "winreg",
        "--collect-submodules", "PyQt6",
    ]

    print("\nBuilding installer executable...")
    result = subprocess.run(cmd, cwd=str(PROJECT))
    if result.returncode != 0:
        print("ERROR: installer build failed")
        sys.exit(1)

    out = DIST_DIR / "SimTelemetryPro_Setup.exe"
    if out.exists():
        size_mb = out.stat().st_size / (1024 * 1024)
        print(f"\nInstaller ready: {out}  ({size_mb:.1f} MB)")
    else:
        print("ERROR: installer .exe not found")
        sys.exit(1)


if __name__ == "__main__":
    if not DIST_APP.exists():
        print(f"ERROR: App build not found at {DIST_APP}")
        print("Run:  python build.py  first.")
        sys.exit(1)

    create_bundle_zip()
    build_installer_exe()
    print("\nAll done!")
    print(f"  App folder:  dist/SimTelemetryPro/")
    print(f"  Installer:   dist/SimTelemetryPro_Setup.exe")
