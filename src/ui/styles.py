"""Dark racing-themed stylesheet."""

DARK_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #0d0d0d;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #2a2a2a;
    background-color: #0d0d0d;
}

QTabBar::tab {
    background-color: #1a1a1a;
    color: #888888;
    padding: 8px 20px;
    border: 1px solid #2a2a2a;
    border-bottom: none;
    font-weight: bold;
    font-size: 12px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QTabBar::tab:selected {
    background-color: #0d0d0d;
    color: #e8b400;
    border-top: 2px solid #e8b400;
}

QTabBar::tab:hover:!selected {
    background-color: #222222;
    color: #cccccc;
}

QPushButton {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2a2a2a;
    border-color: #e8b400;
    color: #e8b400;
}

QPushButton:pressed {
    background-color: #333333;
}

QPushButton:disabled {
    color: #444444;
    border-color: #2a2a2a;
}

QPushButton#btnRecord {
    background-color: #8b0000;
    color: white;
    border-color: #cc0000;
}
QPushButton#btnRecord:hover {
    background-color: #cc0000;
}
QPushButton#btnRecord[recording="true"] {
    background-color: #cc0000;
    color: white;
}

QPushButton#btnPrimary {
    background-color: #1a4a80;
    color: white;
    border-color: #2a6abf;
}
QPushButton#btnPrimary:hover {
    background-color: #2a6abf;
}

QLabel {
    color: #e0e0e0;
}

QLabel#labelValue {
    color: #ffffff;
    font-size: 28px;
    font-weight: bold;
    font-family: 'Consolas', monospace;
}

QLabel#labelSmall {
    color: #888888;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QLabel#labelGear {
    color: #e8b400;
    font-size: 72px;
    font-weight: bold;
    font-family: 'Consolas', monospace;
}

QLabel#labelSpeed {
    color: #ffffff;
    font-size: 48px;
    font-weight: bold;
    font-family: 'Consolas', monospace;
}

QLabel#labelLapTime {
    color: #00d4ff;
    font-size: 32px;
    font-weight: bold;
    font-family: 'Consolas', monospace;
}

QLabel#labelDeltaPos {
    color: #00cc44;
    font-size: 22px;
    font-weight: bold;
    font-family: 'Consolas', monospace;
}

QLabel#labelDeltaNeg {
    color: #ff3333;
    font-size: 22px;
    font-weight: bold;
    font-family: 'Consolas', monospace;
}

QLabel#labelConnected {
    color: #00cc44;
    font-weight: bold;
}

QLabel#labelDisconnected {
    color: #ff3333;
    font-weight: bold;
}

QGroupBox {
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
    color: #888888;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}

QListWidget {
    background-color: #111111;
    border: 1px solid #2a2a2a;
    color: #e0e0e0;
    selection-background-color: #1a3a6a;
    selection-color: #ffffff;
}

QListWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #1a1a1a;
}

QListWidget::item:hover {
    background-color: #1e1e1e;
}

QTextEdit, QPlainTextEdit {
    background-color: #111111;
    border: 1px solid #2a2a2a;
    color: #e0e0e0;
    font-family: 'Consolas', monospace;
    font-size: 12px;
}

QScrollBar:vertical {
    background: #111111;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #111111;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #333333;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QComboBox {
    background-color: #1a1a1a;
    border: 1px solid #3a3a3a;
    color: #e0e0e0;
    padding: 4px 8px;
    border-radius: 3px;
}
QComboBox:hover { border-color: #e8b400; }
QComboBox QAbstractItemView {
    background-color: #1a1a1a;
    border: 1px solid #3a3a3a;
    color: #e0e0e0;
    selection-background-color: #1a3a6a;
}

QLineEdit {
    background-color: #1a1a1a;
    border: 1px solid #3a3a3a;
    color: #e0e0e0;
    padding: 4px 8px;
    border-radius: 3px;
}
QLineEdit:focus { border-color: #e8b400; }

QSplitter::handle {
    background-color: #2a2a2a;
}

QStatusBar {
    background-color: #0a0a0a;
    border-top: 1px solid #2a2a2a;
    color: #888888;
}

QCheckBox {
    color: #e0e0e0;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #3a3a3a;
    background-color: #1a1a1a;
    border-radius: 2px;
}
QCheckBox::indicator:checked {
    background-color: #e8b400;
    border-color: #e8b400;
}

QToolTip {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    padding: 4px;
}
"""

# Lap color palette for multi-lap comparison
LAP_COLORS = [
    "#e8b400",   # gold
    "#00d4ff",   # cyan
    "#ff4444",   # red
    "#44ff88",   # green
    "#ff88ff",   # purple
    "#ff8800",   # orange
    "#88ffff",   # light cyan
    "#ffff44",   # yellow
]
