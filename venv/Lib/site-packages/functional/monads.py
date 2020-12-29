from abc import ABC
from typing import *

T = TypeVar('T')
R = TypeVar('R')
K = TypeVar('K', bound='Functor')
class Functor(Generic[K, T], ABC):
    def map(self: K, f: Callable[[T], R]) -> K:
        raise NotImplementedError
del K

K = TypeVar('K', bound='Monad')
class Monad(Generic[K, T], ABC):
    def flat_map(self, f: Callable[[T], K]) -> K:
        raise NotImplementedError
    @property
    def flatten(self) -> T:
        raise NotImplementedError
del K

__all__ = \
[
    'Monad',
    'Functor',
]
