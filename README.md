# GSG3 Live Captioner

**Version:** `v0.1.0-alpha`

A Windows-focused local speech-to-text captioning utility for OBS and Twitch bot workflows.

This is an early alpha. It is designed for personal streaming setups where you want speech-to-text captions without broadcasting your microphone audio.

## Features

- Local CPU Whisper transcription via `faster-whisper`
- Microphone/device selector
- Caption modes:
  - Continuous
  - Push-to-talk
  - Voice activated
- Global push-to-talk keybind, default `\`
- Global mute/unmute keybind, default `F9`
- Built-in RMS noise gate
- OBS `captions.txt` output
- SRT subtitle export
- Transcript log export
- Twitch queue file for a Node/TMI.js bot to watch
- App log at `logs/app.log`
- PyInstaller build script for one-folder EXE builds

## Installation from source

1. Install Python 3.10 or 3.11.
2. Extract this folder somewhere clean.
3. Run:

```bat
install_requirements.bat
```

4. Run:

```bat
run_captioner.bat
```

## OBS Setup

In OBS:

1. Add a `Text (GDI+)` source.
2. Enable `Read from file`.
3. Select:

```text
output/captions.txt
```

Mute your OBS microphone source if you do not want viewers to hear your mic.

## Global Hotkeys

Default keys:

```text
Push-to-talk: \
Mute/unmute: F9
```

If hotkeys do not work while a game is focused, run the captioner as Administrator.

## Twitch Bot Integration

Enable:

```text
Write twitch_chat_queue.txt
```

Then make your Twitch bot watch:

```text
output/twitch_chat_queue.txt
```

Use `twitch_bot_caption_watcher_example.js` as the clean watcher reference.

## Build EXE

Run:

```bat
build_exe.bat
```

The EXE will be in:

```text
dist/GSG3_Live_Captioner/GSG3_Live_Captioner.exe
```

Do not move only the `.exe`. Keep the whole folder together.

## Known Limitations

- Global hotkeys may require Administrator privileges.
- This is CPU-only by design to avoid CUDA/cuBLAS errors.
- It does not directly authenticate with Twitch; it writes a queue file for your existing bot.
- Noise filtering is basic RMS gating. NVIDIA Broadcast or another noise-reduced virtual mic is still recommended.


Use:

```text
v0.1.0-alpha
```

This should be treated as an early alpha, not a stable public utility yet.
