import typing

class PollHook(object):
    def next(self) -> typing.Optional[float]:
        return None
    def call(self):
        return None
