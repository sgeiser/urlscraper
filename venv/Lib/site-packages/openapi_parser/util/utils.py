import re
import typing
from enum import Enum
from typing import *

from functional import Option, OptionNone, Some
from typing.re import *

StrIO = Union[typing.TextIO, typing.IO[str]]

class SearchableEnum(Enum):
    @classmethod
    def values(cls) -> set:
        return set(x.value for x in cls)
    @classmethod
    def contains_value(cls, value) -> bool:
        return value in cls.values()

T = TypeVar('T')
# noinspection PyTypeChecker
Opt = TypeVar('Opt', Option[T], Optional[T])
def mix_options(*options: Opt) -> Option[List[T]]:
    lst = list(_mix_options(options))
    if (not lst):
        return OptionNone
    else:
        # noinspection PyTypeChecker
        return Some(lst)

def _mix_options(options: Iterable[Opt]) -> Iterator[T]:
    for op in options:
        if (not Option.is_option(op)):
            op = Option(op)
        yield from op

def combine_regular_expressions(regulars: List[Union[AnyStr, Pattern[AnyStr]]]) -> Pattern[AnyStr]:
    # Works only for full-matches
    items: Set[Pattern[str]] = set()
    for r in regulars:
        if (isinstance(r, (str, bytes))):
            r = re.compile(r)
        items.add(r)
    
    if (len(items) == 1):
        return items.pop()
    
    return re.compile(rf"(?!{ '|'.join(fr'(?!{_pattern(p)})' for p in items) })(?:^.*$)")

def _pattern(p: Pattern[AnyStr]) -> str:
    p = p.pattern
    if (isinstance(p, bytes)):
        return p.decode()
    else:
        return p

K = TypeVar('K')
V = TypeVar('V')
def dict_safe_merge(dicts: Iterable[Dict[K, V]]) -> Dict[K, V]:
    result = dict()
    for d in dicts:
        for k, v in d.items():
            if (k not in result):
                result[k] = v
            elif (result[k] != v):
                # ToDo: Mixing of dictionaries error
                raise ValueError
    
    return result

def list_pop_any(lst: List[T], *items: T, pop: bool = True, find_all: bool = False) -> Optional[T]:
    """ Find first occurrence of items from the sequence and pop it from the list """
    
    result: Option[T] = OptionNone
    for i in items:
        if (i in lst):
            if (pop): lst.remove(i)
            if (find_all): result = result or Some(i)
            else: return i
    
    return result.as_optional

__all__ = \
[
    'StrIO',
    'SearchableEnum',
    
    'combine_regular_expressions',
    'dict_safe_merge',
    'list_pop_any',
    'mix_options',
]
__pdoc_extras__ = \
[
    'StrIO',
]
