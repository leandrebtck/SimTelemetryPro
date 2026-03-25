"""Main application window."""
from __future__ import annotations

import psutil
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPushButton, QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

import config
from ..shared_memory.ac_memory import ACReader
from ..shared_memory.acc_memory import ACCReader
from ..shared_memory.lmu_memory import LMUReader
from ..shared_memory.base_reader import BaseReader
from ..telemetry.data_models import TelemetryFrame
from ..telemetry.recorder import LapRecorder
from ..telemetry.data_models import LapData
from .live_dashboard import LiveDashboard
from .analysis_view import AnalysisView
from .ai_advisor_view import AIAdvisorView
from .styles import DARK_THEME


# Process names for auto-detection
_SIM_PROCESSES = {
    "ac":  ["acs.exe", "AssettoCorsa.exe"],
    "acc": ["AC2.exe", "ACCGame.exe", "AssettoCorsa_x64.exe"],
    "lmu": ["LeMansUltimate.exe", "LMU.exe", "rFactor2.exe"],
}


def _detect_running_sim() -> Optional[str]:
    """Return 'ac', 'acc', 'lmu', or None based on running processes."""
    try:
        running = {p.info["name"].lower() for p in psutil.process_iter(["name"])}
        for sim, names in _SIM_PROCESSES.items():
            if any(n.lower() in running for n in names):
                return sim
    except Exception:
        pass
    return None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        cfg = config.load()
        self._recordings_dir = cfg["recordings_dir"]
        self._poll_hz = cfg["poll_rate_hz"]

        # Readers
        self._readers: dict[str, BaseReader] = {
            "ac":  ACReader(self._poll_hz),
            "acc": ACCReader(self._poll_hz),
            "lmu": LMUReader(self._poll_hz),
        }
        self._active_sim: Optional[str] = None
        self._active_reader: Optional[BaseReader] = None

        # Recorder
        self._recorder = LapRecorder(
            recordings_dir=self._recordings_dir,
            on_lap_complete=self._on_lap_complete,
        )

        self._setup_ui()
        self._apply_theme()
        self._start_detection_timer()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle("SimTelemetry Pro")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 850)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        top_bar = self._build_top_bar()
        main_layout.addWidget(top_bar)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        main_layout.addWidget(self._tabs, stretch=1)

        # Tabs
        self._live_dashboard = LiveDashboard()
        self._analysis_view  = AnalysisView(recordings_dir=self._recordings_dir)
        self._ai_view        = AIAdvisorView(recordings_dir=self._recordings_dir)

        self._tabs.addTab(self._live_dashboard, "Live Telemetry")
        self._tabs.addTab(self._analysis_view,  "Analysis")
        self._tabs.addTab(self._ai_view,        "AI Advisor")

        # Analysis view status messages
        self._analysis_view.status_message.connect(self._set_status)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._sim_label    = QLabel("No simulator detected")
        self._conn_label   = QLabel("Disconnected")
        self._rec_label    = QLabel("Not Recording")
        self._lap_label    = QLabel("Lap: —")
        self._fps_label    = QLabel("")

        self._conn_label.setObjectName("labelDisconnected")
        self._rec_label.setStyleSheet("color:#444444;")

        self._status_bar.addPermanentWidget(self._sim_label)
        self._status_bar.addPermanentWidget(self._make_separator())
        self._status_bar.addPermanentWidget(self._conn_label)
        self._status_bar.addPermanentWidget(self._make_separator())
        self._status_bar.addPermanentWidget(self._rec_label)
        self._status_bar.addPermanentWidget(self._make_separator())
        self._status_bar.addPermanentWidget(self._lap_label)
        self._status_bar.addWidget(QLabel(), 1)  # spacer
        self._status_bar.addPermanentWidget(self._fps_label)

        # Menu bar
        self._build_menu()

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet("background:#0a0a0a; border-bottom:1px solid #1e1e1e;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Sim selector
        sim_label = QLabel("Simulator:")
        sim_label.setStyleSheet("color:#666666;")
        layout.addWidget(sim_label)

        self._sim_combo = QComboBox()
        self._sim_combo.addItems(["Auto Detect", "Assetto Corsa", "ACC", "Le Mans Ultimate"])
        self._sim_combo.setFixedWidth(160)
        self._sim_combo.currentIndexChanged.connect(self._on_sim_selected)
        layout.addWidget(self._sim_combo)

        layout.addSpacing(16)

        # Record button
        self._btn_record = QPushButton("● REC")
        self._btn_record.setObjectName("btnRecord")
        self._btn_record.setFixedWidth(100)
        self._btn_record.setCheckable(True)
        self._btn_record.clicked.connect(self._toggle_recording)
        layout.addWidget(self._btn_record)

        layout.addStretch()

        # Settings button
        self._btn_settings = QPushButton("Settings")
        self._btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(self._btn_settings)

        return bar

    def _build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("File")
        act_settings = QAction("Settings", self)
        act_settings.triggered.connect(self._open_settings)
        file_menu.addAction(act_settings)
        file_menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        rec_menu = menu.addMenu("Recording")
        self._act_start_rec = QAction("Start Recording", self)
        self._act_start_rec.setShortcut(QKeySequence("F9"))
        self._act_start_rec.triggered.connect(self._start_recording)
        rec_menu.addAction(self._act_start_rec)

        self._act_stop_rec = QAction("Stop Recording", self)
        self._act_stop_rec.setShortcut(QKeySequence("F10"))
        self._act_stop_rec.triggered.connect(self._stop_recording)
        self._act_stop_rec.setEnabled(False)
        rec_menu.addAction(self._act_stop_rec)

    @staticmethod
    def _make_separator() -> QLabel:
        sep = QLabel("|")
        sep.setStyleSheet("color:#333333; margin:0 4px;")
        return sep

    def _apply_theme(self):
        self.setStyleSheet(DARK_THEME)

    # ------------------------------------------------------------------
    # Sim detection & reader management
    # ------------------------------------------------------------------

    def _start_detection_timer(self):
        self._detection_timer = QTimer(self)
        self._detection_timer.timeout.connect(self._poll_detection)
        self._detection_timer.start(2000)  # check every 2s

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._poll_frame)
        self._frame_timer.start(16)  # ~60 fps UI refresh

        self._frame_count = 0
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)

    def _poll_detection(self):
        selected = self._sim_combo.currentIndex()
        if selected == 0:  # Auto
            sim_key = _detect_running_sim()
        elif selected == 1:
            sim_key = "ac"
        elif selected == 2:
            sim_key = "acc"
        elif selected == 3:
            sim_key = "lmu"
        else:
            sim_key = None

        if sim_key != self._active_sim:
            self._switch_sim(sim_key)

    def _switch_sim(self, sim_key: Optional[str]):
        # Stop old reader
        if self._active_reader:
            self._active_reader.stop()
            self._active_reader = None

        self._active_sim = sim_key

        if sim_key is None:
            self._sim_label.setText("No simulator detected")
            self._conn_label.setText("Disconnected")
            self._conn_label.setObjectName("labelDisconnected")
            self._conn_label.setStyleSheet("color:#ff3333; font-weight:bold;")
            return

        reader = self._readers[sim_key]
        reader.add_callback(self._on_telemetry_frame)
        reader.start()
        self._active_reader = reader
        self._sim_label.setText(f"Sim: {reader.SIM_NAME}")

    def _on_sim_selected(self, idx: int):
        self._poll_detection()

    # ------------------------------------------------------------------
    # Telemetry frame processing
    # ------------------------------------------------------------------

    _latest_frame: Optional[TelemetryFrame] = None

    def _on_telemetry_frame(self, frame: TelemetryFrame):
        """Called from reader thread - store latest frame only."""
        MainWindow._latest_frame = frame
        self._recorder.feed(frame)

    def _poll_frame(self):
        """Called on main thread - update UI with latest frame."""
        frame = MainWindow._latest_frame
        if frame is None:
            return

        if self._active_reader and self._active_reader.connected:
            self._conn_label.setText("Connected")
            self._conn_label.setStyleSheet("color:#00cc44; font-weight:bold;")
        else:
            self._conn_label.setText("Waiting...")
            self._conn_label.setStyleSheet("color:#888888; font-weight:bold;")
            self._live_dashboard.clear()
            return

        self._live_dashboard.update_frame(frame)
        self._lap_label.setText(f"Lap: {frame.lap_number + 1}")
        self._frame_count += 1

    def _update_fps(self):
        self._fps_label.setText(f"{self._frame_count} fps")
        self._frame_count = 0

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _toggle_recording(self, checked: bool):
        if checked:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self._recorder.start()
        self._btn_record.setChecked(True)
        self._btn_record.setText("■ STOP")
        self._btn_record.setProperty("recording", "true")
        self._btn_record.setStyleSheet("background:#cc0000; color:white; border-color:#ff0000;")
        self._rec_label.setText("● Recording")
        self._rec_label.setStyleSheet("color:#ff2222; font-weight:bold;")
        self._act_start_rec.setEnabled(False)
        self._act_stop_rec.setEnabled(True)
        self._set_status("Recording started")

    def _stop_recording(self):
        self._recorder.stop()
        self._btn_record.setChecked(False)
        self._btn_record.setText("● REC")
        self._btn_record.setStyleSheet("")
        self._rec_label.setText("Stopped")
        self._rec_label.setStyleSheet("color:#888888;")
        self._act_start_rec.setEnabled(True)
        self._act_stop_rec.setEnabled(False)
        n = len(self._recorder.completed_laps)
        self._set_status(f"Recording stopped. {n} laps saved.")
        # Refresh analysis view
        self._analysis_view.refresh_file_list()
        self._ai_view.refresh_laps()

    def _on_lap_complete(self, lap: LapData):
        from PyQt6.QtWidgets import QApplication
        msg = (
            f"Lap {lap.lap_number + 1} completed: {lap.lap_time_str}"
            + (" (VALID)" if lap.is_valid else " (INVALID)")
        )
        self._set_status(msg)

    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
        # Reload config
        cfg = config.load()
        self._recordings_dir = cfg["recordings_dir"]
        self._poll_hz = cfg["poll_rate_hz"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self._status_bar.showMessage(msg, 5000)

    def closeEvent(self, event):
        for reader in self._readers.values():
            reader.stop()
        self._recorder.stop()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(480, 320)
        self.setStyleSheet(DARK_THEME)

        cfg = config.load()
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # API Key
        self._api_key = QLineEdit(cfg.get("anthropic_api_key", ""))
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("sk-ant-...")
        form.addRow("Anthropic API Key:", self._api_key)

        # Recordings dir
        self._rec_dir = QLineEdit(cfg.get("recordings_dir", "data/recordings"))
        form.addRow("Recordings Directory:", self._rec_dir)

        # Poll rate
        self._poll_rate = QLineEdit(str(cfg.get("poll_rate_hz", 60)))
        form.addRow("Poll Rate (Hz):", self._poll_rate)

        # AI Model
        self._model_combo = QComboBox()
        models = ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
        self._model_combo.addItems(models)
        current_model = cfg.get("ai_model", "claude-opus-4-6")
        if current_model in models:
            self._model_combo.setCurrentText(current_model)
        form.addRow("AI Model:", self._model_combo)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        cfg = config.load()
        cfg["anthropic_api_key"] = self._api_key.text().strip()
        cfg["recordings_dir"]    = self._rec_dir.text().strip()
        cfg["ai_model"]          = self._model_combo.currentText()
        try:
            cfg["poll_rate_hz"] = int(self._poll_rate.text())
        except ValueError:
            pass
        config.save(cfg)
        self.accept()
