from collections import UserDict
from io import StringIO
from typing import *

from typing.io import *

T = TypeVar('T')
_WILDCARD_ARGUMENT = object()
_DEFAULT_ARGUMENT = object()
_WildcardArgumentType = type(_WILDCARD_ARGUMENT)
AnyArg = Union[str, _WildcardArgumentType]
DataType = Dict[str, T]

class PathTreeMap(UserDict, DataType, Generic[T]):
    separator: str
    
    value: T = None
    data: 'DataMapType' = None
    def __init__(self, *args, separator: str = '/', **kwargs):
        self._create_map()
        self.separator = separator
        super().__init__(*args, **kwargs)
    
    def _create_map(self) -> 'DataMapType':
        self.data: DataMapType = dict()
        return self.data
    
    def __getitem__(self, key: str, **kwargs):
        return self.get(key, **kwargs)
    def __setitem__(self, key: str, value: T, **kwargs):
        return self.set(key, value, **kwargs)
    def __delitem__(self, key: str, **kwargs):
        raise NotImplementedError("Delete operation not supported")
    def __iter__(self, **kwargs):
        return self.keys(**kwargs)
    def __contains__(self, key: str, **kwargs):
        try:
            self.get(key, **kwargs)
        except KeyError:
            return False
        else:
            return True
    def __len__(self):
        return len(list(self.items()))
    
    def get(self, key: str, default: Optional[T] = _DEFAULT_ARGUMENT, **kwargs) -> T:
        try:
            return self._get(key, **kwargs)
        except StopIteration:
            if (default is not _DEFAULT_ARGUMENT):
                return default
            else:
                raise KeyError(f"Key {key} not found")
    def add(self, key: str, value: T, **kwargs):
        return self._add(key, value, **kwargs)
    def set(self, key: str, value: T, **kwargs):
        try:
            m = self._get_map(key, **kwargs)
        except StopIteration:
            self._add(key, value, **kwargs)
        else:
            m.value = value
    
    def _add(self, key: str, value: T, **kwargs):
        return self._add_key(self._split_key(key), value, **kwargs)
    
    def _add_key(self, path: List[str], value: T, **kwargs):
        if (len(path) == 0):
            self.value = value
            return
        
        _key = path[0]
        _next_path = path[1:]
        _is_pattern = self._is_pattern(_key)
        
        if (not _is_pattern):
            self._add_key__add_value(_key, _next_path, value, **kwargs)
        else:
            self._add_key__add_value(_WILDCARD_ARGUMENT, _next_path, value, **kwargs)
    
    def _add_key__add_value(self, data_key: AnyArg, next_path: List[str], value: T, **kwargs):
        _map = self.data.get(data_key, None)
        if (_map is None):
            _map = type(self)(separator=self.separator)
            self.data[data_key] = _map
        
        _map._add_key(next_path, value, **kwargs)
    
    def _is_pattern(self, key: str) -> bool:
        return key.startswith('{') and key.endswith('}')
    
    def _split_key(self, key: str) -> List[str]:
        return key.split(self.separator)
    
    def _get(self, key: str, **kwargs) -> T:
        return self._get_map(key, **kwargs).value
    def _get_map(self, key: str, **kwargs) -> 'PathTreeMap':
        return next(self._get_subtrees(self._split_key(key), **kwargs))
    
    def _get_subtrees(self, path: List[str], **kwargs) -> Iterator['PathTreeMap']:
        if (len(path) == 0):
            yield self
            return
        
        _key = path[0]
        _next_path = path[1:]
        
        if (_key in self.data):
            yield from self._get_subtrees__try(_key, _next_path, **kwargs)
        else:
            yield from self._get_subtrees__try(_WILDCARD_ARGUMENT, _next_path, **kwargs)
    
    def _get_subtrees__try(self, data_key: AnyArg, next_path: List[str], **kwargs) -> Iterator['PathTreeMap']:
        _map = self.data.get(data_key, None)
        if (_map is not None):
            yield from _map._get_subtrees(next_path, **kwargs)
    
    def dump(self, *, indent: Union[int, str, None] = 4, level: int = 0, file: TextIO = None, **kwargs):
        if (isinstance(indent, int)):
            indent = ' ' * indent
        elif (not isinstance(indent, str)):
            raise ValueError(f"Indent must be either or int, or str; not {type(indent)}")
        
        str_output = file is None
        if (str_output):
            file = StringIO()
        
        self._dump(file=file, indent=indent, level=level, **kwargs)
        
        if (str_output):
            file.seek(0)
            return file.read()
    
    def _dump(self, *, file: TextIO, indent: str, level: int, first=True, **kwargs):
        if (self.value is not None):
            file.write(f"=> '{self.value}'")
        for key, subtree in self.data.items():
            if (key is _WILDCARD_ARGUMENT):
                key = '{argument}'
            file.write(f"\n{indent * level}'{key}':")
            subtree._dump(file=file, indent=indent, level=level + 1, first=False, **kwargs)
        
        if (first):
            file.write('\n')
    
    def keys(self, **kwargs) -> Iterator[str]:
        return self._keys(**kwargs)
    def _keys(self, **kwargs) -> Iterator[str]:
        for k, v in self._items():
            yield k
    
    def values(self, **kwargs) -> Iterator[T]:
        return self._values(**kwargs)
    def _values(self, **kwargs) -> Iterator[T]:
        for k, v in self._items():
            yield v
    
    def items(self, **kwargs) -> Iterator[Tuple[str, T]]:
        return self._items(**kwargs)
    
    def _items(self, prefix: Optional[str] = None, **kwargs) -> Iterator[Tuple[str, T]]:
        if (self.value is not None and prefix is not None):
            yield prefix, self.value
        if (prefix is not None):
            _next_prefix = prefix + self.separator
        else:
            _next_prefix = ''
        
        for key, subtree in self.data.items():
            if (key is _WILDCARD_ARGUMENT):
                key = '{argument}'
            yield from subtree._items(_next_prefix + key, **kwargs)
    
    @property
    def has_child(self) -> bool:
        return bool(self.data)
    
    def update(self, data: Mapping[str, T], **kwargs):
        for key, value in data.items():
            self.set(key, value)

DataMapType = Dict[AnyArg, PathTreeMap]

__all__ = \
[
    'AnyArg',
    'DataMapType',
    'DataType',
    'PathTreeMap',
]
__pdoc_extras__ = \
[
    'AnyArg',
    'DataMapType',
    'DataType',
]
