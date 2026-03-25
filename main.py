"""SimTelemetry Pro - Entry point.

Racing telemetry application for:
  - Assetto Corsa (AC)
  - Assetto Corsa Competizione (ACC)
  - Le Mans Ultimate (LMU)

Usage:
    python main.py

Requirements:
    pip install -r requirements.txt
"""
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

import config
from src.ui.main_window import MainWindow


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("SimTelemetry Pro")
    app.setOrganizationName("SimTelemetry")
    app.setApplicationVersion("1.0.0")

    # Ensure data directory exists
    cfg = config.load()
    os.makedirs(cfg["recordings_dir"], exist_ok=True)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
