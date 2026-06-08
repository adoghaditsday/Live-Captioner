from __future__ import annotations

import numpy as np
import sounddevice as sd


def get_input_devices() -> list[tuple[int, str]]:
    devices: list[tuple[int, str]] = []
    for idx, dev in enumerate(sd.query_devices()):
        if int(dev.get("max_input_channels", 0)) > 0:
            devices.append((idx, dev.get("name", f"Device {idx}")))
    return devices


def record_chunk(sample_rate: int, chunk_seconds: float, device_index: int | None) -> np.ndarray:
    frames = int(sample_rate * chunk_seconds)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32", device=device_index)
    sd.wait()
    return audio.reshape(-1)


def rms_level(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))
