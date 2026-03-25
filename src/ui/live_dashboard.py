"""Live telemetry dashboard widget."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QPixmap, QTransform,
)
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGroupBox,
    QGridLayout, QSizePolicy, QFrame,
)

from ..telemetry.data_models import TelemetryFrame, ms_to_laptime

# Lock-to-lock visual range in degrees (normalized -1..+1 maps to ±MAX_ANGLE_DEG)
MAX_ANGLE_DEG = 450.0


def _assets_dir() -> Path:
    """Resolve the assets/ directory whether running from source or bundled."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).parent.parent.parent / "assets"


# ---------------------------------------------------------------------------
# Steering Wheel Image Widget
# ---------------------------------------------------------------------------

class SteeringWheelWidget(QWidget):
    """Rotating steering wheel using the McLaren GT3 PNG image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steering = 0.0   # -1 to +1
        self._pixmap: Optional[QPixmap] = None
        self._load_image()
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _load_image(self) -> None:
        path = _assets_dir() / "maclaren-gt3-v2-removebg-preview.png"
        if path.exists():
            self._pixmap = QPixmap(str(path))
        else:
            self._pixmap = None

    def set_steering(self, value: float) -> None:
        self._steering = max(-1.0, min(1.0, value))
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        size = min(w, h) - 4
        cx, cy = w / 2.0, h / 2.0
        angle_deg = self._steering * MAX_ANGLE_DEG

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.translate(cx, cy)
            painter.rotate(angle_deg)
            painter.drawPixmap(
                -scaled.width() // 2,
                -scaled.height() // 2,
                scaled,
            )
        else:
            # Fallback: simple circle if image not found
            painter.translate(cx, cy)
            painter.rotate(angle_deg)
            painter.setPen(QPen(QColor("#e8b400"), 6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = size / 2
            painter.drawEllipse(QRectF(-r, -r, size, size))
            painter.setPen(QPen(QColor("#cccccc"), 4))
            painter.drawLine(0, int(-r * 0.9), 0, int(-r * 0.3))

        painter.end()


# ---------------------------------------------------------------------------
# Steering Angle Gauge (horizontal)
# ---------------------------------------------------------------------------

class SteeringAngleGauge(QWidget):
    """Horizontal bar showing steering angle, centered at 0."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steering = 0.0
        self.setFixedHeight(38)

    def set_steering(self, value: float) -> None:
        self._steering = max(-1.0, min(1.0, value))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        margin = 16
        track_h = 10
        track_y = 4
        track_w = w - 2 * margin
        center_x = w // 2

        # Background track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#1a1a1a")))
        p.drawRoundedRect(margin, track_y, track_w, track_h, 4, 4)

        # Tick marks at ±25%, ±50%, ±75%
        p.setPen(QPen(QColor("#333333"), 1))
        for frac in (0.25, 0.5, 0.75):
            for sign in (-1, 1):
                tx = center_x + int(sign * frac * track_w / 2)
                p.drawLine(tx, track_y, tx, track_y + track_h)

        # Fill bar from center
        fill_w = int(abs(self._steering) * track_w / 2)
        if fill_w > 0:
            ratio = abs(self._steering)
            if ratio < 0.4:
                color = QColor("#00cc44")
            elif ratio < 0.7:
                color = QColor("#e8b400")
            else:
                color = QColor("#ff3333")
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))
            if self._steering < 0:
                p.drawRoundedRect(center_x - fill_w, track_y, fill_w, track_h, 2, 2)
            else:
                p.drawRoundedRect(center_x, track_y, fill_w, track_h, 2, 2)

        # Center marker
        p.setPen(QPen(QColor("#666666"), 1))
        p.drawLine(center_x, track_y - 1, center_x, track_y + track_h + 1)

        # Angle text
        angle_deg = self._steering * MAX_ANGLE_DEG
        p.setPen(QPen(QColor("#aaaaaa")))
        font = QFont("Consolas", 9)
        p.setFont(font)
        p.drawText(0, track_y + track_h + 2, w, 16,
                   Qt.AlignmentFlag.AlignCenter, f"{angle_deg:+.0f}°")

        p.end()


