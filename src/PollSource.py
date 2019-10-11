import typing

class PollSource(object):
    def get_readables(self) -> typing.List[int]:
        return []
    def get_writables(self) -> typing.List[int]:
        return []

    def is_readable(self, fileno: int):
        pass
    def is_writable(self, fileno: int):
        pass
