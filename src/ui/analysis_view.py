"""Analysis view - Motec i2-style multi-channel lap comparison with pyqtgraph."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QSplitter, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)

from ..telemetry.analyzer import LapAnalyzer, CHANNEL_LABELS, DEFAULT_CHANNELS
from .styles import LAP_COLORS

# Configure pyqtgraph dark theme
pg.setConfigOption("background", "#0d0d0d")
pg.setConfigOption("foreground", "#888888")
pg.setConfigOptions(antialias=True)


class ChannelPanel(pg.PlotWidget):
    """A single channel plot panel with linked x-axis."""

    def __init__(self, channel: str, label: str, parent=None):
        super().__init__(parent)
        self._channel = channel
        self.setLabel("left", label, color="#888888", size="9pt")
        self.showGrid(x=True, y=True, alpha=0.15)
        self.getAxis("bottom").setStyle(showValues=False)
        self.setMouseEnabled(x=True, y=False)
        self.setMenuEnabled(False)
        self.setMinimumHeight(80)
        self.setMaximumHeight(140)
        self._curves: Dict[str, pg.PlotDataItem] = {}

    def set_lap(self, lap_id: str, x: np.ndarray, y: np.ndarray, color: str) -> None:
        if lap_id in self._curves:
            self._curves[lap_id].setData(x, y)
            self._curves[lap_id].setPen(pg.mkPen(color=color, width=1.5))
        else:
            curve = self.plot(x, y, pen=pg.mkPen(color=color, width=1.5))
            self._curves[lap_id] = curve

    def remove_lap(self, lap_id: str) -> None:
        if lap_id in self._curves:
            self.removeItem(self._curves.pop(lap_id))

    def clear_laps(self) -> None:
        for c in self._curves.values():
            self.removeItem(c)
        self._curves.clear()


class DeltaPanel(pg.PlotWidget):
    """Delta time panel (positive = slower than reference)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLabel("left", "Delta (s)", color="#888888", size="9pt")
        self.showGrid(x=True, y=True, alpha=0.15)
        self.getAxis("bottom").setLabel("Lap Progress", color="#888888")
        self.setMouseEnabled(x=True, y=False)
        self.setMenuEnabled(False)
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)
        self._ref_line = self.addLine(y=0, pen=pg.mkPen("#444444", width=1, style=Qt.PenStyle.DashLine))
        self._curves: Dict[str, pg.PlotDataItem] = {}

    def set_delta(self, lap_id: str, x: np.ndarray, delta: np.ndarray, color: str) -> None:
        # Color fill: positive (slower) = red, negative (faster) = green
        if lap_id in self._curves:
            self._curves[lap_id].setData(x, delta)
        else:
            curve = self.plot(x, delta, pen=pg.mkPen(color=color, width=2))
            self._curves[lap_id] = curve

    def remove_delta(self, lap_id: str) -> None:
        if lap_id in self._curves:
            self.removeItem(self._curves.pop(lap_id))

    def clear_deltas(self) -> None:
        for c in self._curves.values():
            self.removeItem(c)
        self._curves.clear()


