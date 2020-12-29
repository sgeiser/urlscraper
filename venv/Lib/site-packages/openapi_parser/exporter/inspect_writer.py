import inspect
from abc import ABC
from typing import *

from openapi_parser.util.utils import StrIO
from .abstract_writer import Writer, yielder, writer
from .footer_writer import Exporting

class InspectWriter(Exporting, Writer, ABC):
    @property
    def type_vars(self) -> Iterator[Any]:
        raise NotImplementedError
    @property
    def utils(self) -> Iterator[Any]:
        raise NotImplementedError
    
    def dump_type_vars(self, items: Iterable[Union[str, Tuple[str, Tuple[Type, ...]]]] = None, *, ordered: bool = None) -> Iterator[str]:
        if (ordered is None):
            ordered = True
        if (items is None):
            items = self.type_vars
        items = map(lambda x: (x, tuple()) if (isinstance(x, str)) else x, items)
        if (ordered):
            items = sorted(items, key=lambda x: x[0])
        
        for t, args in items:
            yield t + ' = ' + self.constructor('TypeVar', repr(t), *(self.ref_name_pretty(arg) for arg in args))
    
    def dump_class_methods(self, module: object) -> Iterator[str]:
        # noinspection PyUnresolvedReferences
        for item in module.__export__:
            cls, _, name = item.partition('.')
            cls = getattr(module, cls)
            method = getattr(cls, name)
            yield from self.dump_util(name, method, export=False)
    
    def indent_len(self, s: str) -> int:
        return len(s) - len(s.lstrip())
    
    def deindent(self, lines: List[str]) -> Iterator[str]:
        indents: List[Tuple[int, str]] = list()
        indents.append((0, ''))
        indent_first_line: bool = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            _indent_len, _indent = indents[-1]
            
            if (not line.startswith(_indent)):
                indents.pop()
                continue
            
            line = line[_indent_len:]
            extra_indent_len = self.indent_len(line)
            if (extra_indent_len):
                indents.append((_indent_len + extra_indent_len, _indent + line[:extra_indent_len]))
                if (i == 0):
                    indent_first_line = True
                continue
            
            with self.indent(len(indents) - 1 - int(indent_first_line)):
                yield line
                i += 1
    
    def dump_util(self, ref_name: str, ref: Any, *, export: bool = True) -> Iterator[str]:
        if (export):
            self.export(ref_name)
        yield from self.deindent(inspect.getsource(ref).splitlines())
        yield
    
    def dump_utils(self, items: Iterable[Any] = None, *, ordered: bool = None) -> Iterator[str]:
        if (ordered is None):
            ordered = False
        if (items is None):
            items = self.utils
        
        items_dict = { self.ref_name_pretty(it).rpartition('.')[-1]: it for it in items }
        if (ordered):
            items_dict = { k: items_dict[k] for k in sorted(items_dict.keys()) }
        
        for ref_name, ref in items_dict.items():
            yield from self.dump_util(ref_name, ref)
    
    # region Writers
    @yielder
    def yield_type_vars(self, items: Iterable[str] = None, *, ordered: bool = None) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_type_vars(items, ordered=ordered)
    
    @overload
    def write_type_vars(self, items: Iterable[str] = None, *, ordered: bool = None) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_type_vars(self, items: Iterable[str] = None, *, ordered: bool = None, file: StrIO) -> None:
        pass
    @writer
    def write_type_vars(self, items: Iterable[str] = None, *, ordered: bool = None) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_type_vars(items, ordered=ordered)
    
    @yielder
    def yield_utils(self, items: Iterable[Any] = None, *, ordered: bool = None) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_utils(items, ordered=ordered)
    
    @overload
    def write_utils(self, items: Iterable[Any] = None, *, ordered: bool = None) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_utils(self, items: Iterable[Any] = None, *, ordered: bool = None, file: StrIO) -> None:
        pass
    @writer
    def write_utils(self, items: Iterable[Any] = None, *, ordered: bool = None) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_utils(items, ordered=ordered)
    # endregion


__all__ = \
[
    'InspectWriter',
]
