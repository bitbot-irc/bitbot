import typing

def try_int(s: str) -> typing.Optional[int]:
    try:
        return int(s)
    except ValueError:
        return None

