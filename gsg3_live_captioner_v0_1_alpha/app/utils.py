import datetime as dt


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def srt_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    ms = int((seconds - int(seconds)) * 1000)
    sec = int(seconds) % 60
    minutes = (int(seconds) // 60) % 60
    hours = int(seconds) // 3600
    return f"{hours:02}:{minutes:02}:{sec:02},{ms:03}"
