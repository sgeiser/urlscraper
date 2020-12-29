from typing import *

K = TypeVar('K')
V = TypeVar('V')

def dict_filter_out(d: Dict[K, Optional[V]]) -> Dict[K, V]:
    return dict(dict_filter_out_iter(d))

def dict_filter_out_iter(d: Dict[K, Optional[V]]) -> Iterator[Tuple[K, V]]:
    for k, v in d.items():
        if (v is not None):
            yield k, filter_out_smart(v)

def filter_out_smart(c: V) -> V:
    if (isinstance(c, dict)):
        return dict_filter_out(c)
    elif (isinstance(c, list)):
        return list_filter_out(c)
    else:
        return c

def list_filter_out(l: List[Optional[V]]) -> List[V]:
    return list(list_filter_out_iter(l))

def list_filter_out_iter(l: List[Optional[V]]) -> Iterator[V]:
    for v in l:
        if (v is not None):
            yield filter_out_smart(v)


__all__ = \
[
    'dict_filter_out',
    'dict_filter_out_iter',
    'filter_out_smart',
    'list_filter_out',
    'list_filter_out_iter',
]
