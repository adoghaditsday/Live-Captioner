from __future__ import annotations

import queue
import threading
import time
from typing import Optional

from faster_whisper import WhisperModel

from .audio import record_chunk, rms_level
from .logger import logger
from .paths import OBS_TEXT_PATH, SRT_PATH, TRANSCRIPT_LOG_PATH, TWITCH_QUEUE_PATH
from .settings import Settings
from .utils import now_stamp, srt_timestamp


class CaptionWorker:
    def __init__(self, settings: Settings, event_queue: queue.Queue):
        self.settings = settings
        self.event_queue = event_queue
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.model: Optional[WhisperModel] = None
        self.thread: Optional[threading.Thread] = None
        self.srt_index = 1
        self.start_time = time.monotonic()
        self.last_caption_time = 0.0

    def start(self) -> None:
        logger.info("Caption worker starting")
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        logger.info("Caption worker stopping")
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def set_paused(self, paused: bool) -> None:
        if paused:
            self.pause_event.set()
        else:
            self.pause_event.clear()

    def _emit(self, kind: str, payload: str) -> None:
        self.event_queue.put((kind, payload))

    def _load_model(self) -> None:
        self._emit("status", f"Loading Whisper model: {self.settings.model_size} / CPU")
        self.model = WhisperModel(
            self.settings.model_size,
            device="cpu",
            compute_type="int8",
        )
        self._emit("status", "Listening")
        logger.info("Whisper model loaded: %s", self.settings.model_size)

    def _run(self) -> None:
        try:
            self._load_model()
        except Exception as exc:
            logger.exception("Model load failed")
            self._emit("error", f"Model load failed: {exc}")
            return

        if self.settings.write_obs_text:
            OBS_TEXT_PATH.write_text("", encoding="utf-8")

        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.05)
                continue

            try:
                audio = record_chunk(self.settings.sample_rate, self.settings.chunk_seconds, self.settings.device_index)
                if self.stop_event.is_set():
                    break

                level = rms_level(audio)
                gate_active = self.settings.noise_gate_enabled or self.settings.caption_mode == "voice_activated"
                if gate_active and level < self.settings.noise_gate_threshold:
                    self._maybe_clear_caption()
                    continue

                assert self.model is not None
                segments, _info = self.model.transcribe(
                    audio,
                    language="en",
                    beam_size=1,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                text = " ".join(seg.text.strip() for seg in segments).strip()
                if not text:
                    self._maybe_clear_caption()
                    continue

                self._handle_caption(text)
            except Exception as exc:
                logger.exception("Caption loop error")
                self._emit("error", str(exc))
                time.sleep(0.5)

        self._emit("status", "Stopped")
        logger.info("Caption worker stopped")

    def _maybe_clear_caption(self) -> None:
        if not self.settings.write_obs_text:
            return
        if self.settings.clear_after_seconds <= 0:
            return
        if self.last_caption_time and time.monotonic() - self.last_caption_time > self.settings.clear_after_seconds:
            OBS_TEXT_PATH.write_text("", encoding="utf-8")
            self.last_caption_time = 0.0

    def _handle_caption(self, raw_text: str) -> None:
        text = " ".join(raw_text.split())
        if len(text) > self.settings.max_caption_chars:
            text = text[-self.settings.max_caption_chars :].strip()
        caption = f"{self.settings.caption_prefix}{text}"

        if self.settings.write_obs_text:
            OBS_TEXT_PATH.write_text(caption, encoding="utf-8")
            self.last_caption_time = time.monotonic()

        elapsed_start = max(0.0, time.monotonic() - self.start_time - self.settings.chunk_seconds)
        elapsed_end = time.monotonic() - self.start_time

        if self.settings.write_srt:
            with SRT_PATH.open("a", encoding="utf-8") as f:
                f.write(f"{self.srt_index}\n")
                f.write(f"{srt_timestamp(elapsed_start)} --> {srt_timestamp(elapsed_end)}\n")
                f.write(f"{caption}\n\n")
            self.srt_index += 1

        if self.settings.write_transcript_log:
            with TRANSCRIPT_LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(f"[{now_stamp()}] {caption}\n")

        if self.settings.write_twitch_queue and len(text) >= self.settings.min_chars_to_post:
            with TWITCH_QUEUE_PATH.open("a", encoding="utf-8") as f:
                f.write(f"{self.settings.twitch_prefix}{text}\n")

        self._emit("caption", caption)
