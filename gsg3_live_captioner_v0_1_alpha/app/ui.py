from __future__ import annotations

import os
import queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from . import __version__
from .audio import get_input_devices
from .hotkeys import HotkeyManager
from .logger import logger
from .paths import OUTPUT_DIR, OBS_TEXT_PATH, SRT_PATH, TRANSCRIPT_LOG_PATH, TWITCH_QUEUE_PATH, APP_LOG_PATH
from .settings import Settings, load_settings, save_settings, validate_settings
from .utils import now_stamp
from .whisper_worker import CaptionWorker

APP_NAME = f"GSG3 Live Captioner {__version__}"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("960x720")
        self.minsize(840, 620)

        self.settings = load_settings()
        self.events: queue.Queue = queue.Queue()
        self.worker: CaptionWorker | None = None
        self.is_running = False
        self.ptt_pressed = False
        self.mic_muted = bool(self.settings.start_muted)
        self.hotkeys = HotkeyManager()
        self.devices: list[tuple[int, str]] = []

        self.status_var = tk.StringVar(value="Ready")
        self.mute_status_var = tk.StringVar(value="Mic input: MUTED" if self.mic_muted else "Mic input: Unmuted")
        self.device_var = tk.StringVar()
        self.model_var = tk.StringVar(value=self.settings.model_size)
        self.mode_var = tk.StringVar(value=self.settings.caption_mode)
        self.chunk_var = tk.StringVar(value=str(self.settings.chunk_seconds))
        self.clear_var = tk.StringVar(value=str(self.settings.clear_after_seconds))
        self.prefix_var = tk.StringVar(value=self.settings.caption_prefix)
        self.ptt_key_var = tk.StringVar(value=self.settings.ptt_key)
        self.mute_key_var = tk.StringVar(value=self.settings.mute_key)
        self.noise_gate_var = tk.BooleanVar(value=self.settings.noise_gate_enabled)
        self.noise_gate_threshold_var = tk.StringVar(value=str(self.settings.noise_gate_threshold))
        self.obs_var = tk.BooleanVar(value=self.settings.write_obs_text)
        self.srt_var = tk.BooleanVar(value=self.settings.write_srt)
        self.log_var = tk.BooleanVar(value=self.settings.write_transcript_log)
        self.twitch_var = tk.BooleanVar(value=self.settings.write_twitch_queue)
        self.twitch_prefix_var = tk.StringVar(value=self.settings.twitch_prefix)
        self.min_chars_var = tk.StringVar(value=str(self.settings.min_chars_to_post))

        self._build_ui()
        self._refresh_devices()
        self._bind_hotkeys()
        self._update_mute_ui()
        self.after(100, self._process_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        logger.info("Application started")

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root)
        top.pack(fill="x")
        ttk.Label(top, textvariable=self.status_var, font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(top, text="Open Output Folder", command=self._open_output_folder).pack(side="right", padx=4)
        ttk.Button(top, text="Open Log", command=self._open_app_log).pack(side="right", padx=4)
        ttk.Button(top, text="Export Transcript", command=self._export_transcript).pack(side="right", padx=4)

        controls = ttk.LabelFrame(root, text="Controls", padding=10)
        controls.pack(fill="x", pady=(12, 8))
        self.start_btn = ttk.Button(controls, text="Start Listening", command=self._toggle_start)
        self.start_btn.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(controls, text="Clear Caption", command=self._clear_caption).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(controls, text="Save Settings", command=self._save_from_ui).grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        self.mute_btn = ttk.Button(controls, text="Mute Mic Input", command=self._toggle_mute)
        self.mute_btn.grid(row=0, column=3, padx=4, pady=4, sticky="ew")
        ttk.Label(controls, textvariable=self.mute_status_var).grid(row=0, column=4, padx=10, pady=4, sticky="w")

        ttk.Label(controls, text="Caption mode:").grid(row=1, column=0, sticky="w", padx=4)
        ttk.Combobox(controls, textvariable=self.mode_var, state="readonly", values=["continuous", "push_to_talk", "voice_activated"], width=18).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(controls, text="PTT key:").grid(row=1, column=2, sticky="e", padx=4)
        ttk.Entry(controls, textvariable=self.ptt_key_var, width=10).grid(row=1, column=3, sticky="w", padx=4)
        ttk.Label(controls, text="Mute key:").grid(row=1, column=4, sticky="e", padx=4)
        ttk.Entry(controls, textvariable=self.mute_key_var, width=10).grid(row=1, column=5, sticky="w", padx=4)
        ttk.Label(controls, text="Defaults: PTT=\\, Mute=F9").grid(row=1, column=6, sticky="w", padx=4)

        settings_frame = ttk.LabelFrame(root, text="Audio / Transcription", padding=10)
        settings_frame.pack(fill="x", pady=8)
        ttk.Label(settings_frame, text="Microphone:").grid(row=0, column=0, sticky="w")
        self.device_combo = ttk.Combobox(settings_frame, textvariable=self.device_var, state="readonly", width=70)
        self.device_combo.grid(row=0, column=1, columnspan=4, sticky="ew", padx=6, pady=3)
        ttk.Button(settings_frame, text="Refresh Devices", command=self._refresh_devices).grid(row=0, column=5, padx=4)

        ttk.Label(settings_frame, text="Model:").grid(row=1, column=0, sticky="w")
        ttk.Combobox(settings_frame, textvariable=self.model_var, state="readonly", values=["tiny.en", "base.en", "small.en"], width=14).grid(row=1, column=1, sticky="w", padx=6, pady=3)
        ttk.Label(settings_frame, text="Chunk seconds:").grid(row=1, column=2, sticky="e")
        ttk.Entry(settings_frame, textvariable=self.chunk_var, width=8).grid(row=1, column=3, sticky="w", padx=6)
        ttk.Label(settings_frame, text="Clear after:").grid(row=1, column=4, sticky="e")
        ttk.Entry(settings_frame, textvariable=self.clear_var, width=8).grid(row=1, column=5, sticky="w", padx=6)

        ttk.Label(settings_frame, text="Caption prefix:").grid(row=2, column=0, sticky="w")
        ttk.Entry(settings_frame, textvariable=self.prefix_var, width=28).grid(row=2, column=1, sticky="w", padx=6)
        ttk.Checkbutton(settings_frame, text="Enable RMS noise gate", variable=self.noise_gate_var, command=self._save_from_ui).grid(row=2, column=2, sticky="w")
        ttk.Label(settings_frame, text="Gate threshold:").grid(row=2, column=3, sticky="e")
        ttk.Entry(settings_frame, textvariable=self.noise_gate_threshold_var, width=8).grid(row=2, column=4, sticky="w", padx=6)
        ttk.Label(settings_frame, text="0.004 quiet / 0.010 strict").grid(row=2, column=5, sticky="w")

        output = ttk.LabelFrame(root, text="Output Options", padding=10)
        output.pack(fill="x", pady=8)
        ttk.Checkbutton(output, text="Write OBS captions.txt", variable=self.obs_var, command=self._save_from_ui).grid(row=0, column=0, sticky="w", padx=4)
        ttk.Checkbutton(output, text="Write captions.srt", variable=self.srt_var, command=self._save_from_ui).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Checkbutton(output, text="Write transcript_log.txt", variable=self.log_var, command=self._save_from_ui).grid(row=0, column=2, sticky="w", padx=4)
        ttk.Checkbutton(output, text="Write twitch_chat_queue.txt", variable=self.twitch_var, command=self._save_from_ui).grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(output, text="Twitch prefix:").grid(row=1, column=0, sticky="e", padx=4)
        ttk.Entry(output, textvariable=self.twitch_prefix_var, width=20).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(output, text="Min chars:").grid(row=1, column=2, sticky="e", padx=4)
        ttk.Entry(output, textvariable=self.min_chars_var, width=8).grid(row=1, column=3, sticky="w", padx=4)

        transcript_frame = ttk.LabelFrame(root, text="Live Transcript", padding=10)
        transcript_frame.pack(fill="both", expand=True, pady=8)
        self.transcript = tk.Text(transcript_frame, wrap="word", height=14)
        self.transcript.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(transcript_frame, command=self.transcript.yview)
        scroll.pack(side="right", fill="y")
        self.transcript.configure(yscrollcommand=scroll.set)

        paths = ttk.LabelFrame(root, text="Files", padding=10)
        paths.pack(fill="x", pady=8)
        for label in [
            f"OBS Text: {OBS_TEXT_PATH}",
            f"SRT Captions: {SRT_PATH}",
            f"Transcript Log: {TRANSCRIPT_LOG_PATH}",
            f"Twitch Queue: {TWITCH_QUEUE_PATH}",
            f"App Log: {APP_LOG_PATH}",
        ]:
            ttk.Label(paths, text=label).pack(anchor="w")

        settings_frame.columnconfigure(1, weight=1)

    def _refresh_devices(self):
        try:
            self.devices = get_input_devices()
            labels = [f"{idx}: {name}" for idx, name in self.devices]
            self.device_combo["values"] = labels
            chosen = None
            if self.settings.device_index is not None:
                for idx, name in self.devices:
                    if idx == self.settings.device_index:
                        chosen = f"{idx}: {name}"
                        break
            if chosen:
                self.device_var.set(chosen)
            elif labels:
                self.device_var.set(labels[0])
            else:
                self.device_var.set("")
            self.status_var.set("Audio devices refreshed")
        except Exception as exc:
            logger.exception("Could not query audio devices")
            messagebox.showwarning("Audio device warning", f"Could not query audio devices:\n{exc}")

    def _save_from_ui(self):
        try:
            selected = self.device_var.get()
            if selected:
                self.settings.device_index = int(selected.split(":", 1)[0])
            self.settings.model_size = self.model_var.get() or "tiny.en"
            self.settings.caption_mode = self.mode_var.get() or "push_to_talk"
            self.settings.chunk_seconds = self._safe_float(self.chunk_var.get(), 4.0)
            self.settings.clear_after_seconds = self._safe_float(self.clear_var.get(), 8.0)
            self.settings.caption_prefix = self.prefix_var.get()
            self.settings.ptt_key = self.ptt_key_var.get().strip() or "\\"
            self.settings.mute_key = self.mute_key_var.get().strip() or "f9"
            self.settings.start_muted = bool(self.mic_muted)
            self.settings.noise_gate_enabled = bool(self.noise_gate_var.get())
            self.settings.noise_gate_threshold = self._safe_float(self.noise_gate_threshold_var.get(), 0.006)
            self.settings.write_obs_text = bool(self.obs_var.get())
            self.settings.write_srt = bool(self.srt_var.get())
            self.settings.write_transcript_log = bool(self.log_var.get())
            self.settings.write_twitch_queue = bool(self.twitch_var.get())
            self.settings.twitch_prefix = self.twitch_prefix_var.get()
            self.settings.min_chars_to_post = self._safe_int(self.min_chars_var.get(), 4)
            self.settings = validate_settings(self.settings)
            save_settings(self.settings)
            if self.worker:
                self.worker.settings = self.settings
                self._sync_worker_pause_state()
            self._bind_hotkeys()
            self._update_mute_ui()
            self.status_var.set("Settings saved")
            logger.info("Settings saved")
        except Exception as exc:
            logger.exception("Settings save failed")
            messagebox.showerror("Settings error", str(exc))

    @staticmethod
    def _safe_float(value: str, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _safe_int(value: str, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _bind_hotkeys(self):
        ok, message = self.hotkeys.bind(
            self.settings.ptt_key,
            self.settings.mute_key,
            lambda: self.after(0, self._global_ptt_down),
            lambda: self.after(0, self._global_ptt_up),
            lambda: self.after(0, self._toggle_mute),
        )
        self.status_var.set(message if ok else f"Global hotkey warning: {message}")

    def _global_ptt_down(self):
        self.ptt_pressed = True
        self._sync_worker_pause_state()
        if self.settings.caption_mode == "push_to_talk" and not self.mic_muted:
            self.status_var.set(f"Listening while {self.settings.ptt_key} is held")

    def _global_ptt_up(self):
        self.ptt_pressed = False
        self._sync_worker_pause_state()
        if self.settings.caption_mode == "push_to_talk" and not self.mic_muted:
            self.status_var.set("Push-to-talk armed")

    def _toggle_mute(self):
        self.mic_muted = not self.mic_muted
        self.settings.start_muted = bool(self.mic_muted)
        save_settings(self.settings)
        self._sync_worker_pause_state()
        self._update_mute_ui()
        logger.info("Mic muted=%s", self.mic_muted)

    def _update_mute_ui(self):
        if self.mic_muted:
            self.mute_status_var.set("Mic input: MUTED")
            self.mute_btn.configure(text="Unmute Mic Input")
            self.status_var.set(f"Mic input muted. Press {self.settings.mute_key} to unmute.")
        else:
            self.mute_status_var.set("Mic input: Unmuted")
            self.mute_btn.configure(text="Mute Mic Input")
            if self.settings.caption_mode == "push_to_talk" and not self.ptt_pressed:
                self.status_var.set("Push-to-talk armed")
            elif self.is_running:
                self.status_var.set("Listening")

    def _sync_worker_pause_state(self):
        if not self.worker:
            return
        should_pause = self.mic_muted or (self.settings.caption_mode == "push_to_talk" and not self.ptt_pressed)
        self.worker.set_paused(should_pause)

    def _toggle_start(self):
        if not self.is_running:
            self._save_from_ui()
            self.worker = CaptionWorker(self.settings, self.events)
            self._sync_worker_pause_state()
            self.worker.start()
            self.is_running = True
            self.start_btn.configure(text="Stop Listening")
        else:
            if self.worker:
                self.worker.stop()
                self.worker = None
            self.is_running = False
            self.start_btn.configure(text="Start Listening")
            self.status_var.set("Stopped")

    def _process_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.status_var.set(payload)
                elif kind == "caption":
                    self.transcript.insert("end", f"[{now_stamp()}] {payload}\n")
                    self.transcript.see("end")
                elif kind == "error":
                    self.status_var.set(f"Error: {payload}")
                    self.transcript.insert("end", f"[ERROR] {payload}\n")
                    self.transcript.see("end")
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def _clear_caption(self):
        OBS_TEXT_PATH.write_text("", encoding="utf-8")
        self.status_var.set("Caption cleared")

    def _open_output_folder(self):
        os.startfile(str(OUTPUT_DIR))

    def _open_app_log(self):
        os.startfile(str(APP_LOG_PATH))

    def _export_transcript(self):
        target = filedialog.asksaveasfilename(
            title="Export transcript log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not target:
            return
        source_text = TRANSCRIPT_LOG_PATH.read_text(encoding="utf-8") if TRANSCRIPT_LOG_PATH.exists() else ""
        Path(target).write_text(source_text, encoding="utf-8")
        messagebox.showinfo("Export complete", f"Transcript exported to:\n{target}")

    def _on_close(self):
        if self.worker:
            self.worker.stop()
        self.hotkeys.clear()
        logger.info("Application closed")
        self.destroy()


def run_app():
    App().mainloop()
