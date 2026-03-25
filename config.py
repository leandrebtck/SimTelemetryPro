"""Application configuration."""
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".sim_telemetry"
CONFIG_FILE = CONFIG_DIR / "config.json"
RECORDINGS_DIR = Path("data") / "recordings"

_defaults = {
    "anthropic_api_key": "",
    "recordings_dir": str(RECORDINGS_DIR),
    "poll_rate_hz": 60,
    "default_sim": "auto",  # "auto", "ac", "acc", "lmu"
    "ai_model": "claude-opus-4-6",
}


def load() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    Path(_defaults["recordings_dir"]).mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
        return {**_defaults, **saved}
    return dict(_defaults)


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key: str):
    return load().get(key, _defaults.get(key))


def set_key(key: str, value) -> None:
    cfg = load()
    cfg[key] = value
    save(cfg)
