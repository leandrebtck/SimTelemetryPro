"""Lap recorder: buffers telemetry frames and saves completed laps as CSV."""
from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from .data_models import TelemetryFrame, LapData, CSV_COLUMNS, frame_to_row, ms_to_laptime


class LapRecorder:
    """Receives TelemetryFrame stream, detects lap completions, saves CSVs."""

    def __init__(
        self,
        recordings_dir: str = "data/recordings",
        on_lap_complete: Optional[Callable[[LapData], None]] = None,
        min_lap_ms: int = 30_000,   # ignore laps shorter than 30 s (out laps etc.)
    ):
        self._dir = Path(recordings_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._on_lap_complete = on_lap_complete
        self._min_lap_ms = min_lap_ms

        self._recording = False
        self._current_frames: List[TelemetryFrame] = []
        self._prev_lap_number = -1
        self._session_id = ""
        self._laps: List[LapData] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def current_lap_frames(self) -> int:
        return len(self._current_frames)

    @property
    def completed_laps(self) -> List[LapData]:
        return list(self._laps)

    def start(self) -> None:
        self._recording = True
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_frames.clear()
        self._prev_lap_number = -1
        self._laps.clear()

    def stop(self) -> None:
        self._recording = False

    def reset(self) -> None:
        self._current_frames.clear()
        self._prev_lap_number = -1
        self._laps.clear()

    def feed(self, frame: TelemetryFrame) -> None:
        """Feed a telemetry frame. Must be called from any thread."""
        if not self._recording:
            return

        # Initialise lap tracking on first frame
        if self._prev_lap_number < 0:
            self._prev_lap_number = frame.lap_number

        self._current_frames.append(frame)

        # Detect lap completion: lap_number incremented
        if frame.lap_number > self._prev_lap_number:
            lap_time_ms = frame.last_lap_ms
            self._save_lap(
                lap_number=self._prev_lap_number,
                lap_time_ms=lap_time_ms,
                is_valid=frame.is_valid_lap,
                sim=frame.sim,
                track=frame.track,
                car_model=frame.car_model,
            )
            self._prev_lap_number = frame.lap_number
            self._current_frames.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save_lap(
        self,
        lap_number: int,
        lap_time_ms: int,
        is_valid: bool,
        sim: str,
        track: str,
        car_model: str,
    ) -> None:
        frames = list(self._current_frames)
        if not frames or lap_time_ms < self._min_lap_ms:
            return

        lap = LapData(
            sim=sim,
            track=track,
            car_model=car_model,
            lap_number=lap_number,
            lap_time_ms=lap_time_ms,
            is_valid=is_valid,
            frames=frames,
            session_date=self._session_id,
        )
        self._laps.append(lap)

        # Build CSV filename
        valid_str = "valid" if is_valid else "invalid"
        track_safe = _safe_name(track)
        car_safe   = _safe_name(car_model)
        laptime_str = ms_to_laptime(lap_time_ms).replace(":", "m").replace(".", "s")
        filename = (
            f"{self._session_id}_{track_safe}_{car_safe}"
            f"_Lap{lap_number:02d}_{laptime_str}_{valid_str}.csv"
        )
        path = self._dir / filename

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for frame in frames:
                writer.writerow(frame_to_row(frame))

        if self._on_lap_complete:
            self._on_lap_complete(lap)


def _safe_name(s: str, maxlen: int = 20) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in s)
    return safe[:maxlen].strip("_") or "Unknown"
