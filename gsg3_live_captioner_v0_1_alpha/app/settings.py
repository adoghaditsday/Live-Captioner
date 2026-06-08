from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Optional

from .paths import SETTINGS_PATH
from .logger import logger


@dataclass
class Settings:
    model_size: str = "tiny.en"
    device: str = "cpu"
    compute_type: str = "int8"
    sample_rate: int = 16000
    chunk_seconds: float = 4.0
    device_index: Optional[int] = None
    caption_mode: str = "push_to_talk"  # continuous | push_to_talk | voice_activated
    caption_prefix: str = ""
    max_caption_chars: int = 160
    clear_after_seconds: float = 8.0
    ptt_key: str = "\\"
    mute_key: str = "f9"
    start_muted: bool = False
    noise_gate_enabled: bool = True
    noise_gate_threshold: float = 0.006
    write_obs_text: bool = True
    write_srt: bool = True
    write_transcript_log: bool = True
    write_twitch_queue: bool = False
    twitch_prefix: str = ""
    min_chars_to_post: int = 4
    tray_enabled: bool = False


def _coerce_float(value, default: float, minimum: float, maximum: float | None = None) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _coerce_int(value, default: int, minimum: int, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except Exception:
        return default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def validate_settings(settings: Settings) -> Settings:
    allowed_models = {"tiny.en", "base.en", "small.en"}
    if settings.model_size not in allowed_models:
        settings.model_size = "tiny.en"
    settings.device = "cpu"
    settings.compute_type = "int8"
    settings.sample_rate = _coerce_int(settings.sample_rate, 16000, 8000, 48000)
    settings.chunk_seconds = _coerce_float(settings.chunk_seconds, 4.0, 1.5, 15.0)
    settings.clear_after_seconds = _coerce_float(settings.clear_after_seconds, 8.0, 0.0, 120.0)
    settings.max_caption_chars = _coerce_int(settings.max_caption_chars, 160, 20, 450)
    settings.noise_gate_threshold = _coerce_float(settings.noise_gate_threshold, 0.006, 0.0, 1.0)
    settings.min_chars_to_post = _coerce_int(settings.min_chars_to_post, 4, 1, 200)
    if settings.caption_mode not in {"continuous", "push_to_talk", "voice_activated"}:
        settings.caption_mode = "push_to_talk"
    if not str(settings.ptt_key).strip():
        settings.ptt_key = "\\"
    if not str(settings.mute_key).strip():
        settings.mute_key = "f9"
    return settings


def load_settings() -> Settings:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            settings = Settings(**{**asdict(Settings()), **data})
            return validate_settings(settings)
        except Exception as exc:
            logger.exception("Failed to load settings; using defaults: %s", exc)
    return Settings()


def save_settings(settings: Settings) -> None:
    settings = validate_settings(settings)
    SETTINGS_PATH.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
