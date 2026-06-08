from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "settings.json"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
OBS_TEXT_PATH = OUTPUT_DIR / "captions.txt"
SRT_PATH = OUTPUT_DIR / "captions.srt"
TRANSCRIPT_LOG_PATH = OUTPUT_DIR / "transcript_log.txt"
TWITCH_QUEUE_PATH = OUTPUT_DIR / "twitch_chat_queue.txt"
APP_LOG_PATH = LOG_DIR / "app.log"

for folder in (OUTPUT_DIR, LOG_DIR):
    folder.mkdir(exist_ok=True)
for file_path in (OBS_TEXT_PATH, SRT_PATH, TRANSCRIPT_LOG_PATH, TWITCH_QUEUE_PATH, APP_LOG_PATH):
    file_path.touch(exist_ok=True)