class AnalysisView(QWidget):
    """Main analysis view with lap selector, channel plots, and stats table."""

    status_message = pyqtSignal(str)

    def __init__(self, recordings_dir: str = "data/recordings", parent=None):
        super().__init__(parent)
        self._analyzer = LapAnalyzer(recordings_dir)
        self._loaded_laps: Dict[str, Tuple[Path, pd.DataFrame]] = {}  # lap_id -> (path, df)
        self._color_map: Dict[str, str] = {}
        self._color_idx = 0
        self._ref_lap_id: Optional[str] = None
        self._panels: List[ChannelPanel] = []
        self._delta_panel: Optional[DeltaPanel] = None
        self._active_channels = list(DEFAULT_CHANNELS)
        self._setup_ui()
        self.refresh_file_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)

        # ---- Left panel: lap selector + channel selector ----
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(6)
        left_widget.setFixedWidth(260)

        # Lap file list
        lap_group = QGroupBox("Lap Files")
        lap_vbox = QVBoxLayout(lap_group)
        lap_vbox.setContentsMargins(4, 4, 4, 4)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._file_list.setMaximumHeight(220)
        lap_vbox.addWidget(self._file_list)

        btn_row = QHBoxLayout()
        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self.refresh_file_list)
        self._btn_add = QPushButton("Add to Plot")
        self._btn_add.clicked.connect(self._add_selected_laps)
        self._btn_clear = QPushButton("Clear All")
        self._btn_clear.clicked.connect(self._clear_all_laps)
        btn_row.addWidget(self._btn_refresh)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_clear)
        lap_vbox.addLayout(btn_row)
        left_layout.addWidget(lap_group)

        # Reference lap
        ref_group = QGroupBox("Reference Lap")
        ref_vbox = QVBoxLayout(ref_group)
        self._ref_combo = QComboBox()
        self._ref_combo.addItem("None (no delta)")
        self._ref_combo.currentIndexChanged.connect(self._on_ref_changed)
        ref_vbox.addWidget(self._ref_combo)
        left_layout.addWidget(ref_group)

        # Active lap list (loaded)
        loaded_group = QGroupBox("Loaded Laps")
        loaded_vbox = QVBoxLayout(loaded_group)
        self._loaded_list = QListWidget()
        self._loaded_list.setMaximumHeight(160)
        self._btn_remove = QPushButton("Remove Selected")
        self._btn_remove.clicked.connect(self._remove_selected_loaded)
        loaded_vbox.addWidget(self._loaded_list)
        loaded_vbox.addWidget(self._btn_remove)
        left_layout.addWidget(loaded_group)

        # Channel selector
        ch_group = QGroupBox("Channels")
        ch_scroll = QScrollArea()
        ch_scroll.setWidgetResizable(True)
        ch_content = QWidget()
        ch_vbox = QVBoxLayout(ch_content)
        ch_vbox.setSpacing(2)
        self._channel_checks: Dict[str, QCheckBox] = {}
        for ch, label in CHANNEL_LABELS.items():
            cb = QCheckBox(label)
            cb.setChecked(ch in DEFAULT_CHANNELS)
            cb.stateChanged.connect(lambda state, c=ch: self._toggle_channel(c, state))
            ch_vbox.addWidget(cb)
            self._channel_checks[ch] = cb
        ch_content.setLayout(ch_vbox)
        ch_scroll.setWidget(ch_content)
        ch_scroll.setMaximumHeight(200)
        ch_group_vbox = QVBoxLayout(ch_group)
        ch_group_vbox.addWidget(ch_scroll)
        left_layout.addWidget(ch_group)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # ---- Right panel: plots + stats ----
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Plot area
        plot_widget = QWidget()
        self._plot_layout = QVBoxLayout(plot_widget)
        self._plot_layout.setContentsMargins(0, 0, 0, 0)
        self._plot_layout.setSpacing(1)
        self._build_channel_panels()
        right_splitter.addWidget(plot_widget)

        # Stats table
        stats_widget = QGroupBox("Channel Statistics")
        stats_vbox = QVBoxLayout(stats_widget)
        self._stats_table = QTableWidget()
        self._stats_table.setMaximumHeight(180)
        self._stats_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        stats_vbox.addWidget(self._stats_table)
        right_splitter.addWidget(stats_widget)

        right_splitter.setSizes([600, 180])
        splitter.addWidget(right_splitter)
        splitter.setSizes([260, 900])

    def _build_channel_panels(self):
        # Clear existing
        for p in self._panels:
            self._plot_layout.removeWidget(p)
            p.deleteLater()
        self._panels.clear()
        if self._delta_panel:
            self._plot_layout.removeWidget(self._delta_panel)
            self._delta_panel.deleteLater()
            self._delta_panel = None

        ref_x_axis = None
        for i, ch in enumerate(self._active_channels):
            label = CHANNEL_LABELS.get(ch, ch)
            panel = ChannelPanel(ch, label)
            if ref_x_axis is None:
                ref_x_axis = panel.getViewBox()
            else:
                panel.setXLink(self._panels[0])
            self._panels.append(panel)
            self._plot_layout.addWidget(panel)

        # Delta panel (always last)
        self._delta_panel = DeltaPanel()
        if self._panels:
            self._delta_panel.setXLink(self._panels[0])
        self._plot_layout.addWidget(self._delta_panel)

        # Reload data into new panels
        self._replot_all()

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def refresh_file_list(self):
        self._file_list.clear()
        for f in self._analyzer.list_lap_files():
            item = QListWidgetItem(f.name)
            item.setData(Qt.ItemDataRole.UserRole, str(f))
            self._file_list.addItem(item)

    def _next_color(self) -> str:
        color = LAP_COLORS[self._color_idx % len(LAP_COLORS)]
        self._color_idx += 1
        return color

    def _add_selected_laps(self):
        for item in self._file_list.selectedItems():
            path = Path(item.data(Qt.ItemDataRole.UserRole))
            lap_id = path.stem[-30:]  # use last 30 chars as ID
            if lap_id in self._loaded_laps:
                continue
            df = self._analyzer.load_lap(path)
            if df is None:
                self.status_message.emit(f"Failed to load: {path.name}")
                continue
            df = self._analyzer.resample_to_distance(df)
            self._loaded_laps[lap_id] = (path, df)
            self._color_map[lap_id] = self._next_color()
            # Add to loaded list UI
            list_item = QListWidgetItem(path.name)
            list_item.setData(Qt.ItemDataRole.UserRole, lap_id)
            list_item.setForeground(QColor(self._color_map[lap_id]))
            self._loaded_list.addItem(list_item)
            # Add to ref combo
            self._ref_combo.addItem(path.name, lap_id)
            self.status_message.emit(f"Loaded: {path.name}")

        self._replot_all()
        self._update_stats_table()

    def _remove_selected_loaded(self):
        for item in self._loaded_list.selectedItems():
            lap_id = item.data(Qt.ItemDataRole.UserRole)
            self._loaded_laps.pop(lap_id, None)
            self._color_map.pop(lap_id, None)
            # Remove from ref combo
            idx = self._ref_combo.findData(lap_id)
            if idx >= 0:
                self._ref_combo.removeItem(idx)
            if self._ref_lap_id == lap_id:
                self._ref_lap_id = None
                self._ref_combo.setCurrentIndex(0)
            self._loaded_list.takeItem(self._loaded_list.row(item))

        self._replot_all()
        self._update_stats_table()

    def _clear_all_laps(self):
        self._loaded_laps.clear()
        self._color_map.clear()
        self._ref_lap_id = None
        self._loaded_list.clear()
        while self._ref_combo.count() > 1:
            self._ref_combo.removeItem(1)
        self._replot_all()
        self._stats_table.setRowCount(0)

    def _on_ref_changed(self, idx: int):
        if idx <= 0:
            self._ref_lap_id = None
        else:
            self._ref_lap_id = self._ref_combo.itemData(idx)
        self._replot_all()

    def _toggle_channel(self, channel: str, state: int):
        if state and channel not in self._active_channels:
            self._active_channels.append(channel)
        elif not state and channel in self._active_channels:
            self._active_channels.remove(channel)
        self._build_channel_panels()

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def _replot_all(self):
        for panel in self._panels:
            panel.clear_laps()
        if self._delta_panel:
            self._delta_panel.clear_deltas()

        ref_df = None
        if self._ref_lap_id and self._ref_lap_id in self._loaded_laps:
            ref_df = self._loaded_laps[self._ref_lap_id][1]

        for lap_id, (path, df) in self._loaded_laps.items():
            color = self._color_map.get(lap_id, "#ffffff")
            x = df["lap_progress"].values

            for panel in self._panels:
                ch = panel._channel
                if ch in df.columns:
                    y = df[ch].values
                    panel.set_lap(lap_id, x, y, color)

            # Delta
            if self._delta_panel and ref_df is not None and lap_id != self._ref_lap_id:
                delta = self._analyzer.compute_delta(ref_df, df)
                x_d = np.linspace(0.0, 1.0, len(delta))
                self._delta_panel.set_delta(lap_id, x_d, delta, color)

    # ------------------------------------------------------------------
    # Stats table
    # ------------------------------------------------------------------

    def _update_stats_table(self):
        if not self._loaded_laps:
            self._stats_table.setRowCount(0)
            return

        visible_channels = [c for c in self._active_channels if c in CHANNEL_LABELS]
        lap_ids = list(self._loaded_laps.keys())

        # Columns: channel + (min/mean/max) per lap
        col_headers = ["Channel"]
        for lid in lap_ids:
            name = self._loaded_laps[lid][0].name[-20:]
            col_headers += [f"{name}\nmin", f"{name}\nmean", f"{name}\nmax"]

        self._stats_table.setColumnCount(len(col_headers))
        self._stats_table.setHorizontalHeaderLabels(col_headers)
        self._stats_table.setRowCount(len(visible_channels))

        for r, ch in enumerate(visible_channels):
            self._stats_table.setItem(r, 0, QTableWidgetItem(CHANNEL_LABELS.get(ch, ch)))
            col = 1
            for lid in lap_ids:
                df = self._loaded_laps[lid][1]
                if ch in df.columns:
                    s = df[ch].dropna()
                    self._stats_table.setItem(r, col,     QTableWidgetItem(f"{s.min():.2f}"))
                    self._stats_table.setItem(r, col + 1, QTableWidgetItem(f"{s.mean():.2f}"))
                    self._stats_table.setItem(r, col + 2, QTableWidgetItem(f"{s.max():.2f}"))
                col += 3
