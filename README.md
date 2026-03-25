# SimTelemetry Pro

Racing telemetry application for **Assetto Corsa**, **Assetto Corsa Competizione** and **Le Mans Ultimate**, with live dashboard, lap recording, Motec-style analysis and an AI driving coach powered by Claude.

---

## Architecture

```
main.py                          ← Entry point
config.py                        ← Config management (~/.sim_telemetry/config.json)
src/
├── shared_memory/
│   ├── base_reader.py           ← Thread-based polling loop (60 Hz)
│   ├── ac_memory.py             ← AC ctypes structures + reader
│   ├── acc_memory.py            ← ACC ctypes structures + reader (extended)
│   └── lmu_memory.py            ← LMU/rF2 ctypes structures + reader
├── telemetry/
│   ├── data_models.py           ← TelemetryFrame dataclass + CSV columns
│   ├── recorder.py              ← Lap detection + CSV saving
│   └── analyzer.py             ← CSV loading, resampling, delta, stats
├── ai/
│   └── advisor.py               ← Claude API integration (analyze/compare/setup)
└── ui/
    ├── styles.py                ← Dark racing theme
    ├── main_window.py           ← Main window, sim auto-detection, tabs
    ├── live_dashboard.py        ← Steering wheel, pedal bars, tyre temps, times
    ├── analysis_view.py         ← Motec-like multi-channel comparison (pyqtgraph)
    └── ai_advisor_view.py       ← Chat-style AI advisor interface
```

---

## Features

### Live Telemetry

- Custom animated steering wheel (rotates ±450°)
- Colored throttle / brake / clutch vertical bars
- Gear display + RPM bar (green → yellow → red)
- Speed, current / last / best lap times, delta vs best
- Tyre inner / middle / outer temperatures (colour-coded cold → optimal → hot), pressures, wear
- TC / ABS / DRS indicators, fuel level, brake bias, water temperature

### Recording (F9 / F10 or toolbar button)

- Automatic lap detection from shared memory lap counter
- One CSV file per lap: `YYYYMMDD_HHMMSS_track_car_LapNN_time_valid.csv`
- 48 telemetry channels recorded at the sim's physics rate (~60 Hz)

### Analysis (Motec i2 style)

- Load multiple laps and overlay them with distinct colours
- Synchronized x-axis across all channel panels (Speed, Throttle, Brake, Steering, Gear, RPM, lateral/longitudinal G-forces…)
- Delta time panel vs a chosen reference lap
- Per-channel min / mean / max statistics table

### AI Advisor (Claude API)

- **Analyze a lap** — identifies braking points, throttle application, consistency issues
- **Compare vs reference lap** — pinpoints exactly where time is lost or gained
- **Setup recommendations** — suspension, aerodynamics, tyres, brakes with realistic numerical values
- **Free chat** — ask any question with the lap telemetry as context

---

## Simulator Compatibility

| Simulator | Shared Memory | Notes |
|-----------|---------------|-------|
| Assetto Corsa | `Local\acpmf_physics` / `_graphics` / `_static` | Fully supported |
| Assetto Corsa Competizione | `Local\acpmf_physics` / `_graphics` / `_static` | Extended ACC structures |
| Le Mans Ultimate | `$rFactor2SMMP_TelemetryV2$` / `ScoringV2$` | Requires rF2 shared memory plugin (auto-installed with LMU) |

---

## Installation (from source)

### Requirements

- Windows 10 / 11 (64-bit)
- Python 3.10 or later

### Steps

```bash
git clone <repo>
cd Telemetry_project
pip install -r requirements.txt
python main.py
```

---

## Installation (installer)

Run `SimTelemetryPro_Setup.exe` and follow the wizard.
The application will be installed to `C:\Program Files\SimTelemetry Pro\` by default.

---

## First Run

1. Launch the application — it will auto-detect any running simulator.
2. Start your simulator and load a session.
3. Press **F9** (or click **● REC**) to begin recording laps.
4. After driving, press **F10** to stop. CSV files are saved to `Documents\SimTelemetry\recordings\`.
5. Switch to the **Analysis** tab to load and compare your laps.
6. Open the **AI Advisor** tab, enter your Anthropic API key in **Settings**, then click **Analyze Selected Lap**.

---

## AI Setup

The AI Advisor uses the [Anthropic Claude API](https://www.anthropic.com).

1. Create a free account at [console.anthropic.com](https://console.anthropic.com)
2. Generate an API key (starts with `sk-ant-...`)
3. Enter it in **Settings → Anthropic API Key** (or directly in the AI Advisor tab)

The default model is **Claude Opus 4.6** for the highest quality analysis. You can switch to Sonnet or Haiku in Settings for faster / cheaper responses.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F9  | Start recording |
| F10 | Stop recording |
| Ctrl+Q | Quit |

---

## Telemetry CSV Columns

`timestamp_ms`, `lap_progress`, `speed_kmh`, `gear`, `rpm`, `throttle`, `brake`, `clutch`, `steering`, `g_lat`, `g_lon`, `g_vert`, `tyre_temp_fl/fr/rl/rr`, `tyre_temp_i/o_fl/fr/rl/rr`, `tyre_pressure_fl/fr/rl/rr`, `tyre_wear_fl/fr/rl/rr`, `suspension_fl/fr/rl/rr`, `brake_temp_fl/fr/rl/rr`, `fuel`, `brake_bias`, `ride_height_front/rear`, `water_temp`, `pit_limiter`, `tc_active`, `abs_active`, `drs_active`

---

## License

MIT
