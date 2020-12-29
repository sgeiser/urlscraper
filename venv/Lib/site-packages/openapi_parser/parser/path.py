from abc import ABC
from dataclasses import field, dataclass
from functools import partial
from typing import *

from openapi_parser.model import HavingPath, ModelSchema
from openapi_parser.util.typing_proxy import extract_generic, GenericProxy
from .filters import find_filters

def split_path_left(path: str) -> Tuple[str, str, str]:
    left, sep, right = path.partition('/')
    if (left.startswith('[')):
        left, _, right = path.partition(']')
        _, sep, right = right.partition('/')
        left = left[1:]
    
    return left, sep, right

def split_path_right(path: str) -> Tuple[str, str, str]:
    left, sep, right = path.rpartition('/')
    if (right.endswith(']')):
        left, _, right = path.rpartition('[')
        left, sep, _ = right.rpartition('/')
        right = right[:-1]
    
    return left, sep, right

def split_path(path: str) -> Iterator[str]:
    while path:
        left, _, path = split_path_left(path)
        yield left

def split_path_reversed(path: str):
    while path:
        path, _, right = split_path_right(path)
        yield right


class Intermediate(HavingPath, ABC):
    pass

@dataclass
class HavingPathImpl(HavingPath, ABC):
    name: str = field(init=False)
    path: str = field(init=False)
    is_top_level: bool = field(init=False, default=False)
    
    _pretty_path: str = field(init=False, default=None)
    @property
    def pretty_path(self) -> str:
        return self._pretty_path
    @pretty_path.setter
    def pretty_path(self, value: Optional[str]):
        if (value is None):
            if (self.is_top_level):
                value = self.name
            else:
                value = self.path
        
        self._pretty_path_setter(value)
        self._pretty_path = value
    
    def _pretty_path_setter(self, value: Optional[str]):
        old_value = self._pretty_path
        self._pretty_path = value
        # noinspection PyTypeChecker
        self.recursive_update(partial(type(self)._update_child_pretty_path, old=old_value))
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        raise NotImplementedError
    
    def recursive_update(self, mapping: Callable[[HavingPath, HavingPath], Any], *, ignore_top_level: bool = True):
        children = list(self._child_items())
        i: int = 0
        while i < len(children):
            child = children[i]
            i += 1
            
            if (isinstance(child, ModelSchema)):
                children.extend(find_filters(child.filter, HavingPath))
                child = child.cls
            
            if (child is None):
                continue
            
            # noinspection PyTypeChecker
            is_generic, base, args = extract_generic(child)
            if (not is_generic):
                args = [ base ]
            for cls in args:
                if (isinstance(cls, HavingPath)):
                    if (ignore_top_level and cls.is_top_level):
                        continue
                    else:
                        mapping(self, cls)
                        cls.recursive_update(mapping, ignore_top_level=ignore_top_level)
    
    def _update_child_pretty_path(self, child: HavingPath, *, old: Optional[str]):
        if (old is not None and child.pretty_path.startswith(old)):
            child.pretty_path = self.pretty_path + child.pretty_path[len(old):]
        elif (isinstance(self, Intermediate)):
            parent_pretty_path, sep, _ = split_path_right(self.pretty_path)
            child.pretty_path = parent_pretty_path + sep + child.name
        else:
            child.pretty_path = self.pretty_path + '/' + child.name

__all__ = \
[
    'split_path',
    'split_path_left',
    'split_path_reversed',
    'split_path_right',
    
    'HavingPathImpl',
    'Intermediate',
]
