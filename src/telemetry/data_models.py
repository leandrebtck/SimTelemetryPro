"""Common telemetry data models shared across all simulators."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TelemetryFrame:
    """Single telemetry sample, normalised across AC / ACC / LMU."""

    sim: str = ""
    timestamp_ms: int = 0

    # ---- Driver inputs ----
    throttle: float = 0.0       # 0-1
    brake: float = 0.0          # 0-1
    clutch: float = 0.0         # 0-1 (0 = fully pressed / disengaged)
    steering: float = 0.0       # -1 … +1  (normalised to ±1 or radians depending on sim)

    # ---- Motion ----
    speed_kmh: float = 0.0
    gear: int = 0               # 0=neutral, -1=reverse, 1-8
    rpm: float = 0.0
    rpm_max: float = 8000.0

    # ---- G-forces (multiples of g) ----
    g_lat: float = 0.0          # lateral  (+left)
    g_lon: float = 0.0          # longitudinal (+forward = braking)
    g_vert: float = 0.0         # vertical

    # ---- Lap info ----
    lap_number: int = 0
    lap_time_ms: int = 0        # current lap elapsed ms
    last_lap_ms: int = 0
    best_lap_ms: int = 0
    lap_progress: float = 0.0   # 0-1 normalised position on track
    sector_index: int = 0
    is_valid_lap: bool = True

    # ---- Tyres (FL, FR, RL, RR) ----
    tyre_temp: List[float] = field(default_factory=lambda: [0.0] * 4)
    tyre_temp_i: List[float] = field(default_factory=lambda: [0.0] * 4)
    tyre_temp_m: List[float] = field(default_factory=lambda: [0.0] * 4)
    tyre_temp_o: List[float] = field(default_factory=lambda: [0.0] * 4)
    tyre_pressure: List[float] = field(default_factory=lambda: [0.0] * 4)
    tyre_wear: List[float] = field(default_factory=lambda: [0.0] * 4)
    tyre_compound: str = ""

    # ---- Suspension ----
    suspension_travel: List[float] = field(default_factory=lambda: [0.0] * 4)
    ride_height_front: float = 0.0
    ride_height_rear: float = 0.0

    # ---- Brakes ----
    brake_temp: List[float] = field(default_factory=lambda: [0.0] * 4)
    brake_bias: float = 0.5     # 0-1, fraction to front

    # ---- Session ----
    fuel: float = 0.0
    is_in_pit: bool = False
    is_in_pit_lane: bool = False
    pit_limiter: bool = False
    tc_active: bool = False
    abs_active: bool = False
    drs_active: bool = False
    position: int = 0
    session_time_left: float = 0.0
    gap_ahead_ms: int = 0
    gap_behind_ms: int = 0

    # ---- World position ----
    pos_x: float = 0.0          # world X coordinate (metres)
    pos_z: float = 0.0          # world Z coordinate (metres)

    # ---- Meta ----
    car_model: str = ""
    track: str = ""
    water_temp: float = 0.0


@dataclass
class LapData:
    """Complete telemetry for a single lap."""
    sim: str
    track: str
    car_model: str
    lap_number: int
    lap_time_ms: int
    is_valid: bool
    frames: List[TelemetryFrame] = field(default_factory=list)
    session_date: str = ""

    @property
    def lap_time_str(self) -> str:
        return ms_to_laptime(self.lap_time_ms)

    @property
    def sample_count(self) -> int:
        return len(self.frames)


def ms_to_laptime(ms: int) -> str:
    """Convert milliseconds to M:SS.mmm string."""
    if ms <= 0:
        return "--:--.---"
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    millis  = ms % 1000
    return f"{minutes}:{seconds:02d}.{millis:03d}"


# CSV column order for recording
CSV_COLUMNS = [
    "timestamp_ms", "lap_progress", "speed_kmh", "gear", "rpm",
    "throttle", "brake", "clutch", "steering",
    "g_lat", "g_lon", "g_vert",
    "tyre_temp_fl", "tyre_temp_fr", "tyre_temp_rl", "tyre_temp_rr",
    "tyre_temp_i_fl", "tyre_temp_i_fr", "tyre_temp_i_rl", "tyre_temp_i_rr",
    "tyre_temp_o_fl", "tyre_temp_o_fr", "tyre_temp_o_rl", "tyre_temp_o_rr",
    "tyre_pressure_fl", "tyre_pressure_fr", "tyre_pressure_rl", "tyre_pressure_rr",
    "tyre_wear_fl", "tyre_wear_fr", "tyre_wear_rl", "tyre_wear_rr",
    "suspension_fl", "suspension_fr", "suspension_rl", "suspension_rr",
    "brake_temp_fl", "brake_temp_fr", "brake_temp_rl", "brake_temp_rr",
    "fuel", "brake_bias", "ride_height_front", "ride_height_rear",
    "water_temp", "pit_limiter", "tc_active", "abs_active", "drs_active",
]


def frame_to_row(f: TelemetryFrame) -> dict:
    """Convert a TelemetryFrame to a CSV row dict."""
    return {
        "timestamp_ms": f.timestamp_ms,
        "lap_progress": f.lap_progress,
        "speed_kmh": f.speed_kmh,
        "gear": f.gear,
        "rpm": f.rpm,
        "throttle": f.throttle,
        "brake": f.brake,
        "clutch": f.clutch,
        "steering": f.steering,
        "g_lat": f.g_lat,
        "g_lon": f.g_lon,
        "g_vert": f.g_vert,
        "tyre_temp_fl": f.tyre_temp[0], "tyre_temp_fr": f.tyre_temp[1],
        "tyre_temp_rl": f.tyre_temp[2], "tyre_temp_rr": f.tyre_temp[3],
        "tyre_temp_i_fl": f.tyre_temp_i[0], "tyre_temp_i_fr": f.tyre_temp_i[1],
        "tyre_temp_i_rl": f.tyre_temp_i[2], "tyre_temp_i_rr": f.tyre_temp_i[3],
        "tyre_temp_o_fl": f.tyre_temp_o[0], "tyre_temp_o_fr": f.tyre_temp_o[1],
        "tyre_temp_o_rl": f.tyre_temp_o[2], "tyre_temp_o_rr": f.tyre_temp_o[3],
        "tyre_pressure_fl": f.tyre_pressure[0], "tyre_pressure_fr": f.tyre_pressure[1],
        "tyre_pressure_rl": f.tyre_pressure[2], "tyre_pressure_rr": f.tyre_pressure[3],
        "tyre_wear_fl": f.tyre_wear[0], "tyre_wear_fr": f.tyre_wear[1],
        "tyre_wear_rl": f.tyre_wear[2], "tyre_wear_rr": f.tyre_wear[3],
        "suspension_fl": f.suspension_travel[0], "suspension_fr": f.suspension_travel[1],
        "suspension_rl": f.suspension_travel[2], "suspension_rr": f.suspension_travel[3],
        "brake_temp_fl": f.brake_temp[0], "brake_temp_fr": f.brake_temp[1],
        "brake_temp_rl": f.brake_temp[2], "brake_temp_rr": f.brake_temp[3],
        "fuel": f.fuel,
        "brake_bias": f.brake_bias,
        "ride_height_front": f.ride_height_front,
        "ride_height_rear": f.ride_height_rear,
        "water_temp": f.water_temp,
        "pit_limiter": int(f.pit_limiter),
        "tc_active": int(f.tc_active),
        "abs_active": int(f.abs_active),
        "drs_active": int(f.drs_active),
    }
