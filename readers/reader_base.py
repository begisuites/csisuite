from typing import Iterable

class Reader(Iterable):
    def get_name(self) -> str:
        raise NotImplementedError("Reader must implement get_name()")
    def __iter__(self):
        raise NotImplementedError("Reader must implement __iter__()")