# ---------------------------------------------------------------------------
# Pedal / Input Bar Widget
# ---------------------------------------------------------------------------

class PedalBarWidget(QWidget):
    """Vertical bar showing throttle/brake/clutch."""

    def __init__(
        self,
        label: str,
        color: str = "#44cc44",
        parent=None,
    ):
        super().__init__(parent)
        self._value = 0.0
        self._label = label
        self._color = QColor(color)
        self.setMinimumSize(40, 120)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(50)

    def set_value(self, v: float) -> None:
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        bar_h = h - 24
        bar_w = w - 10
        x = 5
        y = 4

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#1a1a1a")))
        p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

        # Fill
        fill_h = int(bar_h * self._value)
        if fill_h > 0:
            gradient = QLinearGradient(0, y + bar_h, 0, y)
            gradient.setColorAt(0.0, self._color.darker(80))
            gradient.setColorAt(0.5, self._color)
            gradient.setColorAt(1.0, self._color.lighter(130))
            p.setBrush(QBrush(gradient))
            p.drawRoundedRect(x, y + bar_h - fill_h, bar_w, fill_h, 3, 3)

        # Border
        p.setPen(QPen(QColor("#333333"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

        # Label
        p.setPen(QPen(QColor("#888888")))
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        p.setFont(font)
        p.drawText(0, h - 18, w, 18, Qt.AlignmentFlag.AlignCenter, self._label)

        p.end()


# ---------------------------------------------------------------------------
# RPM Bar
# ---------------------------------------------------------------------------

class RpmBarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rpm = 0.0
        self._rpm_max = 8000.0
        self.setFixedHeight(18)

    def set_rpm(self, rpm: float, rpm_max: float) -> None:
        self._rpm = rpm
        self._rpm_max = max(rpm_max, 1.0)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        ratio = min(1.0, self._rpm / self._rpm_max)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#1a1a1a")))
        p.drawRect(0, 0, w, h)

        if ratio > 0:
            # Color: green -> yellow -> red
            if ratio < 0.7:
                color = QColor("#00cc44")
            elif ratio < 0.9:
                color = QColor("#e8b400")
            else:
                color = QColor("#ff2222")
            p.setBrush(QBrush(color))
            p.drawRect(0, 0, int(w * ratio), h)

        p.end()


# ---------------------------------------------------------------------------
# Tyre Temperature Cell
# ---------------------------------------------------------------------------

class TyreTempCell(QWidget):
    """Shows inner/middle/outer temps for one tyre as colored cells."""

    def __init__(self, corner: str, parent=None):
        super().__init__(parent)
        self._corner = corner
        self._temps = (0.0, 0.0, 0.0)   # inner, mid, outer
        self._pressure = 0.0
        self._wear = 0.0
        self.setFixedSize(80, 90)

    def set_data(self, temps: tuple, pressure: float, wear: float) -> None:
        self._temps = temps
        self._pressure = pressure
        self._wear = wear
        self.update()

    @staticmethod
    def _temp_color(t: float) -> QColor:
        """Green (optimal) -> blue (cold) / red (hot)."""
        if t <= 0:
            return QColor("#333333")
        if t < 60:
            return QColor("#2244aa")
        if t < 80:
            return QColor(int(20 + (t - 60) * 5), int(60 + (t - 60) * 8), 200)
        if t < 95:
            return QColor("#00aa44")
        if t < 115:
            return QColor(int((t - 95) * 12), int(170 - (t - 95) * 8), 40)
        return QColor(min(255, int((t - 115) * 8 + 180)), 20, 10)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        cell_w = (w - 4) // 3
        cell_h = 36

        for i, t in enumerate(self._temps):
            color = self._temp_color(t)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))
            p.drawRoundedRect(2 + i * cell_w, 2, cell_w - 2, cell_h, 2, 2)

        # Text: temps
        p.setPen(QPen(QColor("#e0e0e0")))
        font = QFont("Consolas", 7)
        p.setFont(font)
        for i, t in enumerate(self._temps):
            tx = 2 + i * cell_w + (cell_w - 2) // 2 - 8
            p.drawText(tx, 8, f"{t:.0f}")

        # Corner label
        p.setPen(QPen(QColor("#888888")))
        font2 = QFont("Segoe UI", 8, QFont.Weight.Bold)
        p.setFont(font2)
        p.drawText(0, 42, w, 16, Qt.AlignmentFlag.AlignCenter, self._corner)

        # Pressure
        p.setPen(QPen(QColor("#aaaaaa")))
        font3 = QFont("Consolas", 8)
        p.setFont(font3)
        p.drawText(0, 58, w, 16, Qt.AlignmentFlag.AlignCenter, f"{self._pressure:.1f} kPa")

        # Wear bar
        wear_w = int((w - 4) * max(0, min(1, self._wear)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#222222")))
        p.drawRect(2, 76, w - 4, 8)
        if wear_w > 0:
            p.setBrush(QBrush(QColor("#44aa44")))
            p.drawRect(2, 76, wear_w, 8)

        p.end()


# ---------------------------------------------------------------------------
# Main Live Dashboard
# ---------------------------------------------------------------------------

class LiveDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ---- LEFT: Steering wheel + inputs ----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self._steering_widget = SteeringWheelWidget()
        self._steering_widget.setMinimumSize(180, 180)
        self._steering_widget.setMaximumSize(220, 220)
        left_layout.addWidget(self._steering_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Steering angle gauge
        self._steering_gauge = SteeringAngleGauge()
        left_layout.addWidget(self._steering_gauge)

        # Pedal bars row
        pedals_row = QHBoxLayout()
        pedals_row.setSpacing(4)
        self._throttle_bar = PedalBarWidget("T", "#00cc44")
        self._brake_bar    = PedalBarWidget("B", "#cc2200")
        self._clutch_bar   = PedalBarWidget("C", "#0088cc")
        pedals_row.addWidget(self._throttle_bar)
        pedals_row.addWidget(self._brake_bar)
        pedals_row.addWidget(self._clutch_bar)
        left_layout.addLayout(pedals_row)
        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # ---- CENTER: Speed / Gear / Times ----
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(4, 0, 4, 0)
        center_layout.setSpacing(4)

        # Track name
        self._track_label = QLabel("—")
        self._track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._track_label.setStyleSheet(
            "color:#e8b400; font-size:15px; font-weight:bold; "
            "font-family:'Segoe UI', Arial; letter-spacing:1px;"
        )
        center_layout.addWidget(self._track_label)

        # Gear
        gear_group = QGroupBox("Gear")
        gear_inner = QVBoxLayout(gear_group)
        self._gear_label = QLabel("N")
        self._gear_label.setObjectName("labelGear")
        self._gear_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gear_inner.addWidget(self._gear_label)
        center_layout.addWidget(gear_group)

        # Speed + RPM
        speed_group = QGroupBox("Speed")
        speed_inner = QVBoxLayout(speed_group)
        self._speed_label = QLabel("0")
        self._speed_label.setObjectName("labelSpeed")
        self._speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speed_inner.addWidget(self._speed_label)

        self._rpm_bar = RpmBarWidget()
        speed_inner.addWidget(self._rpm_bar)

        self._rpm_label = QLabel("0 RPM")
        self._rpm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rpm_label.setStyleSheet("color:#888888; font-family:Consolas; font-size:12px;")
        speed_inner.addWidget(self._rpm_label)
        center_layout.addWidget(speed_group)

        # Lap times
        times_group = QGroupBox("Lap Times")
        times_grid = QGridLayout(times_group)
        times_grid.setSpacing(4)

        self._cur_time_label  = self._make_time_label()
        self._last_time_label = self._make_time_label()
        self._best_time_label = self._make_time_label()
        self._delta_label     = QLabel("+0.000")
        self._delta_label.setObjectName("labelDeltaNeg")
        self._delta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        times_grid.addWidget(QLabel("Current"), 0, 0)
        times_grid.addWidget(self._cur_time_label, 0, 1)
        times_grid.addWidget(QLabel("Last"), 1, 0)
        times_grid.addWidget(self._last_time_label, 1, 1)
        times_grid.addWidget(QLabel("Best"), 2, 0)
        times_grid.addWidget(self._best_time_label, 2, 1)
        times_grid.addWidget(QLabel("Delta"), 3, 0)
        times_grid.addWidget(self._delta_label, 3, 1)
        center_layout.addWidget(times_group)
        center_layout.addStretch()

        main_layout.addWidget(center_panel, stretch=1)

        # ---- RIGHT: Tyres ----
        right_panel = QGroupBox("Tyres")
        tyre_layout = QGridLayout(right_panel)
        tyre_layout.setSpacing(4)

        self._tyre_fl = TyreTempCell("FL")
        self._tyre_fr = TyreTempCell("FR")
        self._tyre_rl = TyreTempCell("RL")
        self._tyre_rr = TyreTempCell("RR")

        tyre_layout.addWidget(self._tyre_fl, 0, 0)
        tyre_layout.addWidget(self._tyre_fr, 0, 1)
        tyre_layout.addWidget(self._tyre_rl, 1, 0)
        tyre_layout.addWidget(self._tyre_rr, 1, 1)

        # Fuel + aids
        info_group = QGroupBox("Session")
        info_grid  = QGridLayout(info_group)
        info_grid.setSpacing(3)

        self._fuel_label     = self._small_value_pair(info_grid, "Fuel", 0)
        self._lap_label      = self._small_value_pair(info_grid, "Lap", 1)
        self._pos_label      = self._small_value_pair(info_grid, "Position", 2)
        self._tc_label       = self._small_value_pair(info_grid, "TC", 3)
        self._abs_label      = self._small_value_pair(info_grid, "ABS", 4)
        self._drs_label      = self._small_value_pair(info_grid, "DRS", 5)
        self._bb_label       = self._small_value_pair(info_grid, "Brake Bias", 6)
        self._water_label    = self._small_value_pair(info_grid, "Water", 7)

        right_vbox = QVBoxLayout()
        right_vbox.addWidget(right_panel)
        right_vbox.addWidget(info_group)
        right_vbox.addStretch()
        main_layout.addLayout(right_vbox)

    def _make_time_label(self) -> QLabel:
        lbl = QLabel("--:--.---")
        lbl.setObjectName("labelLapTime")
        lbl.setStyleSheet(
            "color:#00d4ff; font-size:18px; font-weight:bold; font-family:Consolas;"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def _small_value_pair(self, grid: QGridLayout, name: str, row: int) -> QLabel:
        key_lbl = QLabel(name)
        key_lbl.setStyleSheet("color:#666666; font-size:11px;")
        val_lbl = QLabel("—")
        val_lbl.setStyleSheet("color:#cccccc; font-family:Consolas; font-size:12px;")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(key_lbl, row, 0)
        grid.addWidget(val_lbl, row, 1)
        return val_lbl

    # ------------------------------------------------------------------
    # Update from TelemetryFrame
    # ------------------------------------------------------------------

    def update_frame(self, frame: TelemetryFrame) -> None:
        # Track name
        if frame.track:
            self._track_label.setText(frame.track.upper())

        # Steering
        self._steering_widget.set_steering(frame.steering)
        self._steering_gauge.set_steering(frame.steering)

        # Pedals
        self._throttle_bar.set_value(frame.throttle)
        self._brake_bar.set_value(frame.brake)
        self._clutch_bar.set_value(frame.clutch)

        # Gear
        gear_map = {-1: "R", 0: "N"}
        self._gear_label.setText(gear_map.get(frame.gear, str(frame.gear)))

        # Speed
        self._speed_label.setText(f"{frame.speed_kmh:.0f}")

        # RPM
        self._rpm_bar.set_rpm(frame.rpm, frame.rpm_max)
        self._rpm_label.setText(f"{frame.rpm:.0f} RPM")

        # Times
        self._cur_time_label.setText(ms_to_laptime(frame.lap_time_ms))
        self._last_time_label.setText(ms_to_laptime(frame.last_lap_ms))
        self._best_time_label.setText(ms_to_laptime(frame.best_lap_ms))

        # Delta (current vs best)
        if frame.best_lap_ms > 0 and frame.lap_time_ms > 0:
            delta = (frame.lap_time_ms - frame.best_lap_ms) / 1000.0
            delta_str = f"{delta:+.3f}"
            if delta <= 0:
                self._delta_label.setObjectName("labelDeltaPos")
                self._delta_label.setStyleSheet(
                    "color:#00cc44; font-size:16px; font-weight:bold; font-family:Consolas;"
                )
            else:
                self._delta_label.setObjectName("labelDeltaNeg")
                self._delta_label.setStyleSheet(
                    "color:#ff3333; font-size:16px; font-weight:bold; font-family:Consolas;"
                )
            self._delta_label.setText(delta_str)

        # Tyres
        def tyre_tuple(arr, i):
            return (arr[i], arr[i], arr[i])  # inner/mid/outer fallback

        self._tyre_fl.set_data(
            (frame.tyre_temp_i[0], frame.tyre_temp_m[0], frame.tyre_temp_o[0]),
            frame.tyre_pressure[0], 1.0 - frame.tyre_wear[0],
        )
        self._tyre_fr.set_data(
            (frame.tyre_temp_i[1], frame.tyre_temp_m[1], frame.tyre_temp_o[1]),
            frame.tyre_pressure[1], 1.0 - frame.tyre_wear[1],
        )
        self._tyre_rl.set_data(
            (frame.tyre_temp_i[2], frame.tyre_temp_m[2], frame.tyre_temp_o[2]),
            frame.tyre_pressure[2], 1.0 - frame.tyre_wear[2],
        )
        self._tyre_rr.set_data(
            (frame.tyre_temp_i[3], frame.tyre_temp_m[3], frame.tyre_temp_o[3]),
            frame.tyre_pressure[3], 1.0 - frame.tyre_wear[3],
        )

        # Session info
        self._fuel_label.setText(f"{frame.fuel:.1f} L")
        self._lap_label.setText(str(frame.lap_number + 1))
        self._pos_label.setText(str(frame.position) if frame.position > 0 else "—")
        self._tc_label.setText("ON" if frame.tc_active else "off")
        self._abs_label.setText("ON" if frame.abs_active else "off")
        self._drs_label.setText("ON" if frame.drs_active else "off")
        self._bb_label.setText(f"{frame.brake_bias * 100:.0f}% F")
        self._water_label.setText(f"{frame.water_temp:.0f}°C" if frame.water_temp > 0 else "—")

    def clear(self) -> None:
        """Reset display when sim disconnects."""
        self._track_label.setText("—")
        self._steering_widget.set_steering(0.0)
        self._steering_gauge.set_steering(0.0)
        self._throttle_bar.set_value(0.0)
        self._brake_bar.set_value(0.0)
        self._clutch_bar.set_value(0.0)
        self._gear_label.setText("N")
        self._speed_label.setText("0")
        self._rpm_bar.set_rpm(0, 8000)
        self._rpm_label.setText("0 RPM")
        self._cur_time_label.setText("--:--.---")
        self._last_time_label.setText("--:--.---")
        self._best_time_label.setText("--:--.---")
        self._delta_label.setText("—")
