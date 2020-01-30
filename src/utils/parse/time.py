from src.utils import datetime

def duration(s: str):
    if s[0] == "+":
        duration = datetime.parse.from_pretty_time(s[1:])
        if not duration == None:
            return duration
    return None

