"""Lap analysis utilities: load CSV files, compute statistics, resample channels."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .data_models import ms_to_laptime, CSV_COLUMNS


CHANNEL_LABELS = {
    "speed_kmh": "Speed (km/h)",
    "throttle": "Throttle (%)",
    "brake": "Brake (%)",
    "steering": "Steering",
    "gear": "Gear",
    "rpm": "RPM",
    "g_lat": "Lateral G",
    "g_lon": "Longitudinal G",
    "g_vert": "Vertical G",
    "tyre_temp_fl": "Tyre Temp FL (°C)",
    "tyre_temp_fr": "Tyre Temp FR (°C)",
    "tyre_temp_rl": "Tyre Temp RL (°C)",
    "tyre_temp_rr": "Tyre Temp RR (°C)",
    "tyre_pressure_fl": "Pressure FL (kPa)",
    "tyre_pressure_fr": "Pressure FR (kPa)",
    "tyre_pressure_rl": "Pressure RL (kPa)",
    "tyre_pressure_rr": "Pressure RR (kPa)",
    "brake_temp_fl": "Brake Temp FL (°C)",
    "brake_temp_fr": "Brake Temp FR (°C)",
    "suspension_fl": "Susp. FL (m)",
    "suspension_fr": "Susp. FR (m)",
    "suspension_rl": "Susp. RL (m)",
    "suspension_rr": "Susp. RR (m)",
    "fuel": "Fuel (L)",
    "brake_bias": "Brake Bias",
}

DEFAULT_CHANNELS = [
    "speed_kmh", "throttle", "brake", "steering",
    "gear", "rpm", "g_lat", "g_lon",
]


class LapAnalyzer:
    """Load and analyze lap CSV files."""

    def __init__(self, recordings_dir: str = "data/recordings"):
        self._dir = Path(recordings_dir)

    # ------------------------------------------------------------------
    # Listing & loading
    # ------------------------------------------------------------------

    def list_lap_files(self) -> List[Path]:
        """Return all .csv files sorted by modification time (newest first)."""
        if not self._dir.exists():
            return []
        files = sorted(self._dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def load_lap(self, path: Path) -> Optional[pd.DataFrame]:
        """Load a lap CSV. Returns a DataFrame indexed by lap_progress (0-1)."""
        try:
            df = pd.read_csv(path)
            if df.empty:
                return None
            # Ensure lap_progress is monotonically increasing (handle wrap-arounds)
            df = df.sort_values("lap_progress").reset_index(drop=True)
            # Scale inputs to percentage display
            df["throttle"] = df["throttle"] * 100.0
            df["brake"]    = df["brake"]    * 100.0
            df["clutch"]   = df.get("clutch", pd.Series(0.0, index=df.index)) * 100.0
            return df
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return None

    def resample_to_distance(
        self, df: pd.DataFrame, n_points: int = 2000
    ) -> pd.DataFrame:
        """Resample DataFrame to uniform lap_progress grid (0→1) with n_points."""
        x_new = np.linspace(0.0, 1.0, n_points)
        result = {"lap_progress": x_new}
        x_old = df["lap_progress"].values
        for col in df.columns:
            if col == "lap_progress":
                continue
            try:
                y_old = df[col].values.astype(float)
                result[col] = np.interp(x_new, x_old, y_old)
            except Exception:
                pass
        return pd.DataFrame(result)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def channel_stats(self, df: pd.DataFrame, channels: List[str]) -> Dict[str, dict]:
        """Return min/max/mean/std for each channel."""
        stats = {}
        for ch in channels:
            if ch not in df.columns:
                continue
            s = df[ch].dropna()
            stats[ch] = {
                "min": float(s.min()),
                "max": float(s.max()),
                "mean": float(s.mean()),
                "std": float(s.std()),
            }
        return stats

    def compute_delta(
        self, ref_df: pd.DataFrame, lap_df: pd.DataFrame
    ) -> np.ndarray:
        """
        Compute lap-time delta between two laps at each track position.
        Returns array of delta_seconds (positive = lap is SLOWER than ref).
        """
        n = 2000
        ref_r = self.resample_to_distance(ref_df, n)
        lap_r = self.resample_to_distance(lap_df, n)

        ref_t = _cumulative_time(ref_r)
        lap_t = _cumulative_time(lap_r)

        return lap_t - ref_t

    def summary_for_ai(self, df: pd.DataFrame, lap_file: Path) -> str:
        """Generate a text summary of a lap for the AI advisor."""
        name = lap_file.stem
        stats = self.channel_stats(df, list(CHANNEL_LABELS.keys()))

        lines = [
            f"Lap file: {name}",
            f"Samples: {len(df)}",
            "",
            "Channel statistics (min / mean / max):",
        ]
        for ch, label in CHANNEL_LABELS.items():
            if ch in stats:
                s = stats[ch]
                lines.append(
                    f"  {label}: {s['min']:.2f} / {s['mean']:.2f} / {s['max']:.2f}"
                )

        # Throttle / brake application analysis
        if "throttle" in df.columns and "brake" in df.columns:
            full_throttle_pct = (df["throttle"] >= 95).mean() * 100
            heavy_brake_pct   = (df["brake"]    >= 70).mean() * 100
            lines += [
                "",
                f"Full throttle (>95%): {full_throttle_pct:.1f}% of lap",
                f"Heavy braking (>70%): {heavy_brake_pct:.1f}% of lap",
            ]

        if "g_lat" in df.columns:
            max_lat_g = df["g_lat"].abs().max()
            lines.append(f"Max lateral G: {max_lat_g:.2f} g")

        if "tyre_temp_fl" in df.columns:
            avg_temps = [df[f"tyre_temp_{w}"].mean() for w in ["fl", "fr", "rl", "rr"]]
            lines.append(
                f"Avg tyre temps (FL/FR/RL/RR): "
                + " / ".join(f"{t:.0f}°C" for t in avg_temps)
            )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cumulative_time(df: pd.DataFrame) -> np.ndarray:
    """Integrate speed over distance to get cumulative time array."""
    speed = df["speed_kmh"].values
    dist  = df["lap_progress"].values

    # Convert speed to m/s, distance to metres (estimate: 1 lap = 5000m)
    # For relative comparison, the absolute lap length cancels out.
    speed_ms = np.maximum(speed / 3.6, 0.1)   # avoid division by zero
    dx = np.diff(dist, prepend=dist[0])
    dt = dx / speed_ms
    return np.cumsum(dt)


def parse_lap_info_from_filename(filename: str) -> dict:
    """
    Parse metadata from CSV filename.
    Pattern: YYYYMMDD_HHMMSS_track_car_LapNN_time_validity.csv
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    info = {"raw": stem}
    if len(parts) >= 7:
        try:
            info["date"] = parts[0]
            info["time"] = parts[1]
            info["track"] = parts[2]
            info["car"] = parts[3]
            info["lap"] = parts[4].replace("Lap", "")
            info["laptime"] = (
                parts[5].replace("m", ":").replace("s", ".")[:-1]
                + parts[6].split(".")[0]
            )
        except Exception:
            pass
    return info
