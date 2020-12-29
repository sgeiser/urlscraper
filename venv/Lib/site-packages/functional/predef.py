from typing import *

T = TypeVar('T')
def identity(x: T) -> T:
    return x

__all__ = \
[
    'identity',
]
