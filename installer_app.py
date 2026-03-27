"""
SimTelemetry Pro - Installer

This script is bundled into SimTelemetryPro_Setup.exe by PyInstaller.
It extracts the bundled app_bundle.zip to the chosen install directory
and creates Start Menu / Desktop shortcuts.
"""
import sys
import os
import zipfile
import shutil
import winreg
import ctypes
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QProgressBar,
    QTextEdit, QFileDialog, QMessageBox, QWidget,
)

APP_NAME    = "SimTelemetry Pro"
APP_VERSION = "1.0.0"
APP_EXE     = "SimTelemetryPro.exe"
APP_DIR     = "SimTelemetryPro"
PUBLISHER   = "SimTelemetry"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SimTelemetryPro"

# Location of the bundled zip (added as data by PyInstaller)
def _bundle_zip() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / "app_bundle.zip"


# ---------------------------------------------------------------------------
# Worker thread for extraction
# ---------------------------------------------------------------------------

class InstallWorker(QThread):
    progress  = pyqtSignal(int, str)
    finished  = pyqtSignal(bool, str)

    def __init__(self, install_dir: Path, desktop: bool, startmenu: bool):
        super().__init__()
        self._install_dir = install_dir
        self._desktop     = desktop
        self._startmenu   = startmenu

    def run(self):
        try:
            self._install_dir.mkdir(parents=True, exist_ok=True)
            bundle = _bundle_zip()

            if not bundle.exists():
                self.finished.emit(False, f"Bundle not found: {bundle}")
                return

            with zipfile.ZipFile(bundle, "r") as zf:
                members = zf.namelist()
                total   = len(members)
                for i, member in enumerate(members):
                    zf.extract(member, self._install_dir)
                    pct = int((i + 1) / total * 70)
                    self.progress.emit(pct, f"Extracting: {Path(member).name}")

            self.progress.emit(75, "Creating shortcuts...")
            exe_path = self._install_dir / APP_EXE

            if self._desktop:
                _create_shortcut(
                    exe_path,
                    Path.home() / "Desktop" / f"{APP_NAME}.lnk",
                    APP_NAME,
                )

            if self._startmenu:
                sm_dir = _get_startmenu_dir()
                sm_dir.mkdir(parents=True, exist_ok=True)
                _create_shortcut(
                    exe_path,
                    sm_dir / f"{APP_NAME}.lnk",
                    APP_NAME,
                )

            self.progress.emit(85, "Registering application...")
            _register_uninstall(self._install_dir, exe_path)

            # Create recordings dir in Documents
            rec_dir = Path.home() / "Documents" / "SimTelemetry" / "recordings"
            rec_dir.mkdir(parents=True, exist_ok=True)

            self.progress.emit(100, "Installation complete.")
            self.finished.emit(True, str(self._install_dir))

        except Exception as e:
            self.finished.emit(False, str(e))


# ---------------------------------------------------------------------------
# Wizard pages
# ---------------------------------------------------------------------------

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle(f"Welcome to {APP_NAME} {APP_VERSION}")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        desc = QLabel(
            f"This wizard will install <b>{APP_NAME}</b> on your computer.<br><br>"
            "SimTelemetry Pro provides:<br>"
            "• Live telemetry dashboard for AC, ACC and Le Mans Ultimate<br>"
            "• Lap recording and Motec-style analysis<br>"
            "• AI-powered driving coach and setup advisor<br><br>"
            "Click <b>Next</b> to continue."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; line-height: 1.6;")
        layout.addWidget(desc)
        layout.addStretch()


class InstallDirPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installation Folder")
        self.setSubTitle("Choose where to install SimTelemetry Pro.")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        default_dir = str(Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DIR)

        dir_row = QHBoxLayout()
        self._dir_input = QLineEdit(default_dir)
        self.registerField("installDir*", self._dir_input)
        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse)
        dir_row.addWidget(self._dir_input, 1)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        # Shortcut options
        self._desktop_cb   = QCheckBox("Create Desktop shortcut")
        self._startmenu_cb = QCheckBox("Create Start Menu shortcut")
        self._desktop_cb.setChecked(True)
        self._startmenu_cb.setChecked(True)
        self.registerField("desktop",   self._desktop_cb)
        self.registerField("startmenu", self._startmenu_cb)
        layout.addWidget(self._desktop_cb)
        layout.addWidget(self._startmenu_cb)
        layout.addStretch()

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Install Folder", self._dir_input.text())
        if d:
            self._dir_input.setText(d)


class InstallPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installing...")
        self.setSubTitle("Please wait while SimTelemetry Pro is being installed.")
        self._complete = False
        self._worker: InstallWorker | None = None

        layout = QVBoxLayout(self)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._status = QLabel("Preparing...")
        self._status.setStyleSheet("color: #555;")
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        self._log.setStyleSheet("font-family: Consolas; font-size: 11px;")
        layout.addWidget(self._progress)
        layout.addWidget(self._status)
        layout.addWidget(self._log)
        layout.addStretch()

    def initializePage(self):
        install_dir = Path(self.field("installDir"))
        desktop     = bool(self.field("desktop"))
        startmenu   = bool(self.field("startmenu"))

        self._worker = InstallWorker(install_dir, desktop, startmenu)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        # Slight delay so the page renders first
        QTimer.singleShot(300, self._worker.start)

    def _on_progress(self, pct: int, msg: str):
        self._progress.setValue(pct)
        self._status.setText(msg)
        self._log.append(msg)

    def _on_finished(self, success: bool, msg: str):
        if success:
            self._status.setText("Installation successful!")
            self._log.append(f"Installed to: {msg}")
            self._complete = True
            self.completeChanged.emit()
            self.wizard().next()
        else:
            self._status.setText(f"Error: {msg}")
            self._log.append(f"ERROR: {msg}")
            QMessageBox.critical(self, "Installation Failed", msg)

    def isComplete(self):
        return self._complete


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installation Complete")
        layout = QVBoxLayout(self)

        msg = QLabel(
            f"<b>{APP_NAME}</b> has been installed successfully!<br><br>"
            "• Recordings are saved to <i>Documents\\SimTelemetry\\recordings\\</i><br>"
            "• Enter your Anthropic API key in Settings to enable the AI Advisor<br>"
            "• Press F9 to start recording, F10 to stop<br><br>"
            "Click <b>Finish</b> to close the installer."
        )
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 12px; line-height: 1.6;")
        layout.addWidget(msg)

        self._launch_cb = QCheckBox(f"Launch {APP_NAME} now")
        self._launch_cb.setChecked(True)
        layout.addWidget(self._launch_cb)
        self.registerField("launch", self._launch_cb)
        layout.addStretch()


# ---------------------------------------------------------------------------
# Main installer wizard
# ---------------------------------------------------------------------------

INSTALLER_STYLE = """
QWizard {
    background: #f5f5f5;
}
QWizardPage {
    background: white;
    padding: 16px;
}
QWizard QLabel#qt_wizard_titleLabel {
    font-size: 15px;
    font-weight: bold;
    color: #1a1a2e;
}
QWizard QLabel#qt_wizard_subTitleLabel {
    color: #555;
    font-size: 12px;
}
QPushButton {
    background: #1a4a80;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
    min-width: 80px;
}
QPushButton:hover { background: #2a6abf; }
QPushButton:disabled { background: #aaa; }
QProgressBar {
    border: 1px solid #ccc;
    border-radius: 4px;
    text-align: center;
    height: 22px;
}
QProgressBar::chunk {
    background: #1a4a80;
    border-radius: 3px;
}
QCheckBox { font-size: 12px; }
QLineEdit {
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 5px 8px;
    font-size: 12px;
}
"""


class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Setup")
        self.setMinimumSize(560, 420)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setStyleSheet(INSTALLER_STYLE)

        self._welcome_page  = WelcomePage()
        self._dir_page      = InstallDirPage()
        self._install_page  = InstallPage()
        self._finish_page   = FinishPage()

        self.addPage(self._welcome_page)
        self.addPage(self._dir_page)
        self.addPage(self._install_page)
        self.addPage(self._finish_page)

        self.setButtonText(QWizard.WizardButton.FinishButton, "Finish")
        self.setOption(QWizard.WizardOption.DisabledBackButtonOnLastPage)

    def accept(self):
        if self.field("launch"):
            install_dir = Path(self.field("installDir"))
            exe = install_dir / APP_EXE
            if exe.exists():
                subprocess.Popen([str(exe)], cwd=str(install_dir))
        super().accept()


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def _register_uninstall(install_dir: Path, exe_path: Path):
    """Register the app in Add/Remove Programs."""
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        winreg.SetValueEx(key, "DisplayName",     0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion",  0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher",       0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "DisplayIcon",     0, winreg.REG_SZ, str(exe_path))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                         f'"{exe_path}" --uninstall')
        winreg.SetValueEx(key, "NoModify",        0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair",        0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except Exception:
        pass  # Registry write failure is non-fatal


def _get_startmenu_dir() -> Path:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        val, _ = winreg.QueryValueEx(key, "Programs")
        winreg.CloseKey(key)
        return Path(val) / APP_NAME
    except Exception:
        return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME


def _create_shortcut(target: Path, link_path: Path, description: str = ""):
    """Create a Windows .lnk shortcut using PowerShell."""
    try:
        ps_script = (
            f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{link_path}");'
            f'$s.TargetPath="{target}";'
            f'$s.WorkingDirectory="{target.parent}";'
            f'$s.Description="{description}";'
            f'$s.Save()'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    wizard = InstallerWizard()
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
