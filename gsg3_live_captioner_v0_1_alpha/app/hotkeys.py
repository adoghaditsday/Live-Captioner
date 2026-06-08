from __future__ import annotations

try:
    import keyboard
except Exception:
    keyboard = None

from .logger import logger


def normalize_hotkey_name(value: str) -> str:
    key = (value or "").strip()
    if not key:
        return ""
    aliases = {
        "spacebar": "space",
        "esc": "escape",
        "backslash": "\\",
        "\\": "\\",
    }
    return aliases.get(key.lower(), key.lower() if len(key) > 1 else key)


class HotkeyManager:
    def __init__(self):
        self.available = keyboard is not None

    def clear(self) -> None:
        if keyboard is None:
            return
        try:
            keyboard.unhook_all_hotkeys()
            keyboard.unhook_all()
        except Exception as exc:
            logger.warning("Failed clearing hotkeys: %s", exc)

    def bind(self, ptt_key: str, mute_key: str, on_ptt_down, on_ptt_up, on_mute_toggle) -> tuple[bool, str]:
        if keyboard is None:
            return False, "keyboard package is not installed"
        self.clear()
        try:
            ptt = normalize_hotkey_name(ptt_key or "\\")
            mute = normalize_hotkey_name(mute_key or "f9")
            keyboard.on_press_key(ptt, lambda _event: on_ptt_down(), suppress=False)
            keyboard.on_release_key(ptt, lambda _event: on_ptt_up(), suppress=False)
            keyboard.add_hotkey(mute, on_mute_toggle, suppress=False)
            logger.info("Global hotkeys armed: PTT=%s Mute=%s", ptt, mute)
            return True, f"Global hotkeys armed: PTT={ptt_key}, Mute={mute_key}"
        except Exception as exc:
            logger.exception("Global hotkey bind failed")
            return False, str(exc)
