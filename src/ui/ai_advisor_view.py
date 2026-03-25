"""AI Advisor view - chat interface for lap analysis and setup advice."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QGroupBox, QComboBox, QSplitter,
    QScrollArea, QFrame, QSizePolicy, QPlainTextEdit,
)

from ..telemetry.analyzer import LapAnalyzer
from ..ai.advisor import AIAdvisor
import config


class ChatBubble(QFrame):
    """A single message bubble in the chat."""

    def __init__(self, text: str, role: str = "assistant", parent=None):
        super().__init__(parent)
        self.setObjectName("chatBubble")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        if role == "user":
            self.setStyleSheet(
                "background:#1a3050; border-radius:8px; border:1px solid #2a4a70;"
            )
            label_text = "You"
            label_color = "#4a9adf"
        else:
            self.setStyleSheet(
                "background:#1a2a1a; border-radius:8px; border:1px solid #2a4a2a;"
            )
            label_text = "AI Engineer"
            label_color = "#44bb44"

        role_label = QLabel(label_text)
        role_label.setStyleSheet(f"color:{label_color}; font-size:10px; font-weight:bold;")
        layout.addWidget(role_label)

        content = QLabel(text)
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setStyleSheet("color:#e0e0e0; font-size:12px; font-family:'Segoe UI', Arial;")
        content.setOpenExternalLinks(False)
        layout.addWidget(content)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)


class AIAdvisorView(QWidget):
    """Full AI advisor interface with lap selection and chat."""

    def __init__(
        self,
        recordings_dir: str = "data/recordings",
        parent=None,
    ):
        super().__init__(parent)
        self._recordings_dir = Path(recordings_dir)
        self._analyzer = LapAnalyzer(recordings_dir)
        self._advisor = AIAdvisor(self._analyzer)
        self._busy = False
        self._selected_lap: Optional[Path] = None
        self._ref_lap: Optional[Path] = None
        self._chat_history: list[dict] = []
        self._setup_ui()
        self.refresh_laps()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)

        # ---- Left: Lap selectors + quick action buttons ----
        left = QWidget()
        left.setFixedWidth(280)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)

        # API key status
        api_group = QGroupBox("API Configuration")
        api_vbox = QVBoxLayout(api_group)
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("Anthropic API Key (sk-ant-...)")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setText(config.get("anthropic_api_key") or "")
        self._api_key_input.textChanged.connect(self._on_api_key_changed)
        api_vbox.addWidget(self._api_key_input)
        self._api_status_label = QLabel()
        self._update_api_status()
        api_vbox.addWidget(self._api_status_label)
        left_layout.addWidget(api_group)

        # Lap selection
        lap_group = QGroupBox("Lap Selection")
        lap_vbox = QVBoxLayout(lap_group)

        lap_vbox.addWidget(QLabel("Analyze Lap:"))
        self._lap_combo = QComboBox()
        self._lap_combo.currentIndexChanged.connect(self._on_lap_changed)
        lap_vbox.addWidget(self._lap_combo)

        lap_vbox.addWidget(QLabel("Reference Lap (for comparison):"))
        self._ref_combo = QComboBox()
        self._ref_combo.addItem("None", None)
        lap_vbox.addWidget(self._ref_combo)

        self._btn_refresh = QPushButton("Refresh Lap List")
        self._btn_refresh.clicked.connect(self.refresh_laps)
        lap_vbox.addWidget(self._btn_refresh)
        left_layout.addWidget(lap_group)

        # Quick actions
        actions_group = QGroupBox("Quick Analysis")
        actions_vbox = QVBoxLayout(actions_group)

        self._btn_analyze = QPushButton("Analyze Selected Lap")
        self._btn_analyze.setObjectName("btnPrimary")
        self._btn_analyze.clicked.connect(self._do_analyze)
        actions_vbox.addWidget(self._btn_analyze)

        self._btn_compare = QPushButton("Compare vs Reference")
        self._btn_compare.clicked.connect(self._do_compare)
        actions_vbox.addWidget(self._btn_compare)

        self._btn_setup = QPushButton("Setup Recommendations")
        self._btn_setup.clicked.connect(self._do_setup)
        actions_vbox.addWidget(self._btn_setup)

        self._btn_clear_chat = QPushButton("Clear Chat")
        self._btn_clear_chat.clicked.connect(self._clear_chat)
        actions_vbox.addWidget(self._btn_clear_chat)

        left_layout.addWidget(actions_group)

        # Context issues input
        issues_group = QGroupBox("Notes / Issues for AI")
        issues_vbox = QVBoxLayout(issues_group)
        self._issues_input = QPlainTextEdit()
        self._issues_input.setPlaceholderText(
            "Describe handling issues, what you felt, specific corners...\n"
            "e.g. 'Oversteer mid-corner, rear feels loose on traction'"
        )
        self._issues_input.setMaximumHeight(100)
        issues_vbox.addWidget(self._issues_input)
        left_layout.addWidget(issues_group)
        left_layout.addStretch()

        splitter.addWidget(left)

        # ---- Right: Chat area ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(4)

        # Chat scroll area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self._chat_container = QWidget()
        self._chat_vbox = QVBoxLayout(self._chat_container)
        self._chat_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._chat_vbox.setSpacing(8)
        self._chat_vbox.setContentsMargins(8, 8, 8, 8)
        self._scroll_area.setWidget(self._chat_container)

        # Add welcome message
        self._add_ai_bubble(
            "<b>Welcome to the AI Telemetry Advisor!</b><br><br>"
            "Select a lap file and click one of the quick analysis buttons, "
            "or type a custom question below.<br><br>"
            "I can help you with:<br>"
            "• <b>Lap analysis</b> - identifying where time is lost<br>"
            "• <b>Lap comparison</b> - comparing two laps in detail<br>"
            "• <b>Setup advice</b> - spring rates, dampers, aero, tyres<br>"
            "• <b>Driving techniques</b> - braking points, trail braking, traction zones"
        )

        right_layout.addWidget(self._scroll_area, stretch=1)

        # Status / busy indicator
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color:#666666; font-size:11px;")
        right_layout.addWidget(self._status_label)

        # Custom question input row
        input_row = QHBoxLayout()
        self._question_input = QLineEdit()
        self._question_input.setPlaceholderText("Ask anything about driving technique or setup...")
        self._question_input.returnPressed.connect(self._do_custom_question)
        self._btn_send = QPushButton("Send")
        self._btn_send.setObjectName("btnPrimary")
        self._btn_send.clicked.connect(self._do_custom_question)
        input_row.addWidget(self._question_input, stretch=1)
        input_row.addWidget(self._btn_send)
        right_layout.addLayout(input_row)

        splitter.addWidget(right)
        splitter.setSizes([280, 700])

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def refresh_laps(self):
        lap_files = self._analyzer.list_lap_files()
        self._lap_combo.clear()
        self._ref_combo.clear()
        self._ref_combo.addItem("None", None)
        for f in lap_files:
            self._lap_combo.addItem(f.name, str(f))
            self._ref_combo.addItem(f.name, str(f))
        if lap_files:
            self._selected_lap = lap_files[0]

    def _on_lap_changed(self, idx: int):
        path_str = self._lap_combo.itemData(idx)
        self._selected_lap = Path(path_str) if path_str else None

    def _on_api_key_changed(self, text: str):
        config.set_key("anthropic_api_key", text.strip())
        self._advisor.invalidate_client()
        self._update_api_status()

    def _update_api_status(self):
        key = config.get("anthropic_api_key") or ""
        if key.startswith("sk-ant-") and len(key) > 20:
            self._api_status_label.setText("API key configured")
            self._api_status_label.setStyleSheet("color:#44bb44; font-size:11px;")
        elif key:
            self._api_status_label.setText("API key may be invalid")
            self._api_status_label.setStyleSheet("color:#e8b400; font-size:11px;")
        else:
            self._api_status_label.setText("No API key - enter your Anthropic key above")
            self._api_status_label.setStyleSheet("color:#ff4444; font-size:11px;")

    def _do_analyze(self):
        if not self._selected_lap:
            self._set_status("No lap selected.")
            return
        comment = self._issues_input.toPlainText().strip()
        self._add_user_bubble(f"Analyze lap: {self._selected_lap.name}"
                              + (f"\nNotes: {comment}" if comment else ""))
        self._set_busy(True)
        self._advisor.analyze_lap_async(
            self._selected_lap,
            on_result=self._on_ai_result,
            on_error=self._on_ai_error,
            user_comment=comment,
        )

    def _do_compare(self):
        if not self._selected_lap:
            self._set_status("No lap selected.")
            return
        ref_path_str = self._ref_combo.currentData()
        if not ref_path_str:
            self._set_status("No reference lap selected.")
            return
        ref_file = Path(ref_path_str)
        comment = self._issues_input.toPlainText().strip()
        self._add_user_bubble(
            f"Compare:\n  Lap: {self._selected_lap.name}\n  Ref: {ref_file.name}"
            + (f"\nNotes: {comment}" if comment else "")
        )
        self._set_busy(True)
        self._advisor.compare_laps_async(
            ref_file,
            self._selected_lap,
            on_result=self._on_ai_result,
            on_error=self._on_ai_error,
            user_comment=comment,
        )

    def _do_setup(self):
        if not self._selected_lap:
            self._set_status("No lap selected.")
            return
        issues = self._issues_input.toPlainText().strip()
        self._add_user_bubble(
            f"Setup advice for: {self._selected_lap.name}"
            + (f"\nIssues: {issues}" if issues else "")
        )
        self._set_busy(True)
        self._advisor.setup_advice_async(
            self._selected_lap,
            on_result=self._on_ai_result,
            on_error=self._on_ai_error,
            issues=issues,
        )

    def _do_custom_question(self):
        question = self._question_input.text().strip()
        if not question:
            return
        self._question_input.clear()
        self._add_user_bubble(question)
        self._set_busy(True)
        self._advisor.custom_question_async(
            question,
            lap_file=self._selected_lap,
            on_result=self._on_ai_result,
            on_error=self._on_ai_error,
        )

    # ------------------------------------------------------------------
    # Callbacks (from worker thread → must be thread-safe)
    # ------------------------------------------------------------------

    def _on_ai_result(self, text: str):
        # Qt signals are thread-safe; use invokeMethod pattern via lambda + QTimer
        from PyQt6.QtCore import QMetaObject, Q_ARG
        from PyQt6.QtWidgets import QApplication
        # Schedule on main thread
        QApplication.instance().postEvent(
            self,
            _AIResultEvent(text, error=False),
        )

    def _on_ai_error(self, error: str):
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().postEvent(
            self,
            _AIResultEvent(error, error=True),
        )

    def event(self, e):
        if isinstance(e, _AIResultEvent):
            self._set_busy(False)
            if e.error:
                self._add_ai_bubble(
                    f"<span style='color:#ff4444;'>Error: {e.text}</span>"
                )
            else:
                self._add_ai_bubble(_markdown_to_html(e.text))
            return True
        return super().event(e)

    # ------------------------------------------------------------------
    # Chat helpers
    # ------------------------------------------------------------------

    def _add_user_bubble(self, text: str):
        bubble = ChatBubble(text.replace("\n", "<br>"), role="user")
        self._chat_vbox.addWidget(bubble)
        self._scroll_to_bottom()

    def _add_ai_bubble(self, html: str):
        bubble = ChatBubble(html, role="assistant")
        self._chat_vbox.addWidget(bubble)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

    def _clear_chat(self):
        for i in reversed(range(self._chat_vbox.count())):
            item = self._chat_vbox.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._add_ai_bubble("Chat cleared. Select a lap and ask a question to get started.")

    def _set_busy(self, busy: bool):
        self._busy = busy
        self._btn_analyze.setEnabled(not busy)
        self._btn_compare.setEnabled(not busy)
        self._btn_setup.setEnabled(not busy)
        self._btn_send.setEnabled(not busy)
        self._status_label.setText("Analyzing..." if busy else "Ready")
        if busy:
            self._status_label.setStyleSheet("color:#e8b400; font-size:11px;")
        else:
            self._status_label.setStyleSheet("color:#666666; font-size:11px;")

    def _set_status(self, msg: str):
        self._status_label.setText(msg)


# ---------------------------------------------------------------------------
# Custom event for thread-safe UI updates
# ---------------------------------------------------------------------------

from PyQt6.QtCore import QEvent

class _AIResultEvent(QEvent):
    _TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, text: str, error: bool = False):
        super().__init__(self._TYPE)
        self.text = text
        self.error = error


# ---------------------------------------------------------------------------
# Simple markdown → HTML conversion
# ---------------------------------------------------------------------------

def _markdown_to_html(text: str) -> str:
    """Very lightweight markdown to HTML for the chat display."""
    import re
    lines = text.split("\n")
    result = []
    in_list = False
    for line in lines:
        # Headers
        if line.startswith("### "):
            if in_list: result.append("</ul>"); in_list = False
            result.append(f"<h4 style='color:#e8b400;margin:4px 0;'>{line[4:]}</h4>")
        elif line.startswith("## "):
            if in_list: result.append("</ul>"); in_list = False
            result.append(f"<h3 style='color:#e8b400;margin:6px 0;'>{line[3:]}</h3>")
        elif line.startswith("# "):
            if in_list: result.append("</ul>"); in_list = False
            result.append(f"<h2 style='color:#e8b400;margin:8px 0;'>{line[2:]}</h2>")
        # Bullet points
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                result.append("<ul style='margin:2px 0; padding-left:16px;'>")
                in_list = True
            item = line[2:]
            item = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", item)
            result.append(f"<li>{item}</li>")
        # Numbered list
        elif re.match(r"^\d+\.\s", line):
            if in_list: result.append("</ul>"); in_list = False
            item = re.sub(r"^\d+\.\s", "", line)
            item = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", item)
            result.append(f"<p style='margin:2px 0;'>• {item}</p>")
        # Empty line
        elif line.strip() == "":
            if in_list: result.append("</ul>"); in_list = False
            result.append("<br>")
        else:
            if in_list: result.append("</ul>"); in_list = False
            line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
            line = re.sub(r"`(.+?)`", r"<code style='background:#1a1a1a;padding:1px 4px;'>\1</code>", line)
            result.append(f"<p style='margin:2px 0;'>{line}</p>")

    if in_list:
        result.append("</ul>")
    return "".join(result)
