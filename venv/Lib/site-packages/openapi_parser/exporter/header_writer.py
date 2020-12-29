from abc import ABC
from typing import *

from openapi_parser.util.utils import StrIO
from .abstract_writer import Writer, yielder, writer

class HeaderWriter(Writer, ABC):
    @property
    def from_imports(self) -> Iterator[str]:
        raise NotImplementedError
    
    @classmethod
    def objects_to_from_imports(cls, items: Iterable[object]) -> Iterator[str]:
        for item in items:
            yield cls.ref_name_pretty(item, full=True)
    
    def dump_headers(self, items: Iterable[str] = None, *, ordered: bool = None) -> Iterator[str]:
        if (items is None):
            items = self.from_imports
        if (ordered is None):
            ordered = True
        if (ordered):
            items = sorted(items)
        
        for from_import in items:
            left, sep, right = from_import.rpartition('.')
            yield f'from {left} import {right}'
        yield
    
    # region Writers
    @yielder
    def yield_headers(self, items: Iterable[str] = None, *, ordered: bool = None) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_headers(items, ordered=ordered)
    
    @overload
    def write_headers(self, items: Iterable[str] = None, *, ordered: bool = None) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_headers(self, items: Iterable[str] = None, *, ordered: bool = None, file: StrIO) -> None:
        pass
    @writer
    def write_headers(self, items: Iterable[str] = None, *, ordered: bool = None) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_headers(items, ordered=ordered)
    # endregion


__all__ = \
[
    'HeaderWriter',
]
