from abc import ABC
from typing import TypeVar, Generic, Callable, Any

from .monads import *

T = TypeVar('T')
R = TypeVar('R')
K = TypeVar('K', bound=Monad)
class Container(Monad[K, T], Functor[K, T], Generic[K, T], ABC):
    empty: K
    
    @property
    def is_empty(self) -> bool:
        raise NotImplementedError
    
    @property
    def non_empty(self) -> bool:
        raise NotImplementedError
    
    def foreach(self, f: Callable[[T], Any]) -> None:
        raise NotImplementedError


__all__ = \
[
    'Container',
]
