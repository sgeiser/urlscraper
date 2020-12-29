from typing import *

from typing.re import *

@property
def RegExpType():
    from warnings import warn
    warn("'RegExpType' is going to be deprecated. Use Pattern[str] instead", DeprecationWarning, 2)
    return Pattern[str]

JsonSerializable = Union[str, int, float, Dict[str, 'JsonSerializable'], List['JsonSerializable'], None]
Binary = Union[bytes, bytearray, None]

__all__ = \
[
    'Binary',
    'JsonSerializable',
    'RegExpType',
]
__pdoc_extras__ = \
[
    'Binary',
    'JsonSerializable',
    'RegExpType',
]
