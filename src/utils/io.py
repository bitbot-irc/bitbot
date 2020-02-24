import io

def open(path: str, mode: str):
    return io.open(path, mode=mode, encoding="utf8")
